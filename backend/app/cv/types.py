from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ObservationType = Literal["visual_observation", "ai_inference"]


@dataclass
class ConfidenceScore:
    """A confidence attached to every measurement / inference.

    value: 0..1
    basis: human-readable statement of what drove the confidence
    method: stable identifier of the method/version that produced it
    """

    value: float
    basis: str
    method: str

    def clamp(self) -> "ConfidenceScore":
        self.value = max(0.0, min(1.0, float(self.value)))
        return self


@dataclass
class Observation:
    """A single structured CV output. Never a diagnosis.

    We NEVER fabricate a numeric measurement without a confidence and a basis.

    `is_mock` and `validated` are DELIBERATELY SEPARATE, because they answer
    different questions and conflating them is how an unvalidated model quietly
    starts looking trustworthy:

      is_mock=True,  validated=False -> a heuristic stand-in (ships by default)
      is_mock=False, validated=False -> a real trained model that has NOT passed
                                        the stratified fairness evaluation
      is_mock=False, validated=True  -> a real model that has passed it

    Only the third may be presented without a "not validated" warning. There is
    no combination in which `validated=True` is set by anything other than a
    passing evaluation record.
    """

    kind: str
    confidence: ConfidenceScore
    value_num: float | None = None
    value_label: str | None = None
    unit: str | None = None
    model_name: str = ""
    model_version: str = ""
    is_mock: bool = True
    validated: bool = False
    observation_type: ObservationType = "visual_observation"


@dataclass
class ImageQualityReport:
    overall_pass: bool
    blur_score: float
    exposure_score: float
    overexposed_frac: float
    distance_ok: bool
    angle_ok: bool
    confidence: ConfidenceScore
    scalp_visibility: float | None = None
    reasons: list[str] = field(default_factory=list)
    retake_guidance: list[str] = field(default_factory=list)
    is_mock: bool = True


@dataclass
class SegmentationResult:
    masks: dict  # target -> mask handle (array or descriptor)
    areas: dict  # target -> fractional area 0..1
    confidence: ConfidenceScore
    is_mock: bool = True


@dataclass
class LocalizationResult:
    points: dict  # landmark name -> (x, y) normalized
    regions: dict  # region name -> (x0, y0, x1, y1) normalized bbox
    confidence: ConfidenceScore
    is_mock: bool = True


@dataclass
class AlignmentResult:
    transform: dict  # e.g. {"scale":..,"tx":..,"ty":..,"rot":..}
    quality: ConfidenceScore
    is_mock: bool = True


@dataclass
class OCRResult:
    raw_text: str
    fields: dict  # name, manufacturer, expiry, batch, ingredients[]
    confidence: ConfidenceScore
    is_mock: bool = True


@dataclass
class ImageInput:
    """Wraps raw image bytes plus optional decoded pixel data."""

    data: bytes
    view: str = ""
    width: int = 0
    height: int = 0
