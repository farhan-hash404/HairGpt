from __future__ import annotations

from pydantic import BaseModel, Field

# Self-reported symptoms that feed the deterministic safety engine.
#
# WHY THIS EXISTS: several high-severity red flags (scarring, pustules, sudden
# patchy loss, facial swelling) cannot be detected reliably by the current CV
# stack. Rather than let the safety net silently do nothing, we ask the user
# directly. A "yes" here is enough on its own to force a clinician referral —
# self-report is treated as SAFETY-RELEVANT EVIDENCE, not as a diagnosis.


class HairSymptomsIn(BaseModel):
    pustules: bool = Field(default=False, description="Pus-filled spots, crusting, or oozing on the scalp")
    boggy_scalp: bool = Field(default=False, description="Scalp feels boggy, swollen, or painful to touch")
    scarring_signal: bool = Field(default=False, description="Smooth, shiny patches where hair follicles look absent")
    sudden_patchy_loss: bool = Field(default=False, description="Hair lost suddenly in well-defined round patches")
    systemic_symptoms: bool = Field(default=False, description="Fever, unexplained weight loss, or feeling generally unwell")


class SkinSymptomsIn(BaseModel):
    lesion_abcde_signal: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Mole/spot showing asymmetry, irregular border, multiple colors, large size, or evolution",
    )
    lesion_change_delta: float = Field(
        default=0.0, ge=0.0, le=1.0, description="A lesion has changed rapidly in recent weeks"
    )
    facial_swelling: bool = Field(default=False, description="Swelling of the face, lips, eyes, or tongue")
    allergic_reaction: bool = Field(default=False, description="Signs of a severe allergic reaction")
    infection_like: bool = Field(default=False, description="Spreading redness, warmth, pus, or fever with the rash")
    systemic_symptoms: bool = Field(default=False, description="Fever or feeling generally unwell")


class AnalyzeIn(BaseModel):
    """Optional symptom report submitted alongside a scan analysis."""

    hair_symptoms: HairSymptomsIn | None = None
    skin_symptoms: SkinSymptomsIn | None = None
    is_minor: bool = False

    def to_safety_context(self) -> dict:
        ctx: dict = {"is_minor": self.is_minor}
        if self.hair_symptoms:
            ctx.update(self.hair_symptoms.model_dump())
        if self.skin_symptoms:
            ctx.update(self.skin_symptoms.model_dump())
        return ctx
