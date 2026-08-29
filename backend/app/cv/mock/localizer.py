from __future__ import annotations

from app.cv.base import Localizer
from app.cv.imageio import DecodedImage
from app.cv.types import ConfidenceScore, ImageInput, LocalizationResult, SegmentationResult

# Which landmark/region each hair view is responsible for.
_VIEW_REGION = {
    "front_hairline": ("hairline", (0.15, 0.05, 0.85, 0.35)),
    "left_temple": ("left_temple", (0.05, 0.15, 0.45, 0.55)),
    "right_temple": ("right_temple", (0.55, 0.15, 0.95, 0.55)),
    "top": ("mid_scalp", (0.2, 0.2, 0.8, 0.7)),
    "crown": ("crown", (0.25, 0.3, 0.75, 0.85)),
    "sides": ("side", (0.05, 0.25, 0.95, 0.75)),
    "back": ("occipital", (0.2, 0.2, 0.8, 0.8)),
}


class MockLocalizer(Localizer):
    """Region/landmark heuristics for hairline, temples, and crown.

    Provides approximate normalized regions per capture view. Real backend
    replaces this with a landmark model. Never asserts exact measurements.
    """

    VERSION = "mock-loc@0.1"

    def localize(self, img: ImageInput, seg: SegmentationResult, view: str) -> LocalizationResult:
        d = DecodedImage(img.data)
        name, bbox = _VIEW_REGION.get(view, ("region", (0.1, 0.1, 0.9, 0.9)))
        points: dict[str, tuple[float, float]] = {}
        regions = {name: bbox}

        # Approximate a hairline point as the top edge of the hair region.
        if view == "front_hairline":
            points["hairline_center"] = (0.5, 0.18)
            points["hairline_left"] = (0.25, 0.22)
            points["hairline_right"] = (0.75, 0.22)
        elif view in ("left_temple", "right_temple"):
            points[name] = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        elif view == "crown":
            points["crown_center"] = (0.5, 0.55)

        conf = seg.confidence.value * (0.85 if d.real_pixels else 0.5)
        return LocalizationResult(
            points=points,
            regions=regions,
            confidence=ConfidenceScore(
                conf, "region heuristic conditioned on segmentation", self.VERSION
            ).clamp(),
            is_mock=True,
        )
