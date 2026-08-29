from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.scan import Analysis, Observation, ScanSession
from app.models.treatment import Treatment
from app.models.user import User

router = APIRouter(prefix="/timeline", tags=["timeline"])

_TRACKED = ["scalp_visibility", "apparent_density", "crown_density", "hairline_position"]


@router.get("")
def get_timeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Merged longitudinal series: hairline, crown, scalp visibility, apparent
    density, treatment events, adherence, and scan history — each point tagged
    with confidence and is_mock."""
    sessions = db.scalars(
        select(ScanSession).where(ScanSession.user_id == user.id, ScanSession.status == "complete")
        .order_by(ScanSession.created_at.asc())
    ).all()

    series: dict[str, list[dict]] = {k: [] for k in _TRACKED}
    scan_history = []
    for s in sessions:
        analysis = db.scalar(select(Analysis).where(Analysis.session_id == s.id))
        scan_history.append({
            "session_id": str(s.id),
            "domain": s.domain,
            "date": s.created_at.isoformat(),
            "overall_confidence": analysis.overall_confidence if analysis else None,
        })
        obs = db.scalars(select(Observation).where(Observation.session_id == s.id)).all()
        by_kind = {}
        for o in obs:
            by_kind.setdefault(o.kind, o)  # first per kind
        for kind in _TRACKED:
            o = by_kind.get(kind)
            if o:
                series[kind].append({
                    "date": s.created_at.isoformat(),
                    "value": o.value_num,
                    "label": o.value_label,
                    "confidence": o.confidence,
                    "is_mock": o.is_mock,
                })

    treatments = [
        {
            "id": str(t.id),
            "name": t.name,
            "category": t.category,
            "start_date": t.start_date.isoformat(),
            "end_date": t.end_date.isoformat() if t.end_date else None,
            "is_prescribed_by_clinician": t.is_prescribed_by_clinician,
        }
        for t in db.scalars(select(Treatment).where(Treatment.user_id == user.id)).all()
    ]

    return {
        "series": series,
        "treatments": treatments,
        "scan_history": scan_history,
        "disclaimer": "Trends are apparent, image-based observations and do not prove treatment efficacy.",
    }
