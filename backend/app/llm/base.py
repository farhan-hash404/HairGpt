from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExplanationContext:
    domain: str
    observations: list[dict]
    evidence: list[dict]
    safety_verdict: dict
    recommendations: list[dict]
    overall_confidence: float


@dataclass
class Explanation:
    observation: str
    reasoning: str
    confidence: dict  # {value, basis, method}
    evidence: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    summary: str = ""


class LLMProvider(ABC):
    @abstractmethod
    def explain(self, ctx: ExplanationContext) -> Explanation: ...
