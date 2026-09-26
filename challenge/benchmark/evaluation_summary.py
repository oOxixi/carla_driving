"""Fail-closed run coverage accounting for B2 evaluation evidence."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


ALLOWED_STATUSES = (
    "SUCCESS",
    "INFERENCE_ERROR",
    "INVALID_OUTPUT",
)


class EvaluationSummaryError(ValueError):
    """Raised when raw prediction coverage is incomplete or inconsistent."""


def summarize_prediction_coverage(
    cases: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Verify exact case-to-record coverage and summarize run outcomes.

    Raw record order must exactly match frozen benchmark case order.
    No missing, extra, duplicated, or unknown-status record is accepted.
    """
    case_rows = list(cases)
    prediction_rows = list(records)

    if not case_rows:
        raise EvaluationSummaryError(
            "benchmark cases must not be empty"
        )

    case_ids = [
        _required_sample_id(case, f"benchmark case {index}")
        for index, case in enumerate(case_rows, start=1)
    ]

    if len(set(case_ids)) != len(case_ids):
        raise EvaluationSummaryError(
            "benchmark cases contain duplicate sample_id"
        )

    record_ids = [
        _required_sample_id(record, f"prediction record {index}")
        for index, record in enumerate(prediction_rows, start=1)
    ]

    if len(set(record_ids)) != len(record_ids):
        raise EvaluationSummaryError(
            "prediction records contain duplicate sample_id"
        )

    if record_ids != case_ids:
        raise EvaluationSummaryError(
            "prediction records must exactly match benchmark case order"
        )

    status_counts = Counter()
    error_code_counts = Counter()

    for index, record in enumerate(prediction_rows, start=1):
        status = record.get("status")

        if status not in ALLOWED_STATUSES:
            raise EvaluationSummaryError(
                f"prediction record {index} has invalid status: {status!r}"
            )

        status_counts[status] += 1

        if status == "SUCCESS":
            if record.get("error") is not None:
                raise EvaluationSummaryError(
                    f"successful prediction record {index} must not contain error"
                )
            continue

        error = record.get("error")
        if not isinstance(error, Mapping):
            raise EvaluationSummaryError(
                f"failed prediction record {index} must contain error"
            )

        code = error.get("code")
        if not isinstance(code, str) or not code.strip():
            raise EvaluationSummaryError(
                f"failed prediction record {index} must contain error code"
            )

        error_code_counts[code] += 1

    sample_count = len(case_ids)
    success_count = status_counts["SUCCESS"]
    inference_error_count = status_counts["INFERENCE_ERROR"]
    invalid_output_count = status_counts["INVALID_OUTPUT"]
    failed_count = inference_error_count + invalid_output_count

    if success_count + failed_count != sample_count:
        raise EvaluationSummaryError(
            "prediction accounting does not equal benchmark sample count"
        )

    return {
        "sample_count": sample_count,
        "success_count": success_count,
        "failed_count": failed_count,
        "inference_error_count": inference_error_count,
        "invalid_output_count": invalid_output_count,
        "status_counts": {
            status: status_counts[status]
            for status in ALLOWED_STATUSES
        },
        "error_code_counts": dict(
            sorted(error_code_counts.items())
        ),
    }


def _required_sample_id(
    value: Mapping[str, Any],
    label: str,
) -> str:
    if not isinstance(value, Mapping):
        raise EvaluationSummaryError(
            f"{label} must be an object"
        )

    sample_id = value.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise EvaluationSummaryError(
            f"{label} has invalid sample_id"
        )

    return sample_id


__all__ = [
    "ALLOWED_STATUSES",
    "EvaluationSummaryError",
    "summarize_prediction_coverage",
]