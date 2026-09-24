import hashlib
import json
from pathlib import Path

import pytest

from challenge.distillation.candidate_handoff import (
    build_candidate_handoff,
    verify_candidate_handoff,
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "run"
    source.mkdir()
    weights = b"candidate-weights"
    checkpoint = b"best-checkpoint"
    (source / "student_v0_fp32_candidate.pt").write_bytes(weights)
    (source / "student_fp32_best.pt").write_bytes(checkpoint)
    candidate = {
        "git_sha": "a" * 40,
        "source_worktree_dirty": False,
        "teacher_git_sha": "MULTI_PINNED_B1_D2_V1_1",
        "teacher_model_id": "Qwen/Qwen3.5-2B",
        "teacher_model_revision": "b" * 40,
        "teacher_artifact_fingerprint_sha256": "c" * 64,
        "teacher_identity_policy": "signed_d2_release_formal",
        "model_id": "student-v0-r3-fp32",
        "config_id": "student-v0-r3-structure-20260911",
        "weights_sha256": hashlib.sha256(weights).hexdigest(),
        "source_checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest(),
        "dataset_version": "b1_d2_v1_1_a3_strict_positive_v1",
        "release_manifest_sha256": "d" * 64,
        "a3_view_manifest_sha256": "e" * 64,
        "gate_status": "PENDING_A3_FP32_GATE",
    }
    _write_json(source / "student_v0_fp32_candidate.json", candidate)
    _write_json(source / "training_summary.json", {
        "git_sha": candidate["git_sha"],
        "teacher_git_sha": candidate["teacher_git_sha"],
        "teacher_model_id": candidate["teacher_model_id"],
        "teacher_model_revision": candidate["teacher_model_revision"],
        "teacher_artifact_fingerprint_sha256": candidate["teacher_artifact_fingerprint_sha256"],
        "teacher_identity_policy": candidate["teacher_identity_policy"],
        "model_id": candidate["model_id"],
        "model_config_id": candidate["config_id"],
        "dataset_version": candidate["dataset_version"],
        "release_manifest_sha256": candidate["release_manifest_sha256"],
        "a3_view_manifest_sha256": candidate["a3_view_manifest_sha256"],
        "candidate_weights_sha256": candidate["weights_sha256"],
        "best_checkpoint_sha256": candidate["source_checkpoint_sha256"],
        "candidate_gate_status": candidate["gate_status"],
        "smoke_only": False,
        "integration_smoke_only": False,
        "train_samples": 10,
        "validation_samples": 3,
        "hard_case_count": 2,
    })
    _write_json(source / "dataset_preflight.json", {
        "valid": True,
        "error_count": 0,
        "expected_dataset_version": candidate["dataset_version"],
    })
    _write_json(source / "hard_cases" / "summary.json", {"hard_case_count": 2})
    (source / "training_report.md").write_text("report", encoding="utf-8")
    (source / "training.jsonl").write_text("{}\n", encoding="utf-8")
    return source


def test_build_candidate_handoff_is_hash_bound_and_pending(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "handoff"
    manifest = build_candidate_handoff(
        source,
        output,
        config_snapshot=b"config_id: formal\n",
        config_source={"git_sha": "a" * 40, "path": "config.yaml"},
    )

    assert manifest["package_status"] == "PENDING_B2_INDEPENDENT_VALIDATION"
    assert manifest["gate_status"] == "PENDING_A3_FP32_GATE"
    assert manifest["training_evidence"]["development_validation_only"] is True
    assert "README.md" in manifest["files"]
    assert (output / "student_v0_fp32_candidate.pt").read_bytes() == b"candidate-weights"
    written = json.loads((output / "handoff_manifest.json").read_text())
    assert written["gate_status"] == "PENDING_A3_FP32_GATE"

    verification = verify_candidate_handoff(output)
    assert verification["valid"] is True
    assert verification["files_checked"] == 9
    assert verification["weights_sha256"] == manifest["candidate_identity"]["weights_sha256"]


@pytest.mark.parametrize("mutation", ("payload", "extra", "identity", "status"))
def test_verify_candidate_handoff_rejects_changed_or_unsigned_content(
    tmp_path: Path,
    mutation: str,
) -> None:
    source = _source(tmp_path)
    output = tmp_path / "handoff"
    build_candidate_handoff(
        source,
        output,
        config_snapshot=b"config_id: formal\n",
        config_source={"git_sha": "a" * 40, "path": "config.yaml"},
    )
    if mutation == "payload":
        (output / "training_config.yaml").write_text("changed", encoding="utf-8")
    elif mutation == "extra":
        (output / "unsigned.txt").write_text("extra", encoding="utf-8")
    elif mutation == "identity":
        candidate_path = output / "student_v0_fp32_candidate.json"
        candidate = json.loads(candidate_path.read_text())
        candidate["model_id"] = "different-student"
        _write_json(candidate_path, candidate)
        handoff_path = output / "handoff_manifest.json"
        handoff = json.loads(handoff_path.read_text())
        content = candidate_path.read_bytes()
        handoff["files"]["student_v0_fp32_candidate.json"] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
        _write_json(handoff_path, handoff)
    else:
        handoff_path = output / "handoff_manifest.json"
        handoff = json.loads(handoff_path.read_text())
        handoff["gate_status"] = "A3_FP32_GATE_PASSED"
        _write_json(handoff_path, handoff)

    with pytest.raises(ValueError):
        verify_candidate_handoff(output)


def test_build_cumulative_candidate_handoff_preserves_signed_evidence(tmp_path: Path) -> None:
    source = _source(tmp_path)
    candidate_path = source / "student_v0_fp32_candidate.json"
    summary_path = source / "training_summary.json"
    candidate = json.loads(candidate_path.read_text())
    summary = json.loads(summary_path.read_text())
    updates = {
        "teacher_git_sha": "MULTI_PINNED_B1_D2_V1_1_PLUS_D3_WAVE1",
        "teacher_identity_policy": "signed_cumulative_release_formal",
        "d2_release_manifest_sha256": "1" * 64,
        "b1_signature_sha256": "2" * 64,
        "source_evidence_sha256": "3" * 64,
    }
    candidate.update(updates)
    summary.update(updates)
    _write_json(candidate_path, candidate)
    _write_json(summary_path, summary)
    manifest = build_candidate_handoff(
        source,
        tmp_path / "cumulative-handoff",
        config_snapshot=b"config_id: cumulative\n",
        config_source={"git_sha": "a" * 40, "path": "cumulative.yaml"},
    )
    assert manifest["candidate_identity"]["b1_signature_sha256"] == "2" * 64
    assert manifest["candidate_identity"]["source_evidence_sha256"] == "3" * 64
    verification = verify_candidate_handoff(tmp_path / "cumulative-handoff")
    assert verification["valid"] is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("weights", "weight SHA256"),
        ("checkpoint", "checkpoint SHA256"),
        ("smoke", "Smoke"),
        ("dirty", "clean worktree"),
        ("preflight", "preflight"),
        ("hard_cases", "hard-case"),
    ),
)
def test_build_candidate_handoff_rejects_inconsistent_evidence(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    source = _source(tmp_path)
    if mutation == "weights":
        (source / "student_v0_fp32_candidate.pt").write_bytes(b"changed")
    elif mutation == "checkpoint":
        (source / "student_fp32_best.pt").write_bytes(b"changed")
    elif mutation == "smoke":
        summary = json.loads((source / "training_summary.json").read_text())
        summary["integration_smoke_only"] = True
        _write_json(source / "training_summary.json", summary)
    elif mutation == "dirty":
        candidate = json.loads((source / "student_v0_fp32_candidate.json").read_text())
        candidate["source_worktree_dirty"] = True
        _write_json(source / "student_v0_fp32_candidate.json", candidate)
    elif mutation == "preflight":
        preflight = json.loads((source / "dataset_preflight.json").read_text())
        preflight["valid"] = False
        preflight["error_count"] = 1
        _write_json(source / "dataset_preflight.json", preflight)
    else:
        _write_json(source / "hard_cases" / "summary.json", {"hard_case_count": 99})

    with pytest.raises(ValueError, match=message):
        build_candidate_handoff(
            source,
            tmp_path / "handoff",
            config_snapshot=b"config",
            config_source={"git_sha": "a" * 40, "path": "config.yaml"},
        )


def test_build_candidate_handoff_never_overwrites_existing_output(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "handoff"
    output.mkdir()
    with pytest.raises(FileExistsError):
        build_candidate_handoff(
            source,
            output,
            config_snapshot=b"config",
            config_source={"git_sha": "a" * 40, "path": "config.yaml"},
        )
