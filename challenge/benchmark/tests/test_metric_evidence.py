from __future__ import annotations

import copy

import pytest

pytest.importorskip("torch")

from challenge.benchmark.metric_evidence import (
    GATE_METRICS,
    MetricEvidenceError,
    aggregate_gate_metric_evidence,
    reference_gate_denominators,
    score_failed_gate_metrics,
    score_success_gate_metrics,
)

from challenge.benchmark.metric_evidence import (
    MetricEvidenceError,
    reference_gate_denominators,
)
from challenge.distillation.dataset import build_mock_records


def test_reference_denominators_reuse_distillation_metric_contract() -> None:
    cases = build_mock_records(5)

    denominators = reference_gate_denominators(cases)

    assert denominators == {
        "behavior_accuracy": 5,
        "target_pointer_accuracy": 5,
        "target_lane_accuracy": 5,
        "completion_accuracy": 5,
        "plan_sequence_accuracy": 5,
        "safety_critical_behavior_recall": 1,
    }


def test_empty_safety_slice_has_zero_safety_denominator() -> None:
    cases = build_mock_records(2)

    denominators = reference_gate_denominators(cases)

    assert denominators["behavior_accuracy"] == 2
    assert denominators["plan_sequence_accuracy"] == 2
    assert denominators["safety_critical_behavior_recall"] == 0


def test_step_metrics_and_sequence_metrics_use_different_units() -> None:
    case = copy.deepcopy(
        build_mock_records(5)[4]
    )

    plan = case["teacher"]["maneuver_plan"]

    second_step = copy.deepcopy(
        plan["steps"][0]
    )
    second_step["step_id"] = "step-2"
    plan["steps"].append(second_step)

    denominators = reference_gate_denominators(
        [case]
    )

    assert denominators["behavior_accuracy"] == 2
    assert denominators["target_pointer_accuracy"] == 2
    assert denominators["target_lane_accuracy"] == 2
    assert denominators["completion_accuracy"] == 2

    # Sequence accuracy is one opportunity per benchmark case.
    assert denominators["plan_sequence_accuracy"] == 1

    # This mock case is safety-critical, so both valid steps count.
    assert denominators["safety_critical_behavior_recall"] == 2


def test_empty_case_set_fails_closed() -> None:
    with pytest.raises(
        MetricEvidenceError,
        match="must not be empty",
    ):
        reference_gate_denominators([])

def test_exact_teacher_plan_gets_full_gate_credit() -> None:
    case = copy.deepcopy(
        build_mock_records(5)[4]
    )
    prediction = copy.deepcopy(
        case["teacher"]["maneuver_plan"]
    )

    evidence = score_success_gate_metrics(
        case,
        prediction,
    )

    assert set(evidence) == set(GATE_METRICS)

    for metric in GATE_METRICS:
        assert evidence[metric] == {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0,
        }


def test_sequence_metric_reuses_existing_failure_action_semantics() -> None:
    case = copy.deepcopy(
        build_mock_records(2)[0]
    )
    prediction = copy.deepcopy(
        case["teacher"]["maneuver_plan"]
    )

    prediction["steps"][0]["on_failure"] = "REPLAN"

    evidence = score_success_gate_metrics(
        case,
        prediction,
    )

    assert evidence["behavior_accuracy"]["value"] == 1.0
    assert evidence["target_pointer_accuracy"]["value"] == 1.0
    assert evidence["target_lane_accuracy"]["value"] == 1.0
    assert evidence["completion_accuracy"]["value"] == 1.0

    # Existing compute_batch_metrics includes on_failure correctness
    # in whole-plan sequence correctness.
    assert evidence["plan_sequence_accuracy"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }

    # This normal case has no safety-critical opportunity.
    assert evidence["safety_critical_behavior_recall"] == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }


def test_prediction_with_unresolvable_target_fails_closed() -> None:
    case = copy.deepcopy(
        build_mock_records(3)[2]
    )
    prediction = copy.deepcopy(
        case["teacher"]["maneuver_plan"]
    )

    prediction["steps"][0]["target"]["target_id"] = (
        "missing-target"
    )

    with pytest.raises(
        MetricEvidenceError,
        match="cannot score successful prediction",
    ):
        score_success_gate_metrics(
            case,
            prediction,
        )
