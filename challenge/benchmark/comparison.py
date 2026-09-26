"""Teacher-to-Student metric comparison for the B2 benchmark."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from .metric_evidence import GATE_METRICS


class ComparisonError(ValueError):
    """Raised when Teacher and Student evidence cannot be compared safely."""


MATCH_FIELDS = (
    "benchmark_manifest_sha256",
    "policy_manifest_sha256",
    "case_set_digest",
    "evaluator_git_sha",
    "sample_count",
)


def compare_teacher_student(
    teacher: Mapping[str, Any],
    student: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare compatible Teacher and Student evaluation artifacts."""

    if teacher.get("evaluation_role") != "teacher":
        raise ComparisonError(
            "Teacher artifact must have evaluation_role='teacher'"
        )

    if student.get("evaluation_role") != "student":
        raise ComparisonError(
            "Student artifact must have evaluation_role='student'"
        )

    for field in MATCH_FIELDS:
        teacher_value = teacher.get(field)
        student_value = student.get(field)

        if teacher_value is None or student_value is None:
            raise ComparisonError(
                f"comparison requires identity field {field}"
            )

        if teacher_value != student_value:
            raise ComparisonError(
                f"Teacher and Student {field} do not match"
            )

    teacher_metrics = teacher.get("metrics")
    student_metrics = student.get("metrics")

    if not isinstance(teacher_metrics, Mapping):
        raise ComparisonError(
            "Teacher artifact requires metrics"
        )

    if not isinstance(student_metrics, Mapping):
        raise ComparisonError(
            "Student artifact requires metrics"
        )

    comparisons: dict[str, dict[str, float | None]] = {}

    for metric in GATE_METRICS:
        teacher_value = _metric_value(
            teacher_metrics,
            metric,
            role="Teacher",
        )
        student_value = _metric_value(
            student_metrics,
            metric,
            role="Student",
        )

        absolute_drop = teacher_value - student_value

        relative_drop = (
            None
            if teacher_value == 0.0
            else absolute_drop / teacher_value
        )

        comparisons[metric] = {
            "teacher": teacher_value,
            "student": student_value,
            "absolute_drop": absolute_drop,
            "percentage_point_drop": absolute_drop * 100.0,
            "relative_drop": relative_drop,
        }

    return {
        "teacher_evaluation_id": teacher.get("evaluation_id"),
        "student_evaluation_id": student.get("evaluation_id"),
        "benchmark_manifest_sha256": teacher[
            "benchmark_manifest_sha256"
        ],
        "policy_manifest_sha256": teacher[
            "policy_manifest_sha256"
        ],
        "case_set_digest": teacher["case_set_digest"],
        "evaluator_git_sha": teacher["evaluator_git_sha"],
        "sample_count": teacher["sample_count"],
        "metrics": comparisons,
    }


def _metric_value(
    metrics: Mapping[str, Any],
    metric: str,
    *,
    role: str,
) -> float:
    if metric not in metrics:
        raise ComparisonError(
            f"{role} artifact is missing Gate metric {metric!r}"
        )

    value = metrics[metric]

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ComparisonError(
            f"{role} Gate metric {metric!r} must be numeric"
        )

    result = float(value)

    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ComparisonError(
            f"{role} Gate metric {metric!r} must be finite and in [0, 1]"
        )

    return result


__all__ = [
    "ComparisonError",
    "MATCH_FIELDS",
    "compare_teacher_student",
]
