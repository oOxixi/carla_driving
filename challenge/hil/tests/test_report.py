from __future__ import annotations

import json
from pathlib import Path

from ..identity import CandidateIdentity, identity_from_weight_manifest
from ..report import (
    REPORT_FILENAME_J6P,
    REPORT_FILENAME_J6P_BRINGUP,
    REPORT_FILENAME_J6P_UNVERIFIED,
    REPORT_FILENAME_X86,
    build_report,
    claim_scope,
    report_filename,
)


def test_report_filename_follows_the_verified_scope():
    assert report_filename({"scope": "J6P_ON_DEVICE"}) == REPORT_FILENAME_J6P
    assert report_filename("J6P_ON_DEVICE") == REPORT_FILENAME_J6P
    assert report_filename("J6P_BRINGUP") == REPORT_FILENAME_J6P_BRINGUP
    assert report_filename("J6P_CLAIM_UNVERIFIED") == REPORT_FILENAME_J6P_UNVERIFIED
    assert report_filename("X86_WORKSTATION") == REPORT_FILENAME_X86
    assert report_filename("X86_PRE_VALIDATED") == REPORT_FILENAME_X86
    assert report_filename("SOMETHING_ELSE") == REPORT_FILENAME_X86
    # A bare device-class string carries no evidence behind it, so it must not
    # produce the board deliverable name.
    assert report_filename("J6P_BOARD") == REPORT_FILENAME_X86


def test_report_lists_the_runtime_library_versions():
    report = build_report(
        run_id="run-libs",
        identity=CandidateIdentity(),
        capabilities={"full_chain": True, "model_only": True, "plan_validator": True, "stage_source": "INSTRUMENTED"},
        hardware_env={
            "device_class": "X86_WORKSTATION",
            "clock": {"source": "perf_counter_ns", "resolution_ns": 100.0},
            "runtime_libraries": {
                "torch": "2.6.0+cpu",
                "onnxruntime": "1.30.0",
                "numpy": "2.5.3",
            },
        },
        latency_report={"measured_ready_count": 0, "trace_count": 0, "outcome_counts": {}, "metrics_ms": {}, "rounds": {}},
        replay_summary=None,
        telemetry={},
        failure_summary=None,
        run_summary=None,
        blocked_on=[],
    )
    assert "2.6.0+cpu" in report
    assert "1.30.0" in report


def test_x86_scope_forbids_j6p_claims():
    scope = claim_scope(device_class="X86_WORKSTATION")
    assert scope["scope"] == "X86_PRE_VALIDATED"
    assert scope["evidence_level"] == "E1_STRUCTURE_PREVALIDATION"
    assert scope["j6p_status"] == "J6P_PENDING"
    assert any("J6P" in item for item in scope["forbidden_claims"])
    assert any("功耗" in item for item in scope["forbidden_claims"])
    assert "identity_complete" in scope["failed_checks"]


def test_declared_board_class_without_evidence_is_not_board_evidence():
    scope = claim_scope(
        device_class="J6P_BOARD",
        hardware_env={"device_class": "J6P_BOARD"},
    )
    assert scope["scope"] == "J6P_CLAIM_UNVERIFIED"
    assert scope["evidence_level"] == "UNVERIFIED_J6P_CLAIM"
    assert scope["j6p_status"] == "J6P_NOT_VERIFIABLE"
    assert not any("J6P 板端实测" in item for item in scope["allowed_claims"])
    assert any("J6P" in item for item in scope["forbidden_claims"])
    failed = set(scope["failed_checks"])
    assert {"artifact_digest_recorded", "board_runtime_log_recorded"} <= failed
    assert report_filename(scope) == REPORT_FILENAME_J6P_UNVERIFIED


def _gate_passed_identity(tmp_path: Path) -> CandidateIdentity:
    """A candidate whose digest was recomputed from disk against the manifest."""
    weights = tmp_path / "student_fp32.pt"
    weights.write_bytes(b"gate-passed-weights")
    manifest = tmp_path / "weights_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "git_sha": "b" * 40,
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


def _board_evidence(identity: CandidateIdentity, **overrides) -> dict:
    evidence: dict = {
        "device_class": "J6P_BOARD",
        "identity": identity,
        "artifact": {"path": "model.bin", "sha256": identity.model_sha256},
        "runtime": {
            "name": "board",
            "capabilities": {
                "full_chain": True,
                "model_only": False,
                "plan_validator": True,
                "stage_source": "INSTRUMENTED",
            },
        },
        "hardware_env": {
            "device_class": "J6P_BOARD",
            "host": {"hostname": "j6p-board"},
            "clock": {"resolution_ns": 1.0},
            "background_load_cpu_percent": 4.0,
        },
        "telemetry": {
            "power": {
                "measured": True,
                "sample_count": 60,
                "source": "onboard_ina",
                "probe_point": "board_12v_rail",
            },
            "utilization": {
                "bpu_measured": True,
                "sample_count": 60,
                "source": "board_tool",
            },
        },
        "board_runtime": {
            "adapter": "board",
            "command": "a4_runtime --trace",
            "trace_emitted": True,
            "log_path": "logs/board_runtime.jsonl",
            "log_lines": 12,
        },
        "rounds_measured": 3,
    }
    evidence.update(overrides)
    return evidence


