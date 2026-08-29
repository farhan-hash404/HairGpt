from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.scan import Analysis, Recommendation, ScanSession
from app.models.user import User

router = APIRouter(prefix="/analyses", tags=["explainability"])


def _own_analysis(db, user, aid) -> Analysis:
    a = db.get(Analysis, aid)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    s = db.get(ScanSession, a.session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return a


@router.get("/{aid}/why")
def why(aid: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Backs the "Why?" button: observation, reasoning, confidence, limitations."""
    a = _own_analysis(db, user, aid)
    exp = a.explanation or {}
    return {
        "observation": exp.get("observation"),
        "reasoning": exp.get("reasoning"),
        "confidence": exp.get("confidence"),
        "limitations": exp.get("limitations", []),
    }


@router.get("/{aid}/evidence")
def evidence(aid: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Backs the "Evidence" button: resolved sources with grade + provenance."""
    a = _own_analysis(db, user, aid)
    exp = a.explanation or {}
    recs = db.scalars(select(Recommendation).where(Recommendation.analysis_id == a.id)).all()
    used_ids = {rid for r in recs for rid in (r.evidence_refs or [])}
    all_ev = {e["id"]: e for e in exp.get("evidence", [])}
    return {
        "evidence": list(all_ev.values()),
        "cited_by_recommendations": sorted(used_ids),
        "note": "Every medical claim is traceable to an approved source (AAD/FDA/NICE/NHS/peer-reviewed). Social media is never used.",
    }
