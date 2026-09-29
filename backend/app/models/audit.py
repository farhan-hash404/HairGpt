from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import GUID, Base, JSONType, new_uuid, utcnow


class AuditLog(Base):
    """Append-only audit trail. Minimal metadata: hashed IP only, no biometrics."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(48), default="")
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