def test_failed_case_keeps_full_reference_denominator() -> None:
    case = copy.deepcopy(
        build_mock_records(5)[4]
    )

    evidence = score_failed_gate_metrics(
        case,
        status="INFERENCE_ERROR",
    )

    assert evidence["behavior_accuracy"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }

    assert evidence["plan_sequence_accuracy"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }

    assert evidence["safety_critical_behavior_recall"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }


def test_failed_normal_case_keeps_empty_safety_slice_null() -> None:
    case = copy.deepcopy(
        build_mock_records(2)[0]
    )

    evidence = score_failed_gate_metrics(
        case,
        status="INVALID_OUTPUT",
    )

    assert evidence["behavior_accuracy"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }

    assert evidence["safety_critical_behavior_recall"] == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }


def test_unknown_failure_status_fails_closed() -> None:
    case = copy.deepcopy(
        build_mock_records(2)[0]
    )

    with pytest.raises(
        MetricEvidenceError,
        match="unsupported failure status",
    ):
        score_failed_gate_metrics(
            case,
            status="SKIPPED",
        )

def _success_record(case: dict) -> dict:
    return {
        "sample_id": case["sample_id"],
        "status": "SUCCESS",
        "prediction": copy.deepcopy(
            case["teacher"]["maneuver_plan"]
        ),
        "error": None,
    }


def _failure_record(
    case: dict,
    *,
    status: str = "INFERENCE_ERROR",
) -> dict:
    return {
        "sample_id": case["sample_id"],
        "status": status,
        "prediction": None,
        "error": {
            "code": "TEST_FAILURE",
            "type": "RuntimeError",
            "message": "test failure",
        },
    }


def test_aggregate_exact_predictions_get_full_credit() -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    result = aggregate_gate_metric_evidence(
        cases,
        records,
    )

    assert result["coverage"]["sample_count"] == 5
    assert result["coverage"]["success_count"] == 5
    assert result["coverage"]["failed_count"] == 0

    for name in GATE_METRICS:
        metric = result["metrics"][name]

        assert metric["denominator"] > 0
        assert metric["numerator"] == metric["denominator"]
        assert metric["value"] == 1.0


def test_aggregate_failure_stays_in_gate_denominator() -> None:
    source = build_mock_records(5)

    cases = [
        copy.deepcopy(source[0]),
        copy.deepcopy(source[4]),
    ]

    records = [
        _success_record(cases[0]),
        _failure_record(cases[1]),
    ]

    result = aggregate_gate_metric_evidence(
        cases,
        records,
    )

    assert result["coverage"]["sample_count"] == 2
    assert result["coverage"]["success_count"] == 1
    assert result["coverage"]["failed_count"] == 1

    for name in (
        "behavior_accuracy",
        "target_pointer_accuracy",
        "target_lane_accuracy",
        "completion_accuracy",
        "plan_sequence_accuracy",
    ):
        assert result["metrics"][name] == {
            "numerator": 1,
            "denominator": 2,
            "value": 0.5,
        }

    assert result["metrics"][
        "safety_critical_behavior_recall"
    ] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }


def test_aggregate_empty_safety_slice_remains_null() -> None:
    cases = copy.deepcopy(
        build_mock_records(2)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    result = aggregate_gate_metric_evidence(
        cases,
        records,
    )

    assert result["metrics"][
        "safety_critical_behavior_recall"
    ] == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }


def test_aggregate_rejects_reordered_raw_records() -> None:
    cases = copy.deepcopy(
        build_mock_records(2)
    )
    records = [
        _success_record(cases[1]),
        _success_record(cases[0]),
    ]

    with pytest.raises(
        MetricEvidenceError,
        match="invalid prediction coverage",
    ):
        aggregate_gate_metric_evidence(
            cases,
            records,
        )