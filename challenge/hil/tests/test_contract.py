from __future__ import annotations

from typing import Any, Mapping

from ..contract import FAIL, PASS, WARN, check_runtime_contract
from ..identity import CandidateIdentity
from ..runtime_adapter import RuntimeCapabilities
from ..stages import StageTrace
from .fakes import FakeRuntime
from .test_replay_and_failures import _request


def _status(report, name):
    return next(item["status"] for item in report["checks"] if item["check"] == name)


def test_a_conforming_runtime_passes_every_check():
    report = check_runtime_contract(FakeRuntime(), [_request(), _request()])
    assert report["passed"] is True
    assert report["failed"] == []
    assert _status(report, "trace_marks_emitted") == PASS
    assert _status(report, "no_forbidden_outputs") == PASS


class _NoTraceRuntime(FakeRuntime):
    def infer(self, request, *, case_id, round_index, phase="measured"):
        trace = StageTrace(trace_id="t", case_id=case_id, round_index=round_index, phase=phase)
        trace.mark("input_arrival", timestamp_ns=1_000)
        trace.mark("plan_ready", timestamp_ns=2_000)
        trace.finish("READY")
        plan = {
            "schema_version": "2.0",
            "plan_type": "MANEUVER_SEQUENCE",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "confidence": 0.9,
            "reason_code": "OK",
            "steps": [{"behavior": "FOLLOW"}],
        }
        return plan, trace


def test_missing_stage_marks_are_reported_as_failures():
    report = check_runtime_contract(_NoTraceRuntime(), [_request()])
    assert report["passed"] is False
    assert _status(report, "model_only_latency_available") == FAIL
    assert _status(report, "trace_stage_names_known") == PASS


class _ForbiddenOutputRuntime(FakeRuntime):
    def infer(self, request, *, case_id, round_index, phase="measured"):
        plan, trace = FakeRuntime.infer(
            self, request, case_id=case_id, round_index=round_index, phase=phase
        )
        plan = {**plan, "throttle": 0.4}
        return plan, trace


def test_forbidden_control_outputs_fail_the_contract():
    report = check_runtime_contract(_ForbiddenOutputRuntime(), [_request()])
    assert report["passed"] is False
    assert _status(report, "no_forbidden_outputs") == FAIL


class _CrashingRuntime(FakeRuntime):
    def infer(self, request, *, case_id, round_index, phase="measured"):
        raise RuntimeError("boom")


def test_exception_escaping_the_adapter_fails_the_contract():
    report = check_runtime_contract(_CrashingRuntime(), [_request()])
    assert report["passed"] is False
    assert _status(report, "no_exception_escaped") == FAIL
    assert "boom" in next(
        item["detail"] for item in report["checks"] if item["check"] == "no_exception_escaped"
    )


class _UnknownStageRuntime(FakeRuntime):
    def infer(self, request, *, case_id, round_index, phase="measured"):
        plan, trace = FakeRuntime.infer(
            self, request, case_id=case_id, round_index=round_index, phase=phase
        )
        trace.timestamps_ns["bpu_warmup"] = trace.timestamps_ns["plan_ready"] + 10
        return plan, trace


def test_unknown_stage_names_fail_the_contract():
    report = check_runtime_contract(_UnknownStageRuntime(), [_request()])
    assert report["passed"] is False
    assert _status(report, "trace_stage_names_known") == FAIL


class _LateRuntime(FakeRuntime):
    def infer(self, request, *, case_id, round_index, phase="measured"):
        plan, trace = FakeRuntime.infer(
            self, request, case_id=case_id, round_index=round_index, phase=phase
        )
        trace.timestamps_ns["plan_ready"] = trace.timestamps_ns["plan_ready"] + 2_000_000_000
        return plan, trace


def test_latency_budget_is_enforced():
    report = check_runtime_contract(_LateRuntime(), [_request()], latency_budget_ms=100.0)
    assert report["passed"] is False
    assert _status(report, "latency_within_budget") == FAIL


def test_incomplete_identity_is_a_warning_not_a_failure():
    class _AnonRuntime(FakeRuntime):
        identity = CandidateIdentity()

    report = check_runtime_contract(_AnonRuntime(), [_request()])
    assert _status(report, "identity_declared") == WARN
    assert report["passed"] is True
    assert "identity_declared" in report["warned"]


def test_contract_rejects_an_empty_request_list():
    import pytest

    with pytest.raises(ValueError):
        check_runtime_contract(FakeRuntime(), [])
