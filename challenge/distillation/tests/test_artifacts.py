import hashlib
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.artifacts import (  # noqa: E402
    export_candidate_weights,
    promote_fp32_candidate,
)
from challenge.distillation.dummy_student import DummyStudent  # noqa: E402


def _evaluation(evaluation_id: str, value: float, *, split: str = "validation") -> dict:
    return {
        "evaluation_id": evaluation_id,
        "split": split,
        "dataset_version": "b1-v1",
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


def test_candidate_is_not_promoted_without_independent_gate(tmp_path: Path) -> None:
    identity = {
        "git_sha": "a" * 40,
        "teacher_git_sha": "b" * 40,
        "teacher_model_id": "teacher",
        "teacher_model_revision": "teacher-revision",
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
        "teacher_git_sha": "b" * 40,
        "teacher_model_id": "teacher",
        "teacher_model_revision": "teacher-revision",
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
    }
    student_evaluation = _evaluation("student-val", 0.94)
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
            student_evaluation=_evaluation("student-val", 0.94),
            output_path=tmp_path / "rejected.json",
        )
