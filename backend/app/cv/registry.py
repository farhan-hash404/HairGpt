from __future__ import annotations

import logging

from app.core.config import settings
from app.cv.base import (
    Aligner,
    FaceAnalyzer,
    ImageQualityGate,
    Localizer,
    MetricEstimator,
    OCRExtractor,
    Segmenter,
)
from app.cv.mock.aligner import MockAligner
from app.cv.mock.face import MockFaceAnalyzer
from app.cv.mock.localizer import MockLocalizer
from app.cv.mock.metrics import MockMetricEstimator
from app.cv.mock.ocr import MockOCRExtractor
from app.cv.mock.quality import MockImageQualityGate
from app.cv.mock.segmenter import MockSegmenter

log = logging.getLogger("hairgpt.cv")

_MOCK = {
    "quality": MockImageQualityGate,
    "segmenter": MockSegmenter,
    "localizer": MockLocalizer,
    "metrics": MockMetricEstimator,
    "face": MockFaceAnalyzer,
    "aligner": MockAligner,
    "ocr": MockOCRExtractor,
}


def _real(capability: str):
    """Load a real (torch) implementation, falling back to mock when unavailable.

    The torch backend logs its own specific reason (no manifest entry, missing
    checkpoint, torch not installed), so returning None here is an expected
    outcome rather than an error — we do not re-log a vaguer version of it.
    Unexpected exceptions ARE logged loudly: we never silently substitute a
    heuristic for a model the operator believes is running.
    """
    try:
        from app.cv import torch as torch_backend  # noqa: local import; optional

        impl = torch_backend.get(capability, settings.cv_model_dir)
        if impl is not None:
            log.info("CV[%s]: using REAL torch backend", capability)
            return impl
    except Exception as exc:  # pragma: no cover - depends on optional stack
        log.warning(
            "CV[%s]: torch backend raised (%s) -> FALLING BACK TO MOCK (not validated)",
            capability,
            exc,
        )
    return _MOCK[capability]()


def _get(capability: str):
    if settings.cv_backend == "torch":
        return _real(capability)
    return _MOCK[capability]()


def get_quality_gate() -> ImageQualityGate:
    return _get("quality")


def get_segmenter() -> Segmenter:
    return _get("segmenter")


def get_localizer() -> Localizer:
    return _get("localizer")


def get_metric_estimator() -> MetricEstimator:
    return _get("metrics")


def get_face_analyzer() -> FaceAnalyzer:
    return _get("face")


def get_aligner() -> Aligner:
    return _get("aligner")


def get_ocr() -> OCRExtractor:
    return _get("ocr")
