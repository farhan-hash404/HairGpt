from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.cv.types import ConfidenceScore, Observation
from app.db.base import Base
from app.rag.ingest import seed_corpus
from app.recommendations.engine import build_recommendations
from app.safety.engine import evaluate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    seed_corpus(s)
    yield s
    s.close()


def _obs(kind, num, conf=0.7):
    return Observation(kind=kind, value_num=num, confidence=ConfidenceScore(conf, "t", "t"))


def test_no_recommendation_is_ever_a_prescription(db):
    obs = [_obs("scalp_visibility", 0.4), _obs("apparent_density", 0.3)]
    verdict = evaluate("hair", obs, {"overall_confidence": 0.7})
    recs = build_recommendations(db, "hair", obs, verdict, 0.7)
    assert recs, "expected some recommendations"
    for r in recs:
        assert r.is_prescription is False


def test_referral_suppresses_all_cosmetic_recs(db):
    obs = [_obs("scalp_visibility", 0.2)]
    verdict = evaluate("hair", obs, {"scarring_signal": True, "overall_confidence": 0.7})
    recs = build_recommendations(db, "hair", obs, verdict, 0.7)
    assert len(recs) == 1
    assert recs[0].type == "referral"


def test_care_guidance_is_evidence_backed(db):
    obs = [_obs("scalp_visibility", 0.4), _obs("apparent_density", 0.3)]
    verdict = evaluate("hair", obs, {"overall_confidence": 0.7})
    recs = build_recommendations(db, "hair", obs, verdict, 0.7)
    for r in recs:
        if r.type in ("care_guidance", "ingredient"):
            assert r.evidence, f"{r.title} must cite evidence"
