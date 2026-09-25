"""Immutable publication of the B2 Teacher baseline artifact."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .evaluation_artifact import (
    EvaluationArtifactError,
    canonical_evaluation_json,
)


class TeacherBaselineError(ValueError):
    """Raised when a Teacher baseline cannot be published safely."""


def write_teacher_baseline(
    destination: str | Path,
    *,
    teacher_evaluation_path: str | Path,
    teacher_evaluation_sha256: str,
) -> dict[str, Any]:
    """
    Publish an existing canonical Teacher evaluation as teacher_baseline.json.

    No metrics are recomputed. The published bytes must be exactly the
    canonical bytes of the verified Teacher evaluation.
    """

    target = Path(destination)
    source = Path(teacher_evaluation_path)

    if target.exists():
        raise TeacherBaselineError(
            f"destination already exists: {target}"
        )

    if not target.parent.exists():
        raise TeacherBaselineError(
            f"destination parent does not exist: {target.parent}"
        )

    if not source.is_file():
        raise TeacherBaselineError(
            f"Teacher evaluation does not exist: {source}"
        )

    expected_sha = _required_sha256(
        teacher_evaluation_sha256,
        "teacher_evaluation_sha256",
    )

    source_bytes = source.read_bytes()
    actual_sha = hashlib.sha256(source_bytes).hexdigest()

    if actual_sha != expected_sha:
        raise TeacherBaselineError(
            "Teacher evaluation SHA256 does not match expected value"
        )

    try:
        artifact = json.loads(source_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TeacherBaselineError(
            "Teacher evaluation is not valid JSON"
        ) from error

    if not isinstance(artifact, Mapping):
        raise TeacherBaselineError(
            "Teacher evaluation must be a JSON object"
        )

    if artifact.get("evaluation_role") != "teacher":
        raise TeacherBaselineError(
            "Teacher baseline requires evaluation_role='teacher'"
        )

    try:
        canonical_bytes = canonical_evaluation_json(artifact)
    except EvaluationArtifactError as error:
        raise TeacherBaselineError(
            f"Teacher evaluation is not canonicalizable: {error}"
        ) from error

    if source_bytes != canonical_bytes:
        raise TeacherBaselineError(
            "Teacher evaluation bytes are not canonical"
        )

    temporary = target.with_name(
        f".{target.name}.tmp"
    )

    if temporary.exists():
        raise TeacherBaselineError(
            f"temporary destination already exists: {temporary}"
        )

    try:
        with temporary.open("xb") as handle:
            handle.write(source_bytes)
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(target)

    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

        raise TeacherBaselineError(
            f"cannot publish Teacher baseline: {error}"
        ) from error

    return {
        "path": target,
        "sha256": actual_sha,
        "teacher_evaluation_sha256": actual_sha,
        "evaluation_id": artifact.get("evaluation_id"),
        "benchmark_manifest_sha256": artifact.get(
            "benchmark_manifest_sha256"
        ),
        "policy_manifest_sha256": artifact.get(
            "policy_manifest_sha256"
        ),
        "case_set_digest": artifact.get("case_set_digest"),
        "evaluator_git_sha": artifact.get("evaluator_git_sha"),
        "sample_count": artifact.get("sample_count"),
    }


def _required_sha256(
    value: Any,
    label: str,
) -> str:
    if not isinstance(value, str):
        raise TeacherBaselineError(
            f"{label} must be a 64-character SHA256"
        )

    text = value.strip().lower()

    if len(text) != 64:
        raise TeacherBaselineError(
            f"{label} must be a 64-character SHA256"
        )

    try:
        int(text, 16)
    except ValueError as error:
        raise TeacherBaselineError(
            f"{label} must be hexadecimal"
        ) from error

    return text


__all__ = [
    "TeacherBaselineError",
    "write_teacher_baseline",
]