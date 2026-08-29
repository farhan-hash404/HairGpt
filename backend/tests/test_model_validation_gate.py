"""The validation gate.

The most important property of "adding real models" to a medical product is not
the model — it is the machinery that stops an unvalidated model from being
presented as validated. These tests exist to make that impossible to regress.
"""
from __future__ import annotations

import json

import pytest

from app.cv.manifest import (
    MIN_SAMPLES_PER_GROUP,
    ModelSpec,
    ValidationRecord,
    load_manifest,
    validation_passes,
)
from app.eval.gate import build_validation_record
from app.eval.metrics import SUBGROUP_AXES, Sample, evaluate, expected_calibration_error


def _passing_record(**overrides) -> ValidationRecord:
    data = {
        "evaluated_at": "2026-01-01T00:00:00Z",
        "dataset_id": "eval-1",
        "overall_score": 0.88,
        "worst_group_score": 0.84,
        "worst_best_gap": 0.06,
        "calibration_error": 0.04,
        "subgroup_axes": list(SUBGROUP_AXES),
        "min_group_samples": 100,
        "passed": True,
    }
    data.update(overrides)
    return ValidationRecord(**data)


# --- the gate itself -------------------------------------------------------

def test_a_good_record_passes():
    passed, failures = validation_passes(_passing_record())
    assert passed, failures


def test_missing_evaluation_is_rejected():
    passed, failures = validation_passes(ValidationRecord())
    assert not passed
    assert any("no evaluation record" in f for f in failures)


def test_weak_worst_group_is_rejected_despite_good_aggregate():
    """The exact failure this harness exists to catch."""
    passed, failures = validation_passes(
        _passing_record(overall_score=0.90, worst_group_score=0.55, worst_best_gap=0.35)
    )
    assert not passed
    assert any("worst-group score" in f for f in failures)


def test_large_subgroup_gap_is_rejected():
    passed, failures = validation_passes(_passing_record(worst_best_gap=0.40))
    assert not passed
    assert any("gap" in f for f in failures)


def test_overconfident_model_is_rejected():
    passed, failures = validation_passes(_passing_record(calibration_error=0.35))
    assert not passed
    assert any("calibration" in f for f in failures)


@pytest.mark.parametrize("axis", SUBGROUP_AXES)
def test_every_subgroup_axis_is_mandatory(axis):
    """Aggregate-only reporting must never be sufficient."""
    axes = [a for a in SUBGROUP_AXES if a != axis]
    passed, failures = validation_passes(_passing_record(subgroup_axes=axes))
    assert not passed
    assert any(axis in f for f in failures)


def test_thin_subgroup_coverage_is_rejected():
    passed, failures = validation_passes(
        _passing_record(min_group_samples=MIN_SAMPLES_PER_GROUP - 1)
    )
    assert not passed
    assert any("samples" in f for f in failures)


# --- tamper resistance -----------------------------------------------------

def test_hand_editing_passed_cannot_promote_a_failing_model(tmp_path):
    """A manifest claiming success while its metrics say otherwise is rejected.

    Promotion is re-derived from the recorded numbers on every load, so flipping
    one boolean by hand achieves nothing.
    """
    manifest = {
        "models": [
            {
                "capability": "segmenter",
                "name": "sneaky",
                "version": "1.0.0",
                "checkpoint": "x.pt",
                "validation": {
                    "evaluated_at": "2026-01-01T00:00:00Z",
                    "dataset_id": "eval-1",
                    "overall_score": 0.95,
                    "worst_group_score": 0.20,  # terrible for one subgroup
                    "worst_best_gap": 0.70,
                    "calibration_error": 0.02,
                    "subgroup_axes": list(SUBGROUP_AXES),
                    "min_group_samples": 100,
                    "passed": True,  # <- the lie
                },
            }
        ]
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    specs = load_manifest(str(tmp_path))
    assert specs["segmenter"].is_validated is False


def test_missing_manifest_is_not_an_error(tmp_path):
    """No manifest simply means no real models; the registry falls back to mock."""
    assert load_manifest(str(tmp_path)) == {}


def test_malformed_manifest_falls_back_rather_than_crashing(tmp_path):
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
    assert load_manifest(str(tmp_path)) == {}


def test_shipped_example_manifest_is_unvalidated():
    """The example must never ship claiming validation."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "models" / "manifest.example.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data["models"]:
        spec = ModelSpec(
            capability=entry["capability"],
            name=entry["name"],
            version=entry["version"],
            checkpoint=entry["checkpoint"],
            validation=ValidationRecord.from_dict(entry["validation"]),
        )
        assert spec.is_validated is False


# --- evaluation metrics ----------------------------------------------------

def _sample(score: float, fitz: str = "III", confidence: float = 0.8, correct: bool = True) -> Sample:
    return Sample(
        sample_id="s", score=score, confidence=confidence, correct=correct,
        fitzpatrick=fitz, age_group="30-39", sex="female",
        device_make="Apple", lighting="daylight", geography="EU",
    )


def test_evaluation_surfaces_the_worst_subgroup():
    samples = [_sample(0.9, "I") for _ in range(50)] + [_sample(0.4, "VI") for _ in range(50)]
    result = evaluate(samples)
    assert result.worst_group.group == "VI"
    assert result.worst_group.mean_score == pytest.approx(0.4, abs=0.01)
    # The aggregate alone would look mediocre-but-workable; the gap is the story.
    assert result.worst_best_gap == pytest.approx(0.5, abs=0.01)


def test_perfectly_calibrated_model_has_near_zero_ece():
    # 80% confident and right 80% of the time.
    samples = [_sample(0.9, confidence=0.8, correct=i < 80) for i in range(100)]
    assert expected_calibration_error(samples) < 0.05


def test_overconfident_model_has_high_ece():
    # 99% confident but right only half the time.
    samples = [_sample(0.9, confidence=0.99, correct=i < 50) for i in range(100)]
    assert expected_calibration_error(samples) > 0.4


def test_built_record_agrees_with_the_gate():
    """The writer and the reader must never disagree about promotion."""
    samples = [_sample(0.9, f, confidence=0.8, correct=i % 5 != 0) for f in ["I", "VI"] for i in range(100)]
    result = evaluate(samples)
    record = build_validation_record(result, "eval-x")
    assert record.passed == validation_passes(record)[0]
