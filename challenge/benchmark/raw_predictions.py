"""Canonical raw-prediction evidence for B2 evaluations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


class RawPredictionError(ValueError):
    """Raised when raw B2 prediction evidence cannot be serialized safely."""


def canonical_prediction_jsonl(
    records: Iterable[Mapping[str, Any]],
) -> bytes:
    """
    Serialize prediction records to canonical UTF-8 JSONL.

    Record order is preserved because it corresponds to the frozen benchmark
    case order. Object keys are sorted and line endings are always LF.
    """
    materialized = list(records)

    if not materialized:
        raise RawPredictionError(
            "prediction records must not be empty"
        )

    lines: list[str] = []

    for index, record in enumerate(materialized, start=1):
        if not isinstance(record, Mapping):
            raise RawPredictionError(
                f"prediction record {index} must be an object"
            )

        try:
            encoded = json.dumps(
                dict(record),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise RawPredictionError(
                f"prediction record {index} is not canonical JSON"
            ) from error

        lines.append(encoded)

    return ("\n".join(lines) + "\n").encode("utf-8")


def prediction_records_sha256(
    records: Iterable[Mapping[str, Any]],
) -> str:
    """Return SHA256 of the exact canonical raw-prediction JSONL bytes."""
    payload = canonical_prediction_jsonl(records)
    return hashlib.sha256(payload).hexdigest()


def write_prediction_records(
    path: str | Path,
    records: Iterable[Mapping[str, Any]],
) -> str:
    """
    Write canonical raw predictions and return the SHA256 of written bytes.
    """
    destination = Path(path)
    payload = canonical_prediction_jsonl(records)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination.write_bytes(payload)

    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "RawPredictionError",
    "canonical_prediction_jsonl",
    "prediction_records_sha256",
    "write_prediction_records",
]