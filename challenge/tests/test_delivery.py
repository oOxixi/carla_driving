"""Regression checks for the public A1 delivery workflows."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import torch

from challenge.export.validate_artifacts import validate_artifacts
from challenge.planner.student_backend import StudentBackend
from challenge.student.model import StudentModelConfig, StudentPlannerV0

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def candidate(tmp_path_factory):
    root = tmp_path_factory.mktemp("candidate")
    weights = root / "weights.pt"
    torch.save(StudentPlannerV0().state_dict(), weights)
    manifest = {
        "git_sha": "a" * 40,
        "model_id": StudentPlannerV0.model_id,
        "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
        "dataset_version": "train-v1",
        "config_id": StudentModelConfig().config_id,
        "gate_status": "A3_FP32_GATE_PASSED",
    }
    return weights, manifest


@pytest.mark.parametrize("field,value", [
    ("config_id", "WRONG_CONFIG"), ("git_sha", ""),
    ("git_sha", "deadbeef"), ("dataset_version", "  "),
    ("dataset_version", None), ("gate_status", "PENDING"),
])
def test_backend_rejects_invalid_candidate_identity(candidate, tmp_path, field, value):
    weights, valid = candidate
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({**valid, field: value}), encoding="utf-8")
    with pytest.raises(ValueError):
        StudentBackend(weights=weights, weights_manifest=manifest)


def test_backend_accepts_matching_candidate(candidate, tmp_path):
    weights, valid = candidate
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(valid), encoding="utf-8")
    assert StudentBackend(weights=weights, weights_manifest=manifest).health()[0]


def test_documented_export_refreshes_all_reports(tmp_path):
    shutil.copytree(ROOT / "interfaces", tmp_path / "interfaces")
    destination = tmp_path / "challenge"
    destination.mkdir()
    for name in ("model_structure.json", "flops_report.json"):
        shutil.copy2(ROOT / "challenge" / name, destination / name)
    for sha in ("a" * 40, "b" * 40):
        subprocess.run([
            sys.executable, "-m", "challenge.export.export_onnx",
            "--output", str(destination / "student_v0_fp32.onnx"),
            "--source-git-sha", sha,
        ], cwd=ROOT, check=True, capture_output=True, text=True)
        assert validate_artifacts(tmp_path)["status"] == "PASS"
        for name in ("model_structure.json", "flops_report.json"):
            assert json.loads((destination / name).read_text())["source_git_sha"] == sha
