from __future__ import annotations

from app.cv.base import MetricEstimator
from app.cv.imageio import HAS_PIXELS, DecodedImage
from app.cv.types import (
    ConfidenceScore,
    ImageInput,
    LocalizationResult,
    Observation,
    SegmentationResult,
)


class MockMetricEstimator(MetricEstimator):
    """Derives apparent scalp visibility, coverage/density observations.

    Every value carries confidence and a basis. We NEVER emit an exact clinical
    measurement — labels are qualitative and values are 'apparent' fractions.
    """

    VERSION = "mock-metric@0.1"

    def estimate(
        self, img: ImageInput, seg: SegmentationResult, loc: LocalizationResult, view: str
    ) -> list[Observation]:
        d = DecodedImage(img.data)
        obs: list[Observation] = []
        base_conf = seg.confidence.value * (0.9 if HAS_PIXELS else 0.5)

        scalp_area = seg.areas.get("scalp", seg.areas.get("skin", 0.0))
        hair_area = seg.areas.get("hair", 0.0)

        # Scalp visibility (apparent).
        obs.append(
            Observation(
                kind="scalp_visibility",
                value_num=round(min(1.0, scalp_area), 3),
                unit="fraction",
                confidence=ConfidenceScore(
                    base_conf, "scalp mask area / analyzed region", self.VERSION
                ).clamp(),
                model_name="mock-metric",
                model_version=self.VERSION,
                is_mock=True,
                observation_type="visual_observation",
            )
        )

        # Apparent hair coverage.
        coverage = min(1.0, hair_area)
        obs.append(
            Observation(
                kind="apparent_coverage",
                value_num=round(coverage, 3),
                unit="fraction",
                confidence=ConfidenceScore(
                    base_conf * 0.9, "hair mask area / analyzed region", self.VERSION
                ).clamp(),
                model_name="mock-metric",
                model_version=self.VERSION,
                is_mock=True,
                observation_type="visual_observation",
            )
        )

        # Apparent density (qualitative label derived from texture density proxy).
        density_val = round(min(1.0, coverage * (1.0 - scalp_area * 0.5)), 3)
        label = "sparse" if density_val < 0.35 else "moderate" if density_val < 0.65 else "dense"
        obs.append(
            Observation(
                kind="apparent_density",
                value_num=density_val,
                value_label=f"apparent {label}",
                unit="index",
                confidence=ConfidenceScore(
                    base_conf * 0.75,
                    "texture-density proxy within hair mask (apparent, not follicular count)",
                    self.VERSION,
                ).clamp(),
                model_name="mock-metric",
                model_version=self.VERSION,
                is_mock=True,
                observation_type="ai_inference",
            )
        )

        # Region-specific observation for hairline / crown views.
        if view == "front_hairline":
            obs.append(
                Observation(
                    kind="hairline_position",
                    value_label="apparent hairline localized (see limitations)",
                    confidence=ConfidenceScore(
                        loc.confidence.value * 0.85, "hairline region heuristic", self.VERSION
                    ).clamp(),
                    model_name="mock-metric",
                    model_version=self.VERSION,
                    is_mock=True,
                    observation_type="ai_inference",
                )
            )
        if view == "crown":
            obs.append(
                Observation(
                    kind="crown_density",
                    value_num=density_val,
                    value_label=f"crown appears {label}",
                    unit="index",
                    confidence=ConfidenceScore(
                        base_conf * 0.7, "crown region density proxy", self.VERSION
                    ).clamp(),
                    model_name="mock-metric",
                    model_version=self.VERSION,
                    is_mock=True,
                    observation_type="ai_inference",
                )
            )

        return obs
