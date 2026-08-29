from __future__ import annotations

from app.cv.base import Segmenter
from app.cv.imageio import HAS_PIXELS, DecodedImage
from app.cv.types import ConfidenceScore, ImageInput, SegmentationResult


class MockSegmenter(Segmenter):
    """Approximate hair / scalp / skin area fractions via luminance heuristics.

    NOT a trained segmentation model. Areas are apparent fractions with honest,
    reduced confidence. Real backend replaces this with a U-Net/SegFormer head.
    """

    VERSION = "mock-seg@0.1"

    def segment(self, img: ImageInput, targets: list[str]) -> SegmentationResult:
        d = DecodedImage(img.data)
        areas: dict[str, float] = {}
        masks: dict[str, str] = {}

        if d.real_pixels:
            g = d.gray
            mean = float(g.mean())
            std = float(g.std())
            bright = float((g > mean + 0.5 * std).mean())  # scalp/skin-like
            dark = float((g < mean - 0.3 * std).mean())    # hair-like
            for t in targets:
                if t == "hair":
                    areas[t] = round(min(1.0, dark), 3)
                elif t in ("scalp", "skin"):
                    areas[t] = round(min(1.0, bright), 3)
                else:
                    areas[t] = round(max(0.0, 1.0 - dark - bright), 3)
                masks[t] = f"heuristic-mask:{t}"
            conf = 0.6
            basis = "luminance clustering of scalp vs hair"
        else:
            for i, t in enumerate(targets):
                areas[t] = round(0.2 + 0.15 * ((i + 1) % 3), 3)
                masks[t] = f"pseudo-mask:{t}"
            conf = 0.3
            basis = "no pixel decoder; deterministic fallback"

        return SegmentationResult(
            masks=masks,
            areas=areas,
            confidence=ConfidenceScore(conf, basis, self.VERSION).clamp(),
            is_mock=True,
        )
