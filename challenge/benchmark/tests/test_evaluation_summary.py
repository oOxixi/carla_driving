from __future__ import annotations

import pytest

from challenge.benchmark.evaluation_summary import (
    EvaluationSummaryError,
    summarize_prediction_coverage,
)


def _cases() -> list[dict]:
    return [
        {"sample_id": "sample-1"},
        {"sample_id": "sample-2"},
        {"sample_id": "sample-3"},
    ]


def _success(sample_id: str) -> dict:
    return {
        "sample_id": sample_id,
        "status": "SUCCESS",
        "prediction": {},
        "error": None,
    }


def _failure(
    sample_id: str,
    *,
    status: str,
    code: str,
) -> dict:
    return {
        "sample_id": sample_id,
        "status": status,
        "prediction": None,
        "error": {
            "code": code,
            "type": "RuntimeError",
            "message": "test failure",
        },
    }


def test_summary_counts_every_frozen_case() -> None:
    records = [
        _success("sample-1"),
        _failure(
            "sample-2",
            status="INFERENCE_ERROR",
            code="QWEN_CLIENT_ERROR",
        ),
        _failure(
            "sample-3",
            status="INVALID_OUTPUT",
            code="INVALID_PLAN_SCHEMA",
        ),
    ]

    summary = summarize_prediction_coverage(
        _cases(),
        records,
    )

    assert summary["sample_count"] == 3
    assert summary["success_count"] == 1
    assert summary["failed_count"] == 2
    assert summary["inference_error_count"] == 1
    assert summary["invalid_output_count"] == 1

    assert summary["status_counts"] == {
        "SUCCESS": 1,
        "INFERENCE_ERROR": 1,
        "INVALID_OUTPUT": 1,
    }

    assert summary["error_code_counts"] == {
        "INVALID_PLAN_SCHEMA": 1,
        "QWEN_CLIENT_ERROR": 1,
    }


def test_missing_prediction_fails_closed() -> None:
    records = [
        _success("sample-1"),
        _success("sample-2"),
    ]

    with pytest.raises(
        EvaluationSummaryError,
        match="exactly match benchmark case order",
    ):
        summarize_prediction_coverage(
            _cases(),
            records,
        )


def test_extra_prediction_fails_closed() -> None:
    records = [
        _success("sample-1"),
        _success("sample-2"),
        _success("sample-3"),
        _success("sample-4"),
    ]

    with pytest.raises(
        EvaluationSummaryError,
        match="exactly match benchmark case order",
    ):
        summarize_prediction_coverage(
            _cases(),
            records,
        )


def test_reordered_predictions_fail_closed() -> None:
    records = [
        _success("sample-2"),
        _success("sample-1"),
        _success("sample-3"),
    ]

    with pytest.raises(
        EvaluationSummaryError,
        match="exactly match benchmark case order",
    ):
        summarize_prediction_coverage(
            _cases(),
            records,
        )


def test_duplicate_prediction_sample_id_fails_closed() -> None:
    records = [
        _success("sample-1"),
        _success("sample-1"),
        _success("sample-3"),
    ]

    with pytest.raises(
        EvaluationSummaryError,
        match="duplicate sample_id",
    ):
        summarize_prediction_coverage(
            _cases(),
            records,
        )


def test_unknown_status_fails_closed() -> None:
    records = [
        _success("sample-1"),
        _success("sample-2"),
        {
            "sample_id": "sample-3",
            "status": "SKIPPED",
            "prediction": None,
            "error": None,
        },
    ]

    with pytest.raises(
        EvaluationSummaryError,
        match="invalid status",
    ):
        summarize_prediction_coverage(
            _cases(),
            records,
        )


def test_failure_without_error_code_fails_closed() -> None:
    records = [
        _success("sample-1"),
        _success("sample-2"),
        {
            "sample_id": "sample-3",
            "status": "INFERENCE_ERROR",
            "prediction": None,
            "error": {
                "type": "RuntimeError",
                "message": "test failure",
            },
        },
    ]

    with pytest.raises(
        EvaluationSummaryError,
        match="must contain error code",
    ):
        summarize_prediction_coverage(
            _cases(),
            records,
        )


def test_success_with_error_fails_closed() -> None:
    records = [
        _success("sample-1"),
        _success("sample-2"),
        {
            "sample_id": "sample-3",
            "status": "SUCCESS",
            "prediction": {},
            "error": {
                "code": "SHOULD_NOT_EXIST",
            },
        },
    ]

    with pytest.raises(
        EvaluationSummaryError,
        match="must not contain error",
    ):
        summarize_prediction_coverage(
            _cases(),
            records,
        )