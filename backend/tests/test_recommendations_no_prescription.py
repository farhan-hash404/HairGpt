from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.cv.types import ConfidenceScore, Observation
from app.db.base import Base
from app.rag.ingest import ensure_evidence
from app.recommendations.engine import EVIDENCE_EXEMPT, build_recommendations
from app.safety.engine import evaluate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    ensure_evidence(s)
    yield s
    s.close()


def _obs(kind, num, conf=0.7, label=None):
    return Observation(kind=kind, value_num=num, value_label=label, confidence=ConfidenceScore(conf, "t", "t"))


THINNING = [_obs("scalp_visibility", 0.4), _obs("apparent_density", 0.3, label="apparent sparse")]


def test_no_recommendation_is_ever_a_prescription(db):
    verdict = evaluate("hair", THINNING, {"overall_confidence": 0.7})
    recs = build_recommendations(db, "hair", THINNING, verdict, 0.7)
    assert recs, "expected some recommendations"
    assert all(r.is_prescription is False for r in recs)


def test_referral_suppresses_all_cosmetic_recs(db):
    obs = [_obs("scalp_visibility", 0.2)]
    verdict = evaluate("hair", obs, {"scarring_signal": True, "overall_confidence": 0.7})
    recs = build_recommendations(db, "hair", obs, verdict, 0.7)
    assert [r.type for r in recs] == ["referral"]


def test_every_non_exempt_recommendation_cites_evidence(db):
    """The grounding contract: no medical claim without a source."""
    signals = {"iron_deficiency": True, "thyroid_condition": True, "scalp_itch": True}
    verdict = evaluate("hair", THINNING, {"overall_confidence": 0.7})
    recs = build_recommendations(db, "hair", THINNING, verdict, 0.7, signals=signals)
    for r in recs:
        if r.type not in EVIDENCE_EXEMPT:
            assert r.evidence, f"{r.rule_id} has no evidence"
            assert all(e.url and e.license for e in r.evidence), f"{r.rule_id} cites untraceable evidence"


def test_history_signals_trigger_their_rules(db):
    verdict = evaluate("hair", THINNING, {"overall_confidence": 0.7})
    plain = {r.rule_id for r in build_recommendations(db, "hair", THINNING, verdict, 0.7)}
    flagged = {r.rule_id for r in build_recommendations(
        db, "hair", THINNING, verdict, 0.7, signals={"iron_deficiency": True, "thyroid_condition": True})}
    assert "iron" not in plain and "iron" in flagged
    assert "thyroid" not in plain and "thyroid" in flagged


def test_patterned_thinning_rules_only_fire_on_thinning(db):
    healthy = [_obs("scalp_visibility", 0.1), _obs("apparent_density", 0.8, label="apparent dense")]
    verdict = evaluate("hair", healthy, {"overall_confidence": 0.7})
    ids = {r.rule_id for r in build_recommendations(db, "hair", healthy, verdict, 0.7)}
    assert "patterned-options" not in ids and "minoxidil-stop-signs" not in ids


def test_caution_adds_a_monitoring_step_that_survives_grounding(db):
    """Regression: the old engine appended "monitor and re-scan" without evidence
    and then deleted it in its own grounding filter, so it never appeared."""
    verdict = evaluate("hair", THINNING, {"overall_confidence": 0.3})
    assert verdict.verdict == "caution"
    recs = build_recommendations(db, "hair", THINNING, verdict, 0.3)
    assert any(r.type == "monitoring" for r in recs)


def test_prescription_drugs_only_appear_in_clinician_discussion(db):
    verdict = evaluate("hair", THINNING, {"overall_confidence": 0.7})
    for r in build_recommendations(db, "hair", THINNING, verdict, 0.7):
        if "finasteride" in r.body.lower():
            assert r.type == "clinician_discussion_point" and r.requires_clinician
