from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.treatment import AdherenceLog, Treatment
from app.models.user import User
from app.schemas.treatment import (
    AdherenceIn,
    AdherenceSummaryOut,
    TreatmentIn,
    TreatmentOut,
)

router = APIRouter(prefix="/treatments", tags=["treatments"])


def _own(db, user, tid) -> Treatment:
    t = db.get(Treatment, tid)
    if not t or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment not found")
    return t


@router.get("", response_model=list[TreatmentOut])
def list_treatments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Treatment).where(Treatment.user_id == user.id)).all()


@router.post("", response_model=TreatmentOut, status_code=201)
def create_treatment(body: TreatmentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # NOTE: this records what a user/clinician is already doing. The app never prescribes.
    t = Treatment(
        user_id=user.id,
        category=body.category,
        name=body.name,
        dose=body.dose,
        frequency=body.frequency,
        start_date=body.start_date or date.today(),
        end_date=body.end_date,
        notes=body.notes,
        is_prescribed_by_clinician=body.is_prescribed_by_clinician,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/{tid}", response_model=TreatmentOut)
def update_treatment(tid: uuid.UUID, body: TreatmentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _own(db, user, tid)
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(t, field, val)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{tid}", status_code=204)
def delete_treatment(tid: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _own(db, user, tid)
    db.delete(t)
    db.commit()
    return None


@router.post("/{tid}/adherence")
def log_adherence(tid: uuid.UUID, body: AdherenceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _own(db, user, tid)
    d = body.date or date.today()
    log = db.scalar(select(AdherenceLog).where(AdherenceLog.treatment_id == t.id, AdherenceLog.date == d))
    if not log:
        log = AdherenceLog(treatment_id=t.id, date=d)
        db.add(log)
    log.taken = body.taken
    log.note = body.note
    db.commit()
    return {"treatment_id": str(t.id), "date": d.isoformat(), "taken": body.taken}


@router.get("/adherence/summary", response_model=list[AdherenceSummaryOut])
def adherence_summary(window_days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=window_days)
    out = []
    for t in db.scalars(select(Treatment).where(Treatment.user_id == user.id)).all():
        logs = [
            log for log in db.scalars(select(AdherenceLog).where(AdherenceLog.treatment_id == t.id)).all()
            if log.date >= since
        ]
        expected = min(window_days, (date.today() - max(t.start_date, since)).days + 1)
        taken = sum(1 for log in logs if log.taken)
        pct = round(100.0 * taken / expected, 1) if expected > 0 else 0.0
        out.append(
            AdherenceSummaryOut(
                treatment_id=t.id, name=t.name, adherence_pct=min(pct, 100.0),
                logged_days=len(logs), window_days=window_days,
            )
        )
    return out
