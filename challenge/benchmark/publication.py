"""Atomic publication layout for final B2 evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .accuracy_report import (
    AccuracyReportError,
    verify_accuracy_report,
    write_accuracy_report,
)
from .comparison_artifact import (
    ComparisonArtifactError,
    verify_model_comparison_csv,
    write_model_comparison_csv,
)
from .gate_decision_package import (
    GateDecisionPackageError,
    verify_gate_decision_package,
)
from .policy_manifest import policy_manifest_sha256
from .teacher_baseline import (
    TeacherBaselineError,
    write_teacher_baseline,
)

class PublicationError(ValueError):
    """Raised when a B2 publication cannot be published safely."""


_TEACHER_FILES = frozenset(
    {
        "benchmark_manifest.json",
        "policy_manifest.json",
        "teacher_predictions.jsonl",
        "teacher_evaluation.json",
        "predictions.sha256",
    }
)

_STUDENT_FILES = frozenset(
    {
        "benchmark_manifest.json",
        "policy_manifest.json",
        "student_predictions.jsonl",
        "student_evaluation.json",
        "predictions.sha256",
    }
)

_TOP_LEVEL = frozenset(
    {
        "raw_results",
        "gate_decisions",
        "teacher_baseline.json",
        "model_comparison.csv",
        "accuracy_report.md",
    }
)

_RAW_RESULTS = frozenset(
    {
        "teacher",
        "student",
    }
)


def publish_b2_publication(
    destination: str | Path,
    *,
    teacher_bundle: str | Path,
    student_bundle: str | Path,
    gate_decision_package: str | Path,
) -> dict[str, Any]:
    """Publish verified B2 evidence without recomputing results."""

    target = Path(destination)
    staging = target.with_name(f".{target.name}.tmp")

    teacher = Path(teacher_bundle)
    student = Path(student_bundle)
    gate = Path(gate_decision_package)

    if target.exists():
        raise PublicationError(
            f"destination already exists: {target}"
        )

    if staging.exists():
        raise PublicationError(
            f"temporary destination already exists: {staging}"
        )

    _verify_evidence_bundle(
        teacher,
        role="teacher",
        expected_files=_TEACHER_FILES,
    )
    _verify_evidence_bundle(
        student,
        role="student",
        expected_files=_STUDENT_FILES,
    )
    _verify_gate(gate)

    _reject_overlap(
        target=target,
        staging=staging,
        sources=(teacher, student, gate),
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        (staging / "raw_results").mkdir(
            parents=True,
        )

        shutil.copytree(
            teacher,
            staging / "raw_results" / "teacher",
        )

        shutil.copytree(
            student,
            staging / "raw_results" / "student",
        )

        shutil.copytree(
            gate,
            staging / "gate_decisions",
        )

        teacher_evaluation_path = (
            staging
            / "raw_results"
            / "teacher"
            / "teacher_evaluation.json"
        )

        student_evaluation_path = (
            staging
            / "raw_results"
            / "student"
            / "student_evaluation.json"
        )

        teacher_evaluation = _read_json_object(
            teacher_evaluation_path,
            label="Teacher evaluation",
        )

        student_evaluation = _read_json_object(
            student_evaluation_path,
            label="Student evaluation",
        )

        gate_decision = _read_json_object(
            staging
            / "gate_decisions"
            / "gate_decision.json",
            label="Gate decision",
        )

        teacher_evaluation_sha = _sha256(
            teacher_evaluation_path
        )

        write_teacher_baseline(
            staging / "teacher_baseline.json",
            teacher_evaluation_path=teacher_evaluation_path,
            teacher_evaluation_sha256=teacher_evaluation_sha,
        )

        write_model_comparison_csv(
            staging / "model_comparison.csv",
            teacher_evaluation=teacher_evaluation,
            student_evaluation=student_evaluation,
        )

        write_accuracy_report(
            staging / "accuracy_report.md",
            gate_decision=gate_decision,
            model_comparison_path=(
                staging / "model_comparison.csv"
            ),
        )

        verified = verify_b2_publication(staging)

        staging.replace(target)

    except Exception as error:
        if staging.exists():
            shutil.rmtree(staging)

        if isinstance(error, PublicationError):
            raise

        raise PublicationError(
            f"cannot publish B2 evidence: {error}"
        ) from error

    result = dict(verified)
    result["directory"] = str(target)
    return result


def verify_b2_publication(
    directory: str | Path,
) -> dict[str, Any]:
    """Verify a published B2 evidence directory."""

    root = Path(directory)

    if not root.is_dir():
        raise PublicationError(
            f"publication directory does not exist: {root}"
        )

    _require_entries(
        root,
        _TOP_LEVEL,
        label="publication",
    )

    raw_results = root / "raw_results"

    if not raw_results.is_dir():
        raise PublicationError(
            "raw_results must be a directory"
        )

    _require_entries(
        raw_results,
        _RAW_RESULTS,
        label="raw_results",
    )

    teacher = raw_results / "teacher"
    student = raw_results / "student"
    gate = root / "gate_decisions"

    teacher_result = _verify_evidence_bundle(
        teacher,
        role="teacher",
        expected_files=_TEACHER_FILES,
    )

    student_result = _verify_evidence_bundle(
        student,
        role="student",
        expected_files=_STUDENT_FILES,
    )

    gate_result = _verify_gate(gate)

    teacher_evaluation = _read_json_object(
        teacher / "teacher_evaluation.json",
        label="Teacher evaluation",
    )

    student_evaluation = _read_json_object(
        student / "student_evaluation.json",
        label="Student evaluation",
    )

    gate_decision = _read_json_object(
        gate / "gate_decision.json",
        label="Gate decision",
    )

    _require_same_identity(
        teacher_evaluation,
        student_evaluation,
        fields=(
            "benchmark_manifest_sha256",
            "policy_manifest_sha256",
            "case_set_digest",
        ),
    )

    teacher_policy_manifest = _read_json_object(
        teacher / "policy_manifest.json",
        label="Teacher policy manifest",
    )

    student_policy_manifest = _read_json_object(
        student / "policy_manifest.json",
        label="Student policy manifest",
    )

    teacher_policy_sha = policy_manifest_sha256(
        teacher_policy_manifest
    )

    student_policy_sha = policy_manifest_sha256(
        student_policy_manifest
    )

    if teacher_policy_sha != student_policy_sha:
        raise PublicationError(
            "Teacher and Student policy manifests differ"
        )

    teacher_policy_binding = teacher_evaluation.get(
        "policy_manifest_sha256"
    )

    student_policy_binding = student_evaluation.get(
        "policy_manifest_sha256"
    )

    if teacher_policy_binding != teacher_policy_sha:
        raise PublicationError(
            "Teacher evaluation policy binding does not "
            "match published policy manifest"
        )

    if student_policy_binding != student_policy_sha:
        raise PublicationError(
            "Student evaluation policy binding does not "
            "match published policy manifest"
        )

    if (
        gate_result["policy_manifest_sha256"]
        != teacher_policy_sha
    ):
        raise PublicationError(
            "gate decision policy evidence does not match "
            "published policy manifest"
        )

    teacher_evaluation_sha = _canonical_mapping_sha256(
        teacher_evaluation
    )

    student_evaluation_sha = _canonical_mapping_sha256(
        student_evaluation
    )
    teacher_baseline = root / "teacher_baseline.json"

    try:
        teacher_baseline_bytes = teacher_baseline.read_bytes()
        teacher_evaluation_bytes = (
            teacher / "teacher_evaluation.json"
        ).read_bytes()
    except OSError as error:
        raise PublicationError(
            "cannot read Teacher baseline evidence"
        ) from error

    if teacher_baseline_bytes != teacher_evaluation_bytes:
        raise PublicationError(
            "Teacher baseline does not match "
            "published Teacher evaluation"
        )

    teacher_baseline_sha = _sha256(
        teacher_baseline
    )

    teacher_evaluation_file_sha = _sha256(
        teacher / "teacher_evaluation.json"
    )

    if teacher_baseline_sha != teacher_evaluation_file_sha:
        raise PublicationError(
            "Teacher baseline SHA256 does not match "
            "published Teacher evaluation"
        )

    try:
        comparison_result = verify_model_comparison_csv(
            root / "model_comparison.csv",
            gate_decision=gate_decision,
        )

        report_result = verify_accuracy_report(
            root / "accuracy_report.md",
            gate_decision=gate_decision,
            model_comparison_path=(
                root / "model_comparison.csv"
            ),
        )
    except (
        ComparisonArtifactError,
        AccuracyReportError,
        OSError,
    ) as error:
        raise PublicationError(
            f"invalid publication report artifact: {error}"
        ) from error

    if (
        gate_result["teacher_evaluation_sha256"]
        != teacher_evaluation_sha
    ):
        raise PublicationError(
            "gate decision Teacher evidence does not match "
            "published Teacher evaluation"
        )

    if (
        gate_result["student_evaluation_sha256"]
        != student_evaluation_sha
    ):
        raise PublicationError(
            "gate decision Student evidence does not match "
            "published Student evaluation"
        )

    return {
        "valid": True,
        "gate_status": gate_result["gate_status"],
        "teacher_predictions_sha256": teacher_result[
            "predictions_sha256"
        ],
        "student_predictions_sha256": student_result[
            "predictions_sha256"
        ],
        "teacher_evaluation_sha256": (
            teacher_evaluation_sha
        ),
        "student_evaluation_sha256": (
            student_evaluation_sha
        ),
        "policy_manifest_sha256": teacher_policy_sha,
        "gate_decision_sha256": gate_result[
            "gate_decision_sha256"
        ],
        "gate_manifest_sha256": gate_result[
            "manifest_sha256"
        ],
        "teacher_baseline_sha256": teacher_baseline_sha,
        "model_comparison_sha256": comparison_result["sha256"],
        "accuracy_report_sha256": report_result["sha256"],
    }


def _verify_evidence_bundle(
    directory: Path,
    *,
    role: str,
    expected_files: frozenset[str],
) -> dict[str, str]:
    if not directory.is_dir():
        raise PublicationError(
            f"{role} bundle does not exist: {directory}"
        )

    _require_entries(
        directory,
        expected_files,
        label=f"{role} bundle",
    )

    predictions_name = f"{role}_predictions.jsonl"
    evaluation_name = f"{role}_evaluation.json"

    predictions_path = directory / predictions_name
    evaluation_path = directory / evaluation_name
    checksum_path = directory / "predictions.sha256"

    predictions_sha = _sha256(predictions_path)

    try:
        checksum_text = checksum_path.read_text(
            encoding="ascii"
        )
    except (OSError, UnicodeError) as error:
        raise PublicationError(
            f"cannot read {role} prediction checksum"
        ) from error

    expected_checksum = (
        f"{predictions_sha}  {predictions_name}\n"
    )

    if checksum_text != expected_checksum:
        raise PublicationError(
            f"{role} prediction checksum does not match"
        )

    evaluation = _read_json_object(
        evaluation_path,
        label=f"{role} evaluation",
    )

    if (
        evaluation.get("predictions_sha256")
        != predictions_sha
    ):
        raise PublicationError(
            f"{role} evaluation prediction binding "
            "does not match"
        )

    benchmark_sha = _sha256(
        directory / "benchmark_manifest.json"
    )

    policy_manifest = _read_json_object(
        directory / "policy_manifest.json",
        label=f"{role} policy manifest",
    )

    policy_sha = policy_manifest_sha256(
        policy_manifest
    )

    if (
        evaluation.get("benchmark_manifest_sha256")
        != benchmark_sha
    ):
        raise PublicationError(
            f"{role} evaluation benchmark binding "
            "does not match"
        )

    if (
        evaluation.get("policy_manifest_sha256")
        != policy_sha
    ):
        raise PublicationError(
            f"{role} evaluation policy binding "
            "does not match"
        )

    return {
        "predictions_sha256": predictions_sha,
        "evaluation_sha256": (
            _canonical_mapping_sha256(evaluation)
        ),
        "benchmark_manifest_sha256": benchmark_sha,
        "policy_manifest_sha256": policy_sha,
    }


def _verify_gate(
    directory: Path,
) -> dict[str, Any]:
    try:
        return verify_gate_decision_package(directory)
    except (GateDecisionPackageError, OSError) as error:
        raise PublicationError(
            f"invalid gate decision package: {error}"
        ) from error


def _require_entries(
    directory: Path,
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    try:
        actual = {
            path.name
            for path in directory.iterdir()
        }
    except OSError as error:
        raise PublicationError(
            f"cannot inspect {label}"
        ) from error

    if actual != expected:
        raise PublicationError(
            f"{label} contents do not match contract: "
            f"expected {sorted(expected)}, "
            f"got {sorted(actual)}"
        )


def _read_json_object(
    path: Path,
    *,
    label: str,
) -> Mapping[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        raise PublicationError(
            f"cannot read {label}"
        ) from error

    if not isinstance(value, Mapping):
        raise PublicationError(
            f"{label} must be an object"
        )

    return value


def _canonical_mapping_sha256(
    value: Mapping[str, Any],
) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )

    return hashlib.sha256(payload).hexdigest()


def _sha256(
    path: Path,
) -> str:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise PublicationError(
            f"cannot read file: {path}"
        ) from error

    return hashlib.sha256(payload).hexdigest()


def _require_same_identity(
    teacher: Mapping[str, Any],
    student: Mapping[str, Any],
    *,
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        teacher_value = teacher.get(field)
        student_value = student.get(field)

        if (
            not isinstance(teacher_value, str)
            or not teacher_value
            or teacher_value != student_value
        ):
            raise PublicationError(
                f"Teacher and Student {field} "
                "do not match"
            )


def _reject_overlap(
    *,
    target: Path,
    staging: Path,
    sources: tuple[Path, ...],
) -> None:
    target_resolved = target.resolve()
    staging_resolved = staging.resolve()

    for source in sources:
        source_resolved = source.resolve()

        if (
            source_resolved == target_resolved
            or source_resolved == staging_resolved
            or source_resolved in target_resolved.parents
            or target_resolved in source_resolved.parents
            or source_resolved in staging_resolved.parents
            or staging_resolved in source_resolved.parents
        ):
            raise PublicationError(
                "publication source overlaps destination "
                f"or staging directory: {source}"
            )


__all__ = [
    "PublicationError",
    "publish_b2_publication",
    "verify_b2_publication",
]