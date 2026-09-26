from __future__ import annotations

import hashlib

import pytest

from challenge.benchmark.raw_predictions import (
    RawPredictionError,
    canonical_prediction_jsonl,
    prediction_records_sha256,
    write_prediction_records,
)


def _records() -> list[dict]:
    return [
        {
            "sample_id": "sample-1",
            "status": "SUCCESS",
            "prediction": {
                "behavior": "STOP",
                "confidence": 0.9,
            },
        },
        {
            "sample_id": "sample-2",
            "status": "INFERENCE_ERROR",
            "prediction": None,
            "error": {
                "type": "RuntimeError",
                "message": "service unavailable",
            },
        },
    ]


def test_canonical_jsonl_uses_utf8_and_lf() -> None:
    payload = canonical_prediction_jsonl(
        [
            {
                "text": "向左变道",
                "sample_id": "sample-1",
            }
        ]
    )

    assert payload.endswith(b"\n")
    assert b"\r\n" not in payload
    assert "向左变道" in payload.decode("utf-8")


def test_object_key_order_does_not_change_digest() -> None:
    first = [
        {
            "sample_id": "sample-1",
            "status": "SUCCESS",
        }
    ]
    second = [
        {
            "status": "SUCCESS",
            "sample_id": "sample-1",
        }
    ]

    assert prediction_records_sha256(
        first
    ) == prediction_records_sha256(
        second
    )


def test_record_order_changes_digest() -> None:
    records = _records()

    assert prediction_records_sha256(
        records
    ) != prediction_records_sha256(
        reversed(records)
    )


def test_empty_predictions_fail_closed() -> None:
    with pytest.raises(
        RawPredictionError,
        match="must not be empty",
    ):
        canonical_prediction_jsonl([])


def test_non_json_numeric_values_fail_closed() -> None:
    records = [
        {
            "sample_id": "sample-1",
            "metric": float("nan"),
        }
    ]

    with pytest.raises(
        RawPredictionError,
        match="not canonical JSON",
    ):
        canonical_prediction_jsonl(records)


def test_write_digest_matches_exact_file_bytes(
    tmp_path,
) -> None:
    path = tmp_path / "teacher_predictions.jsonl"
    records = _records()

    digest = write_prediction_records(
        path,
        records,
    )

    written = path.read_bytes()

    assert digest == hashlib.sha256(
        written
    ).hexdigest()

    assert digest == prediction_records_sha256(
        records
    )

    assert written == canonical_prediction_jsonl(
        records
    )