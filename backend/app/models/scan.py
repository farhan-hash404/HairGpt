from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, JSONType, new_uuid, utcnow


class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    domain: Mapped[str] = mapped_column(String(8), nullable=False)  # hair | skin
    status: Mapped[str] = mapped_column(String(16), default="capturing")
    capture_protocol: Mapped[str] = mapped_column(String(32), default="hair_v1")
    device_make: Mapped[str | None] = mapped_column(String(64), nullable=True)  # fairness metadata
    lighting_label: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    images: Mapped[list["ScanImage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    observations: Mapped[list["Observation"]] = relationship(cascade="all, delete-orphan")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")


class ScanImage(Base):
    __tablename__ = "scan_images"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scan_sessions.id", ondelete="CASCADE"), index=True)
    view: Mapped[str] = mapped_column(String(24), nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    quality_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    alignment_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    session: Mapped["ScanSession"] = relationship(back_populates="images")
    quality: Mapped["ImageQualityReport | None"] = relationship(
        back_populates="image", uselist=False, cascade="all, delete-orphan"
    )


class ImageQualityReport(Base):
    __tablename__ = "image_quality_reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    image_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scan_images.id", ondelete="CASCADE"), unique=True)
    blur_score: Mapped[float] = mapped_column(Float, default=0.0)
    exposure_score: Mapped[float] = mapped_column(Float, default=0.0)
    overexposed_frac: Mapped[float] = mapped_column(Float, default=0.0)
    distance_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    angle_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    scalp_visibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    # Framing similarity to the previous scan's same view (0..1). NULL when there
    # was no reference scan to compare against.
    framing_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasons: Mapped[list] = mapped_column(JSONType, default=list)
    retake_guidance: Mapped[list] = mapped_column(JSONType, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    method: Mapped[str] = mapped_column(String(48), default="quality_gate_v1")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)

    image: Mapped["ScanImage"] = relationship(back_populates="quality")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scan_sessions.id", ondelete="CASCADE"), index=True)
    image_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("scan_images.id", ondelete="CASCADE"), nullable=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_basis: Mapped[str] = mapped_column(String(160), default="")
    model_name: Mapped[str] = mapped_column(String(64), default="")
    model_version: Mapped[str] = mapped_column(String(48), default="")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    # Separate from is_mock: a REAL model that has not passed the stratified
    # fairness evaluation is is_mock=False, validated=False. Only a passing
    # evaluation record sets this true.
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    # visual_observation | ai_inference  (never "diagnosis")
    observation_type: Mapped[str] = mapped_column(String(24), default="visual_observation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scan_sessions.id", ondelete="CASCADE"), unique=True)
    skin_appearance_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    hair_summary: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    llm_model: Mapped[str] = mapped_column(String(48), default="")
    explanation: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["ScanSession"] = relationship(back_populates="analysis")
    safety_verdict: Mapped["SafetyVerdict | None"] = relationship(
        back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class SafetyVerdict(Base):
    __tablename__ = "safety_verdicts"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    analysis_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("analyses.id", ondelete="CASCADE"), unique=True)
    verdict: Mapped[str] = mapped_column(String(12), default="ok")  # ok | caution | refer
    red_flags: Mapped[list] = mapped_column(JSONType, default=list)
    triggered_rules: Mapped[list] = mapped_column(JSONType, default=list)
    suppressed_cosmetic: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped["Analysis"] = relationship(back_populates="safety_verdict")


class Recommendation(Base):
    __tablename__ = "recommendations"
    # Structural guarantee: the system can NEVER store an autonomous prescription.
    __table_args__ = (CheckConstraint("is_prescription = 0", name="ck_no_autonomous_prescription"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    analysis_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    # care_guidance | clinician_discussion_point | product | ingredient | routine_step | referral
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    evidence_refs: Mapped[list] = mapped_column(JSONType, default=list)  # list of evidence_document ids
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    requires_clinician: Mapped[bool] = mapped_column(Boolean, default=False)
    is_prescription: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped["Analysis"] = relationship(back_populates="recommendations")


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_before: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scan_sessions.id", ondelete="CASCADE"))
    session_after: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scan_sessions.id", ondelete="CASCADE"))
    metrics: Mapped[list] = mapped_column(JSONType, default=list)
    alignment_quality: Mapped[float] = mapped_column(Float, default=0.0)
    limitations: Mapped[list] = mapped_column(JSONType, default=list)
    explanation: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
