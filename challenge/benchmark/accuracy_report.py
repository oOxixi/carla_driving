"""Deterministic human-readable B2 accuracy report artifact."""

from __future__ import annotations

import hashlib
import math
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .comparison_artifact import (
    ComparisonArtifactError,
    verify_model_comparison_csv,
)
from .metric_evidence import GATE_METRICS


class AccuracyReportError(ValueError):
    """Raised when an accuracy report cannot be published safely."""


_IDENTITY_FIELDS = (
    "benchmark_manifest_sha256",
    "policy_manifest_sha256",
    "case_set_digest",
    "evaluator_git_sha",
    "sample_count",
)


def write_accuracy_report(
    destination: str | Path,
    *,
    gate_decision: Mapping[str, Any],
    model_comparison_path: str | Path,
) -> dict[str, Any]:
    """
    Publish a deterministic Markdown view of an existing gate decision.

    The report does not recompute metrics or gate outcomes. The supplied
    model comparison CSV must exactly match the comparison embedded in the
    gate decision.
    """

    path = Path(destination)

    if path.exists():
        raise AccuracyReportError(
            f"destination already exists: {path}"
        )

    if not path.parent.exists():
        raise AccuracyReportError(
            f"destination parent does not exist: {path.parent}"
        )

    decision = _validated_gate_decision(gate_decision)

    try:
        comparison_verification = verify_model_comparison_csv(
            model_comparison_path,
            gate_decision=decision,
        )
    except ComparisonArtifactError as error:
        raise AccuracyReportError(
            f"model comparison verification failed: {error}"
        ) from error

    payload = _accuracy_report_bytes(
        decision,
        comparison_sha256=comparison_verification["sha256"],
    )
    digest = hashlib.sha256(payload).hexdigest()

    temporary = path.with_name(f".{path.name}.tmp")

    if temporary.exists():
        raise AccuracyReportError(
            f"temporary destination already exists: {temporary}"
        )

    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(path)

    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

        raise AccuracyReportError(
            f"cannot publish accuracy report: {error}"
        ) from error

    return {
        "path": path,
        "sha256": digest,
        "model_comparison_sha256": comparison_verification["sha256"],
        "gate_status": decision["gate_status"],
        "teacher_evaluation_id": decision["teacher_evaluation_id"],
        "student_evaluation_id": decision["student_evaluation_id"],
        **{
            field: decision[field]
            for field in _IDENTITY_FIELDS
        },
    }


def accuracy_report_sha256(
    path: str | Path,
) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_accuracy_report(
    path: str | Path,
    *,
    gate_decision: Mapping[str, Any],
    model_comparison_path: str | Path,
) -> dict[str, Any]:
    report_path = Path(path)

    if not report_path.is_file():
        raise AccuracyReportError(
            f"accuracy report does not exist: {report_path}"
        )

    decision = _validated_gate_decision(gate_decision)

    try:
        comparison_verification = verify_model_comparison_csv(
            model_comparison_path,
            gate_decision=decision,
        )
    except ComparisonArtifactError as error:
        raise AccuracyReportError(
            f"model comparison verification failed: {error}"
        ) from error

    expected = _accuracy_report_bytes(
        decision,
        comparison_sha256=comparison_verification["sha256"],
    )
    actual = report_path.read_bytes()

    if actual != expected:
        raise AccuracyReportError(
            "accuracy report does not match gate decision"
        )

    return {
        "valid": True,
        "sha256": hashlib.sha256(actual).hexdigest(),
        "model_comparison_sha256": comparison_verification["sha256"],
        "gate_status": decision["gate_status"],
        "teacher_evaluation_id": decision["teacher_evaluation_id"],
        "student_evaluation_id": decision["student_evaluation_id"],
        **{
            field: decision[field]
            for field in _IDENTITY_FIELDS
        },
    }


def _validated_gate_decision(
    gate_decision: Mapping[str, Any],
) -> Mapping[str, Any]:
    if not isinstance(gate_decision, Mapping):
        raise AccuracyReportError(
            "gate_decision must be an object"
        )

    status = gate_decision.get("gate_status")
    if status not in {"PASS", "FAIL"}:
        raise AccuracyReportError(
            "gate_status must be PASS or FAIL"
        )

    comparison = gate_decision.get("comparison")
    if not isinstance(comparison, Mapping):
        raise AccuracyReportError(
            "gate decision requires comparison"
        )

    for field in (
        *_IDENTITY_FIELDS,
        "teacher_evaluation_id",
        "student_evaluation_id",
    ):
        if gate_decision.get(field) != comparison.get(field):
            raise AccuracyReportError(
                f"gate decision {field} does not match comparison"
            )

    metrics = comparison.get("metrics")
    if not isinstance(metrics, Mapping):
        raise AccuracyReportError(
            "gate decision comparison requires metrics"
        )

    for metric in GATE_METRICS:
        values = metrics.get(metric)

        if not isinstance(values, Mapping):
            raise AccuracyReportError(
                f"comparison metric {metric!r} is missing"
            )

        for field in (
            "teacher",
            "student",
            "absolute_drop",
            "percentage_point_drop",
        ):
            _finite_number(
                values.get(field),
                f"{metric}.{field}",
            )

        relative = values.get("relative_drop")
        if relative is not None:
            _finite_number(
                relative,
                f"{metric}.relative_drop",
            )

    checks = gate_decision.get("checks")
    if (
        not isinstance(checks, Sequence)
        or isinstance(checks, (str, bytes))
    ):
        raise AccuracyReportError(
            "gate decision checks must be a sequence"
        )

    metric_checks: dict[str, Mapping[str, Any]] = {}

    for check in checks:
        if not isinstance(check, Mapping):
            raise AccuracyReportError(
                "gate decision check must be an object"
            )

        name = check.get("name")

        if name in GATE_METRICS:
            if name in metric_checks:
                raise AccuracyReportError(
                    f"duplicate gate check for {name!r}"
                )
            metric_checks[name] = check

    if set(metric_checks) != set(GATE_METRICS):
        raise AccuracyReportError(
            "gate decision does not contain every metric check"
        )

    for metric in GATE_METRICS:
        values = metrics[metric]
        check = metric_checks[metric]

        for field in (
            "teacher",
            "student",
            "absolute_drop",
            "percentage_point_drop",
            "relative_drop",
        ):
            if check.get(field) != values.get(field):
                raise AccuracyReportError(
                    f"gate check {metric!r} {field} "
                    "does not match comparison"
                )

        _finite_number(
            check.get("max_drop"),
            f"{metric}.max_drop",
        )

        if not isinstance(check.get("passed"), bool):
            raise AccuracyReportError(
                f"gate check {metric!r} passed must be boolean"
            )

    schema_checks = [
        check
        for check in checks
        if isinstance(check, Mapping)
        and check.get("name") == "schema_validity"
    ]

    if len(schema_checks) != 1:
        raise AccuracyReportError(
            "gate decision requires exactly one schema_validity check"
        )

    schema_check = schema_checks[0]

    _finite_number(
        schema_check.get("student"),
        "schema_validity.student",
    )
    _finite_number(
        schema_check.get("required"),
        "schema_validity.required",
    )

    if not isinstance(schema_check.get("passed"), bool):
        raise AccuracyReportError(
            "schema_validity passed must be boolean"
        )

    return gate_decision


