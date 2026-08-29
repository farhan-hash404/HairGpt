from __future__ import annotations

from datetime import datetime, timezone

from app.cv.manifest import (
    MAX_CALIBRATION_ERROR,
    MAX_WORST_BEST_GAP,
    MIN_SAMPLES_PER_GROUP,
    MIN_WORST_GROUP_SCORE,
    ValidationRecord,
    validation_passes,
)
from app.eval.metrics import SUBGROUP_AXES, EvaluationResult


def build_validation_record(result: EvaluationResult, dataset_id: str) -> ValidationRecord:
    """Turn an evaluation into the record the manifest stores.

    The pass/fail decision is derived by the SAME function the loader uses, so a
    model can never be promoted by one code path and rejected by the other.
    """
    record = ValidationRecord(
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        dataset_id=dataset_id,
        overall_score=result.overall_score,
        worst_group_score=result.worst_group.mean_score if result.worst_group else 0.0,
        worst_best_gap=result.worst_best_gap,
        calibration_error=result.calibration_error,
        subgroup_axes=list(SUBGROUP_AXES),
        min_group_samples=result.min_group_samples,
    )
    passed, failures = validation_passes(record)
    record.passed = passed
    record.failures = failures
    return record


def format_report(result: EvaluationResult, record: ValidationRecord, model_name: str) -> str:
    """A human-readable stratified report.

    Aggregate score is shown LAST and never alone — the per-subgroup table is
    the point, and the worst group is what decides promotion.
    """
    lines: list[str] = []
    lines.append(f"Stratified evaluation — {model_name}")
    lines.append("=" * 72)
    lines.append(f"Samples: {result.total_samples}   Dataset: {record.dataset_id}")
    lines.append("")

    current_axis = None
    for group in result.groups:
        if group.axis != current_axis:
            current_axis = group.axis
            lines.append(f"  {group.axis}")
        flag = ""
        if group.samples < MIN_SAMPLES_PER_GROUP:
            flag = f"  <- only {group.samples} samples"
        elif group.mean_score < MIN_WORST_GROUP_SCORE:
            flag = "  <- BELOW THRESHOLD"
        lines.append(f"    {group.group:<20} n={group.samples:<5} score={group.mean_score:.3f}{flag}")

    lines.append("")
    lines.append("-" * 72)
    worst = result.worst_group
    best = result.best_group
    if worst and best:
        lines.append(f"Worst group : {worst.axis}/{worst.group} = {worst.mean_score:.3f}")
        lines.append(f"Best group  : {best.axis}/{best.group} = {best.mean_score:.3f}")
        lines.append(f"Gap         : {result.worst_best_gap:.3f} (max allowed {MAX_WORST_BEST_GAP})")
    lines.append(
        f"Calibration : {result.calibration_error:.3f} ECE (max allowed {MAX_CALIBRATION_ERROR})"
    )
    lines.append(f"Aggregate   : {result.overall_score:.3f}  <- not sufficient on its own")
    lines.append("")

    if record.passed:
        lines.append("RESULT: PASSED — this model may be marked validated.")
    else:
        lines.append("RESULT: NOT VALIDATED")
        for failure in record.failures:
            lines.append(f"  - {failure}")
        lines.append("")
        lines.append("The model may still be deployed, but its output will be labelled")
        lines.append("unvalidated and its confidence capped.")

    return "\n".join(lines)
