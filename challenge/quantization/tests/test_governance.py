from __future__ import annotations

import json
from pathlib import Path

from challenge.quantization.governance import audit_a3_candidate, load_b1_closeout


REPO = Path(__file__).resolve().parents[3]


def test_b1_closeout_is_hash_verified_and_role_separated() -> None:
    closeout = load_b1_closeout(REPO)
    identity = closeout.identity

    assert identity["status"] == "VERIFIED_B1_DATA_CLOSEOUT"
    assert identity["dataset_version"] == "b1_governed_dataset_closeout_v1"
    assert identity["governed_counts"]["train"] == 6037
    assert identity["governed_counts"]["dev"] == 1158
    assert identity["calibration"] == {
        "dataset_version": "b1_calibration_v1",
        "sample_count": 300,
        "group_count": 300,
        "jsonl_sha256": "e7520afc683b4545ca0981c549d0aebef50a90962a0d95378d89c1ca4bfbe8cc",
        "manifest_sha256": "659c5e8210ee95cf835be685da1deb55bc1990874ba3e120955d6bdf392d8059",
    }
    assert identity["independent_validation"]["sample_count"] == 240
    assert identity["independent_validation"]["a2_usage"].startswith("FORBIDDEN")
    assert identity["governed_release_manifest_sha256"] == (
        "07d3a82502005646d8f29d0c493fa8a5b0270a5194fd5c802a04b4870ba7d37d"
    )


def test_current_a3_candidate_is_blocked_against_latest_b1_closeout() -> None:
    release = Path("challenge/distillation/releases/a3_final_fp32_candidate_v1")
    report = audit_a3_candidate(
        REPO,
        weights=release / "student_v0_fp32_candidate.pt",
        weights_manifest=release / "handoff_manifest.json",
    )

    assert report["status"] == "BLOCKED"
    assert report["formal_eligible"] is False
    assert report["candidate_use"] == "DIAGNOSTIC_ONLY"
    assert report["requirements"]["expected_train_samples"] == 6037
    assert report["requirements"]["expected_dev_samples"] == 1158
    assert report["candidate"]["optimizer_train_samples"] == 5826
    assert report["candidate"]["optimizer_dev_samples"] == 1104
    assert report["candidate"]["governed_source_train_samples"] is None
    assert report["candidate"]["governed_source_dev_samples"] is None
    assert report["verified_weights"]["sha256"] == (
        "eaee4402197fb3fed53ed82bc2fbaceef62e5ed2d4cde86e8aa1a55dc6d46515"
    )
    assert "A3_GOVERNED_TRAIN_COUNT_MISMATCH:None!=6037" in report["blockers"]
    assert "A3_GOVERNED_DEV_COUNT_MISMATCH:None!=1158" in report["blockers"]
    assert "A3_MISSING_B1_GOVERNED_RELEASE_BINDING" in report["blockers"]
    assert "A3_FP32_GATE_NOT_PASSED:PENDING_A3_FP32_GATE" in report["blockers"]


def test_gate_string_alone_cannot_promote_a_stale_candidate(tmp_path: Path) -> None:
    source = REPO / "challenge/distillation/releases/a3_final_fp32_candidate_v1/handoff_manifest.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    manifest["gate_status"] = "A3_FP32_GATE_PASSED"
    spoofed = tmp_path / "handoff_manifest.json"
    spoofed.write_text(json.dumps(manifest), encoding="utf-8")

    report = audit_a3_candidate(REPO, weights_manifest=spoofed)

    assert report["status"] == "BLOCKED"
    assert report["formal_eligible"] is False
    assert "A3_GOVERNED_TRAIN_COUNT_MISMATCH:None!=6037" in report["blockers"]
    assert "A3_GOVERNED_DEV_COUNT_MISMATCH:None!=1158" in report["blockers"]
    assert "A3_MISSING_B1_GOVERNED_RELEASE_BINDING" in report["blockers"]
    assert not any(item.startswith("A3_FP32_GATE_NOT_PASSED") for item in report["blockers"])
