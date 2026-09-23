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
SIGNED_D2_FORMAL_POLICY = "signed_d2_release_formal"
SIGNED_CUMULATIVE_FORMAL_POLICY = "signed_cumulative_release_formal"
FORMAL_SIGNED_POLICIES = {
    SIGNED_D2_FORMAL_POLICY,
    SIGNED_CUMULATIVE_FORMAL_POLICY,
}
SIGNED_D2_MULTI_TEACHER_ID = "MULTI_PINNED_B1_D2_V1_1"
SIGNED_CUMULATIVE_MULTI_TEACHER_ID = "MULTI_PINNED_B1_D2_V1_1_PLUS_D3_WAVE1"
FORMAL_GATE_TEACHER_V4 = {
    "teacher_profile": "b1-pinned-teacher-v4",
    "teacher_git_sha": "95e97b00def8ec36f12937da34ce8bb9082c4a04",
    "teacher_model_id": "Qwen/Qwen3.5-2B",
    "teacher_model_revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
    "teacher_artifact_fingerprint_sha256": (
        "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
    ),
    "teacher_quantization": None,
    "teacher_dtype": "bfloat16",
}


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
        "release_manifest_sha256": identity.get("release_manifest_sha256"),
        "a3_view_manifest_sha256": identity.get("a3_view_manifest_sha256"),
        "d2_release_manifest_sha256": identity.get("d2_release_manifest_sha256"),
        "b1_signature_sha256": identity.get("b1_signature_sha256"),
        "source_evidence_sha256": identity.get("source_evidence_sha256"),
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
    _validate_formal_evaluation_pair(
        candidate_manifest,
        teacher_evaluation,
        student_evaluation,
    )
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
    if candidate_manifest.get("teacher_identity_policy") in FORMAL_SIGNED_POLICIES:
        report["gate_evidence"] = {
            "benchmark_manifest_sha256": teacher_evaluation["benchmark_manifest_sha256"],
            "policy_manifest_sha256": teacher_evaluation["policy_manifest_sha256"],
            "case_set_digest": teacher_evaluation["case_set_digest"],
            "evaluator_git_sha": teacher_evaluation["evaluator_git_sha"],
            "sample_count": teacher_evaluation["sample_count"],
            "teacher_predictions_sha256": teacher_evaluation["predictions_sha256"],
            "student_predictions_sha256": student_evaluation["predictions_sha256"],
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
    if candidate.get("teacher_identity_policy") in FORMAL_SIGNED_POLICIES:
        for field, expected in FORMAL_GATE_TEACHER_V4.items():
            if evaluation.get(field) != expected:
                raise ValueError(
                    f"{label} evaluation {field} does not match the frozen Teacher v4 gate identity"
                )
    else:
        for field in (
            "teacher_git_sha", "teacher_model_id", "teacher_model_revision",
            "teacher_artifact_fingerprint_sha256",
        ):
            if evaluation.get(field) != candidate.get(field):
                raise ValueError(f"{label} evaluation {field} does not match candidate")
    if label == "Student":
        for field in ("model_id", "config_id", "weights_sha256"):
            if evaluation.get(field) != candidate.get(field):
                raise ValueError(f"Student evaluation {field} does not match candidate")


def _validate_pinned_teacher_candidate(candidate: Mapping[str, Any]) -> None:
    policy = str(candidate.get("teacher_identity_policy", ""))
    if policy not in {"frozen_manifest", *FORMAL_SIGNED_POLICIES}:
        raise ValueError(
            "production candidate requires frozen_manifest or "
            "a formal signed-release Teacher identity"
        )
    revision = str(candidate.get("teacher_model_revision", ""))
    fingerprint = str(candidate.get("teacher_artifact_fingerprint_sha256", ""))
    _require_hex(revision, 40, "production candidate requires a full Teacher model revision")
    _require_hex(
        fingerprint,
        64,
        "production candidate requires a valid Teacher artifact fingerprint",
    )
    if policy == "frozen_manifest":
        _require_hex(
            str(candidate.get("teacher_git_sha", "")),
            40,
            "frozen_manifest candidate requires a full Teacher Git SHA",
        )
        return
    expected_multi_teacher = (
        SIGNED_CUMULATIVE_MULTI_TEACHER_ID
        if policy == SIGNED_CUMULATIVE_FORMAL_POLICY
        else SIGNED_D2_MULTI_TEACHER_ID
    )
    if candidate.get("teacher_git_sha") != expected_multi_teacher:
        raise ValueError(
            "signed candidate requires the fixed multi-cohort Teacher identity"
        )
    for field in ("release_manifest_sha256", "a3_view_manifest_sha256"):
        _require_hex(
            str(candidate.get(field, "")),
            64,
            f"signed D2 candidate requires a valid {field}",
        )
    if policy == SIGNED_CUMULATIVE_FORMAL_POLICY:
        for field in (
            "d2_release_manifest_sha256", "b1_signature_sha256",
            "source_evidence_sha256",
        ):
            _require_hex(
                str(candidate.get(field, "")), 64,
                f"signed cumulative candidate requires a valid {field}",
            )


def _validate_formal_evaluation_pair(
    candidate: Mapping[str, Any],
    teacher: Mapping[str, Any],
    student: Mapping[str, Any],
) -> None:
    if candidate.get("teacher_identity_policy") not in FORMAL_SIGNED_POLICIES:
        return
    for evaluation, label in ((teacher, "Teacher"), (student, "Student")):
        evidence_fields = ["release_manifest_sha256", "a3_view_manifest_sha256"]
        if candidate.get("teacher_identity_policy") == SIGNED_CUMULATIVE_FORMAL_POLICY:
            evidence_fields.extend([
                "d2_release_manifest_sha256", "b1_signature_sha256",
                "source_evidence_sha256",
            ])
        for field in evidence_fields:
            if evaluation.get(field) != candidate.get(field):
                raise ValueError(f"{label} evaluation {field} does not match candidate")
        for field in (
            "benchmark_manifest_sha256",
            "policy_manifest_sha256",
            "case_set_digest",
            "predictions_sha256",
        ):
            _require_hex(
                str(evaluation.get(field, "")),
                64,
                f"{label} evaluation requires a valid {field}",
            )
        _require_hex(
            str(evaluation.get("evaluator_git_sha", "")),
            40,
            f"{label} evaluation requires a valid evaluator_git_sha",
        )
        sample_count = evaluation.get("sample_count")
        if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 1:
            raise ValueError(f"{label} evaluation sample_count must be a positive integer")
    for field in (
        "benchmark_manifest_sha256",
        "policy_manifest_sha256",
        "case_set_digest",
        "evaluator_git_sha",
        "sample_count",
    ):
        if teacher.get(field) != student.get(field):
            raise ValueError(f"Teacher and Student evaluation {field} must match")
    if student.get("weights_sha256") != candidate.get("weights_sha256"):
        raise ValueError("Student evaluation weights_sha256 does not match candidate")


def _require_hex(value: str, length: int, message: str) -> None:
    if len(value) != length or any(
        char not in "0123456789abcdef" for char in value.lower()
    ):
        raise ValueError(message)


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
    "CORE_METRICS", "SAFETY_METRICS", "SIGNED_D2_FORMAL_POLICY",
    "FORMAL_GATE_TEACHER_V4",
    "export_candidate_weights",
    "promote_fp32_candidate",
]
