from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.cv.registry import get_aligner
from app.cv.types import ImageInput
from app.db.session import get_db
from app.models.scan import Comparison, Observation, ScanImage, ScanSession
from app.models.user import User
from app.services.storage import storage

router = APIRouter(prefix="/comparisons", tags=["comparisons"])

_EFFICACY_DISCLAIMER = "Apparent changes only — images cannot prove treatment efficacy."


class ComparisonIn(BaseModel):
    session_before: uuid.UUID
    session_after: uuid.UUID


def _obs_map(db, session_id) -> dict[str, Observation]:
    out: dict[str, Observation] = {}
    for o in db.scalars(select(Observation).where(Observation.session_id == session_id)).all():
        out.setdefault(o.kind, o)
    return out


# Preferred views for the visual comparison, most informative first.
_VIEW_PRIORITY = ["crown", "top", "front_hairline", "back", "front"]


def _matched_images(db, before_id, after_id) -> tuple[ScanImage | None, ScanImage | None]:
    """Pick the SAME view from both sessions.

    Comparing different views would be meaningless, so we intersect the
    quality-passed views of both scans and choose by priority.
    """
    def passed(session_id) -> dict[str, ScanImage]:
        rows = db.scalars(
            select(ScanImage).where(
                ScanImage.session_id == session_id, ScanImage.quality_passed.is_(True)
            )
        ).all()
        return {img.view: img for img in rows}

    b_map, a_map = passed(before_id), passed(after_id)
    common = set(b_map) & set(a_map)
    if not common:
        return None, None
    view = next((v for v in _VIEW_PRIORITY if v in common), sorted(common)[0])
    return b_map[view], a_map[view]


@router.post("")
def create_comparison(body: ComparisonIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for sid in (body.session_before, body.session_after):
        s = db.get(ScanSession, sid)
        if not s or s.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")

    before = _obs_map(db, body.session_before)
    after = _obs_map(db, body.session_after)

    # Alignment quality (standardized alignment before any comparison claim).
    align_q = 0.0
    limitations = [_EFFICACY_DISCLAIMER]
    img_b, img_a = _matched_images(db, body.session_before, body.session_after)
    if not (img_b and img_a):
        limitations.append("No view passed quality in both scans, so images could not be aligned.")
    if img_b and img_a:
        try:
            ab = get_aligner().align(ImageInput(data=storage.get(img_b.storage_key), view=img_b.view), img_b.view, None)
            aa = get_aligner().align(ImageInput(data=storage.get(img_a.storage_key), view=img_a.view), img_a.view, ab.transform)
            align_q = round(min(ab.quality.value, aa.quality.value), 3)
        except Exception:
            limitations.append("Could not reliably align the two images.")
    if align_q < 0.5:
        limitations.append("Alignment quality is low; differences may reflect pose/lighting, not real change.")

    metrics = []
    for kind in set(before) | set(after):
        b, a = before.get(kind), after.get(kind)
        if b is None or a is None or b.value_num is None or a.value_num is None:
            continue
        delta = round(a.value_num - b.value_num, 3)
        conf = round(min(b.confidence, a.confidence) * (0.5 + 0.5 * align_q), 3)
        metrics.append({
            "kind": kind,
            "before": b.value_num,
            "after": a.value_num,
            "delta": delta,
            "direction": "increase" if delta > 0 else "decrease" if delta < 0 else "no_change",
            "confidence": conf,
            "is_mock": b.is_mock or a.is_mock,
        })

    if any(m["is_mock"] for m in metrics):
        limitations.append("Metrics derived from non-validated mock models.")

    explanation = {
        "observation": "Apparent differences between the two scans are summarized below.",
        "reasoning": "Values are compared after standardized alignment. Lighting and image quality strongly affect apparent change.",
        "confidence": {"value": align_q, "basis": "alignment quality gates comparison confidence", "method": "compare_v1"},
        "limitations": limitations,
        # The view actually used for the visual panes, so the client renders the
        # same pair the alignment was computed on.
        "compared_view": img_b.view if img_b else None,
    }

    comp = Comparison(
        user_id=user.id,
        session_before=body.session_before,
        session_after=body.session_after,
        metrics=metrics,
        alignment_quality=align_q,
        limitations=limitations,
        explanation=explanation,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return _serialize(comp)


@router.get("/{cid}")
def get_comparison(cid: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comp = db.get(Comparison, cid)
    if not comp or comp.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comparison not found")
    return _serialize(comp)


def _serialize(comp: Comparison) -> dict:
    return {
        "id": str(comp.id),
        "session_before": str(comp.session_before),
        "session_after": str(comp.session_after),
        "aligned_overlay_url": f"/api/v1/comparisons/{comp.id}/overlay",  # rendered client-side in MVP
        "diff_url": f"/api/v1/comparisons/{comp.id}/diff",
        "metrics": comp.metrics,
        "alignment_quality": comp.alignment_quality,
        "limitations": comp.limitations,
        "explanation": comp.explanation,
    }
