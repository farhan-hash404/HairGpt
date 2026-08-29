from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import client_ip_hash, get_current_user, require_analysis_consent
from app.core.audit import record_audit
from app.cv.registry import get_quality_gate
from app.cv.types import ImageInput
from app.db.session import get_db
from app.models.scan import (
    Analysis,
    ImageQualityReport,
    Observation,
    Recommendation,
    ScanImage,
    ScanSession,
)
from app.models.user import User
from app.schemas.scan import (
    HAIR_VIEWS,
    SKIN_VIEWS,
    AnalysisOut,
    ConfidenceOut,
    ObservationOut,
    PresignIn,
    PresignOut,
    QualityOut,
    RecommendationOut,
    SafetyVerdictOut,
    ScanCreateIn,
    ScanCreateOut,
    ScanSummaryOut,
)
from app.schemas.symptoms import AnalyzeIn
from app.services.orchestrator import run_analysis
from app.services.storage import make_storage_key, storage

router = APIRouter(prefix="/scans", tags=["scans"])

_DISCLAIMERS = [
    "HairGPT provides image-based observations, not a medical diagnosis.",
]
_MOCK_DISCLAIMER = "Some results were produced by mock inference and are NOT medically validated."


def _required_views(domain: str) -> list[str]:
    return HAIR_VIEWS if domain == "hair" else SKIN_VIEWS


