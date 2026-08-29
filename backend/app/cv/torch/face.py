from __future__ import annotations

import logging

from app.cv.base import FaceAnalyzer
from app.cv.manifest import ModelSpec
from app.cv.torch.loader import load_checkpoint, preprocess, require_torch
from app.cv.types import ConfidenceScore, ImageInput, Observation

log = logging.getLogger("hairgpt.cv.torch")

# Attributes that are inferences about appearance rather than direct readings.
_INFERRED = {"pigmentation", "fine_lines", "under_eye", "acne_like_lesion_count"}


class TorchFaceAnalyzer(FaceAnalyzer):
    """Multi-head skin-attribute regression from a trained checkpoint.

    NO facial recognition and no identity embedding is computed or stored. The
    model outputs one scalar per attribute in `spec.labels`; a second output
    head, if present, is read as per-attribute predictive uncertainty.
    """

    def __init__(self, spec: ModelSpec, model_dir: str):
        self.spec = spec
        self.model = load_checkpoint(spec, model_dir)
        self.validated = spec.is_validated

    def analyze(self, img: ImageInput, view: str) -> list[Observation]:
        torch = require_torch()
        tensor = preprocess(img.data, self.spec.input_size)

        with torch.no_grad():
            output = self.model(tensor)

        # Accept either a plain tensor of values, or (values, uncertainty).
        uncertainty = None
        if isinstance(output, (tuple, list)) and len(output) == 2:
            values, uncertainty = output
        elif isinstance(output, dict):
            values = output.get("values", output.get("out"))
            uncertainty = output.get("uncertainty")
        else:
            values = output

        values = values.reshape(-1).tolist()
        uncertainties = uncertainty.reshape(-1).tolist() if uncertainty is not None else None
        labels = self.spec.labels or [f"attribute_{i}" for i in range(len(values))]

        observations: list[Observation] = []
        for index, label in enumerate(labels):
            if index >= len(values):
                break

            if uncertainties is not None and index < len(uncertainties):
                # Higher predicted uncertainty -> lower confidence.
                confidence_value = max(0.0, 1.0 - float(uncertainties[index]))
                basis = "model-predicted uncertainty"
            else:
                # A model that reports no uncertainty does not get to look
                # confident: we cap it rather than inventing a number.
                confidence_value = 0.5
                basis = "model reports no uncertainty; fixed conservative value"

            if not self.validated:
                confidence_value = min(confidence_value, 0.6)
                basis += "; capped: model not validated"

            observations.append(
                Observation(
                    kind=label,
                    value_num=round(float(values[index]), 3),
                    unit="index",
                    confidence=ConfidenceScore(
                        confidence_value, basis, f"{self.spec.name}@{self.spec.version}"
                    ).clamp(),
                    model_name=self.spec.name,
                    model_version=self.spec.version,
                    is_mock=False,
                    validated=self.validated,
                    observation_type="ai_inference" if label in _INFERRED else "visual_observation",
                )
            )
        return observations
