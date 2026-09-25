from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from challenge.benchmark.student_candidate import (
    StudentCandidateError,
    verify_student_candidate,
)
from challenge.distillation.candidate_handoff import (
    build_candidate_handoff,
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "run"
    source.mkdir()

    weights = b"candidate-weights"
    checkpoint = b"best-checkpoint"

    (
        source / "student_v0_fp32_candidate.pt"
    ).write_bytes(weights)

    (
        source / "student_fp32_best.pt"
    ).write_bytes(checkpoint)

    candidate = {
        "git_sha": "a" * 40,
        "source_worktree_dirty": False,
        "teacher_git_sha": "MULTI_PINNED_B1_D2_V1_1",
        "teacher_model_id": "Qwen/Qwen3.5-2B",
        "teacher_model_revision": "b" * 40,
        "teacher_artifact_fingerprint_sha256": "c" * 64,
        "teacher_identity_policy": "signed_d2_release_formal",
        "model_id": "student-v0-r3-fp32",
        "config_id": "student-v0-r3-structure-test",
        "weights_sha256": hashlib.sha256(
            weights
        ).hexdigest(),
        "source_checkpoint_sha256": hashlib.sha256(
            checkpoint
        ).hexdigest(),
        "dataset_version": "test-dataset-v1",
        "release_manifest_sha256": "d" * 64,
        "a3_view_manifest_sha256": "e" * 64,
        "gate_status": "PENDING_A3_FP32_GATE",
    }

    _write_json(
        source / "student_v0_fp32_candidate.json",
        candidate,
    )

    _write_json(
        source / "training_summary.json",
        {
            "git_sha": candidate["git_sha"],
            "teacher_git_sha": candidate["teacher_git_sha"],
            "teacher_model_id": candidate["teacher_model_id"],
            "teacher_model_revision": candidate[
                "teacher_model_revision"
            ],
            "teacher_artifact_fingerprint_sha256": candidate[
                "teacher_artifact_fingerprint_sha256"
            ],
            "teacher_identity_policy": candidate[
                "teacher_identity_policy"
            ],
            "model_id": candidate["model_id"],
            "model_config_id": candidate["config_id"],
            "dataset_version": candidate["dataset_version"],
            "release_manifest_sha256": candidate[
                "release_manifest_sha256"
            ],
            "a3_view_manifest_sha256": candidate[
                "a3_view_manifest_sha256"
            ],
            "candidate_weights_sha256": candidate[
                "weights_sha256"
            ],
            "best_checkpoint_sha256": candidate[
                "source_checkpoint_sha256"
            ],
            "candidate_gate_status": candidate[
                "gate_status"
            ],
            "smoke_only": False,
            "integration_smoke_only": False,
            "train_samples": 10,
            "validation_samples": 3,
            "hard_case_count": 2,
        },
    )

    _write_json(
        source / "dataset_preflight.json",
        {
            "valid": True,
            "error_count": 0,
            "expected_dataset_version": candidate[
                "dataset_version"
            ],
        },
    )

    _write_json(
        source / "hard_cases" / "summary.json",
        {"hard_case_count": 2},
    )

    (
        source / "training_report.md"
    ).write_text(
        "report",
        encoding="utf-8",
    )

    (
        source / "training.jsonl"
    ).write_text(
        "{}\n",
        encoding="utf-8",
    )

    return source


def _handoff(tmp_path: Path) -> Path:
    source = _source(tmp_path)
    output = tmp_path / "handoff"

    build_candidate_handoff(
        source,
        output,
        config_snapshot=b"config_id: formal\n",
        config_source={
            "git_sha": "a" * 40,
            "path": "config.yaml",
        },
    )

    return output


def test_verified_candidate_identity_is_exposed_to_b2(
    tmp_path: Path,
) -> None:
    package = _handoff(tmp_path)

    identity = verify_student_candidate(
        package
    )

    weights = (
        package / "student_v0_fp32_candidate.pt"
    ).read_bytes()

    assert identity["model_id"] == (
        "student-v0-r3-fp32"
    )
    assert identity["config_id"] == (
        "student-v0-r3-structure-test"
    )
    assert identity["dataset_version"] == (
        "test-dataset-v1"
    )
    assert identity["weights_sha256"] == (
        hashlib.sha256(weights).hexdigest()
    )
    assert identity["candidate_git_sha"] == (
        "a" * 40
    )
    assert len(
        identity["handoff_manifest_sha256"]
    ) == 64


def test_tampered_candidate_weights_fail_closed(
    tmp_path: Path,
) -> None:
    package = _handoff(tmp_path)

    (
        package / "student_v0_fp32_candidate.pt"
    ).write_bytes(
        b"tampered-candidate-weights"
    )

    with pytest.raises(
        StudentCandidateError,
        match="cannot verify A3 candidate handoff",
    ):
        verify_student_candidate(
            package
        )


def test_changed_handoff_status_fails_closed(
    tmp_path: Path,
) -> None:
    package = _handoff(tmp_path)

    manifest_path = (
        package / "handoff_manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    manifest["package_status"] = (
        "B2_VALIDATION_PASSED"
    )

    _write_json(
        manifest_path,
        manifest,
    )

    with pytest.raises(
        StudentCandidateError,
        match="cannot verify A3 candidate handoff",
    ):
        verify_student_candidate(
            package
        )