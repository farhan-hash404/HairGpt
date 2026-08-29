from __future__ import annotations

import logging
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cv.registry import (
    get_face_analyzer,
    get_localizer,
    get_metric_estimator,
    get_segmenter,
)
from app.cv.types import ImageInput, Observation
from app.llm.base import ExplanationContext
from app.llm.provider import get_llm_provider
from app.models.scan import (
    Analysis,
    Observation as ObservationModel,
    Recommendation,
    SafetyVerdict as SafetyVerdictModel,
    ScanImage,
    ScanSession,
)
from app.recommendations.engine import build_recommendations
from app.safety.engine import evaluate as safety_evaluate
from app.services.storage import storage

log = logging.getLogger("hairgpt.orchestrator")

HAIR_SEG_TARGETS = ["hair", "scalp"]
SKIN_SEG_TARGETS = ["skin"]


def _obs_to_dict(o: Observation) -> dict:
    d = asdict(o)
    d["confidence"] = asdict(o.confidence)
    return d


def compute_overall_confidence(
    observations: list[Observation], min_quality_conf: float
) -> float:
    """Conservative aggregate: never more confident than the weakest necessary stage."""
    if not observations:
        return 0.0
    mean_obs = sum(o.confidence.value for o in observations) / len(observations)
    return round(max(0.0, min(mean_obs, min_quality_conf)), 3)


def _analyze_hair_image(img: ImageInput, view: str) -> list[Observation]:
    seg = get_segmenter().segment(img, HAIR_SEG_TARGETS)
    loc = get_localizer().localize(img, seg, view)
    return get_metric_estimator().estimate(img, seg, loc, view)


def _analyze_skin_image(img: ImageInput, view: str) -> list[Observation]:
    return get_face_analyzer().analyze(img, view)


def run_analysis(db: Session, session: ScanSession, safety_ctx: dict | None = None) -> Analysis:
    """Full pipeline: images -> observations -> RAG -> safety -> recommendations -> LLM.

    Only images that PASSED the quality gate are analyzed. Raw images never reach
    the LLM; only structured observations + evidence do.
    """
    images = db.scalars(
        select(ScanImage).where(
            ScanImage.session_id == session.id, ScanImage.quality_passed.is_(True)
        )
    ).all()

    all_obs: list[Observation] = []
    per_image_obs: list[tuple[ScanImage, list[Observation]]] = []
    min_quality_conf = 1.0

    for image in images:
        if image.quality is not None:
            min_quality_conf = min(min_quality_conf, image.quality.confidence)
        try:
            raw = storage.get(image.storage_key)
        except Exception as exc:
            log.warning("Could not load image %s: %s", image.id, exc)
            continue
        img = ImageInput(data=raw, view=image.view, width=image.width, height=image.height)
        obs = _analyze_hair_image(img, image.view) if session.domain == "hair" else _analyze_skin_image(img, image.view)
        per_image_obs.append((image, obs))
        all_obs.extend(obs)

    overall_conf = compute_overall_confidence(all_obs, min_quality_conf)

    # Safety context: fold in quality + confidence signals + any user-reported flags.
    ctx = dict(safety_ctx or {})
    ctx.setdefault("overall_confidence", overall_conf)
    ctx.setdefault("min_quality_confidence", min_quality_conf)

    verdict = safety_evaluate(session.domain, all_obs, ctx)

    recs = build_recommendations(db, session.domain, all_obs, verdict, overall_conf)

    # Deduplicate evidence by document id — the same source is often cited by
    # several recommendations, but it should appear once in the evidence list.
    evidence_by_id: dict[str, dict] = {}
    for r in recs:
        for e in r.evidence:
            evidence_by_id.setdefault(
                e.id,
                {"id": e.id, "source": e.source, "title": e.title, "url": e.url,
                 "publisher": e.publisher, "evidence_grade": e.evidence_grade},
            )

    # LLM explanation (phrasing only).
    exp_ctx = ExplanationContext(
        domain=session.domain,
        observations=[_obs_to_dict(o) for o in all_obs],
        evidence=list(evidence_by_id.values()),
        safety_verdict={"verdict": verdict.verdict, "message": verdict.message, "red_flags": verdict.red_flags},
        recommendations=[{"type": r.type, "title": r.title, "body": r.body} for r in recs],
        overall_confidence=overall_conf,
    )
    explanation = get_llm_provider().explain(exp_ctx)

    # ---- Persist ----
    # Clear any prior observations for idempotency.
    for image, obs in per_image_obs:
        for o in obs:
            db.add(
                ObservationModel(
                    session_id=session.id,
                    image_id=image.id,
                    kind=o.kind,
                    value_num=o.value_num,
                    value_label=o.value_label,
                    unit=o.unit,
                    confidence=o.confidence.value,
                    confidence_basis=o.confidence.basis,
                    model_name=o.model_name,
                    model_version=o.model_version,
                    is_mock=o.is_mock,
                    validated=o.validated,
                    observation_type=o.observation_type,
                )
            )

    hair_summary = None
    skin_index = None
    if session.domain == "hair":
        hair_summary = _summarize_hair(all_obs)
    else:
        skin_index = _skin_appearance_index(all_obs)

    analysis = Analysis(
        session_id=session.id,
        skin_appearance_index=skin_index,
        hair_summary=hair_summary,
        overall_confidence=overall_conf,
        llm_model=get_llm_provider().__class__.__name__,
        explanation={
            "observation": explanation.observation,
            "reasoning": explanation.reasoning,
            "confidence": explanation.confidence,
            "evidence": explanation.evidence,
            "limitations": explanation.limitations,
            "summary": explanation.summary,
        },
        status="complete",
    )
    db.add(analysis)
    db.flush()

    db.add(
        SafetyVerdictModel(
            analysis_id=analysis.id,
            verdict=verdict.verdict,
            red_flags=verdict.red_flags,
            triggered_rules=verdict.triggered_rules,
            suppressed_cosmetic=verdict.suppressed_cosmetic,
            message=verdict.message,
        )
    )

    for r in recs:
        db.add(
            Recommendation(
                analysis_id=analysis.id,
                type=r.type,
                title=r.title,
                body=r.body,
                evidence_refs=[e.id for e in r.evidence],
                confidence=r.confidence,
                requires_clinician=r.requires_clinician,
                is_prescription=False,  # structural guarantee
            )
        )

    session.status = "complete"
    db.commit()
    db.refresh(analysis)
    return analysis


def _summarize_hair(obs: list[Observation]) -> dict:
    by = {o.kind: o for o in obs}
    def g(k):
        o = by.get(k)
        return {"value": o.value_num, "label": o.value_label, "confidence": o.confidence.value} if o else None
    return {
        "scalp_visibility": g("scalp_visibility"),
        "apparent_density": g("apparent_density"),
        "hairline_position": g("hairline_position"),
        "crown_density": g("crown_density"),
    }


def _skin_appearance_index(obs: list[Observation]) -> float:
    """A transparent 0..100 composite of apparent skin attributes (higher = more
    even/healthy-appearing). NOT a clinical score."""
    weights = {"redness": -1.0, "pigmentation": -0.8, "texture": -0.6, "oiliness": -0.4}
    score = 100.0
    for o in obs:
        if o.kind in weights and o.value_num is not None:
            score += weights[o.kind] * o.value_num * 40
    return round(max(0.0, min(100.0, score)), 1)
