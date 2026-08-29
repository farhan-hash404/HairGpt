from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import client_ip_hash, get_current_user
from app.core.audit import record_audit
from app.db.session import get_db
from app.models.product import Product
from app.models.scan import Analysis, Observation, ScanImage, ScanSession
from app.models.treatment import Treatment
from app.models.user import Consent, User
from app.services.storage import storage

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/export")
def export_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Full data export (right to data portability). Returns structured JSON;
    images are referenced by key and can be downloaded via a signed job in prod."""
    sessions = db.scalars(select(ScanSession).where(ScanSession.user_id == user.id)).all()
    return {
        "user": {"id": str(user.id), "email": user.email, "display_name": user.display_name},
        "consents": [{"purpose": c.purpose, "granted": c.granted} for c in
                     db.scalars(select(Consent).where(Consent.user_id == user.id)).all()],
        "scans": [
            {
                "id": str(s.id), "domain": s.domain, "status": s.status, "created_at": s.created_at.isoformat(),
                "observations": [
                    {"kind": o.kind, "value_num": o.value_num, "value_label": o.value_label,
                     "confidence": o.confidence, "is_mock": o.is_mock}
                    for o in db.scalars(select(Observation).where(Observation.session_id == s.id)).all()
                ],
            }
            for s in sessions
        ],
        "treatments": [
            {"name": t.name, "category": t.category, "start_date": t.start_date.isoformat()}
            for t in db.scalars(select(Treatment).where(Treatment.user_id == user.id)).all()
        ],
        "note": "This export contains your data. Images are stored encrypted and available on request.",
    }


@router.delete("")
def delete_account(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Hard delete: purge images from storage, then all rows. Writes a final audit entry."""
    # 1) Purge images from object storage.
    for s in db.scalars(select(ScanSession).where(ScanSession.user_id == user.id)).all():
        for img in db.scalars(select(ScanImage).where(ScanImage.session_id == s.id)).all():
            try:
                storage.delete(img.storage_key)
            except Exception:
                pass
    for p in db.scalars(select(Product).where(Product.user_id == user.id)).all():
        _ = p  # products carry no stored image in MVP

    uid = user.id
    # 2) Final audit entry BEFORE deletion (references user id only).
    record_audit(db, action="account.delete", actor_id=uid, user_id=uid,
                 resource_type="user", resource_id=uid, ip_hash=client_ip_hash(request))

    # 3) Delete the user; cascades remove sessions, images, observations, treatments, etc.
    db.delete(user)
    db.commit()
    return {"deleted": True, "user_id": str(uid)}
