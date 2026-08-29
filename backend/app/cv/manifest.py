from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("hairgpt.cv.manifest")

# Subgroups that MUST be reported separately before any model is considered
# validated. Aggregate accuracy is not an acceptable substitute — a model can
# look excellent overall while failing badly for one skin tone or one camera.
REQUIRED_SUBGROUP_AXES = frozenset(
    {"fitzpatrick", "age_group", "sex", "device_make", "lighting", "geography"}
)

# Promotion thresholds. Deliberately conservative: the cost of a confidently
# wrong reading in a health context is far higher than the cost of saying
# "not validated".
MIN_WORST_GROUP_SCORE = 0.70
MAX_WORST_BEST_GAP = 0.15
MAX_CALIBRATION_ERROR = 0.10
MIN_SAMPLES_PER_GROUP = 30


@dataclass
class ValidationRecord:
    """The evidence that a model may be presented as validated.

    Produced by the evaluation harness (`app.eval`), never written by hand.
    """

    evaluated_at: str = ""
    dataset_id: str = ""
    overall_score: float = 0.0
    worst_group_score: float = 0.0
    worst_best_gap: float = 1.0
    calibration_error: float = 1.0
    subgroup_axes: list[str] = field(default_factory=list)
    min_group_samples: int = 0
    passed: bool = False
    failures: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationRecord":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


@dataclass
class ModelSpec:
    """One entry in the model manifest."""

    capability: str
    name: str
    version: str
    checkpoint: str
    architecture: str = ""
    input_size: int = 512
    labels: list[str] = field(default_factory=list)
    model_card: str = ""
    validation: ValidationRecord = field(default_factory=ValidationRecord)

    @property
    def is_validated(self) -> bool:
        """A model is validated ONLY if a passing evaluation record says so.

        This re-checks the thresholds rather than trusting `passed` alone, so a
        hand-edited manifest cannot promote a model by flipping one boolean.
        """
        return validation_passes(self.validation)[0]


def validation_passes(record: ValidationRecord) -> tuple[bool, list[str]]:
    """Re-derive the pass/fail decision from the recorded metrics.

    Returns (passed, reasons_for_failure). Called both when writing a record and
    when reading one back, so the two can never disagree.
    """
    failures: list[str] = []

    if not record.evaluated_at or not record.dataset_id:
        failures.append("no evaluation record")
    missing_axes = REQUIRED_SUBGROUP_AXES - set(record.subgroup_axes)
    if missing_axes:
        failures.append(f"missing subgroup axes: {', '.join(sorted(missing_axes))}")
    if record.min_group_samples < MIN_SAMPLES_PER_GROUP:
        failures.append(
            f"smallest subgroup has {record.min_group_samples} samples "
            f"(need >= {MIN_SAMPLES_PER_GROUP})"
        )
    if record.worst_group_score < MIN_WORST_GROUP_SCORE:
        failures.append(
            f"worst-group score {record.worst_group_score:.3f} "
            f"below {MIN_WORST_GROUP_SCORE}"
        )
    if record.worst_best_gap > MAX_WORST_BEST_GAP:
        failures.append(
            f"worst-to-best gap {record.worst_best_gap:.3f} exceeds {MAX_WORST_BEST_GAP}"
        )
    if record.calibration_error > MAX_CALIBRATION_ERROR:
        failures.append(
            f"calibration error {record.calibration_error:.3f} exceeds {MAX_CALIBRATION_ERROR}"
        )

    return (not failures), failures


# Cache keyed by (path, mtime) so the manifest is parsed once and its warnings
# are logged once, while an edited file is still picked up without a restart.
_manifest_cache: dict[tuple[str, float], dict[str, "ModelSpec"]] = {}


def clear_manifest_cache() -> None:
    _manifest_cache.clear()


def load_manifest(model_dir: str) -> dict[str, ModelSpec]:
    """Read `<model_dir>/manifest.json` into ModelSpecs keyed by capability.

    A missing or malformed manifest is NOT an error — it simply means no real
    models are configured, and the registry falls back to mock.
    """
    path = Path(model_dir) / "manifest.json"
    if not path.exists():
        return {}

    try:
        cache_key = (str(path.resolve()), path.stat().st_mtime)
        if cache_key in _manifest_cache:
            return _manifest_cache[cache_key]
    except OSError:
        cache_key = None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("model manifest at %s is unreadable (%s); using mock", path, exc)
        return {}

    specs: dict[str, ModelSpec] = {}
    for entry in raw.get("models", []):
        try:
            spec = ModelSpec(
                capability=entry["capability"],
                name=entry["name"],
                version=entry["version"],
                checkpoint=entry["checkpoint"],
                architecture=entry.get("architecture", ""),
                input_size=int(entry.get("input_size", 512)),
                labels=list(entry.get("labels", [])),
                model_card=entry.get("model_card", ""),
                validation=ValidationRecord.from_dict(entry.get("validation", {})),
            )
        except KeyError as exc:
            log.warning("manifest entry missing %s; skipping", exc)
            continue

        passed, failures = validation_passes(spec.validation)
        if not passed:
            log.warning(
                "CV model %s@%s is NOT validated (%s). It may still run, but its "
                "output will be labelled unvalidated.",
                spec.name, spec.version, "; ".join(failures),
            )
        specs[spec.capability] = spec

    if cache_key is not None:
        _manifest_cache[cache_key] = specs
    return specs
