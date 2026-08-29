from __future__ import annotations

from abc import ABC, abstractmethod

from app.cv.types import (
    AlignmentResult,
    ImageInput,
    ImageQualityReport,
    LocalizationResult,
    OCRResult,
    Observation,
    SegmentationResult,
)

# Every capability is an interface with a mock (default) and a real slot.
# The application depends ONLY on these ABCs — swapping models is a config change.


class ImageQualityGate(ABC):
    @abstractmethod
    def assess(self, img: ImageInput, view: str, domain: str) -> ImageQualityReport: ...


class Segmenter(ABC):
    @abstractmethod
    def segment(self, img: ImageInput, targets: list[str]) -> SegmentationResult: ...


class Localizer(ABC):
    @abstractmethod
    def localize(self, img: ImageInput, seg: SegmentationResult, view: str) -> LocalizationResult: ...


class MetricEstimator(ABC):
    @abstractmethod
    def estimate(
        self, img: ImageInput, seg: SegmentationResult, loc: LocalizationResult, view: str
    ) -> list[Observation]: ...


class FaceAnalyzer(ABC):
    @abstractmethod
    def analyze(self, img: ImageInput, view: str) -> list[Observation]: ...


class Aligner(ABC):
    @abstractmethod
    def align(self, img: ImageInput, view: str, reference: dict | None) -> AlignmentResult: ...


class OCRExtractor(ABC):
    @abstractmethod
    def extract(self, img: ImageInput) -> OCRResult: ...
