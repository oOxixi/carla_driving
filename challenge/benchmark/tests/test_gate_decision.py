from __future__ import annotations

import copy
from pathlib import Path

import pytest

from challenge.benchmark.gate_decision import (
    GateDecisionError,
    build_gate_decision,
)
from challenge.benchmark.policy_manifest import (
    build_policy_manifest,
    load_benchmark_policy_config,
    policy_manifest_sha256,
)
from challenge.distillation.artifacts import (
    CORE_METRICS,
    SAFETY_METRICS,
)


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = (
    ROOT
    / "challenge"
    / "benchmark"
    / "benchmark_config.yaml"
)


def _policy_manifest() -> dict:
    config = load_benchmark_policy_config(
        CONFIG_PATH
    )
    config = copy.deepcopy(config)

    config["formal_policy"] = {
        "status": "FROZEN",
        "policy_version": "b2-gate-test-v1",
        "slice_minimum_denominators": {
            "seen": 1,
            "variant": 1,
            "unseen": 1,
        },
        "multi_run_merge_rule": (
            "pool_numerators_and_denominators"
        ),
    }

    return build_policy_manifest(config)


def _evaluation(
    role: str,
    *,
    policy_sha: str,
    value: float,
) -> dict:
    artifact = {
        "evaluation_id": f"{role}-evaluation",
        "evaluation_role": role,
        "benchmark_manifest_sha256": "a" * 64,
        "policy_manifest_sha256": policy_sha,
        "case_set_digest": "b" * 64,
        "evaluator_git_sha": "c" * 40,
        "sample_count": 100,
        "predictions_sha256": (
            "d" * 64
            if role == "teacher"
            else "e" * 64
        ),
        "schema_validity": 1.0,
        "metrics": {
            name: value
            for name in (
                *CORE_METRICS,
                *SAFETY_METRICS,
            )
        },
    }

    if role == "student":
        artifact.update({
            "model_id": "student-v0-r3-fp32",
            "config_id": "student-v0-r3-structured",
            "weights_sha256": "f" * 64,
        })

    return artifact


def test_gate_decision_passes_policy_compliant_student() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.94,
    )

    # Safety may not drop under the frozen policy.
    for name in SAFETY_METRICS:
        student["metrics"][name] = (
            teacher["metrics"][name]
        )

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    assert decision["gate_status"] == "PASS"
    assert decision["policy_manifest_sha256"] == (
        policy_sha
    )
    assert decision["gate_thresholds"] == {
        "schema_validity_required": 1.0,
        "max_core_drop": 0.015,
        "max_safety_drop": 0.0,
    }

    assert all(
        check["passed"]
        for check in decision["checks"]
    )

def test_gate_decision_fails_core_drop_above_policy() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.93,
    )

    # Keep safety equal so this failure is isolated to core.
    for name in SAFETY_METRICS:
        student["metrics"][name] = (
            teacher["metrics"][name]
        )

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    assert decision["gate_status"] == "FAIL"

    core_checks = [
        check
        for check in decision["checks"]
        if check["group"] == "core"
    ]

    assert core_checks
    assert all(
        check["absolute_drop"] == pytest.approx(0.02)
        for check in core_checks
    )
    assert all(
        check["max_drop"] == pytest.approx(0.015)
        for check in core_checks
    )
    assert all(
        check["passed"] is False
        for check in core_checks
    )


def test_gate_decision_fails_any_safety_drop() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.95,
    )

    safety_metric = SAFETY_METRICS[0]
    student["metrics"][safety_metric] = 0.949

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    assert decision["gate_status"] == "FAIL"

    safety_check = next(
        check
        for check in decision["checks"]
        if check["name"] == safety_metric
    )

    assert safety_check["absolute_drop"] == pytest.approx(
        0.001
    )
    assert safety_check["max_drop"] == 0.0
    assert safety_check["passed"] is False


def test_gate_decision_fails_schema_validity_below_policy() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.95,
    )

    student["schema_validity"] = 0.99

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    assert decision["gate_status"] == "FAIL"

    schema_check = next(
        check
        for check in decision["checks"]
        if check["name"] == "schema_validity"
    )

    assert schema_check == {
        "name": "schema_validity",
        "group": "contract",
        "student": 0.99,
        "required": 1.0,
        "passed": False,
    }

def test_gate_decision_rejects_supplied_policy_mismatch() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.95,
    )

    tampered_policy = copy.deepcopy(policy)
    tampered_policy["gate"]["max_core_drop"] = 0.50

    with pytest.raises(
        GateDecisionError,
        match="supplied policy manifest",
    ):
        build_gate_decision(
            teacher,
            student,
            tampered_policy,
        )


def test_gate_decision_rejects_teacher_student_identity_mismatch() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.95,
    )

    student["case_set_digest"] = "9" * 64

    with pytest.raises(
        GateDecisionError,
        match="comparison failed",
    ):
        build_gate_decision(
            teacher,
            student,
            policy,
        )

def test_gate_decision_passes_core_drop_exactly_at_policy_limit() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.935,
    )

    # Safety must remain unchanged.
    for name in SAFETY_METRICS:
        student["metrics"][name] = teacher["metrics"][name]

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    assert decision["gate_status"] == "PASS"

    core_checks = [
        check
        for check in decision["checks"]
        if check["group"] == "core"
    ]

    assert core_checks
    assert all(
        check["absolute_drop"] == pytest.approx(0.015)
        for check in core_checks
    )
    assert all(
        check["passed"] is True
        for check in core_checks
    )


def test_gate_decision_preserves_student_improvement_as_negative_drop() -> None:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.90,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.92,
    )

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    assert decision["gate_status"] == "PASS"

    for check in decision["checks"]:
        if check["group"] in {"core", "safety"}:
            assert check["absolute_drop"] == pytest.approx(-0.02)
            assert check["percentage_point_drop"] == pytest.approx(-2.0)
            assert check["relative_drop"] == pytest.approx(
                -0.02 / 0.90
            )
            assert check["passed"] is True
