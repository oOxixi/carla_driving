from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from car_control_D import DControlRuntime, ExecutionFeedbackTracker


ROOT = Path(__file__).resolve().parents[2]


def _example(name: str) -> dict:
    return json.loads((ROOT / "interfaces" / "examples" / f"{name}.json").read_text(encoding="utf-8"))


def test_execution_feedback_has_received_executing_and_one_terminal() -> None:
    tracker = ExecutionFeedbackTracker()
    received = tracker.received("cmd", "received", emitted_at_ns=100)
    executing = tracker.executing("cmd", "executing", t_action_apply_ns=200)
    terminal = tracker.finish("cmd", "SUCCEEDED", "done", "TARGET_REACHED", emitted_at_ns=300)
    duplicate = tracker.finish("cmd", "FAILED", "late failure", "SHOULD_NOT_REPLACE", emitted_at_ns=400)
    assert [received["status"], executing["status"], terminal["status"]] == ["RECEIVED", "EXECUTING", "SUCCEEDED"]
    assert terminal["latency_ms"] == pytest.approx(0.0001)
    assert duplicate == terminal
    assert tracker.unfinished_command_ids == ()


def test_d_runtime_is_unique_final_exit_and_records_safety_override() -> None:
    runtime = DControlRuntime()
    command = _example("control_command")
    perception = _example("perception_state")
    perception["risk_level"] = "EMERGENCY"
    perception["ttc_s"] = 1.0
    result = runtime.apply(
        command,
        perception,
        {"frame": 1, "speed_mps": 5.0},
        {"throttle": 0.4, "brake": 0.0, "steer": 0.1},
        now_ns=1_100_000_000,
    )
    assert result.final_control.throttle == 0.0
    assert result.final_control.brake == 1.0
    assert result.safety.safety_override
    assert result.feedback["status"] == "SAFETY_OVERRIDE"
    assert result.feedback["safety_event"]["raw_control"]["throttle"] == 0.4
    assert result.feedback["safety_event"]["final_control"]["brake"] == 1.0


def test_d_runtime_stale_perception_fails_closed() -> None:
    runtime = DControlRuntime()
    command = _example("control_command")
    perception = _example("perception_state")
    perception["stale"] = True
    perception["sync"]["within_tolerance"] = False
    result = runtime.apply(
        command, perception, {"speed_mps": 1.0},
        {"throttle": 0.2, "brake": 0.0, "steer": 0.0},
        now_ns=1_100_000_000,
    )
    assert result.safety.reason == "WATCHDOG_ALERT"
    assert result.final_control.brake == 1.0


def test_d_runtime_rejects_throttle_brake_conflict() -> None:
    runtime = DControlRuntime()
    command = _example("control_command")
    perception = _example("perception_state")
    result = runtime.apply(
        command, perception, {"speed_mps": 1.0},
        {"throttle": 0.5, "brake": 0.5, "steer": 0.0},
        now_ns=1_100_000_000,
    )
    assert result.safety.reason == "INVALID_CONTROL_OUTPUT_THROTTLE_BRAKE_CONFLICT"
    assert result.final_control.brake == 1.0


def test_d_runtime_clear_control_can_complete_with_terminal_feedback() -> None:
    runtime = DControlRuntime()
    command = _example("control_command")
    perception = _example("perception_state")
    result = runtime.apply(
        command, perception, {"speed_mps": 2.0},
        {"throttle": 0.2, "brake": 0.0, "steer": 0.0},
        now_ns=1_100_000_000,
    )
    assert not result.safety.safety_override
    assert result.feedback["status"] == "EXECUTING"
    terminal = runtime.complete(command["command_id"], succeeded=True, reason="TARGET_REACHED", now_ns=1_200_000_000)
    assert terminal["status"] == "SUCCEEDED"
    assert runtime.metrics()["unfinished_command_ids"] == []
