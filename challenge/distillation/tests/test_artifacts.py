import hashlib
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

TEACHER_SHA = "b" * 40
TEACHER_REVISION = "d" * 40
TEACHER_FINGERPRINT = "e" * 64

from challenge.distillation.artifacts import (  # noqa: E402
    FORMAL_GATE_TEACHER_V4,
    export_candidate_weights,
    promote_fp32_candidate,
)
from challenge.distillation.dummy_student import DummyStudent  # noqa: E402


def test_formal_gate_teacher_identity_matches_frozen_v4_manifest() -> None:
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads(
        (root / "challenge" / "teacher_pinned_manifest_v4.json").read_text(
            encoding="utf-8"
        )
    )
    assert FORMAL_GATE_TEACHER_V4 == {
        "teacher_profile": manifest["teacher_profile"],
        "teacher_git_sha": manifest["teacher_git_sha"],
        "teacher_model_id": manifest["model_id"],
        "teacher_model_revision": manifest["model_revision"],
        "teacher_artifact_fingerprint_sha256": manifest["model_artifact_sha256"],
        "teacher_quantization": manifest["quantization"],
        "teacher_dtype": manifest["dtype"],
    }


def _evaluation(evaluation_id: str, value: float, *, split: str = "validation") -> dict:
    return {
        "evaluation_id": evaluation_id,
        "split": split,
        "dataset_version": "b1-v1",
        "teacher_git_sha": TEACHER_SHA,
        "teacher_model_id": "teacher",
        "teacher_model_revision": TEACHER_REVISION,
        "teacher_artifact_fingerprint_sha256": TEACHER_FINGERPRINT,
        "schema_validity": 1.0,
        "metrics": {
            "behavior_accuracy": value,
            "target_pointer_accuracy": value,
            "target_lane_accuracy": value,
            "completion_accuracy": value,
            "plan_sequence_accuracy": value,
            "safety_critical_behavior_recall": value,
        },
    }


def _student_evaluation(
    evaluation_id: str,
    value: float,
    weights_sha256: str,
    *,
    split: str = "validation",
) -> dict:
    evaluation = _evaluation(evaluation_id, value, split=split)
    evaluation.update({
        "model_id": "student-v0-r3-fp32",
        "config_id": "student-v0-r3-structure-20260911",
        "weights_sha256": weights_sha256,
    })
    return evaluation


def _formal_candidate(weights_sha256: str) -> dict:
    return {
        "gate_status": "PENDING_A3_FP32_GATE",
        "weights_sha256": weights_sha256,
        "dataset_version": "b1-v1",
        "git_sha": "a" * 40,
        "model_id": "student-v0-r3-fp32",
        "config_id": "student-v0-r3-structure-20260911",
        "source_worktree_dirty": False,
        "teacher_git_sha": "MULTI_PINNED_B1_D2_V1_1",
        "teacher_model_id": "teacher",
        "teacher_model_revision": TEACHER_REVISION,
        "teacher_artifact_fingerprint_sha256": TEACHER_FINGERPRINT,
        "teacher_identity_policy": "signed_d2_release_formal",
        "release_manifest_sha256": "1" * 64,
        "a3_view_manifest_sha256": "2" * 64,
    }


def _formal_evaluation(
    evaluation_id: str,
    value: float,
    *,
    weights_sha256: str | None = None,
) -> dict:
    evaluation = _evaluation(evaluation_id, value)
    evaluation.update({
        **FORMAL_GATE_TEACHER_V4,
        "release_manifest_sha256": "1" * 64,
        "a3_view_manifest_sha256": "2" * 64,
        "benchmark_manifest_sha256": "3" * 64,
        "policy_manifest_sha256": "4" * 64,
        "case_set_digest": "5" * 64,
        "evaluator_git_sha": "6" * 40,
        "predictions_sha256": "7" * 64 if weights_sha256 is None else "8" * 64,
        "sample_count": 128,
    })
    if weights_sha256 is not None:
        evaluation.update({
            "model_id": "student-v0-r3-fp32",
            "config_id": "student-v0-r3-structure-20260911",
            "weights_sha256": weights_sha256,
        })
    return evaluation


