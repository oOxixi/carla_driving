"""A3 Student weight artifacts and fail-closed FP32 promotion gate."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

from .preflight import is_protected_split


CORE_METRICS = (
    "behavior_accuracy",
    "target_pointer_accuracy",
    "target_lane_accuracy",
    "completion_accuracy",
    "plan_sequence_accuracy",
)
SAFETY_METRICS = ("safety_critical_behavior_recall",)


def export_candidate_weights(
    output_directory: str | Path,
    *,
    model: torch.nn.Module,
    identity: Mapping[str, Any],
    validation: Mapping[str, Any],
    checkpoint_sha256: str,
) -> dict[str, Any]:
    """Write a pure state_dict plus a non-promoted provenance manifest."""
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    weights_path = root / "student_v0_fp32_candidate.pt"
    temporary = weights_path.with_name(weights_path.name + ".tmp")
    torch.save(model.state_dict(), temporary)
    temporary.replace(weights_path)
    weights_sha = _sha256(weights_path)
    smoke = bool(identity.get("smoke_only") or identity.get("integration_smoke_only"))
    manifest = {
        "schema_version": "1.0",
        "git_sha": str(identity["git_sha"]),
        "source_worktree_dirty": bool(identity.get("git_dirty", True)),
        "teacher_git_sha": str(identity["teacher_git_sha"]),
        "teacher_model_id": str(identity["teacher_model_id"]),
        "teacher_model_revision": str(identity["teacher_model_revision"]),
        "teacher_artifact_fingerprint_sha256": str(
            identity["teacher_artifact_fingerprint_sha256"]
        ),
        "teacher_identity_policy": str(identity["teacher_identity_policy"]),
        "model_id": str(identity["model_id"]),
        "config_id": str(identity["model_config_id"]),
        "weights_file": weights_path.name,
        "weights_sha256": weights_sha,
        "source_checkpoint_sha256": str(checkpoint_sha256),
        "dataset_version": str(identity["dataset_version"]),
        "gate_status": "MOCK_ONLY" if smoke else "PENDING_A3_FP32_GATE",
        "validation_metrics": dict(validation),
    }
    manifest_path = root / "student_v0_fp32_candidate.json"
    _write_json(manifest_path, manifest)
    return {**manifest, "weights_path": str(weights_path), "manifest_path": str(manifest_path)}


def promote_fp32_candidate(
    candidate_manifest: Mapping[str, Any],
    *,
    weights_path: str | Path,
    teacher_evaluation: Mapping[str, Any],
    student_evaluation: Mapping[str, Any],
    output_path: str | Path,
    max_core_drop: float = 0.015,
    max_safety_drop: float = 0.0,
    core_metrics: Sequence[str] = CORE_METRICS,
    safety_metrics: Sequence[str] = SAFETY_METRICS,
) -> dict[str, Any]:
    """Promote only independent Validation evidence; frozen Test is forbidden."""
    if candidate_manifest.get("gate_status") != "PENDING_A3_FP32_GATE":
        raise ValueError("only a production candidate pending the A3 gate can be promoted")
    if candidate_manifest.get("source_worktree_dirty") is not False:
        raise ValueError("candidate must come from a clean committed challenge worktree")
    _validate_pinned_teacher_candidate(candidate_manifest)
    actual_weights_sha = _sha256(Path(weights_path))
    if actual_weights_sha != candidate_manifest.get("weights_sha256"):
        raise ValueError("candidate weight SHA256 does not match the manifest")
    if not 0.0 <= max_core_drop <= 1.0 or not 0.0 <= max_safety_drop <= 1.0:
        raise ValueError("gate drops must be in [0,1]")
    _validate_evaluation_identity(candidate_manifest, teacher_evaluation, "Teacher")
    _validate_evaluation_identity(candidate_manifest, student_evaluation, "Student")
    teacher_metrics = _metrics(teacher_evaluation, "Teacher")
    student_metrics = _metrics(student_evaluation, "Student")
    checks = []
    for name in core_metrics:
        checks.append(_drop_check(name, teacher_metrics, student_metrics, max_core_drop, "core"))
    for name in safety_metrics:
        checks.append(_drop_check(name, teacher_metrics, student_metrics, max_safety_drop, "safety"))
    try:
        schema_validity = float(student_evaluation.get("schema_validity", -1.0))
    except (TypeError, ValueError) as error:
        raise ValueError("Student schema_validity must be numeric") from error
    checks.append({
        "name": "schema_validity",
        "group": "contract",
        "teacher": 1.0,
        "student": schema_validity,
        "max_drop": 0.0,
        "passed": schema_validity == 1.0,
    })
    passed = all(bool(check["passed"]) for check in checks)
    report = {
        **dict(candidate_manifest),
        "gate_status": "A3_FP32_GATE_PASSED" if passed else "A3_FP32_GATE_FAILED",
        "gate_thresholds": {
            "max_core_drop": max_core_drop,
            "max_safety_drop": max_safety_drop,
        },
        "gate_checks": checks,
        "teacher_evaluation_id": teacher_evaluation.get("evaluation_id"),
        "student_evaluation_id": student_evaluation.get("evaluation_id"),
    }
    _write_json(Path(output_path), report)
    return report


def _validate_evaluation_identity(
    candidate: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    label: str,
) -> None:
    split = str(evaluation.get("split", ""))
    if is_protected_split(split) or split.strip().lower() not in {
        "val", "valid", "validation", "dev",
    }:
        raise ValueError(f"{label} gate evidence must use Validation, never frozen Test")
    if str(evaluation.get("dataset_version")) != str(candidate.get("dataset_version")):
        raise ValueError(f"{label} evaluation dataset_version does not match candidate")
    if not str(evaluation.get("evaluation_id", "")).strip():
        raise ValueError(f"{label} evaluation_id is required")
    for field in (
        "teacher_git_sha", "teacher_model_id", "teacher_model_revision",
        "teacher_artifact_fingerprint_sha256",
    ):
        if evaluation.get(field) != candidate.get(field):
            raise ValueError(f"{label} evaluation {field} does not match candidate")


def _validate_pinned_teacher_candidate(candidate: Mapping[str, Any]) -> None:
    if candidate.get("teacher_identity_policy") != "frozen_manifest":
        raise ValueError("production candidate requires the pinned Teacher identity")
    revision = str(candidate.get("teacher_model_revision", ""))
    fingerprint = str(candidate.get("teacher_artifact_fingerprint_sha256", ""))
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision.lower()):
        raise ValueError("production candidate requires a full Teacher model revision")
    if len(fingerprint) != 64 or any(
        char not in "0123456789abcdef" for char in fingerprint.lower()
    ):
        raise ValueError("production candidate requires a valid Teacher artifact fingerprint")


def _metrics(evaluation: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    value = evaluation.get("metrics")
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} evaluation.metrics must be an object")
    return value


def _drop_check(
    name: str,
    teacher: Mapping[str, Any],
    student: Mapping[str, Any],
    max_drop: float,
    group: str,
) -> dict[str, Any]:
    if name not in teacher or name not in student:
        raise ValueError(f"gate metric {name!r} is required for Teacher and Student")
    try:
        teacher_value, student_value = float(teacher[name]), float(student[name])
    except (TypeError, ValueError) as error:
        raise ValueError(f"gate metric {name!r} must be numeric") from error
    if (
        not math.isfinite(teacher_value)
        or not math.isfinite(student_value)
        or not 0.0 <= teacher_value <= 1.0
        or not 0.0 <= student_value <= 1.0
    ):
        raise ValueError(f"gate metric {name!r} must be in [0,1]")
    drop = teacher_value - student_value
    return {
        "name": name,
        "group": group,
        "teacher": teacher_value,
        "student": student_value,
        "drop": drop,
        "max_drop": max_drop,
        "passed": drop <= max_drop,
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(_json_safe(dict(value)), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "CORE_METRICS", "SAFETY_METRICS", "export_candidate_weights",
    "promote_fp32_candidate",
]
