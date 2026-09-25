"""Deterministic CSV artifact writer for B2 model comparisons."""

from __future__ import annotations

import csv
import hashlib
import io
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .comparison import compare_teacher_student
from .metric_evidence import GATE_METRICS


class ComparisonArtifactError(ValueError):
    """Raised when a comparison artifact cannot be published safely."""


CSV_FIELDS = (
    "metric",
    "teacher_value",
    "student_value",
    "absolute_drop",
    "percentage_point_drop",
    "relative_drop",
)


def write_model_comparison_csv(
    destination: str | Path,
    *,
    teacher_evaluation: Mapping[str, Any],
    student_evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    """Write a deterministic Teacher-to-Student comparison CSV."""

    path = Path(destination)

    if path.exists():
        raise ComparisonArtifactError(
            f"destination already exists: {path}"
        )

    if not path.parent.exists():
        raise ComparisonArtifactError(
            f"destination parent does not exist: {path.parent}"
        )

    comparison = compare_teacher_student(
        teacher_evaluation,
        student_evaluation,
    )

    payload = _comparison_csv_bytes(comparison)
    digest = hashlib.sha256(payload).hexdigest()

    temporary = path.with_name(f".{path.name}.tmp")

    if temporary.exists():
        raise ComparisonArtifactError(
            f"temporary destination already exists: {temporary}"
        )

    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return {
        "path": path,
        "sha256": digest,
        "row_count": len(GATE_METRICS),
        "benchmark_manifest_sha256": comparison[
            "benchmark_manifest_sha256"
        ],
        "policy_manifest_sha256": comparison[
            "policy_manifest_sha256"
        ],
        "case_set_digest": comparison["case_set_digest"],
        "evaluator_git_sha": comparison["evaluator_git_sha"],
        "sample_count": comparison["sample_count"],
    }


def model_comparison_csv_sha256(
    path: str | Path,
) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_model_comparison_csv(
    path: str | Path,
    *,
    gate_decision: Mapping[str, Any],
) -> dict[str, Any]:
    csv_path = Path(path)

    if not csv_path.is_file():
        raise ComparisonArtifactError(
            f"comparison CSV does not exist: {csv_path}"
        )

    comparison = gate_decision.get("comparison")
    if not isinstance(comparison, Mapping):
        raise ComparisonArtifactError(
            "gate decision requires comparison"
        )

    for field in (
        "benchmark_manifest_sha256",
        "policy_manifest_sha256",
        "case_set_digest",
        "evaluator_git_sha",
        "sample_count",
        "teacher_evaluation_id",
        "student_evaluation_id",
    ):
        if gate_decision.get(field) != comparison.get(field):
            raise ComparisonArtifactError(
                f"gate decision {field} does not match comparison"
            )

    expected = _comparison_csv_bytes(comparison)
    actual = csv_path.read_bytes()

    if actual != expected:
        raise ComparisonArtifactError(
            "comparison CSV does not match gate decision"
        )

    return {
        "valid": True,
        "sha256": hashlib.sha256(actual).hexdigest(),
        "row_count": len(GATE_METRICS),
        "gate_status": gate_decision.get("gate_status"),
        "benchmark_manifest_sha256": comparison[
            "benchmark_manifest_sha256"
        ],
        "policy_manifest_sha256": comparison[
            "policy_manifest_sha256"
        ],
        "case_set_digest": comparison["case_set_digest"],
        "evaluator_git_sha": comparison["evaluator_git_sha"],
        "sample_count": comparison["sample_count"],
    }

def _comparison_csv_bytes(
    comparison: Mapping[str, Any],
) -> bytes:
    metrics = comparison["metrics"]

    output = io.StringIO(
        newline="",
    )

    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()

    for metric in GATE_METRICS:
        values = metrics[metric]

        writer.writerow(
            {
                "metric": metric,
                "teacher_value": _format_float(
                    values["teacher"]
                ),
                "student_value": _format_float(
                    values["student"]
                ),
                "absolute_drop": _format_float(
                    values["absolute_drop"]
                ),
                "percentage_point_drop": _format_float(
                    values["percentage_point_drop"]
                ),
                "relative_drop": _format_optional_float(
                    values["relative_drop"]
                ),
            }
        )

    return output.getvalue().encode("utf-8")


def _format_optional_float(
    value: float | None,
) -> str:
    if value is None:
        return ""

    return _format_float(value)


def _format_float(value: float) -> str:
    return format(value, ".17g")


__all__ = [
    "CSV_FIELDS",
    "ComparisonArtifactError",
    "model_comparison_csv_sha256",
    "verify_model_comparison_csv",
    "write_model_comparison_csv",
]