def _cumulative_candidate(weights_sha256: str) -> dict:
    candidate = _formal_candidate(weights_sha256)
    candidate.update({
        "teacher_git_sha": "MULTI_PINNED_B1_D2_V1_1_PLUS_D3_WAVE1",
        "teacher_identity_policy": "signed_cumulative_release_formal",
        "d2_release_manifest_sha256": "9" * 64,
        "b1_signature_sha256": "a" * 64,
        "source_evidence_sha256": "b" * 64,
    })
    return candidate


def _cumulative_evaluation(
    evaluation_id: str, value: float, *, weights_sha256: str | None = None,
) -> dict:
    evaluation = _formal_evaluation(
        evaluation_id, value, weights_sha256=weights_sha256,
    )
    evaluation.update({
        "d2_release_manifest_sha256": "9" * 64,
        "b1_signature_sha256": "a" * 64,
        "source_evidence_sha256": "b" * 64,
    })
    return evaluation


def test_candidate_is_not_promoted_without_independent_gate(tmp_path: Path) -> None:
    identity = {
        "git_sha": "a" * 40,
        "teacher_git_sha": TEACHER_SHA,
        "teacher_model_id": "teacher",
        "teacher_model_revision": TEACHER_REVISION,
        "teacher_artifact_fingerprint_sha256": TEACHER_FINGERPRINT,
        "teacher_identity_policy": "frozen_manifest",
        "model_id": "student-v0-r3-fp32",
        "model_config_id": "student-v0-r3-structure-20260911",
        "dataset_version": "b1-v1",
        "smoke_only": False,
        "integration_smoke_only": False,
    }
    candidate = export_candidate_weights(
        tmp_path, model=DummyStudent(), identity=identity,
        validation={}, checkpoint_sha256="c" * 64,
    )

    assert candidate["gate_status"] == "PENDING_A3_FP32_GATE"
    payload = torch.load(candidate["weights_path"], weights_only=True)
    assert set(payload) == set(DummyStudent().state_dict())


def test_candidate_serializes_undefined_metrics_as_null(tmp_path: Path) -> None:
    identity = {
        "git_sha": "a" * 40,
        "teacher_git_sha": TEACHER_SHA,
        "teacher_model_id": "teacher",
        "teacher_model_revision": TEACHER_REVISION,
        "teacher_artifact_fingerprint_sha256": TEACHER_FINGERPRINT,
        "teacher_identity_policy": "frozen_manifest",
        "model_id": "student-v0-r3-fp32",
        "model_config_id": "student-v0-r3-structure-20260911",
        "dataset_version": "mock-v1",
        "smoke_only": True,
        "integration_smoke_only": False,
    }
    candidate = export_candidate_weights(
        tmp_path, model=DummyStudent(), identity=identity,
        validation={"undefined_recall": float("nan")}, checkpoint_sha256="c" * 64,
    )
    text = Path(candidate["manifest_path"]).read_text(encoding="utf-8")
    assert '"undefined_recall": null' in text


