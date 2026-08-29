from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

HAIR_VIEWS = ["front_hairline", "left_temple", "right_temple", "top", "crown", "sides", "back"]
SKIN_VIEWS = ["front", "left", "right"]


class ScanCreateIn(BaseModel):
    domain: str = Field(pattern="^(hair|skin)$")
    capture_protocol: str | None = None
    device_make: str | None = None
    lighting_label: str | None = None


class ScanCreateOut(BaseModel):
    session_id: uuid.UUID
    domain: str
    required_views: list[str]
    status: str


class PresignIn(BaseModel):
    view: str
    content_type: str = "image/jpeg"


class PresignOut(BaseModel):
    upload_url: str
    storage_key: str
    method: str = "PUT"


class ImageIn(BaseModel):
    view: str
    storage_key: str
    width: int = 0
    height: int = 0


class ConfidenceOut(BaseModel):
    value: float
    basis: str
    method: str


class QualityOut(BaseModel):
    image_id: uuid.UUID
    view: str
    overall_pass: bool
    blur_score: float
    exposure_score: float
    overexposed_frac: float
    distance_ok: bool
    angle_ok: bool
    scalp_visibility: float | None
    reasons: list[str]
    retake_guidance: list[str]
    # How closely this capture matches the previous scan's framing for this view.
    # None when there is no reference scan (a first scan) — never treat as failure.
    framing_match: float | None = None
    confidence: ConfidenceOut
    is_mock: bool


class ObservationOut(BaseModel):
    kind: str
    value_num: float | None
    value_label: str | None
    unit: str | None
    confidence: float
    confidence_basis: str
    model_name: str
    model_version: str
    is_mock: bool
    # False for both mock heuristics and real-but-unevaluated models; the UI
    # must warn on either.
    validated: bool = False
    observation_type: str

    model_config = {"from_attributes": True}


class EvidenceRefOut(BaseModel):
    id: str
    source: str
    title: str
    url: str
    publisher: str
    evidence_grade: str


class RecommendationOut(BaseModel):
    type: str
    title: str
    body: str
    confidence: float
    requires_clinician: bool
    is_prescription: bool
    evidence: list[EvidenceRefOut] = []

    model_config = {"from_attributes": True}


class SafetyVerdictOut(BaseModel):
    verdict: str
    red_flags: list[str]
    suppressed_cosmetic: bool
    message: str


class AnalysisOut(BaseModel):
    session_id: uuid.UUID
    domain: str
    status: str
    overall_confidence: float
    skin_appearance_index: float | None = None
    hair_summary: dict | None = None
    observations: list[ObservationOut] = []
    safety_verdict: SafetyVerdictOut | None = None
    recommendations: list[RecommendationOut] = []
    explanation: dict | None = None
    disclaimers: list[str] = []


class ScanSummaryOut(BaseModel):
    id: uuid.UUID
    domain: str
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
