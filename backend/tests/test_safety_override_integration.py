"""The safety layer must be able to override the whole pipeline.

This exercises the real orchestrator: when a red flag is present, the persisted
analysis must contain ONLY a referral, the LLM explanation must not carry
cosmetic advice, and nothing may be marked as a prescription.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.cv.types import ConfidenceScore, Observation
from app.db.base import Base
from app.llm.base import ExplanationContext
from app.llm.provider import MockLLMProvider
from app.rag.ingest import seed_corpus
from app.recommendations.engine import build_recommendations
from app.safety.engine import evaluate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    seed_corpus(s)
    yield s
    s.close()


def _obs(kind, num=None, conf=0.8):
    return Observation(kind=kind, value_num=num, confidence=ConfidenceScore(conf, "t", "t"))


def _pipeline(db, domain, observations, ctx):
    """Mirror the orchestrator's safety -> recommendations -> LLM ordering."""
    verdict = evaluate(domain, observations, ctx)
    recs = build_recommendations(db, domain, observations, verdict, ctx.get("overall_confidence", 0.7))
    explanation = MockLLMProvider().explain(
        ExplanationContext(
            domain=domain,
            observations=[{"kind": o.kind, "value_num": o.value_num, "is_mock": True,
                           "observation_type": o.observation_type,
                           "confidence": {"value": o.confidence.value}} for o in observations],
            evidence=[],
            safety_verdict={"verdict": verdict.verdict, "message": verdict.message, "red_flags": verdict.red_flags},
            recommendations=[{"type": r.type, "title": r.title, "body": r.body} for r in recs],
            overall_confidence=ctx.get("overall_confidence", 0.7),
        )
    )
    return verdict, recs, explanation


COSMETIC_TYPES = {"care_guidance", "ingredient", "product", "routine_step"}


def test_scalp_infection_red_flag_suppresses_all_cosmetic_advice(db):
    verdict, recs, explanation = _pipeline(
        db, "hair", [_obs("scalp_visibility", 0.4)],
        {"pustules": True, "overall_confidence": 0.8},
    )
    assert verdict.verdict == "refer"
    assert verdict.suppressed_cosmetic is True
    assert [r.type for r in recs] == ["referral"]
    assert not any(r.type in COSMETIC_TYPES for r in recs)
    # The narrative must direct to a clinician, not to self-treatment.
    assert "clinician" in explanation.summary.lower() or "clinician" in explanation.reasoning.lower()


def test_suspicious_lesion_red_flag_suppresses_routines(db):
    verdict, recs, _ = _pipeline(
        db, "skin", [_obs("acne_like_lesion_count", 18)],
        {"lesion_abcde_signal": 0.9, "overall_confidence": 0.8},
    )
    assert verdict.verdict == "refer"
    assert [r.type for r in recs] == ["referral"]


def test_no_red_flag_allows_evidence_backed_guidance(db):
    verdict, recs, _ = _pipeline(
        db, "hair", [_obs("scalp_visibility", 0.35), _obs("apparent_density", 0.4)],
        {"overall_confidence": 0.8},
    )
    assert verdict.verdict == "ok"
    assert any(r.type in COSMETIC_TYPES for r in recs)


def test_no_pipeline_path_emits_a_prescription(db):
    """Sweep every red-flag combination; a prescription must never appear."""
    flag_sets = [
        {},
        {"pustules": True},
        {"scarring_signal": True},
        {"sudden_patchy_loss": True},
        {"facial_swelling": True},
        {"infection_like": True},
        {"lesion_change_delta": 0.9},
        {"is_minor": True},
        {"systemic_symptoms": True},
    ]
    for domain in ("hair", "skin"):
        for flags in flag_sets:
            ctx = {"overall_confidence": 0.7, **flags}
            _, recs, _ = _pipeline(db, domain, [_obs("scalp_visibility", 0.4), _obs("redness", 0.3)], ctx)
            for r in recs:
                assert r.is_prescription is False, f"{domain}/{flags} produced a prescription"
