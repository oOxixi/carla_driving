import copy

import pytest

from challenge.benchmark.comparison import (
    ComparisonError,
    compare_teacher_student,
)
from challenge.benchmark.metric_evidence import (
    GATE_METRICS,
)


def _artifact(role: str) -> dict:
    return {
        "evaluation_id": f"{role}-001",
        "evaluation_role": role,
        "benchmark_manifest_sha256": "a" * 64,
        "policy_manifest_sha256": "b" * 64,
        "case_set_digest": "c" * 64,
        "evaluator_git_sha": "d" * 40,
        "sample_count": 100,
        "metrics": {
            metric: 0.9
            for metric in GATE_METRICS
        },
    }


def test_comparison_reports_absolute_percentage_point_and_relative_drop():
    teacher = _artifact("teacher")
    student = _artifact("student")

    metric = GATE_METRICS[0]

    teacher["metrics"][metric] = 0.9
    student["metrics"][metric] = 0.885

    result = compare_teacher_student(
        teacher,
        student,
    )

    comparison = result["metrics"][metric]

    assert comparison["teacher"] == pytest.approx(0.9)
    assert comparison["student"] == pytest.approx(0.885)
    assert comparison["absolute_drop"] == pytest.approx(0.015)
    assert comparison["percentage_point_drop"] == pytest.approx(1.5)
    assert comparison["relative_drop"] == pytest.approx(
        0.015 / 0.9
    )


def test_comparison_rejects_identity_mismatch():
    teacher = _artifact("teacher")
    student = _artifact("student")

    student["case_set_digest"] = "e" * 64

    with pytest.raises(
        ComparisonError,
        match="case_set_digest do not match",
    ):
        compare_teacher_student(
            teacher,
            student,
        )


def test_comparison_rejects_missing_gate_metric():
    teacher = _artifact("teacher")
    student = _artifact("student")

    del student["metrics"][GATE_METRICS[0]]

    with pytest.raises(
        ComparisonError,
        match="missing Gate metric",
    ):
        compare_teacher_student(
            teacher,
            student,
        )


def test_relative_drop_is_null_when_teacher_is_zero():
    teacher = _artifact("teacher")
    student = _artifact("student")

    metric = GATE_METRICS[0]

    teacher["metrics"][metric] = 0.0
    student["metrics"][metric] = 0.0

    result = compare_teacher_student(
        teacher,
        student,
    )

    comparison = result["metrics"][metric]

    assert comparison["absolute_drop"] == 0.0
    assert comparison["percentage_point_drop"] == 0.0
    assert comparison["relative_drop"] is None

def test_comparison_preserves_negative_drop_when_student_improves():
    teacher = _artifact("teacher")
    student = _artifact("student")

    metric = GATE_METRICS[0]

    teacher["metrics"][metric] = 0.90
    student["metrics"][metric] = 0.92

    result = compare_teacher_student(
        teacher,
        student,
    )

    comparison = result["metrics"][metric]

    assert comparison["absolute_drop"] == pytest.approx(-0.02)
    assert comparison["percentage_point_drop"] == pytest.approx(-2.0)
    assert comparison["relative_drop"] == pytest.approx(
        -0.02 / 0.90
    )


def test_comparison_absolute_drop_matches_a3_gate_math():
    teacher = _artifact("teacher")
    student = _artifact("student")

    metric = GATE_METRICS[0]

    teacher["metrics"][metric] = 0.95
    student["metrics"][metric] = 0.935

    result = compare_teacher_student(
        teacher,
        student,
    )

    comparison = result["metrics"][metric]

    # A3 artifacts._drop_check uses:
    #     drop = teacher_value - student_value
    #     passed = drop <= max_drop
    assert comparison["absolute_drop"] == pytest.approx(
        0.95 - 0.935
    )
    assert comparison["absolute_drop"] <= 0.015
