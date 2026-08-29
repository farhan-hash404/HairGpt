from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.cv.types import Observation

# Severity: "high" forces referral; "medium" forces caution.
Severity = str


@dataclass
class RuleResult:
    code: str
    severity: Severity
    matched: bool
    rationale: str


def _by_kind(obs: list[Observation]) -> dict[str, Observation]:
    return {o.kind: o for o in obs}


# ---------------------------------------------------------------------------
# Skin (SkinGPT) red flags — force referral.
# These operate on STRUCTURED observations, never on LLM free text.
# ---------------------------------------------------------------------------

def rule_suspicious_lesion(obs, ctx) -> RuleResult:
    m = _by_kind(obs)
    o = m.get("acne_like_lesion_count")
    lesion_signal = ctx.get("lesion_abcde_signal", 0.0)
    matched = lesion_signal >= 0.5 or (o is not None and (o.value_num or 0) >= 15)
    return RuleResult(
        "skin_suspicious_lesion",
        "high",
        matched,
        "Image features may be consistent with a lesion that warrants in-person evaluation (ABCDE-type signals).",
    )


def rule_rapidly_changing_lesion(obs, ctx) -> RuleResult:
    matched = ctx.get("lesion_change_delta", 0.0) >= 0.4
    return RuleResult(
        "skin_rapidly_changing_lesion",
        "high",
        matched,
        "A rapidly changing lesion appearance was reported/observed; prompt clinical review is advised.",
    )


def rule_severe_inflammation(obs, ctx) -> RuleResult:
    m = _by_kind(obs)
    redness = (m.get("redness").value_num if m.get("redness") else 0.0) or 0.0
    matched = redness >= 0.45 or ctx.get("infection_like", False)
    return RuleResult(
        "skin_severe_inflammation",
        "high",
        matched,
        "Appearance may be consistent with severe inflammation/infection; professional evaluation is advised.",
    )


def rule_facial_swelling(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("facial_swelling", False) or ctx.get("allergic_reaction", False))
    return RuleResult(
        "skin_facial_swelling_or_allergy",
        "high",
        matched,
        "Facial swelling / possible severe allergic reaction requires urgent professional assessment.",
    )


# ---------------------------------------------------------------------------
# Hair (HairGPT) red flags — force referral.
# ---------------------------------------------------------------------------

def rule_scarring_alopecia(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("scarring_signal", False))
    return RuleResult(
        "hair_scarring_alopecia_signal",
        "high",
        matched,
        "Scalp appearance may suggest scarring hair loss; this needs clinician evaluation to avoid permanent loss.",
    )


def rule_scalp_infection(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("pustules", False) or ctx.get("boggy_scalp", False))
    return RuleResult(
        "hair_scalp_infection_signal",
        "high",
        matched,
        "Pustules / boggy or painful scalp may indicate infection; professional evaluation is advised.",
    )


def rule_sudden_patchy_loss(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("sudden_patchy_loss", False))
    return RuleResult(
        "hair_sudden_patchy_loss",
        "high",
        matched,
        "Sudden, well-defined patchy loss may warrant evaluation (e.g. for alopecia areata).",
    )


# ---------------------------------------------------------------------------
# Cross-cutting caution triggers — force caution (language downgrade).
# ---------------------------------------------------------------------------

def rule_low_confidence(obs, ctx) -> RuleResult:
    matched = ctx.get("overall_confidence", 1.0) < 0.4
    return RuleResult(
        "low_overall_confidence",
        "medium",
        matched,
        "Overall interpretation confidence is low; conclusions should be treated cautiously.",
    )


def rule_poor_quality_passed(obs, ctx) -> RuleResult:
    matched = ctx.get("min_quality_confidence", 1.0) < 0.5
    return RuleResult(
        "borderline_image_quality",
        "medium",
        matched,
        "Image quality was borderline; results may be unreliable.",
    )


def rule_minor(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("is_minor", False))
    return RuleResult(
        "user_is_minor",
        "medium",
        matched,
        "User is a minor; clinician involvement is recommended for any treatment decision.",
    )


def rule_systemic_symptoms(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("systemic_symptoms", False))
    return RuleResult(
        "reported_systemic_symptoms",
        "medium",
        matched,
        "Reported systemic symptoms warrant clinical attention.",
    )


