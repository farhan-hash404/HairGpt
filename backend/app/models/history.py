from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import GUID, Base, JSONType, new_uuid, utcnow


class ClinicalHistory(Base):
    """Structured medical history — the context photos cannot show.

    A dermatologist's first move is history-taking, and several of the most
    common causes of hair loss (thyroid disease, iron deficiency, telogen
    effluvium after illness/stress/childbirth, drug-induced shedding) are
    INVISIBLE to any camera. Without this the app is blind to them.

    One row per user, updated in place. Every field is self-reported and is
    recorded as such — none of it is a diagnosis.
    """

    __tablename__ = "clinical_histories"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    # --- Onset & pattern -----------------------------------------------------
    # onset: gradual | sudden | unsure
    onset: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_months: Mapped[int | None] = mapped_column(nullable=True)
    # pattern: receding | crown | diffuse | patchy | unsure
    pattern: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # --- Family history ------------------------------------------------------
    family_history_hair_loss: Mapped[bool] = mapped_column(Boolean, default=False)
    family_history_side: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # --- Conditions that commonly present as hair loss -----------------------
    thyroid_condition: Mapped[bool] = mapped_column(Boolean, default=False)
    iron_deficiency: Mapped[bool] = mapped_column(Boolean, default=False)
    autoimmune_condition: Mapped[bool] = mapped_column(Boolean, default=False)
    pcos: Mapped[bool] = mapped_column(Boolean, default=False)
    scalp_condition: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Telogen effluvium triggers (typically 2-4 months before shedding) ----
    recent_illness: Mapped[bool] = mapped_column(Boolean, default=False)
    recent_surgery: Mapped[bool] = mapped_column(Boolean, default=False)
    major_stress: Mapped[bool] = mapped_column(Boolean, default=False)
    rapid_weight_loss: Mapped[bool] = mapped_column(Boolean, default=False)
    postpartum: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger_months_ago: Mapped[int | None] = mapped_column(nullable=True)

    # --- Medications & styling ----------------------------------------------
    # Free-text list of medications the user reports taking.
    medications: Mapped[list] = mapped_column(JSONType, default=list)
    tight_hairstyles: Mapped[bool] = mapped_column(Boolean, default=False)
    chemical_treatments: Mapped[bool] = mapped_column(Boolean, default=False)
    heat_styling: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Associated symptoms -------------------------------------------------
    scalp_itch: Mapped[bool] = mapped_column(Boolean, default=False)
    scalp_pain: Mapped[bool] = mapped_column(Boolean, default=False)
    body_hair_change: Mapped[bool] = mapped_column(Boolean, default=False)
    menstrual_irregularity: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SheddingLog(Base):
    """Daily/periodic hair-shedding count.

    Users notice shedding long before a photo shows anything, so this is the
    product's leading indicator and its main reason to open the app between
    scans. Counts are self-reported estimates, never measurements.
    """

    __tablename__ = "shedding_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    # count_estimate | bucket. Buckets keep logging low-friction.
    count: Mapped[int | None] = mapped_column(nullable=True)
    # none | light | moderate | heavy | very_heavy
    bucket: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # wash | brush | pillow | general — shedding varies hugely by context, so an
    # unlabelled count is not comparable day to day.
    context: Mapped[str] = mapped_column(String(16), default="general")
    washed_hair: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
