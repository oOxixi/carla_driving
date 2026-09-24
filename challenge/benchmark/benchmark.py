"""B2 benchmark data boundary and traceability checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "sample_id",
    "model_request",
    "teacher_plan",
)


def canonical_lf_sha256(path: str | Path) -> str:
    """Return SHA256 after normalizing Windows CRLF to repository LF bytes."""
    data = Path(path).read_bytes()
    canonical = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical).hexdigest()


def load_benchmark_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load B1 JSONL records without filtering or changing their semantics."""
    source = Path(path)

    if not source.is_file():
        raise FileNotFoundError(source)

    cases: list[dict[str, Any]] = []

    for line_number, raw in enumerate(
        source.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue

        try:
            record = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{source}:{line_number}: invalid JSON: {error}"
            ) from error

        _validate_case(record, source, line_number)
        cases.append(record)

    if not cases:
        raise ValueError(f"{source}: no benchmark cases")

    return cases


def _validate_case(
    record: Any,
    source: Path,
    line_number: int,
) -> None:
    """Fail closed when a benchmark case loses its basic identity."""

    if not isinstance(record, dict):
        raise ValueError(
            f"{source}:{line_number}: benchmark case must be an object"
        )

    missing = [field for field in REQUIRED_FIELDS if field not in record]

    if missing:
        raise ValueError(
            f"{source}:{line_number}: missing required fields: {missing}"
        )

    sample_id = record["sample_id"]
    request = record["model_request"]
    plan = record["teacher_plan"]

    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError(
            f"{source}:{line_number}: sample_id must be non-empty"
        )

    if not isinstance(request, dict):
        raise ValueError(
            f"{source}:{line_number}: model_request must be an object"
        )

    if not isinstance(plan, dict):
        raise ValueError(
            f"{source}:{line_number}: teacher_plan must be an object"
        )

    for identity_field in ("request_id", "command_id"):
        request_value = request.get(identity_field)
        plan_value = plan.get(identity_field)

        if not request_value or not plan_value:
            raise ValueError(
                f"{source}:{line_number}: missing {identity_field}"
            )

        if request_value != plan_value:
            raise ValueError(
                f"{source}:{line_number}: {identity_field} mismatch"
            )

    if plan.get("schema_version") != "2.0":
        raise ValueError(
            f"{source}:{line_number}: teacher_plan must use ManeuverPlan V2"
        )

    steps = plan.get("steps")

    if not isinstance(steps, list) or not steps:
        raise ValueError(
            f"{source}:{line_number}: teacher_plan.steps must be non-empty"
        )


__all__ = [
    "canonical_lf_sha256",
    "load_benchmark_cases",
]