from __future__ import annotations

from app.cv.base import Aligner
from app.cv.imageio import HAS_PIXELS, DecodedImage
from app.cv.types import AlignmentResult, ConfidenceScore, ImageInput


class MockAligner(Aligner):
    """Standardized alignment for longitudinal comparison.

    Produces a normalization transform (scale/translation) toward a canonical
    pose so photos captured weeks/months apart can be overlaid. Returns an
    HONEST low quality when it cannot reliably align (e.g. no pixels).
    """

    VERSION = "mock-align@0.1"

    def align(self, img: ImageInput, view: str, reference: dict | None) -> AlignmentResult:
        d = DecodedImage(img.data)
        if d.real_pixels:
            g = d.gray
            # Centroid of bright region as a coarse anchor; scale from spread.
            h, w = g.shape
            ys, xs = (g > g.mean()).nonzero()
            if len(xs) > 0:
                cx, cy = float(xs.mean()) / w, float(ys.mean()) / h
                spread = float(xs.std()) / w if len(xs) > 1 else 0.25
            else:
                cx, cy, spread = 0.5, 0.5, 0.25
            transform = {
                "scale": round(0.25 / max(spread, 1e-3), 3),
                "tx": round(0.5 - cx, 3),
                "ty": round(0.5 - cy, 3),
                "rot": 0.0,
            }
            quality = 0.6
            basis = "centroid + spread normalization"
        else:
            transform = {"scale": 1.0, "tx": 0.0, "ty": 0.0, "rot": 0.0}
            quality = 0.2
            basis = "no pixel decoder; identity transform (unreliable)"

        return AlignmentResult(
            transform=transform,
            quality=ConfidenceScore(quality, basis, self.VERSION).clamp(),
            is_mock=True,
        )
