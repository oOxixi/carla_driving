"""Policy-bound B2 Teacher/Student gate decision."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from challenge.distillation.artifacts import (
    CORE_METRICS,
    SAFETY_METRICS,
)

from .comparison import (
    ComparisonError,
    compare_teacher_student,
)
from .policy_manifest import policy_manifest_sha256


class GateDecisionError(ValueError):
    """Raised when B2 cannot produce a policy-bound gate decision."""


def build_gate_decision(
    teacher_evaluation: Mapping[str, Any],
    student_evaluation: Mapping[str, Any],
    policy_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(policy_manifest, Mapping):
        raise GateDecisionError(
            "policy_manifest must be an object"
        )

    expected_policy_sha = policy_manifest_sha256(
        policy_manifest
    )

    for evaluation, label in (
        (teacher_evaluation, "Teacher"),
        (student_evaluation, "Student"),
    ):
        if (
            evaluation.get("policy_manifest_sha256")
            != expected_policy_sha
        ):
            raise GateDecisionError(
                f"{label} evaluation is not bound to "
                "the supplied policy manifest"
            )

    gate = policy_manifest.get("gate")
    if not isinstance(gate, Mapping):
        raise GateDecisionError(
            "policy manifest gate must be an object"
        )

    schema_required = _threshold(
        gate,
        "schema_validity_required",
    )
    max_core_drop = _threshold(
        gate,
        "max_core_drop",
    )
    max_safety_drop = _threshold(
        gate,
        "max_safety_drop",
    )

    try:
        comparison = compare_teacher_student(
            teacher_evaluation,
            student_evaluation,
        )
    except ComparisonError as error:
        raise GateDecisionError(
            f"Teacher/Student comparison failed: {error}"
        ) from error

    checks: list[dict[str, Any]] = []

    for name in CORE_METRICS:
        metric = comparison["metrics"][name]
        checks.append(
            _metric_check(
                name,
                "core",
                metric,
                max_core_drop,
            )
        )

    for name in SAFETY_METRICS:
        metric = comparison["metrics"][name]
        checks.append(
            _metric_check(
                name,
                "safety",
                metric,
                max_safety_drop,
            )
        )

    schema_validity = _evaluation_schema_validity(
        student_evaluation
    )

    checks.append({
        "name": "schema_validity",
        "group": "contract",
        "student": schema_validity,
        "required": schema_required,
        "passed": schema_validity >= schema_required,
    })

    passed = all(
        bool(check["passed"])
        for check in checks
    )

    return {
        "schema_version": "1.0",
        "gate_status": (
            "PASS"
            if passed
            else "FAIL"
        ),
        "policy_manifest_sha256": expected_policy_sha,
        "benchmark_manifest_sha256": comparison[
            "benchmark_manifest_sha256"
        ],
        "case_set_digest": comparison[
            "case_set_digest"
        ],
        "evaluator_git_sha": comparison[
            "evaluator_git_sha"
        ],
        "sample_count": comparison[
            "sample_count"
        ],
        "teacher_evaluation_id": teacher_evaluation.get(
            "evaluation_id"
        ),
        "student_evaluation_id": student_evaluation.get(
            "evaluation_id"
        ),
        "gate_thresholds": {
            "schema_validity_required": schema_required,
            "max_core_drop": max_core_drop,
            "max_safety_drop": max_safety_drop,
        },
        "checks": checks,
        "comparison": comparison,
    }


def _metric_check(
    name: str,
    group: str,
    metric: Mapping[str, Any],
    max_drop: float,
) -> dict[str, Any]:
    drop = float(metric["absolute_drop"])

    return {
        "name": name,
        "group": group,
        "teacher": metric["teacher"],
        "student": metric["student"],
        "absolute_drop": drop,
        "percentage_point_drop": metric[
            "percentage_point_drop"
        ],
        "relative_drop": metric["relative_drop"],
        "max_drop": max_drop,
        "passed": drop <= max_drop,
    }


def _threshold(
    gate: Mapping[str, Any],
    name: str,
) -> float:
    value = gate.get(name)

    if isinstance(value, bool):
        raise GateDecisionError(
            f"gate threshold {name!r} must be numeric"
        )

    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise GateDecisionError(
            f"gate threshold {name!r} must be numeric"
        ) from error

    if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise GateDecisionError(
            f"gate threshold {name!r} must be in [0,1]"
        )

    return numeric


def _evaluation_schema_validity(
    evaluation: Mapping[str, Any],
) -> float:
    value = evaluation.get("schema_validity")

    if isinstance(value, bool):
        raise GateDecisionError(
            "Student schema_validity must be numeric"
        )

    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise GateDecisionError(
            "Student schema_validity must be numeric"
        ) from error

    if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise GateDecisionError(
            "Student schema_validity must be in [0,1]"
        )

    return numeric


__all__ = [
    "GateDecisionError",
    "build_gate_decision",
]