def test_fp32_gate_passes_small_drop_and_rejects_test_evidence(tmp_path: Path) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"candidate")
    candidate = {
        "gate_status": "PENDING_A3_FP32_GATE",
        "weights_sha256": hashlib.sha256(b"candidate").hexdigest(),
        "dataset_version": "b1-v1",
        "git_sha": "a" * 40,
        "model_id": "student-v0-r3-fp32",
        "config_id": "student-v0-r3-structure-20260911",
        "source_worktree_dirty": False,
        "teacher_git_sha": TEACHER_SHA,
        "teacher_model_id": "teacher",
        "teacher_model_revision": TEACHER_REVISION,
        "teacher_artifact_fingerprint_sha256": TEACHER_FINGERPRINT,
        "teacher_identity_policy": "frozen_manifest",
    }
    student_evaluation = _student_evaluation(
        "student-val", 0.94, candidate["weights_sha256"]
    )
    student_evaluation["metrics"]["safety_critical_behavior_recall"] = 0.95
    report = promote_fp32_candidate(
        candidate,
        weights_path=weights,
        teacher_evaluation=_evaluation("teacher-val", 0.95),
        student_evaluation=student_evaluation,
        output_path=tmp_path / "manifest.json",
    )
    assert report["gate_status"] == "A3_FP32_GATE_PASSED"

    with pytest.raises(ValueError, match="never frozen Test"):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=_evaluation("teacher-test", 0.95, split="frozen_test"),
            student_evaluation=_student_evaluation(
                "student-val", 0.94, candidate["weights_sha256"]
            ),
            output_path=tmp_path / "rejected.json",
        )

    mismatched = _student_evaluation(
        "student-wrong-teacher", 0.94, candidate["weights_sha256"]
    )
    mismatched["teacher_artifact_fingerprint_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="fingerprint"):
        promote_fp32_candidate(
            candidate, weights_path=weights,
            teacher_evaluation=_evaluation("teacher-val-2", 0.95),
            student_evaluation=mismatched,
            output_path=tmp_path / "mismatched.json",
        )


@pytest.mark.parametrize("field", ("model_id", "config_id", "weights_sha256"))
def test_fp32_gate_rejects_mismatched_student_identity(
    tmp_path: Path,
    field: str,
) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"candidate")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = {
        **_formal_candidate(weights_sha),
        "teacher_git_sha": TEACHER_SHA,
        "teacher_identity_policy": "frozen_manifest",
        "release_manifest_sha256": None,
        "a3_view_manifest_sha256": None,
    }
    student = _student_evaluation("student-val", 0.94, weights_sha)
    student[field] = "mismatch"

    with pytest.raises(ValueError, match=field):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=_evaluation("teacher-val", 0.95),
            student_evaluation=student,
            output_path=tmp_path / "rejected.json",
        )


def test_signed_d2_formal_candidate_accepts_matched_independent_evidence(
    tmp_path: Path,
) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"signed-d2-candidate")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = _formal_candidate(weights_sha)
    student_evaluation = _formal_evaluation(
        "student-independent-val", 0.94, weights_sha256=weights_sha
    )
    student_evaluation["metrics"]["safety_critical_behavior_recall"] = 0.95

    report = promote_fp32_candidate(
        candidate,
        weights_path=weights,
        teacher_evaluation=_formal_evaluation("teacher-independent-val", 0.95),
        student_evaluation=student_evaluation,
        output_path=tmp_path / "signed-formal-manifest.json",
    )

    assert report["gate_status"] == "A3_FP32_GATE_PASSED"
    assert report["teacher_identity_policy"] == "signed_d2_release_formal"
    assert report["gate_evidence"] == {
        "benchmark_manifest_sha256": "3" * 64,
        "policy_manifest_sha256": "4" * 64,
        "case_set_digest": "5" * 64,
        "evaluator_git_sha": "6" * 40,
        "sample_count": 128,
        "teacher_predictions_sha256": "7" * 64,
        "student_predictions_sha256": "8" * 64,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("benchmark_manifest_sha256", "5" * 64, "benchmark_manifest_sha256"),
        ("policy_manifest_sha256", "6" * 64, "policy_manifest_sha256"),
        ("case_set_digest", "9" * 64, "case_set_digest"),
        ("evaluator_git_sha", "a" * 40, "evaluator_git_sha"),
        ("sample_count", 127, "sample_count"),
        ("weights_sha256", "7" * 64, "weights_sha256"),
    ),
)
def test_signed_d2_formal_candidate_rejects_mismatched_evaluation_identity(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"signed-d2-candidate")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = _formal_candidate(weights_sha)
    student = _formal_evaluation(
        "student-independent-val", 0.94, weights_sha256=weights_sha
    )
    student[field] = value

    with pytest.raises(ValueError, match=message):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=_formal_evaluation("teacher-independent-val", 0.95),
            student_evaluation=student,
            output_path=tmp_path / "rejected.json",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("benchmark_manifest_sha256", "bad"),
        ("policy_manifest_sha256", None),
        ("case_set_digest", "bad"),
        ("evaluator_git_sha", "bad"),
        ("predictions_sha256", "bad"),
        ("sample_count", 0),
    ),
)
def test_signed_d2_formal_candidate_rejects_invalid_evidence_fields(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"signed-d2-candidate")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = _formal_candidate(weights_sha)
    teacher = _formal_evaluation("teacher-independent-val", 0.95)
    teacher[field] = value

    with pytest.raises(ValueError, match=field):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=teacher,
            student_evaluation=_formal_evaluation(
                "student-independent-val", 0.94, weights_sha256=weights_sha
            ),
            output_path=tmp_path / "rejected.json",
        )


