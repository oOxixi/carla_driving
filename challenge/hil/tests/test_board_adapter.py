from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from ..runtime_adapter import AdapterError, BoardCliRuntime


_PLAN = {
    "schema_version": "2.0",
    "plan_type": "MANEUVER_SEQUENCE",
    "request_id": "req-1",
    "command_id": "cmd-1",
    "confidence": 0.5,
    "reason_code": "OK",
    "steps": [{"behavior": "FOLLOW", "target": {"target_id": None}, "on_failure": "SAFE_STOP"}],
}


def _runtime_command(tmp_path: Path, payload: dict) -> str:
    """A stand-in for A4's board runtime: reads a request, prints one plan."""
    data = tmp_path / "plan.json"
    data.write_text(json.dumps(payload), encoding="utf-8")
    script = tmp_path / "board_runtime.py"
    script.write_text(
        "import json, sys\n"
        f"payload = json.loads(open({json.dumps(str(data))}, encoding='utf-8').read())\n"
        "sys.stdin.read()\n"
        "print(json.dumps(payload))\n",
        encoding="utf-8",
    )
    return f'"{sys.executable}" "{script}"'


def _request() -> dict:
    return {"request_id": "req-1", "command_id": "cmd-1", "source_text": "keep lane"}


def test_contract_compliant_full_trace_is_merged_not_rejected(tmp_path: Path):
    """A runtime that emits T0..T7 must not collide with the host envelope."""
    full_trace = {
        "input_arrival": 1_000_000,
        "preprocess_end": 1_100_000,
        "packing_end": 1_200_000,
        "inference_start": 1_300_000,
        "inference_end": 1_500_000,
        "postprocess_end": 1_600_000,
        "adapter_end": 1_700_000,
        "plan_ready": 1_800_000,
    }
    payload = dict(_PLAN, trace=full_trace)
    command = _runtime_command(tmp_path, payload)
    runtime = BoardCliRuntime(command, log_path=tmp_path / "logs" / "board.jsonl")
    plan, trace = runtime.infer(_request(), case_id="c1", round_index=1)

    assert plan is not None
    assert trace.stage_source == "INSTRUMENTED"
    assert trace.missing_stages() == ()
    durations = trace.durations_ms()
    assert durations["planner_e2e_ms"] == pytest.approx(0.8)
    assert durations["model_only_ms"] == pytest.approx(0.2)
    assert runtime.emitted_trace is True
    assert runtime.log_lines == 1


def test_runtime_without_trace_falls_back_to_the_host_envelope(tmp_path: Path):
    command = _runtime_command(tmp_path, dict(_PLAN))
    runtime = BoardCliRuntime(command, log_path=tmp_path / "logs" / "board.jsonl")
    _, trace = runtime.infer(_request(), case_id="c1", round_index=1)

    assert trace.stage_source == "NOT_INSTRUMENTED"
    assert runtime.capabilities.stage_source == "NOT_INSTRUMENTED"
    assert trace.timestamps_ns.keys() >= {"input_arrival", "plan_ready"}


def test_out_of_order_runtime_trace_is_reported_as_an_adapter_error(tmp_path: Path):
    payload = dict(
        _PLAN,
        trace={"input_arrival": 5_000, "preprocess_end": 1_000_000, "plan_ready": 900},
    )
    command = _runtime_command(tmp_path, payload)
    runtime = BoardCliRuntime(command)
    with pytest.raises(AdapterError, match="monotonic"):
        runtime.infer(_request(), case_id="c1", round_index=1)


def test_unknown_trace_keys_are_ignored_not_fatal(tmp_path: Path):
    payload = dict(
        _PLAN,
        trace={"input_arrival": 1_000, "host_extra_stage": 2_000, "plan_ready": 3_000},
    )
    command = _runtime_command(tmp_path, payload)
    runtime = BoardCliRuntime(command)
    _, trace = runtime.infer(_request(), case_id="c1", round_index=1)
    assert runtime.ignored_stages == ("host_extra_stage",)
    assert "host_extra_stage" not in trace.timestamps_ns
