from __future__ import annotations

from ..identity import CandidateIdentity
from ..report import (
    REPORT_FILENAME_J6P,
    REPORT_FILENAME_X86,
    build_report,
    claim_scope,
    report_filename,
)


def test_report_filename_follows_the_measured_environment():
    assert report_filename("J6P_BOARD") == REPORT_FILENAME_J6P
    assert report_filename("X86_WORKSTATION") == REPORT_FILENAME_X86
    assert report_filename("SOMETHING_ELSE") == REPORT_FILENAME_X86


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
    scope = claim_scope(
        device_class="X86_WORKSTATION", power_measured=False, bpu_measured=False
    )
    assert scope["scope"] == "X86_PRE_VALIDATED"
    assert scope["j6p_status"] == "J6P_PENDING"
    assert any("J6P" in item for item in scope["forbidden_claims"])
    assert any("功耗" in item for item in scope["forbidden_claims"])


def test_board_scope_only_allows_measured_metrics():
    scope = claim_scope(device_class="J6P_BOARD", power_measured=False, bpu_measured=False)
    assert scope["scope"] == "J6P_ON_DEVICE"
    assert not any("功耗" in item for item in scope["allowed_claims"])


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
    assert "J6P_PENDING" in report
    assert "身份不完整" in report
    assert "NOT_MEASURED" in report
    assert "BLOCKED_ON_A3" in report
    assert "clock note" in report
    assert "异构算力利用率" in report
    assert "time.monotonic" in report
