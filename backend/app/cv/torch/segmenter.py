from __future__ import annotations

import logging

from app.cv.base import Segmenter
from app.cv.manifest import ModelSpec
from app.cv.torch.loader import load_checkpoint, preprocess, require_torch
from app.cv.types import ConfidenceScore, ImageInput, SegmentationResult

log = logging.getLogger("hairgpt.cv.torch")


class TorchSegmenter(Segmenter):
    """Semantic segmentation of hair / scalp / skin from a trained checkpoint.

    The model is expected to output per-class logits shaped (1, C, H, W), with
    class order given by `spec.labels`. Confidence is derived from the model's
    own softmax margin rather than assumed — an uncertain mask must report as
    uncertain, and it is capped when the model is not validated.
    """

    def __init__(self, spec: ModelSpec, model_dir: str):
        self.spec = spec
        self.model = load_checkpoint(spec, model_dir)
        self.validated = spec.is_validated

    def segment(self, img: ImageInput, targets: list[str]) -> SegmentationResult:
        torch = require_torch()
        tensor = preprocess(img.data, self.spec.input_size)

        with torch.no_grad():
            logits = self.model(tensor)
            if isinstance(logits, dict):  # torchvision segmentation heads
                logits = logits["out"]
            probs = torch.softmax(logits, dim=1)[0]  # (C, H, W)

        labels = self.spec.labels or [f"class_{i}" for i in range(probs.shape[0])]
        winners = probs.argmax(dim=0)

        areas: dict[str, float] = {}
        masks: dict[str, str] = {}
        total = float(winners.numel())
        for index, label in enumerate(labels):
            if label not in targets:
                continue
            areas[label] = round(float((winners == index).sum()) / total, 4)
            masks[label] = f"{self.spec.name}@{self.spec.version}:{label}"

        # Any requested target the model does not predict is reported as absent
        # rather than silently omitted.
        for target in targets:
            areas.setdefault(target, 0.0)
            masks.setdefault(target, f"{self.spec.name}:unsupported")

        # Mean top-class probability: how decisively the model assigned pixels.
        top_probability = float(probs.max(dim=0).values.mean())

        confidence = ConfidenceScore(
            value=top_probability if self.validated else min(top_probability, 0.6),
            basis=(
                "mean top-class softmax probability"
                if self.validated
                else "mean top-class softmax probability, capped: model not validated"
            ),
            method=f"{self.spec.name}@{self.spec.version}",
        ).clamp()

        return SegmentationResult(masks=masks, areas=areas, confidence=confidence, is_mock=False)
