"""A3-compatible Teacher evaluation artifact for B2."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

from challenge.distillation.artifacts import (
    FORMAL_GATE_TEACHER_V4,
)

from .metric_evidence import (
    GATE_METRICS,
    MetricEvidenceError,
    aggregate_gate_metric_evidence,
)
from .raw_predictions import prediction_records_sha256


class EvaluationArtifactError(ValueError):
    """Raised when B2 cannot build a formal evaluation artifact."""


def build_teacher_evaluation(
    cases: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
    *,
    evaluation_id: str,
    dataset_version: str,
    benchmark_manifest_sha256: str,
    policy_manifest_sha256: str,
    case_set_digest: str,
    evaluator_git_sha: str,
    evidence_bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Build an A3-compatible Teacher evaluation from complete raw evidence.

    Gate metrics are exposed as flat numeric values for A3 promotion while
    numerator/denominator evidence and run coverage remain available for B2
    audit.
    """
    evaluation_id = _required_text(
        evaluation_id,
        "evaluation_id",
    )
    dataset_version = _required_text(
        dataset_version,
        "dataset_version",
    )

    benchmark_manifest_sha256 = _required_hex(
        benchmark_manifest_sha256,
        64,
        "benchmark_manifest_sha256",
    )
    policy_manifest_sha256 = _required_hex(
        policy_manifest_sha256,
        64,
        "policy_manifest_sha256",
    )
    case_set_digest = _required_hex(
        case_set_digest,
        64,
        "case_set_digest",
    )
    evaluator_git_sha = _required_hex(
        evaluator_git_sha,
        40,
        "evaluator_git_sha",
    )

    case_rows = list(cases)
    record_rows = list(records)

    try:
        evidence = aggregate_gate_metric_evidence(
            case_rows,
            record_rows,
        )
    except MetricEvidenceError as error:
        raise EvaluationArtifactError(
            f"cannot build Teacher metric evidence: {error}"
        ) from error

    coverage = evidence["coverage"]
    metric_evidence = evidence["metrics"]

    sample_count = coverage["sample_count"]

    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < 1
    ):
        raise EvaluationArtifactError(
            "sample_count must be a positive integer"
        )

    flat_metrics: dict[str, float] = {}

    for name in GATE_METRICS:
        metric = metric_evidence[name]
        denominator = metric["denominator"]
        value = metric["value"]

        # A3 requires every Gate metric to be finite and numeric.
        # B2 must not fabricate 0/1 for an empty denominator.
        if denominator <= 0 or value is None:
            raise EvaluationArtifactError(
                f"formal Teacher evaluation has empty denominator "
                f"for metric {name!r}"
            )

        numeric = float(value)

        if (
            not math.isfinite(numeric)
            or not 0.0 <= numeric <= 1.0
        ):
            raise EvaluationArtifactError(
                f"formal Teacher metric {name!r} must be in [0, 1]"
            )

        flat_metrics[name] = numeric

    artifact: dict[str, Any] = {
        "schema_version": "1.0",
        "evaluation_id": evaluation_id,
        "evaluation_role": "teacher",
        "split": "validation",
        "dataset_version": dataset_version,
        **FORMAL_GATE_TEACHER_V4,
        "benchmark_manifest_sha256": benchmark_manifest_sha256,
        "policy_manifest_sha256": policy_manifest_sha256,
        "case_set_digest": case_set_digest,
        "evaluator_git_sha": evaluator_git_sha,
        "sample_count": sample_count,
        "predictions_sha256": prediction_records_sha256(
            record_rows
        ),
        "metrics": flat_metrics,
        "metric_evidence": metric_evidence,
        "coverage": coverage,
    }

    for field, value in (
        evidence_bindings or {}
    ).items():
        if field not in {
            "release_manifest_sha256",
            "a3_view_manifest_sha256",
            "d2_release_manifest_sha256",
            "b1_signature_sha256",
            "source_evidence_sha256",
        }:
            raise EvaluationArtifactError(
                f"unsupported evidence binding: {field}"
            )

        artifact[field] = _required_hex(
            value,
            64,
            field,
        )

    return artifact


def _required_text(
    value: Any,
    label: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationArtifactError(
            f"{label} must be a non-empty string"
        )

    return value.strip()


def _required_hex(
    value: Any,
    length: int,
    label: str,
) -> str:
    text = _required_text(value, label).lower()

    if len(text) != length:
        raise EvaluationArtifactError(
            f"{label} must be {length} hex characters"
        )

    try:
        int(text, 16)
    except ValueError as error:
        raise EvaluationArtifactError(
            f"{label} must be hexadecimal"
        ) from error

    return text


__all__ = [
    "EvaluationArtifactError",
    "build_teacher_evaluation",
]