def _get_session(db: Session, user: User, session_id: uuid.UUID) -> ScanSession:
    s = db.get(ScanSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    return s


@router.post("", response_model=ScanCreateOut, status_code=201)
def create_scan(body: ScanCreateIn, user: User = Depends(require_analysis_consent), db: Session = Depends(get_db)):
    protocol = body.capture_protocol or ("hair_v1" if body.domain == "hair" else "skin_v1")
    s = ScanSession(
        user_id=user.id,
        domain=body.domain,
        capture_protocol=protocol,
        device_make=body.device_make,
        lighting_label=body.lighting_label,
        status="capturing",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return ScanCreateOut(
        session_id=s.id, domain=s.domain, required_views=_required_views(s.domain), status=s.status
    )


@router.post("/{session_id}/images/presign", response_model=PresignOut)
def presign(session_id: uuid.UUID, body: PresignIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get_session(db, user, session_id)
    if body.view not in _required_views(s.domain):
        raise HTTPException(422, f"Invalid view '{body.view}' for domain {s.domain}")
    key = make_storage_key(user.id, s.id, body.view)
    # In S3 mode this would be a true presigned PUT URL. In local mode the client
    # PUTs to our own upload endpoint below.
    return PresignOut(upload_url=f"/api/v1/scans/{s.id}/images/upload", storage_key=key)


@router.post("/{session_id}/images/upload", response_model=QualityOut)
async def upload_image(
    session_id: uuid.UUID,
    request: Request,
    view: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_analysis_consent),
    db: Session = Depends(get_db),
):
    """Store an image and run the quality gate SYNCHRONOUSLY. Low-quality images
    are stored but flagged and NOT analyzed."""
    s = _get_session(db, user, session_id)
    if view not in _required_views(s.domain):
        raise HTTPException(422, f"Invalid view '{view}' for domain {s.domain}")

    data = await file.read()
    if not data:
        raise HTTPException(422, "Empty file")
    key = make_storage_key(user.id, s.id, view)
    storage.put(key, data)

    # Quality gate
    report = get_quality_gate().assess(ImageInput(data=data, view=view), view, s.domain)

    # Upsert image row
    image = db.scalar(select(ScanImage).where(ScanImage.session_id == s.id, ScanImage.view == view))
    if not image:
        image = ScanImage(session_id=s.id, view=view, storage_key=key)
        db.add(image)
        db.flush()
    image.storage_key = key
    image.quality_passed = report.overall_pass

    q = db.scalar(select(ImageQualityReport).where(ImageQualityReport.image_id == image.id))
    if not q:
        q = ImageQualityReport(image_id=image.id)
        db.add(q)
    q.blur_score = report.blur_score
    q.exposure_score = report.exposure_score
    q.overexposed_frac = report.overexposed_frac
    q.distance_ok = report.distance_ok
    q.angle_ok = report.angle_ok
    q.scalp_visibility = report.scalp_visibility
    q.overall_pass = report.overall_pass
    q.reasons = report.reasons
    q.retake_guidance = report.retake_guidance
    q.confidence = report.confidence.value
    q.method = report.confidence.method
    q.is_mock = report.is_mock

    s.status = "quality_review"
    db.commit()
    db.refresh(image)

    record_audit(db, action="scan.image.upload", actor_id=user.id, user_id=user.id,
                 resource_type="scan_image", resource_id=image.id, ip_hash=client_ip_hash(request),
                 meta={"view": view, "quality_pass": report.overall_pass})

    return QualityOut(
        image_id=image.id,
        view=view,
        overall_pass=report.overall_pass,
        blur_score=report.blur_score,
        exposure_score=report.exposure_score,
        overexposed_frac=report.overexposed_frac,
        distance_ok=report.distance_ok,
        angle_ok=report.angle_ok,
        scalp_visibility=report.scalp_visibility,
        reasons=report.reasons,
        retake_guidance=report.retake_guidance,
        confidence=ConfidenceOut(value=report.confidence.value, basis=report.confidence.basis, method=report.confidence.method),
        is_mock=report.is_mock,
    )


@router.get("/{session_id}/images/{view}/content")
def get_image_content(
    session_id: uuid.UUID,
    view: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream a stored image back to its owner (decrypted in memory).

    Ownership is enforced via the session lookup; there is no public/unauthenticated
    path to any image, and nothing here is cached by intermediaries.
    """
    s = _get_session(db, user, session_id)
    image = db.scalar(select(ScanImage).where(ScanImage.session_id == s.id, ScanImage.view == view))
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    try:
        data = storage.get(image.storage_key)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image data unavailable")
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, private"},
    )


@router.post("/{session_id}/analyze")
def analyze(
    session_id: uuid.UUID,
    body: AnalyzeIn | None = None,
    user: User = Depends(require_analysis_consent),
    db: Session = Depends(get_db),
):
    """Run the pipeline. An optional self-reported symptom report feeds the
    deterministic safety engine — several high-severity red flags cannot be
    detected from images alone, so a user's "yes" is enough to force a referral."""
    s = _get_session(db, user, session_id)
    required = set(_required_views(s.domain))
    passed = {
        img.view
        for img in db.scalars(select(ScanImage).where(ScanImage.session_id == s.id)).all()
        if img.quality_passed
    }
    missing = required - passed
    if missing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "views_incomplete", "missing_or_failed": sorted(missing)},
        )
    s.status = "analyzing"
    db.commit()
    safety_ctx = (body or AnalyzeIn()).to_safety_context()
    run_analysis(db, s, safety_ctx)  # synchronous in MVP; a worker in production
    return {"status": "complete", "session_id": str(s.id)}


def _assemble_analysis(db: Session, s: ScanSession) -> AnalysisOut:
    analysis = db.scalar(select(Analysis).where(Analysis.session_id == s.id))
    if not analysis:
        raise HTTPException(status.HTTP_202_ACCEPTED, "Analysis not ready")
    obs = db.scalars(select(Observation).where(Observation.session_id == s.id)).all()
    recs = db.scalars(select(Recommendation).where(Recommendation.analysis_id == analysis.id)).all()
    sv = analysis.safety_verdict

    disclaimers = list(_DISCLAIMERS)
    if any(o.is_mock for o in obs):
        disclaimers.append(_MOCK_DISCLAIMER)

    # Resolve evidence refs on recommendations from the analysis explanation store.
    ev_index = {e["id"]: e for e in (analysis.explanation or {}).get("evidence", [])} if analysis.explanation else {}
    rec_out = []
    for r in recs:
        evs = [ev_index[i] for i in (r.evidence_refs or []) if i in ev_index]
        rec_out.append(
            RecommendationOut(
                type=r.type, title=r.title, body=r.body, confidence=r.confidence,
                requires_clinician=r.requires_clinician, is_prescription=r.is_prescription, evidence=evs,
            )
        )

    return AnalysisOut(
        session_id=s.id,
        domain=s.domain,
        status=analysis.status,
        overall_confidence=analysis.overall_confidence,
        skin_appearance_index=analysis.skin_appearance_index,
        hair_summary=analysis.hair_summary,
        observations=[ObservationOut.model_validate(o) for o in obs],
        safety_verdict=SafetyVerdictOut(
            verdict=sv.verdict, red_flags=sv.red_flags, suppressed_cosmetic=sv.suppressed_cosmetic, message=sv.message
        ) if sv else None,
        recommendations=rec_out,
        explanation=analysis.explanation,
        disclaimers=disclaimers,
    )


@router.get("/{session_id}/result", response_model=AnalysisOut)
def get_result(session_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get_session(db, user, session_id)
    return _assemble_analysis(db, s)


@router.get("/{session_id}")
def get_scan(session_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get_session(db, user, session_id)
    images = db.scalars(select(ScanImage).where(ScanImage.session_id == s.id)).all()
    return {
        "session": ScanSummaryOut.model_validate(s),
        "required_views": _required_views(s.domain),
        "images": [
            {
                "id": str(i.id),
                "view": i.view,
                "quality_passed": i.quality_passed,
                "quality": {
                    "overall_pass": i.quality.overall_pass,
                    "reasons": i.quality.reasons,
                    "retake_guidance": i.quality.retake_guidance,
                } if i.quality else None,
            }
            for i in images
        ],
    }


@router.get("", response_model=list[ScanSummaryOut])
def list_scans(user: User = Depends(get_current_user), db: Session = Depends(get_db), limit: int = 50):
    return db.scalars(
        select(ScanSession).where(ScanSession.user_id == user.id).order_by(ScanSession.created_at.desc()).limit(limit)
    ).all()


@router.get("/{session_id}/doctor-report")
def doctor_report(session_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Structured clinician-facing draft. Explicitly framed as not-a-diagnosis."""
    s = _get_session(db, user, session_id)
    analysis = _assemble_analysis(db, s)

    # Attach the capture view to each observation: a clinician needs to know which
    # image each row came from, and it explains why a kind appears several times.
    view_by_image = {
        img.id: img.view for img in db.scalars(select(ScanImage).where(ScanImage.session_id == s.id)).all()
    }
    raw_obs = db.scalars(select(Observation).where(Observation.session_id == s.id)).all()
    observations = []
    for model_row, out in zip(raw_obs, analysis.observations):
        payload = out.model_dump()
        payload["view"] = view_by_image.get(model_row.image_id)
        observations.append(payload)

    return {
        "report_type": "clinician_draft",
        "generated_for_clinician_review": True,
        "not_a_diagnosis": True,
        "patient_self_reported": {"user_id": str(user.id)},
        "domain": s.domain,
        "captured_at": s.created_at.isoformat(),
        "overall_confidence": analysis.overall_confidence,
        "observations": observations,
        "safety_verdict": analysis.safety_verdict.model_dump() if analysis.safety_verdict else None,
        "recommendations": [r.model_dump() for r in analysis.recommendations],
        "explanation": analysis.explanation,
        "disclaimers": analysis.disclaimers + [
            "All values are apparent, image-based observations, several produced by non-validated mock models.",
            "This draft supports a clinical conversation and is not a substitute for in-person assessment.",
        ],
    }