def _accuracy_report_bytes(
    decision: Mapping[str, Any],
    *,
    comparison_sha256: str,
) -> bytes:
    comparison = decision["comparison"]
    metrics = comparison["metrics"]

    metric_checks = {
        check["name"]: check
        for check in decision["checks"]
        if check["name"] in GATE_METRICS
    }

    schema_check = next(
        check
        for check in decision["checks"]
        if check["name"] == "schema_validity"
    )

    lines = [
        "# B2 Accuracy Report",
        "",
        "## Decision",
        "",
        f"- Gate status: **{decision['gate_status']}**",
        f"- Teacher evaluation: `{decision['teacher_evaluation_id']}`",
        f"- Student evaluation: `{decision['student_evaluation_id']}`",
        f"- Sample count: {decision['sample_count']}",
        "",
        "## Evidence Identity",
        "",
        (
            "- Benchmark manifest SHA256: "
            f"`{decision['benchmark_manifest_sha256']}`"
        ),
        (
            "- Policy manifest SHA256: "
            f"`{decision['policy_manifest_sha256']}`"
        ),
        f"- Case-set digest: `{decision['case_set_digest']}`",
        f"- Evaluator Git SHA: `{decision['evaluator_git_sha']}`",
        f"- Model comparison SHA256: `{comparison_sha256}`",
        "",
        "## Schema Validity",
        "",
        "| Student | Required | Result |",
        "| ---: | ---: | :---: |",
        (
            f"| {_format_number(schema_check['student'])} "
            f"| {_format_number(schema_check['required'])} "
            f"| {_result(schema_check['passed'])} |"
        ),
        "",
        "## Gate Metrics",
        "",
        (
            "| Metric | Teacher | Student | Absolute drop | "
            "Percentage-point drop | Relative drop | "
            "Max drop | Result |"
        ),
        (
            "| --- | ---: | ---: | ---: | ---: | ---: | "
            "---: | :---: |"
        ),
    ]

    for metric in GATE_METRICS:
        values = metrics[metric]
        check = metric_checks[metric]

        lines.append(
            "| "
            + " | ".join(
                (
                    metric,
                    _format_number(values["teacher"]),
                    _format_number(values["student"]),
                    _format_number(values["absolute_drop"]),
                    _format_number(
                        values["percentage_point_drop"]
                    ),
                    _format_optional_percent(
                        values["relative_drop"]
                    ),
                    _format_number(check["max_drop"]),
                    _result(check["passed"]),
                )
            )
            + " |"
        )

    lines.extend(
        (
            "",
            "## Interpretation",
            "",
            (
                "Absolute drop is Teacher minus Student. "
                "Percentage-point drop is absolute drop × 100. "
                "Relative drop is absolute drop divided by the "
                "Teacher value; it is reported as N/A when the "
                "Teacher value is zero."
            ),
            "",
            (
                "This report is a deterministic view of the "
                "policy-bound gate decision. It does not recompute "
                "metrics or independently change the gate outcome."
            ),
            "",
        )
    )

    return "\n".join(lines).encode("utf-8")


def _finite_number(
    value: Any,
    label: str,
) -> float:
    if isinstance(value, bool):
        raise AccuracyReportError(
            f"{label} must be numeric"
        )

    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise AccuracyReportError(
            f"{label} must be numeric"
        ) from error

    if not math.isfinite(numeric):
        raise AccuracyReportError(
            f"{label} must be finite"
        )

    return numeric


def _format_number(value: Any) -> str:
    return format(_finite_number(value, "report value"), ".17g")


def _format_optional_percent(value: Any) -> str:
    if value is None:
        return "N/A"

    numeric = _finite_number(
        value,
        "relative_drop",
    )
    return f"{format(numeric * 100.0, '.17g')}%"


def _result(value: Any) -> str:
    if not isinstance(value, bool):
        raise AccuracyReportError(
            "gate result must be boolean"
        )

    return "PASS" if value else "FAIL"


__all__ = [
    "AccuracyReportError",
    "accuracy_report_sha256",
    "verify_accuracy_report",
    "write_accuracy_report",
]
