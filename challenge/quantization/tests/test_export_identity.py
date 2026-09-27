from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import torch

from challenge.export.export_onnx import _load_verified_weights
from challenge.student.model import StudentModelConfig, StudentPlannerV0


def test_formal_weight_loader_requires_gate_and_digest(tmp_path: Path) -> None:
    weights = tmp_path / "weights.pt"
    torch.save(StudentPlannerV0().state_dict(), weights)
    manifest = {
        "gate_status": "PENDING_A3_FP32_GATE",
        "model_id": StudentPlannerV0.model_id,
        "config_id": StudentModelConfig().config_id,
        "dataset_version": "unit",
        "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="A3_FP32_GATE_PASSED"):
        _load_verified_weights(
            StudentPlannerV0(), weights=weights, weights_manifest=manifest_path,
        )

    candidate = _load_verified_weights(
        StudentPlannerV0(), weights=weights, weights_manifest=manifest_path,
        allow_pending_candidate=True,
    )
    assert candidate["weights_status"] == "PENDING_A3_FP32_GATE"
    assert candidate["source_weights_sha256"] == manifest["weights_sha256"]

    manifest["gate_status"] = "A3_FP32_GATE_PASSED"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = _load_verified_weights(
        StudentPlannerV0(), weights=weights, weights_manifest=manifest_path,
    )
    assert result["weights_status"] == "A3_FP32_GATE_PASSED"
    assert result["source_weights_sha256"] == manifest["weights_sha256"]


def test_weight_and_manifest_arguments_are_atomic(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="provided together"):
        _load_verified_weights(
            StudentPlannerV0(), weights=tmp_path / "missing.pt", weights_manifest=None,
        )


def test_weight_loader_accepts_canonical_nested_handoff_manifest(tmp_path: Path) -> None:
    weights = tmp_path / "weights.pt"
    torch.save(StudentPlannerV0().state_dict(), weights)
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "gate_status": "PENDING_A3_FP32_GATE",
        "package_status": "PENDING_B2_INDEPENDENT_VALIDATION",
        "candidate_identity": {
            "git_sha": "1" * 40,
            "model_id": StudentPlannerV0.model_id,
            "config_id": StudentModelConfig().config_id,
            "dataset_version": "nested-unit",
            "weights_sha256": digest,
        },
    }
    manifest_path = tmp_path / "handoff_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = _load_verified_weights(
        StudentPlannerV0(),
        weights=weights,
        weights_manifest=manifest_path,
        allow_pending_candidate=True,
    )

    assert result["weights_status"] == "PENDING_A3_FP32_GATE"
    assert result["dataset_version"] == "nested-unit"
    assert result["source_weights_sha256"] == digest
    assert result["source_weights_git_sha"] == "1" * 40
    assert result["weights_identity_layout"] == "nested_candidate_identity"
