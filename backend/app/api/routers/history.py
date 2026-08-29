from __future__ import annotations

import statistics
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.history import ClinicalHistory, SheddingLog
from app.models.user import User
from app.schemas.history import (
    ClinicalHistoryIn,
    ClinicalHistoryOut,
    SheddingLogIn,
    SheddingLogOut,
    SheddingTrendOut,
    flag_medications,
)

router = APIRouter(tags=["history"])

_SHEDDING_DISCLAIMER = (
    "Shedding counts are self-reported estimates and vary widely with washing, "
    "brushing and hair length. Trends are indicative only and do not diagnose anything."
)


# ---------------------------------------------------------------------------
# Clinical history
# ---------------------------------------------------------------------------

def _to_out(history: ClinicalHistory) -> ClinicalHistoryOut:
    out = ClinicalHistoryOut.model_validate(history)
    out.flagged_medications = flag_medications(history.medications or [])
    return out


@router.get("/history", response_model=ClinicalHistoryOut | None)
def get_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = db.scalar(select(ClinicalHistory).where(ClinicalHistory.user_id == user.id))
    return _to_out(history) if history else None


@router.put("/history", response_model=ClinicalHistoryOut)
def upsert_history(
    body: ClinicalHistoryIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update the user's history. One row per user, updated in place."""
    history = db.scalar(select(ClinicalHistory).where(ClinicalHistory.user_id == user.id))
    if not history:
        history = ClinicalHistory(user_id=user.id)
        db.add(history)
    for field, value in body.model_dump().items():
        setattr(history, field, value)
    db.commit()
    db.refresh(history)
    return _to_out(history)


def build_history_context(db: Session, user_id) -> dict:
    """Flatten a user's history into the safety engine's context dict.

    Called by the analyze endpoint so history-driven rules can fire. Returns an
    empty dict when no history exists — the safety engine must degrade quietly,
    not error.
    """
    history = db.scalar(select(ClinicalHistory).where(ClinicalHistory.user_id == user_id))
    if not history:
        return {}

    ctx = {
        "onset": history.onset,
        "pattern": history.pattern,
        "thyroid_condition": history.thyroid_condition,
        "iron_deficiency": history.iron_deficiency,
        "autoimmune_condition": history.autoimmune_condition,
        "pcos": history.pcos,
        "scalp_condition": history.scalp_condition,
        "recent_illness": history.recent_illness,
        "recent_surgery": history.recent_surgery,
        "major_stress": history.major_stress,
        "rapid_weight_loss": history.rapid_weight_loss,
        "postpartum": history.postpartum,
        "tight_hairstyles": history.tight_hairstyles,
        "scalp_itch": history.scalp_itch,
        "scalp_pain": history.scalp_pain,
        "body_hair_change": history.body_hair_change,
        "menstrual_irregularity": history.menstrual_irregularity,
    }
    ctx["medication_associated_shedding"] = bool(flag_medications(history.medications or []))
    return ctx


# ---------------------------------------------------------------------------
# Shedding log
# ---------------------------------------------------------------------------

_BUCKET_MIDPOINT = {"none": 0, "light": 25, "moderate": 75, "heavy": 150, "very_heavy": 250}


@router.get("/shedding", response_model=list[SheddingLogOut])
def list_shedding(
    days: int = 90,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    return db.scalars(
        select(SheddingLog)
        .where(SheddingLog.user_id == user.id, SheddingLog.date >= since)
        .order_by(SheddingLog.date.asc())
    ).all()


@router.post("/shedding", response_model=SheddingLogOut, status_code=201)
def log_shedding(
    body: SheddingLogIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    when = body.date or date.today()
    entry = db.scalar(
        select(SheddingLog).where(
            SheddingLog.user_id == user.id,
            SheddingLog.date == when,
            SheddingLog.context == body.context,
        )
    )
    if not entry:
        entry = SheddingLog(user_id=user.id, date=when, context=body.context)
        db.add(entry)
    entry.count = body.count
    entry.bucket = body.bucket
    entry.washed_hair = body.washed_hair
    entry.note = body.note
    db.commit()
    db.refresh(entry)
    return entry


def _numeric_value(entry: SheddingLog) -> float | None:
    if entry.count is not None:
        return float(entry.count)
    if entry.bucket:
        return float(_BUCKET_MIDPOINT.get(entry.bucket, 0))
    return None


@router.get("/shedding/trend", response_model=SheddingTrendOut)
def shedding_trend(
    window_days: int = 60,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Shedding trend, computed PER CONTEXT.

    Wash-day shedding is naturally several times higher than brush-day shedding,
    so blending them produces a number driven by how often the user washed rather
    than by how much they shed. We therefore compare like with like, and refuse
    to call a trend at all without enough data.
    """
    since = date.today() - timedelta(days=window_days)
    entries = db.scalars(
        select(SheddingLog)
        .where(SheddingLog.user_id == user.id, SheddingLog.date >= since)
        .order_by(SheddingLog.date.asc())
    ).all()

    by_context: dict[str, list[tuple[date, float]]] = {}
    for entry in entries:
        value = _numeric_value(entry)
        if value is None:
            continue
        by_context.setdefault(entry.context, []).append((entry.date, value))

    averages = {
        context: round(statistics.mean(v for _, v in points), 1)
        for context, points in by_context.items()
    }

    # Trend from the context with the most observations, comparing the first and
    # second halves of the window.
    trend, note = "insufficient_data", "Log shedding on at least 6 comparable days to see a trend."
    if by_context:
        context, points = max(by_context.items(), key=lambda kv: len(kv[1]))
        if len(points) >= 6:
            midpoint = len(points) // 2
            first = statistics.mean(v for _, v in points[:midpoint])
            second = statistics.mean(v for _, v in points[midpoint:])
            spread = statistics.pstdev([v for _, v in points]) or 1.0
            change = second - first
            # Require the change to clear the natural variability of the data
            # before calling it a trend at all.
            if abs(change) < spread * 0.5:
                trend = "stable"
                note = f"No clear change in {context} shedding; day-to-day variation is larger than the shift."
            elif change > 0:
                trend = "increasing"
                note = f"{context.title()} shedding appears higher in the recent half of this window."
            else:
                trend = "decreasing"
                note = f"{context.title()} shedding appears lower in the recent half of this window."

    return SheddingTrendOut(
        window_days=window_days,
        entries=len(entries),
        average_by_context=averages,
        trend=trend,
        trend_note=note,
        disclaimer=_SHEDDING_DISCLAIMER,
    )
