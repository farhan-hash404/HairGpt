from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    actor_id=None,
    user_id=None,
    resource_type: str = "",
    resource_id: str = "",
    ip_hash: str | None = None,
    meta: dict | None = None,
) -> None:
    """Write an append-only audit entry. Never raises into the request path."""
    try:
        entry = AuditLog(
            action=action,
            actor_id=actor_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            ip_hash=ip_hash,
            meta=meta,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
