from __future__ import annotations

from app.cv.base import FaceAnalyzer
from app.cv.imageio import HAS_PIXELS, DecodedImage
from app.cv.types import ConfidenceScore, ImageInput, Observation

# SkinGPT attributes described as IMAGE-BASED OBSERVATIONS, never diagnoses.
_ATTRS = [
    "oiliness",
    "dryness",
    "redness",
    "pigmentation",
    "acne_like_lesion_count",
    "texture",
    "pore_visibility",
    "fine_lines",
    "under_eye",
]


class MockFaceAnalyzer(FaceAnalyzer):
    """Approximate skin appearance attributes from channel/texture statistics.

    NO facial recognition, NO identity matching. Values are visible-appearance
    observations with confidence, not diagnoses.
    """

    VERSION = "mock-face@0.1"

    def analyze(self, img: ImageInput, view: str) -> list[Observation]:
        d = DecodedImage(img.data)
        obs: list[Observation] = []
        conf = 0.55 if HAS_PIXELS else 0.3

        if d.real_pixels:
            g = d.gray
            mean = float(g.mean()) / 255.0
            std = float(g.std()) / 255.0
            bright_frac = float((g > 200).mean())
            dark_frac = float((g < 60).mean())
        else:
            p = d._pseudo
            mean, std, bright_frac, dark_frac = p[0], p[1] * 0.3, p[2] * 0.2, p[3] * 0.2

        def ob(kind, value_num, label, ctype="visual_observation", cmul=1.0):
            return Observation(
                kind=kind,
                value_num=round(value_num, 3),
                value_label=label,
                unit="index",
                confidence=ConfidenceScore(
                    conf * cmul, "skin appearance statistics (apparent)", self.VERSION
                ).clamp(),
                model_name="mock-face",
                model_version=self.VERSION,
                is_mock=True,
                observation_type=ctype,
            )

        obs.append(ob("oiliness", bright_frac, "apparent surface shine" if bright_frac > 0.15 else "low apparent shine"))
        obs.append(ob("dryness", max(0.0, 0.4 - std), "possible dry texture" if std < 0.15 else "no obvious dryness"))
        obs.append(ob("redness", std, "some apparent unevenness" if std > 0.2 else "even tone appearance"))
        obs.append(ob("pigmentation", dark_frac, "apparent darker regions" if dark_frac > 0.12 else "even pigmentation appearance", "ai_inference"))
        obs.append(ob("texture", std, "textured appearance" if std > 0.22 else "smooth appearance"))
        obs.append(ob("pore_visibility", std * 0.8, "pores may be visible" if std > 0.2 else "pores not prominent"))
        obs.append(ob("fine_lines", std * 0.6, "possible fine lines" if std > 0.25 else "few apparent lines", "ai_inference", 0.8))
        obs.append(ob("under_eye", dark_frac * 0.9, "apparent under-eye shadowing" if dark_frac > 0.15 else "no obvious under-eye shadow", "ai_inference", 0.8))
        # A count-like observation kept explicitly low-confidence.
        obs.append(
            Observation(
                kind="acne_like_lesion_count",
                value_num=round(min(20.0, bright_frac * 40), 0),
                value_label="apparent acne-like spots (screening proxy, not a count of lesions)",
                unit="count_estimate",
                confidence=ConfidenceScore(conf * 0.6, "bright-spot proxy", self.VERSION).clamp(),
                model_name="mock-face",
                model_version=self.VERSION,
                is_mock=True,
                observation_type="ai_inference",
            )
        )
        return obs
