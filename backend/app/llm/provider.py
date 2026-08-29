from __future__ import annotations

import json
import logging

from app.core.config import settings
from app.llm.base import Explanation, ExplanationContext, LLMProvider
from app.llm.prompts import REFERRAL_INSTRUCTION, SYSTEM_PROMPT
from app.llm.safety_filter import scrub_output

log = logging.getLogger("hairgpt.llm")

_BASE_LIMITATIONS = [
    "This is an image-based observation, not a medical diagnosis.",
    "Results may be affected by lighting, camera, and angle.",
]
_MOCK_LIMITATION = "Produced by mock inference — NOT medically validated."


def _common_limitations(ctx: ExplanationContext) -> list[str]:
    lims = list(_BASE_LIMITATIONS)
    if any(o.get("is_mock") for o in ctx.observations):
        lims.append(_MOCK_LIMITATION)
    if ctx.overall_confidence < 0.5:
        lims.append("Overall confidence is low; interpret with caution.")
    return lims


class MockLLMProvider(LLMProvider):
    """Deterministic explanation generator. Requires no external API.

    Composes the explanation strictly from the structured inputs — it cannot
    invent findings because it only templates over what it is given.
    """

    def explain(self, ctx: ExplanationContext) -> Explanation:
        if ctx.safety_verdict.get("verdict") == "refer":
            return scrub_output(
                Explanation(
                    observation="The image observations include a feature we flag for professional review.",
                    reasoning=(
                        "A deterministic safety rule was triggered, so cosmetic/self-treatment guidance is "
                        "withheld. " + REFERRAL_INSTRUCTION
                    ),
                    confidence={"value": 0.9, "basis": "safety rule match", "method": "safety_v1"},
                    evidence=ctx.evidence[:1],
                    limitations=_common_limitations(ctx),
                    summary=ctx.safety_verdict.get("message", "Please seek professional evaluation."),
                )
            )

        obs_lines = []
        for o in ctx.observations[:6]:
            val = o.get("value_label") or (
                f"{o.get('value_num')}{(' ' + o['unit']) if o.get('unit') else ''}"
                if o.get("value_num") is not None
                else "observed"
            )
            tag = "observation" if o.get("observation_type") == "visual_observation" else "AI inference"
            obs_lines.append(f"- {o['kind'].replace('_', ' ')}: {val} ({tag}, confidence {o['confidence']['value']:.0%})")
        observation = "Here is what the images appear to show:\n" + "\n".join(obs_lines)

        reasoning = (
            "These are visual observations and AI inferences from your photos. Where we suggest care steps, "
            "they are drawn from the cited medical sources and are general, non-prescription measures. "
            "A clinician is the only one who can make a diagnosis."
        )

        summary_bits = [r["title"] for r in ctx.recommendations[:3]]
        summary = "Suggested next steps: " + "; ".join(summary_bits) if summary_bits else (
            "No specific concerns were flagged; keep up gentle care and re-scan periodically."
        )

        return scrub_output(
            Explanation(
                observation=observation,
                reasoning=reasoning,
                confidence={
                    "value": round(ctx.overall_confidence, 2),
                    "basis": "conservative aggregate of stage confidences",
                    "method": "agg_v1",
                },
                evidence=ctx.evidence[:5],
                limitations=_common_limitations(ctx),
                summary=summary,
            )
        )


class AnthropicLLMProvider(LLMProvider):  # pragma: no cover - requires API key
    """Real explanation generator. Still constrained: the safety verdict and
    recommendations are computed BEFORE this runs, and the output is scrubbed after."""

    def __init__(self):
        import anthropic

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.llm_model

    def explain(self, ctx: ExplanationContext) -> Explanation:
        mock = MockLLMProvider().explain(ctx)  # fallback skeleton
        try:
            user_payload = {
                "domain": ctx.domain,
                "observations": ctx.observations,
                "evidence": ctx.evidence,
                "safety_verdict": ctx.safety_verdict,
                "recommendations": ctx.recommendations,
                "overall_confidence": ctx.overall_confidence,
            }
            instruction = REFERRAL_INSTRUCTION if ctx.safety_verdict.get("verdict") == "refer" else (
                "Write 'observation', 'reasoning', and 'summary' fields grounded only in the payload."
            )
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": instruction + "\n\n" + json.dumps(user_payload)}],
            )
            text = msg.content[0].text if msg.content else ""
            # Keep structured fields; use the model text as the human-facing narrative.
            mock.reasoning = text or mock.reasoning
        except Exception as exc:
            log.warning("Anthropic LLM failed (%s); using deterministic explanation", exc)
        return scrub_output(mock)


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        try:
            return AnthropicLLMProvider()
        except Exception as exc:
            log.warning("LLM provider init failed (%s); using mock", exc)
    return MockLLMProvider()
