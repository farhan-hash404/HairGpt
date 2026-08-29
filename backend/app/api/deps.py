from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token, hash_ip
from app.db.session import get_db
from app.models.user import Consent, User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_role(*roles: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return _dep


def require_analysis_consent(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Analysis is blocked unless BOTH storage and analysis consent are currently granted."""
    rows = db.scalars(select(Consent).where(Consent.user_id == user.id)).all()
    granted = {c.purpose for c in rows if c.granted and c.revoked_at is None}
    missing = {"storage", "analysis"} - granted
    if missing:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "consent_required", "missing": sorted(missing)},
        )
    return user


def client_ip_hash(request: Request) -> str | None:
    return hash_ip(request.client.host if request.client else None)