# ---------------------------------------------------------------------------
# History-driven rules. Photos cannot show thyroid disease, iron deficiency or a
# drug side effect, yet these are among the most common and most TREATABLE
# causes of hair loss. Missing them is the costliest failure this app can make:
# the user spends months on cosmetic routines while a reversible cause goes
# undiagnosed. These escalate to a clinician rather than diagnosing anything.
# ---------------------------------------------------------------------------

def rule_possible_systemic_cause(obs, ctx) -> RuleResult:
    matched = any(
        ctx.get(k)
        for k in ("thyroid_condition", "iron_deficiency", "autoimmune_condition", "pcos")
    )
    return RuleResult(
        "history_possible_systemic_cause",
        "medium",
        matched,
        "A reported medical condition can itself cause hair loss and is often treatable; "
        "a clinician should assess whether it is contributing.",
    )


def rule_possible_telogen_effluvium(obs, ctx) -> RuleResult:
    """Sudden diffuse shedding 2-4 months after a physiological trigger.

    This pattern is usually self-limiting, but it is managed completely
    differently from patterned hair loss — so cosmetic 'regrowth' advice is the
    wrong answer and a clinician should confirm the cause.
    """
    trigger = any(
        ctx.get(k)
        for k in ("recent_illness", "recent_surgery", "major_stress", "rapid_weight_loss", "postpartum")
    )
    diffuse_or_sudden = ctx.get("pattern") == "diffuse" or ctx.get("onset") == "sudden"
    matched = bool(trigger and diffuse_or_sudden)
    return RuleResult(
        "history_possible_telogen_effluvium",
        "medium",
        matched,
        "Sudden or diffuse shedding after illness, surgery, major stress, weight loss or childbirth "
        "may reflect a temporary shedding phase, which is managed differently from patterned hair loss.",
    )


def rule_medication_associated_shedding(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("medication_associated_shedding"))
    return RuleResult(
        "history_medication_associated_shedding",
        "medium",
        matched,
        "A reported medication is associated with hair shedding. Never stop a prescribed medication "
        "on the basis of an app — discuss it with the prescriber.",
    )


def rule_traction_risk(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("tight_hairstyles")) and ctx.get("pattern") in ("receding", "patchy")
    return RuleResult(
        "history_traction_risk",
        "medium",
        matched,
        "Tight hairstyles with recession or patchy loss may indicate traction-related damage, "
        "which can become permanent if it continues.",
    )


def rule_endocrine_signals(obs, ctx) -> RuleResult:
    matched = bool(ctx.get("menstrual_irregularity")) and bool(ctx.get("body_hair_change"))
    return RuleResult(
        "history_endocrine_signals",
        "medium",
        matched,
        "Reported menstrual irregularity together with body-hair change warrants clinical assessment.",
    )


def rule_painful_or_itchy_scalp(obs, ctx) -> RuleResult:
    """Scarring alopecias often present with symptoms before visible signs.

    HIGH severity: scarring loss is permanent, and the window to prevent it is
    exactly when a photo still looks unremarkable.
    """
    matched = bool(ctx.get("scalp_pain")) and bool(ctx.get("scalp_condition"))
    return RuleResult(
        "history_symptomatic_scalp",
        "high",
        matched,
        "A painful scalp alongside a reported scalp condition can precede scarring hair loss, "
        "which is permanent once established. This needs in-person evaluation.",
    )


HISTORY_RULES: list[Callable] = [
    rule_possible_systemic_cause,
    rule_possible_telogen_effluvium,
    rule_medication_associated_shedding,
    rule_traction_risk,
    rule_endocrine_signals,
    rule_painful_or_itchy_scalp,
]


SKIN_RULES: list[Callable] = [
    rule_suspicious_lesion,
    rule_rapidly_changing_lesion,
    rule_severe_inflammation,
    rule_facial_swelling,
]
HAIR_RULES: list[Callable] = [
    rule_scarring_alopecia,
    rule_scalp_infection,
    rule_sudden_patchy_loss,
]
COMMON_RULES: list[Callable] = [
    rule_low_confidence,
    rule_poor_quality_passed,
    rule_minor,
    rule_systemic_symptoms,
]


def run_rules(domain: str, obs: list[Observation], ctx: dict) -> list[RuleResult]:
    rules = (HAIR_RULES if domain == "hair" else SKIN_RULES) + COMMON_RULES
    # History applies to hair, where systemic and drug-related causes are common
    # and invisible to a camera.
    if domain == "hair":
        rules = rules + HISTORY_RULES
    return [r(obs, ctx) for r in rules]
