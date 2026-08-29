from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

_ph = PasswordHasher()
_ALGO = "HS256"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, role: str) -> str:
    exp = _now() + timedelta(minutes=settings.access_token_ttl_min)
    payload = {"sub": subject, "role": role, "type": "access", "exp": exp, "jti": str(uuid.uuid4())}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO)


def create_refresh_token(subject: str) -> tuple[str, str]:
    """Return (token, jti). The jti is stored server-side so refresh can be revoked."""
    jti = str(uuid.uuid4())
    exp = _now() + timedelta(days=settings.refresh_token_ttl_days)
    payload = {"sub": subject, "type": "refresh", "exp": exp, "jti": jti}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO), jti


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[_ALGO])
    except JWTError:
        return None


def hash_ip(ip: str | None) -> str | None:
    """Minimal-metadata IP handling: store a salted hash, never the raw IP."""
    if not ip:
        return None
    return hashlib.sha256((settings.secret_key + ip).encode()).hexdigest()[:32]