def test_full_board_evidence_reaches_on_device_scope(tmp_path: Path):
    identity = _gate_passed_identity(tmp_path)
    scope = claim_scope(**_board_evidence(identity))
    assert scope["scope"] == "J6P_ON_DEVICE"
    assert scope["evidence_level"] == "E4_J6P_INDEPENDENT_MEASURED"
    assert scope["j6p_status"] == "J6P_MEASURED"
    assert scope["failed_checks"] == []
    assert any("功耗" in item for item in scope["allowed_claims"])
    assert report_filename(scope) == REPORT_FILENAME_J6P


def test_board_run_without_telemetry_stops_at_bringup(tmp_path: Path):
    identity = _gate_passed_identity(tmp_path)
    scope = claim_scope(**_board_evidence(identity, telemetry={}, rounds_measured=1))
    assert scope["scope"] == "J6P_BRINGUP"
    assert scope["evidence_level"] == "E3_J6P_BRINGUP"
    assert scope["j6p_status"] == "J6P_BRINGUP_ONLY"
    assert not any("J6P 板端实测" in item for item in scope["allowed_claims"])
    assert report_filename(scope) == REPORT_FILENAME_J6P_BRINGUP


def test_missing_board_log_downgrades_a_board_run(tmp_path: Path):
    identity = _gate_passed_identity(tmp_path)
    scope = claim_scope(
        **_board_evidence(
            identity,
            board_runtime={"adapter": "board", "command": "a4_runtime --trace"},
        )
    )
    assert scope["scope"] == "J6P_CLAIM_UNVERIFIED"
    assert "board_runtime_log_recorded" in scope["failed_checks"]


def test_artifact_digest_mismatch_blocks_the_board_claim(tmp_path: Path):
    identity = _gate_passed_identity(tmp_path)
    scope = claim_scope(
        **_board_evidence(identity, artifact={"path": "model.bin", "sha256": "0" * 64})
    )
    assert scope["scope"] == "J6P_CLAIM_UNVERIFIED"
    assert "artifact_matches_identity" in scope["failed_checks"]


def test_gated_x86_candidate_is_reported_as_candidate_prevalidation(tmp_path: Path):
    identity = _gate_passed_identity(tmp_path)
    scope = claim_scope(
        device_class="X86_WORKSTATION",
        identity=identity,
        artifact={"sha256": identity.model_sha256},
        runtime={
            "name": "inprocess-torch",
            "capabilities": {
                "full_chain": True,
                "model_only": True,
                "plan_validator": True,
                "stage_source": "INSTRUMENTED",
            },
        },
    )
    assert scope["scope"] == "X86_CANDIDATE_PREVALIDATED"
    assert scope["evidence_level"] == "E2_CANDIDATE_X86"
    assert scope["j6p_status"] == "J6P_PENDING"


def _env() -> dict:
    return {
        "device_class": "X86_WORKSTATION",
        "clock": {
            "source": "perf_counter_ns",
            "resolution_ns": 100.0,
            "platform_monotonic_resolution_ns": 15_625_000.0,
        },
    }


def test_report_states_incomplete_identity_and_missing_measurements():
    report = build_report(
        run_id="run-1",
        identity=CandidateIdentity(),
        capabilities={
            "full_chain": True,
            "model_only": True,
            "plan_validator": False,
            "stage_source": "PARTIAL",
            "notes": ["jsonschema missing"],
        },
        hardware_env=_env(),
        latency_report={
            "measured_ready_count": 1,
            "trace_count": 2,
            "outcome_counts": {"READY": 1, "REJECTED": 1},
            "metrics_ms": {
                "planner_e2e_ms": {
                    "count": 1,
                    "mean": 12.0,
                    "p50": 12.0,
                    "p95": 12.0,
                    "p99": 12.0,
                    "max": 12.0,
                }
            },
            "rounds": {
                "1": {
                    "count": 1,
                    "metrics_ms": {"planner_e2e_ms": {"count": 1, "p95": 12.0, "max": 12.0}},
                }
            },
        },
        replay_summary=None,
        telemetry={
            "power": {"measured": False, "source": "NOT_APPLICABLE"},
            "utilization": {"bpu_measured": False},
        },
        failure_summary=None,
        run_summary=None,
        blocked_on=["BLOCKED_ON_A3"],
        extra_notes=["clock note"],
    )
    assert "X86_PRE_VALIDATED" in report
    assert "E1_STRUCTURE_PREVALIDATION" in report
    assert "J6P_PENDING" in report
    assert "身份不完整" in report
    assert "NOT_MEASURED" in report
    assert "BLOCKED_ON_A3" in report
    assert "clock note" in report
    assert "异构算力利用率" in report
    assert "time.monotonic" in report


def test_report_shows_the_scope_checks_that_were_not_met(tmp_path: Path):
    identity = _gate_passed_identity(tmp_path)
    evidence = _board_evidence(identity, telemetry={}, rounds_measured=1)
    scope = claim_scope(**evidence)
    report = build_report(
        run_id="run-2",
        identity=identity,
        capabilities=evidence["runtime"]["capabilities"],
        hardware_env=evidence["hardware_env"],
        latency_report={"measured_ready_count": 0, "trace_count": 0, "outcome_counts": {}, "metrics_ms": {}, "rounds": {}},
        replay_summary={
            "case_count": 1,
            "teacher_comparison": "GATE_ELIGIBLE",
            "teacher_comparison_reason": "verified",
            "gate_failed_checks": [],
        },
        telemetry=evidence["telemetry"],
        failure_summary=None,
        run_summary=None,
        blocked_on=[],
        scope=scope,
    )
    assert "J6P_BRINGUP" in report
    assert "未满足的核验项" in report
    assert "power_probe_verified" in report
    assert "GATE_ELIGIBLE" in report
