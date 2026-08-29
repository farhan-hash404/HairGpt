from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

# Drug classes with a documented association with hair shedding. This list exists
# ONLY to prompt a conversation with the prescriber — it is not a claim that a
# given medication caused anything, and the app never advises stopping a drug.
MEDICATIONS_ASSOCIATED_WITH_SHEDDING = {
    "warfarin", "heparin", "lithium", "valproate", "carbamazepine",
    "isotretinoin", "acitretin", "colchicine", "allopurinol",
    "propranolol", "metoprolol", "atenolol", "captopril", "lisinopril",
    "levothyroxine", "carbimazole", "methimazole", "propylthiouracil",
    "methotrexate", "azathioprine", "cyclophosphamide", "tamoxifen",
    "interferon", "amphetamine", "testosterone", "danazol",
}


def flag_medications(medications: list[str]) -> list[str]:
    """Return the reported medications that appear on the association list."""
    flagged: list[str] = []
    for med in medications:
        low = med.lower().strip()
        for known in MEDICATIONS_ASSOCIATED_WITH_SHEDDING:
            if known in low:
                flagged.append(med)
                break
    return flagged


class ClinicalHistoryIn(BaseModel):
    onset: str | None = Field(default=None, pattern="^(gradual|sudden|unsure)$")
    duration_months: int | None = Field(default=None, ge=0, le=1200)
    pattern: str | None = Field(default=None, pattern="^(receding|crown|diffuse|patchy|unsure)$")

    family_history_hair_loss: bool = False
    family_history_side: str | None = Field(default=None, pattern="^(maternal|paternal|both|unsure)$")

    thyroid_condition: bool = False
    iron_deficiency: bool = False
    autoimmune_condition: bool = False
    pcos: bool = False
    scalp_condition: bool = False

    recent_illness: bool = False
    recent_surgery: bool = False
    major_stress: bool = False
    rapid_weight_loss: bool = False
    postpartum: bool = False
    trigger_months_ago: int | None = Field(default=None, ge=0, le=120)

    medications: list[str] = Field(default_factory=list, max_length=40)
    tight_hairstyles: bool = False
    chemical_treatments: bool = False
    heat_styling: bool = False

    scalp_itch: bool = False
    scalp_pain: bool = False
    body_hair_change: bool = False
    menstrual_irregularity: bool = False

    notes: str | None = Field(default=None, max_length=2000)


class ClinicalHistoryOut(ClinicalHistoryIn):
    id: uuid.UUID
    updated_at: dt.datetime
    # Medications the user reported that carry a documented shedding association.
    flagged_medications: list[str] = []

    model_config = {"from_attributes": True}


class SheddingLogIn(BaseModel):
    date: dt.date | None = None
    count: int | None = Field(default=None, ge=0, le=2000)
    bucket: str | None = Field(default=None, pattern="^(none|light|moderate|heavy|very_heavy)$")
    context: str = Field(default="general", pattern="^(wash|brush|pillow|general)$")
    washed_hair: bool = False
    note: str | None = Field(default=None, max_length=500)


class SheddingLogOut(BaseModel):
    id: uuid.UUID
    date: dt.date
    count: int | None
    bucket: str | None
    context: str
    washed_hair: bool
    note: str | None

    model_config = {"from_attributes": True}


class SheddingTrendOut(BaseModel):
    window_days: int
    entries: int
    # Averages are reported PER CONTEXT: wash-day shedding is naturally much
    # higher than brush-day shedding, so a single blended average is misleading.
    average_by_context: dict[str, float]
    trend: str  # increasing | stable | decreasing | insufficient_data
    trend_note: str
    disclaimer: str