@pytest.mark.parametrize("field", tuple(FORMAL_GATE_TEACHER_V4))
def test_signed_d2_formal_candidate_requires_teacher_v4_gate_identity(
    tmp_path: Path,
    field: str,
) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"signed-d2-candidate")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = _formal_candidate(weights_sha)
    teacher = _formal_evaluation("teacher-independent-val", 0.95)
    teacher[field] = "mismatch"

    with pytest.raises(ValueError, match=field):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=teacher,
            student_evaluation=_formal_evaluation(
                "student-independent-val", 0.94, weights_sha256=weights_sha
            ),
            output_path=tmp_path / "rejected.json",
        )


@pytest.mark.parametrize("field", ("release_manifest_sha256", "a3_view_manifest_sha256"))
def test_signed_d2_formal_candidate_requires_signed_data_hashes(
    tmp_path: Path,
    field: str,
) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"signed-d2-candidate")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = _formal_candidate(weights_sha)
    candidate[field] = None

    with pytest.raises(ValueError, match=field):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=_formal_evaluation("teacher-independent-val", 0.95),
            student_evaluation=_formal_evaluation(
                "student-independent-val", 0.94, weights_sha256=weights_sha
            ),
            output_path=tmp_path / "rejected.json",
        )


def test_signed_d2_formal_candidate_rejects_smoke_policy(tmp_path: Path) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"signed-d2-candidate")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = _formal_candidate(weights_sha)
    candidate["teacher_identity_policy"] = "signed_d2_release_smoke"

    with pytest.raises(ValueError, match="Teacher identity"):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=_formal_evaluation("teacher-independent-val", 0.95),
            student_evaluation=_formal_evaluation(
                "student-independent-val", 0.94, weights_sha256=weights_sha
            ),
            output_path=tmp_path / "rejected.json",
        )


def test_signed_cumulative_candidate_binds_both_releases_and_signature(
    tmp_path: Path,
) -> None:
    weights = tmp_path / "student.pt"
    weights.write_bytes(b"cumulative-student")
    weights_sha = hashlib.sha256(weights.read_bytes()).hexdigest()
    candidate = _cumulative_candidate(weights_sha)
    report = promote_fp32_candidate(
        candidate,
        weights_path=weights,
        teacher_evaluation=_cumulative_evaluation("teacher-cumulative", 0.95),
        student_evaluation=_cumulative_evaluation(
            "student-cumulative", 0.95, weights_sha256=weights_sha,
        ),
        output_path=tmp_path / "promoted.json",
    )
    assert report["gate_status"] == "A3_FP32_GATE_PASSED"

    changed = _cumulative_evaluation(
        "student-changed", 0.95, weights_sha256=weights_sha,
    )
    changed["b1_signature_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="b1_signature_sha256"):
        promote_fp32_candidate(
            candidate,
            weights_path=weights,
            teacher_evaluation=_cumulative_evaluation("teacher-cumulative", 0.95),
            student_evaluation=changed,
            output_path=tmp_path / "rejected.json",
        )
