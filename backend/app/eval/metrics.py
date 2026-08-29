from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Sample:
    """One evaluated example with the subgroup metadata fairness requires.

    Every axis is mandatory. A dataset that cannot say which skin tones or which
    devices it covers cannot support a fairness claim, so the harness refuses it
    rather than reporting a misleading aggregate.
    """

    sample_id: str
    score: float  # per-sample quality: IoU, 1-normalized-error, or accuracy
    confidence: float  # the model's own confidence for this sample
    correct: bool  # whether the prediction was acceptable, for calibration
    fitzpatrick: str
    age_group: str
    sex: str
    device_make: str
    lighting: str
    geography: str

    def subgroup(self, axis: str) -> str:
        return getattr(self, axis)


SUBGROUP_AXES = ["fitzpatrick", "age_group", "sex", "device_make", "lighting", "geography"]


@dataclass
class GroupResult:
    axis: str
    group: str
    samples: int
    mean_score: float


@dataclass
class EvaluationResult:
    overall_score: float
    calibration_error: float
    groups: list[GroupResult] = field(default_factory=list)
    total_samples: int = 0

    @property
    def worst_group(self) -> GroupResult | None:
        return min(self.groups, key=lambda g: g.mean_score) if self.groups else None

    @property
    def best_group(self) -> GroupResult | None:
        return max(self.groups, key=lambda g: g.mean_score) if self.groups else None

    @property
    def worst_best_gap(self) -> float:
        if not self.groups:
            return 1.0
        return round(self.best_group.mean_score - self.worst_group.mean_score, 4)

    @property
    def min_group_samples(self) -> int:
        return min((g.samples for g in self.groups), default=0)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def iou(predicted: set, actual: set) -> float:
    """Intersection over union for mask or region comparison."""
    if not predicted and not actual:
        return 1.0
    union = predicted | actual
    return len(predicted & actual) / len(union) if union else 0.0


def normalized_error_score(predicted: float, actual: float, scale: float = 1.0) -> float:
    """Map an absolute error onto a 0..1 score where 1 is perfect."""
    if scale <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(predicted - actual) / scale)


def expected_calibration_error(samples: list[Sample], bins: int = 10) -> float:
    """ECE: the average gap between stated confidence and observed accuracy.

    A model that says "90% confident" should be right about 90% of the time. In
    a health product an overconfident model is more dangerous than a weak one,
    because the interface presents confidence as a reason to trust the result.
    """
    if not samples:
        return 1.0

    total_error = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        bucket = [
            s for s in samples if (low < s.confidence <= high) or (index == 0 and s.confidence == 0)
        ]
        if not bucket:
            continue
        avg_confidence = mean([s.confidence for s in bucket])
        accuracy = mean([1.0 if s.correct else 0.0 for s in bucket])
        total_error += (len(bucket) / len(samples)) * abs(avg_confidence - accuracy)

    return round(total_error, 4)


def evaluate(samples: list[Sample], min_group_samples: int = 1) -> EvaluationResult:
    """Compute overall and per-subgroup scores.

    Groups smaller than `min_group_samples` are still reported — under-covered
    groups are a finding, not something to quietly drop. The promotion gate
    penalises them via `min_group_samples`.
    """
    groups: list[GroupResult] = []
    for axis in SUBGROUP_AXES:
        buckets: dict[str, list[float]] = {}
        for sample in samples:
            buckets.setdefault(sample.subgroup(axis), []).append(sample.score)
        for group, scores in sorted(buckets.items()):
            groups.append(
                GroupResult(axis=axis, group=group, samples=len(scores), mean_score=round(mean(scores), 4))
            )

    return EvaluationResult(
        overall_score=round(mean([s.score for s in samples]), 4),
        calibration_error=expected_calibration_error(samples),
        groups=groups,
        total_samples=len(samples),
    )
