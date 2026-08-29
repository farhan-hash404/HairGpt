from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.cv.types import Observation
from app.safety.rules import RuleResult, run_rules

REFERRAL_MESSAGE = (
    "Based on the image observations, we recommend evaluation by a qualified "
    "clinician (e.g. a dermatologist) rather than self-treatment. HairGPT provides "
    "image-based observations only and cannot diagnose."
)


@dataclass
class SafetyVerdict:
    verdict: str  # ok | caution | refer
    red_flags: list[str] = field(default_factory=list)
    triggered_rules: list[dict] = field(default_factory=list)
    suppressed_cosmetic: bool = False
    message: str = ""

    @property
    def allows_cosmetic(self) -> bool:
        return not self.suppressed_cosmetic


def evaluate(domain: str, observations: list[Observation], ctx: dict | None = None) -> SafetyVerdict:
    """Deterministic safety evaluation. Sits ABOVE the LLM and can hard-override it.

    - Any HIGH-severity flag -> verdict='refer' and cosmetic recommendations are
      suppressed entirely (the LLM never receives them, so it cannot reintroduce them).
    - Any MEDIUM flag -> verdict='caution' (language is downgraded downstream).
    - On error, fail-safe to at least 'caution' when SAFETY_STRICT.
    """
    ctx = ctx or {}
    try:
        results: list[RuleResult] = run_rules(domain, observations, ctx)
    except Exception:
        if settings.safety_strict:
            return SafetyVerdict(
                verdict="caution",
                message="Safety evaluation degraded; treating results cautiously.",
            )
        raise

    triggered = [r for r in results if r.matched]
    high = [r for r in triggered if r.severity == "high"]
    medium = [r for r in triggered if r.severity == "medium"]

    triggered_dump = [
        {"code": r.code, "severity": r.severity, "rationale": r.rationale} for r in triggered
    ]

    if high:
        return SafetyVerdict(
            verdict="refer",
            red_flags=[r.code for r in high],
            triggered_rules=triggered_dump,
            suppressed_cosmetic=True,
            message=REFERRAL_MESSAGE,
        )
    if medium:
        return SafetyVerdict(
            verdict="caution",
            red_flags=[r.code for r in medium],
            triggered_rules=triggered_dump,
            suppressed_cosmetic=False,
            message="Some findings suggest caution. Consider discussing with a clinician.",
        )
    return SafetyVerdict(
        verdict="ok",
        triggered_rules=triggered_dump,
        message="No red flags detected in the image observations.",
    )
