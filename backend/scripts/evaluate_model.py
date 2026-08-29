"""Run a stratified evaluation and write the validation record into the manifest.

    python -m scripts.evaluate_model --results results.json --model hair-seg
    python -m scripts.evaluate_model --demo            # synthetic walkthrough

`results.json` is produced by your own inference run and holds one entry per
evaluated sample:

    {"dataset_id": "eval-2026-Q1",
     "samples": [
       {"sample_id": "0001", "score": 0.86, "confidence": 0.81, "correct": true,
        "fitzpatrick": "III", "age_group": "30-39", "sex": "female",
        "device_make": "Apple", "lighting": "daylight", "geography": "EU"},
       ...
     ]}

Writing the record is the ONLY supported way to mark a model validated. The
gate re-derives pass/fail from the metrics, so editing the manifest by hand
cannot promote a failing model.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from app.eval.gate import build_validation_record, format_report
from app.eval.metrics import Sample, evaluate

REQUIRED_FIELDS = {
    "sample_id", "score", "confidence", "correct",
    "fitzpatrick", "age_group", "sex", "device_make", "lighting", "geography",
}


def load_samples(path: Path) -> tuple[str, list[Sample]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_samples = payload.get("samples", [])
    if not raw_samples:
        sys.exit("No samples found in results file.")

    samples: list[Sample] = []
    for index, entry in enumerate(raw_samples):
        missing = REQUIRED_FIELDS - set(entry)
        if missing:
            sys.exit(
                f"Sample {index} is missing required fields: {', '.join(sorted(missing))}.\n"
                "Every sample must carry full subgroup metadata — a dataset that cannot "
                "say who it covers cannot support a fairness claim."
            )
        samples.append(Sample(**{k: entry[k] for k in REQUIRED_FIELDS}))
    return payload.get("dataset_id", path.stem), samples


def synthesize_demo_samples(biased: bool) -> list[Sample]:
    """Synthetic samples for demonstrating the gate.

    `biased=True` reproduces the failure this whole harness exists to catch: a
    model with a strong aggregate score that performs materially worse on darker
    skin tones. The aggregate looks fine; the gate still refuses it.
    """
    rng = random.Random(11)
    fitzpatricks = ["I", "II", "III", "IV", "V", "VI"]
    samples: list[Sample] = []

    for index in range(600):
        skin = fitzpatricks[index % len(fitzpatricks)]
        base = 0.88
        if biased and skin in ("V", "VI"):
            base = 0.62  # the hidden failure
        score = min(1.0, max(0.0, rng.gauss(base, 0.05)))

        # A well-calibrated model: stated confidence matches how often it is
        # actually right, so ECE is near zero and the subgroup gap is the only
        # thing the gate can object to.
        confidence = min(0.99, max(0.05, rng.gauss(0.85, 0.08)))
        correct = rng.random() < confidence

        samples.append(
            Sample(
                sample_id=f"demo-{index:04d}",
                score=score,
                confidence=round(confidence, 3),
                correct=correct,
                fitzpatrick=skin,
                age_group=["18-29", "30-39", "40-49", "50-59", "60+"][index % 5],
                sex=["female", "male", "other"][index % 3],
                device_make=["Apple", "Samsung", "Google", "Xiaomi"][index % 4],
                lighting=["daylight", "indoor_warm", "indoor_cool", "low"][index % 4],
                geography=["EU", "NA", "APAC", "AFR"][index % 4],
            )
        )
    return samples


def write_record_into_manifest(manifest_path: Path, model_name: str, record) -> None:
    if not manifest_path.exists():
        sys.exit(f"Manifest not found at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("models", []):
        if entry.get("name") == model_name:
            entry["validation"] = {
                "evaluated_at": record.evaluated_at,
                "dataset_id": record.dataset_id,
                "overall_score": record.overall_score,
                "worst_group_score": record.worst_group_score,
                "worst_best_gap": record.worst_best_gap,
                "calibration_error": record.calibration_error,
                "subgroup_axes": record.subgroup_axes,
                "min_group_samples": record.min_group_samples,
                "passed": record.passed,
                "failures": record.failures,
            }
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(f"\nWrote validation record for '{model_name}' into {manifest_path}")
            return
    sys.exit(f"No model named '{model_name}' in the manifest.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, help="JSON file of per-sample evaluation results")
    parser.add_argument("--model", help="Model name in the manifest to record against")
    parser.add_argument("--manifest", type=Path, default=Path("models/manifest.json"))
    parser.add_argument("--demo", action="store_true", help="Run a synthetic demonstration")
    parser.add_argument(
        "--demo-biased", action="store_true",
        help="Synthetic run where the model underperforms on Fitzpatrick V-VI",
    )
    args = parser.parse_args()

    if args.demo or args.demo_biased:
        dataset_id = "synthetic-demo"
        samples = synthesize_demo_samples(biased=args.demo_biased)
        model_name = args.model or "demo-model"
    elif args.results:
        dataset_id, samples = load_samples(args.results)
        model_name = args.model or args.results.stem
    else:
        parser.error("Provide --results, or --demo / --demo-biased")

    result = evaluate(samples)
    record = build_validation_record(result, dataset_id)
    print(format_report(result, record, model_name))

    if args.results and args.model:
        write_record_into_manifest(args.manifest, args.model, record)

    sys.exit(0 if record.passed else 1)


if __name__ == "__main__":
    main()
