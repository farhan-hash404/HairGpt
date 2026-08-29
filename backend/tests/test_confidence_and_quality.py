from __future__ import annotations

from app.cv.mock.quality import MockImageQualityGate
from app.cv.types import ConfidenceScore, ImageInput, Observation
from app.services.orchestrator import compute_overall_confidence


def test_overall_confidence_never_exceeds_weakest_stage():
    obs = [
        Observation("a", ConfidenceScore(0.9, "", "")),
        Observation("b", ConfidenceScore(0.8, "", "")),
    ]
    # Even with high observation confidence, a weak quality stage caps it.
    overall = compute_overall_confidence(obs, min_quality_conf=0.3)
    assert overall <= 0.3


def test_overall_confidence_zero_without_observations():
    assert compute_overall_confidence([], 0.9) == 0.0


def test_quality_gate_returns_report_with_confidence():
    gate = MockImageQualityGate()
    report = gate.assess(ImageInput(data=b"not-an-image"), "front_hairline", "hair")
    assert 0.0 <= report.confidence.value <= 1.0
    assert isinstance(report.overall_pass, bool)
    assert report.is_mock is True  # never claims to be validated


def test_quality_gate_flags_are_actionable():
    gate = MockImageQualityGate()
    report = gate.assess(ImageInput(data=b"x"), "front_hairline", "hair")
    # If it failed, there must be human-actionable retake guidance.
    if not report.overall_pass:
        assert len(report.retake_guidance) == len(report.reasons) or report.retake_guidance
