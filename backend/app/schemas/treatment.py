from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


class TreatmentIn(BaseModel):
    category: str = Field(pattern="^(oral_med|topical|procedure|shampoo|scalp_care|other)$")
    name: str = Field(max_length=160)
    dose: str | None = None
    frequency: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    notes: str | None = None
    is_prescribed_by_clinician: bool = False


class TreatmentOut(BaseModel):
    id: uuid.UUID
    category: str
    name: str
    dose: str | None
    frequency: str | None
    start_date: dt.date
    end_date: dt.date | None
    notes: str | None
    is_prescribed_by_clinician: bool

    model_config = {"from_attributes": True}


class AdherenceIn(BaseModel):
    # Field name `date` deliberately kept for the API; type referenced via module
    # to avoid the name shadowing the `date` type in the class namespace.
    date: dt.date | None = None
    taken: bool = True
    note: str | None = None


class AdherenceSummaryOut(BaseModel):
    treatment_id: uuid.UUID
    name: str
    adherence_pct: float
    logged_days: int
    window_days: int
