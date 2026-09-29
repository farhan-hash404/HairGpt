from __future__ import annotations

import uuid

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, new_uuid, utcnow


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # oral_med | topical | procedure | shampoo | scalp_care | other
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(120), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # User attests a clinician prescribed this. The app itself NEVER prescribes.
    is_prescribed_by_clinician: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    adherence: Mapped[list["AdherenceLog"]] = relationship(back_populates="treatment", cascade="all, delete-orphan")


class AdherenceLog(Base):
    __tablename__ = "adherence_logs"
    __table_args__ = (UniqueConstraint("treatment_id", "date", name="uq_adherence_per_day"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    treatment_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("treatments.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, default=date.today)
    taken: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    treatment: Mapped["Treatment"] = relationship(back_populates="adherence")
