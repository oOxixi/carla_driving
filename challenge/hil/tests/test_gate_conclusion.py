from __future__ import annotations

import json
from pathlib import Path

from ..gate import gate_verified, replay_conclusion
from ..identity import CandidateIdentity, identity_from_weight_manifest
from ..replay import run_replay
from ..tests.fakes import FakeRuntime
from .test_replay_and_failures import _case


def _verified_identity(tmp_path: Path) -> CandidateIdentity:
    weights = tmp_path / "student_fp32.pt"
    weights.write_bytes(b"gate-passed-weights")
    manifest = tmp_path / "weights_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "git_sha": "c" * 40,
                "model_id": "student-v0-r3-fp32",
                "weights_sha256": "",
                "dataset_version": "teacher_distill_v2",
                "config_id": "cfg-candidate",
                "gate_status": "A3_FP32_GATE_PASSED",
            }
        ),
        encoding="utf-8",
    )
    return identity_from_weight_manifest(weights, manifest)


class _GatedRuntime(FakeRuntime):
    def __init__(self, identity: CandidateIdentity) -> None:
        super().__init__()
        self.identity = identity


def test_identity_without_verification_record_stays_diagnostic():
    """Fail closed: a self-declared gate status is not a verified gate status."""
    declared = CandidateIdentity(
        git_sha="d" * 40,
        model_id="student-v0-r3-fp32",
        model_sha256="e" * 64,
        dataset_version="teacher_distill_v2",
        config_id="cfg-candidate",
        gate_status="A3_FP32_GATE_PASSED",
    )
    assert declared.gate_status == "A3_FP32_GATE_PASSED"
    assert gate_verified(declared) is False
    conclusion = replay_conclusion(declared)
    assert conclusion["teacher_comparison"] == "DIAGNOSTIC_ONLY"
    assert conclusion["diagnostic_only"] is True
    assert "weights_manifest_verified" in conclusion["gate_failed_checks"]
    assert "digest_matches_identity" in conclusion["gate_failed_checks"]


def test_verified_candidate_is_promoted_by_evidence_not_by_hand(tmp_path: Path):
    identity = _verified_identity(tmp_path)
    assert gate_verified(identity) is True
    conclusion = replay_conclusion(identity)
    assert conclusion["teacher_comparison"] == "GATE_ELIGIBLE"
    assert conclusion["diagnostic_only"] is False
    assert conclusion["gate_failed_checks"] == []


def test_run_replay_writes_the_evidence_derived_conclusion(tmp_path: Path):
    identity = _verified_identity(tmp_path)
    result = run_replay(_GatedRuntime(identity), [_case()], run_id="r", round_index=1)
    assert result.rows[0]["diagnostic_only"] is False
    assert result.summary["teacher_comparison"] == "GATE_ELIGIBLE"
    assert result.summary["gate_verified"] is True
    assert result.summary["gate_failed_checks"] == []


def test_run_replay_stays_diagnostic_for_a_random_structure():
    result = run_replay(FakeRuntime(), [_case()], run_id="r", round_index=1)
    assert result.rows[0]["diagnostic_only"] is True
    assert result.summary["teacher_comparison"] == "DIAGNOSTIC_ONLY"
    assert result.summary["gate_verified"] is False
    assert "weights_manifest_verified" in result.summary["gate_failed_checks"]
