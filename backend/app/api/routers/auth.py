from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import client_ip_hash, get_current_user
from app.core.audit import record_audit
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import Consent, RefreshToken, User
from app.schemas.auth import (
    ConsentIn,
    ConsentOut,
    LoginIn,
    ProfileIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(db: Session, user: User) -> TokenOut:
    access = create_access_token(str(user.id), user.role)
    refresh, jti = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    db.commit()
    return TokenOut(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        fitzpatrick_self=body.fitzpatrick_self,
        year_of_birth=body.year_of_birth,
        sex=body.sex,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit(db, action="user.register", actor_id=user.id, user_id=user.id,
                 resource_type="user", resource_id=user.id, ip_hash=client_ip_hash(request))
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    record_audit(db, action="user.login", actor_id=user.id, user_id=user.id,
                 resource_type="user", resource_id=user.id, ip_hash=client_ip_hash(request))
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    rt = db.get(RefreshToken, payload["jti"])
    if not rt or rt.revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")
    rt.revoked = True  # rotate
    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return _issue_tokens(db, user)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload and payload.get("jti"):
        rt = db.get(RefreshToken, payload["jti"])
        if rt:
            rt.revoked = True
            db.commit()
    return None


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    consents = db.scalars(select(Consent).where(Consent.user_id == user.id)).all()
    return {
        "user": UserOut.model_validate(user),
        "consents": [ConsentOut.model_validate(c) for c in consents],
    }


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update the optional profile fields.

    These exist for FAIRNESS STRATIFICATION — reporting model performance by
    skin tone, age band and sex — and for nothing else. They are self-reported,
    always optional, and never used for identification.
    """
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/consents", response_model=list[ConsentOut])
def get_consents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Consent).where(Consent.user_id == user.id)).all()


@router.post("/consents", response_model=ConsentOut)
def set_consent(body: ConsentIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    valid = {"storage", "analysis", "longitudinal", "clinician_share", "research_optin"}
    if body.purpose not in valid:
        raise HTTPException(422, f"Unknown consent purpose: {body.purpose}")
    consent = db.scalar(select(Consent).where(Consent.user_id == user.id, Consent.purpose == body.purpose))
    now = datetime.now(timezone.utc)
    if not consent:
        consent = Consent(user_id=user.id, purpose=body.purpose)
        db.add(consent)
    consent.granted = body.granted
    consent.policy_version = body.policy_version
    if body.granted:
        consent.granted_at = now
        consent.revoked_at = None
    else:
        consent.revoked_at = now
    db.commit()
    db.refresh(consent)
    record_audit(db, action="consent.update", actor_id=user.id, user_id=user.id,
                 resource_type="consent", resource_id=consent.id, ip_hash=client_ip_hash(request),
                 meta={"purpose": body.purpose, "granted": body.granted})
    return consent
