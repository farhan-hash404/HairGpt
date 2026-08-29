from __future__ import annotations

from app.cv.base import ImageQualityGate
from app.cv.imageio import HAS_PIXELS, DecodedImage
from app.cv.types import ConfidenceScore, ImageInput, ImageQualityReport

# Thresholds are conservative heuristics, NOT clinically validated.
_BLUR_MIN = 0.35
_BRIGHT_LO = 0.22
_BRIGHT_HI = 0.85
_OVEREXP_MAX = 0.12
_ANGLE_SYM_MIN = 0.55
_DISTANCE_MIN = 0.30
_SCALP_MIN = 0.12  # hair only


class MockImageQualityGate(ImageQualityGate):
    """Heuristic image-quality gate. Detects blur, poor/over lighting, distance,
    angle, and (for hair) insufficient scalp visibility. Blocks bad images."""

    NAME = "mock-quality"
    VERSION = "mock-quality@0.1"

    def assess(self, img: ImageInput, view: str, domain: str) -> ImageQualityReport:
        d = DecodedImage(img.data)
        blur = d.blur_score()
        brightness = d.mean_brightness()
        overexp = d.overexposed_fraction()
        symmetry = d.symmetry()
        distance = d.size_proxy()
        scalp_vis = d.bright_parting_fraction() if domain == "hair" else None

        reasons: list[str] = []
        guidance: list[str] = []

        if blur < _BLUR_MIN:
            reasons.append("blur")
            guidance.append("Hold the camera steady and refocus before capturing.")
        if brightness < _BRIGHT_LO:
            reasons.append("too_dark")
            guidance.append("Move to brighter, even lighting.")
        if brightness > _BRIGHT_HI:
            reasons.append("too_bright")
            guidance.append("Reduce direct light or move away from the light source.")
        if overexp > _OVEREXP_MAX:
            reasons.append("overexposed")
            guidance.append("Avoid glare and harsh direct light; diffuse the lighting.")
        # NOTE: `distance` is a resolution-adequacy proxy, not true distance
        # estimation (which needs the landmark model in the real backend).
        distance_ok = distance >= _DISTANCE_MIN
        if not distance_ok:
            reasons.append("incorrect_distance")
            guidance.append("Move closer or use a higher-resolution photo so the region fills the guide outline.")
        angle_ok = symmetry >= _ANGLE_SYM_MIN
        if not angle_ok:
            reasons.append("incorrect_angle")
            guidance.append("Align the camera squarely with the guide outline.")
        if scalp_vis is not None and scalp_vis < _SCALP_MIN:
            reasons.append("low_scalp_visibility")
            guidance.append("Part the hair to expose more scalp in the frame.")

        overall_pass = len(reasons) == 0
        # Confidence in the QUALITY JUDGEMENT itself (not clinical). Lower when we
        # had no real pixels to analyze.
        conf_val = 0.85 if HAS_PIXELS else 0.4
        confidence = ConfidenceScore(
            value=conf_val,
            basis=("laplacian + exposure + symmetry heuristics" if HAS_PIXELS
                   else "no pixel decoder available; deterministic fallback"),
            method=self.VERSION,
        ).clamp()

        return ImageQualityReport(
            overall_pass=overall_pass,
            blur_score=round(blur, 3),
            exposure_score=round(brightness, 3),
            overexposed_frac=round(overexp, 3),
            distance_ok=distance_ok,
            angle_ok=angle_ok,
            scalp_visibility=None if scalp_vis is None else round(scalp_vis, 3),
            reasons=reasons,
            retake_guidance=guidance,
            confidence=confidence,
            is_mock=True,
        )
