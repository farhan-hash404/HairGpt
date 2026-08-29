"""Safety engine is the most important guarantee — it can override the LLM."""
from __future__ import annotations

from app.cv.types import ConfidenceScore, Observation
from app.safety.engine import evaluate


def _obs(kind, num=None, conf=0.8):
    return Observation(kind=kind, value_num=num, confidence=ConfidenceScore(conf, "test", "t"))


def test_high_confidence_clean_hair_scan_is_ok():
    obs = [_obs("scalp_visibility", 0.15), _obs("apparent_density", 0.7)]
    v = evaluate("hair", obs, {"overall_confidence": 0.8, "min_quality_confidence": 0.8})
    assert v.verdict == "ok"
    assert v.suppressed_cosmetic is False


def test_scarring_signal_forces_referral_and_suppresses_cosmetic():
    v = evaluate("hair", [_obs("scalp_visibility", 0.2)], {"scarring_signal": True, "overall_confidence": 0.8})
    assert v.verdict == "refer"
    assert v.suppressed_cosmetic is True
    assert "hair_scarring_alopecia_signal" in v.red_flags


def test_suspicious_lesion_forces_referral_skin():
    v = evaluate("skin", [_obs("acne_like_lesion_count", 20)], {"overall_confidence": 0.8})
    assert v.verdict == "refer"
    assert v.suppressed_cosmetic is True


def test_facial_swelling_forces_referral():
    v = evaluate("skin", [_obs("redness", 0.1)], {"facial_swelling": True})
    assert v.verdict == "refer"


def test_low_confidence_forces_caution():
    v = evaluate("hair", [_obs("scalp_visibility", 0.2, conf=0.2)], {"overall_confidence": 0.3})
    assert v.verdict == "caution"


def test_fail_safe_on_error_when_strict(monkeypatch):
    import app.safety.engine as eng

    def boom(*a, **k):
        raise RuntimeError("bad")

    monkeypatch.setattr(eng, "run_rules", boom)
    v = eng.evaluate("hair", [], {})
    assert v.verdict == "caution"  # fail-safe, not "ok"
