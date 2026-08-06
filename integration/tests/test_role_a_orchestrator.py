from __future__ import annotations

import copy
import json
from pathlib import Path
import threading
import time

import pytest

from runtime import LatencyCollector, OrchestratorConfig, PipelineOrchestrator, StageTrace


ROOT = Path(__file__).resolve().parents[2]


def _example(name: str) -> dict:
    return json.loads((ROOT / "interfaces" / "examples" / f"{name}.json").read_text(encoding="utf-8"))


def _clock(start: int = 1_000_000_000):
    state = {"now": start}
    return state, lambda: state["now"]


def test_fast_path_validates_without_qwen_and_clamps_speed_limit() -> None:
    state, clock = _clock()
    command = _example("driving_command")
    scene = _example("perception_state")
    with PipelineOrchestrator(clock_ns=clock) as runtime:
        result = runtime.submit_command(command, scene, now_ns=1_100_000_000)
    assert result.disposition == "FAST"
    assert result.control_command is not None
    assert result.control_command["path_type"] == "FAST"
    assert result.control_command["target"]["target_speed_mps"] == pytest.approx(5.5555555556)
    assert result.feedback["status"] == "RECEIVED"


def test_standard_command_still_works_when_qwen_is_unavailable() -> None:
    command = _example("driving_command")
    scene = _example("perception_state")
    with PipelineOrchestrator(infer=None) as runtime:
        assert runtime.submit_command(command, scene, now_ns=1_100_000_000).disposition == "FAST"
        complex_command = copy.deepcopy(command)
        complex_command.update({"command_id": "complex", "intent": "CHANGE_LANE"})
        complex_command["parameters"] = {"direction": "LEFT"}
        result = runtime.submit_command(complex_command, scene, now_ns=1_100_000_000)
    assert result.disposition == "REJECTED"
    assert result.reason_code == "QWEN_UNAVAILABLE"


def test_stale_perception_fail_closes_propulsion_to_stop() -> None:
    command = _example("driving_command")
    scene = _example("perception_state")
    scene["stale"] = True
    scene["sync"]["within_tolerance"] = False
    scene["sync"]["missing_modalities"] = ["LIDAR"]
    with PipelineOrchestrator() as runtime:
        result = runtime.submit_command(command, scene, now_ns=1_100_000_000)
    assert result.control_command["source"] == "SAFETY_SYSTEM"
    assert result.control_command["behavior"] == "STOP"
    assert result.feedback["status"] == "SAFETY_OVERRIDE"


def test_slow_path_is_async_and_validates_matching_target() -> None:
    command = _example("driving_command")
    command.update({"command_id": "complex", "intent": "FOLLOW", "source_text": "跟随正前方车辆"})
    command["parameters"] = {"target_id": "vehicle-0001"}
    scene = _example("perception_state")

    def infer(request):
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": "FOLLOW",
            "target_id": "vehicle-0001",
            "behavior": "FOLLOW",
            "parameters": {"target_speed_mps": 4.0, "time_gap_s": 2.0},
            "confidence": 0.95,
            "reason_code": "UNIQUE_TARGET",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": "test-backend",
        }

    with PipelineOrchestrator(infer=infer) as runtime:
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)
        assert queued.disposition == "SLOW_PENDING"
        assert queued.control_command is None
        deadline = time.monotonic() + 1.0
        ready = ()
        while time.monotonic() < deadline and not ready:
            ready = runtime.poll_slow(now_ns=1_150_000_000)
            time.sleep(0.001)
    assert len(ready) == 1
    assert ready[0].disposition == "SLOW_READY"
    assert ready[0].control_command["target"]["target_id"] == "vehicle-0001"


def test_completed_slow_result_uses_completion_time_not_late_poll_time() -> None:
    state, clock = _clock(1_100_000_000)
    command = _example("driving_command")
    command.update({"command_id": "completed", "intent": "FOLLOW"})
    command["parameters"] = {"target_id": "vehicle-0001"}
    scene = _example("perception_state")
    finished = threading.Event()

    def infer(request):
        state["now"] = 1_180_000_000
        finished.set()
        return {
            "schema_version": "1.0", "request_id": request["request_id"],
            "command_id": request["command_id"], "intent": "FOLLOW",
            "target_id": "vehicle-0001", "behavior": "FOLLOW",
            "parameters": {"target_speed_mps": 4.0, "time_gap_s": 2.0},
            "confidence": 0.95, "reason_code": "TEST",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False, "model_id": "test-backend",
        }

    with PipelineOrchestrator(infer=infer, clock_ns=clock) as runtime:
        runtime.submit_command(command, scene, now_ns=1_100_000_000)
        assert finished.wait(0.5)
        deadline = time.monotonic() + 0.5
        while runtime._result_queue.empty() and time.monotonic() < deadline:
            time.sleep(0.001)
        assert not runtime._result_queue.empty()
        state["now"] = 1_500_000_000
        result = runtime.poll_slow(now_ns=1_500_000_000)

    assert len(result) == 1
    assert result[0].disposition == "SLOW_READY"
    assert result[0].model_completed_ns == 1_180_000_000


def test_poll_slow_can_wait_for_same_frame_result() -> None:
    command = _example("driving_command")
    command.update({"command_id": "wait", "intent": "FOLLOW"})
    command["parameters"] = {"target_id": "vehicle-0001"}
    scene = _example("perception_state")

    def infer(request):
        time.sleep(0.01)
        return {
            "schema_version": "1.0", "request_id": request["request_id"],
            "command_id": request["command_id"], "intent": "FOLLOW",
            "target_id": "vehicle-0001", "behavior": "FOLLOW",
            "parameters": {"target_speed_mps": 4.0, "time_gap_s": 2.0},
            "confidence": 0.95, "reason_code": "TEST",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False, "model_id": "test-backend",
        }

    with PipelineOrchestrator(infer=infer) as runtime:
        runtime.submit_command(command, scene, now_ns=1_100_000_000)
        result = runtime.poll_slow(now_ns=1_100_000_000, wait_timeout_ms=100.0)

    assert len(result) == 1
    assert result[0].disposition == "SLOW_READY"


def test_qwen_timeout_does_not_block_caller() -> None:
    release = threading.Event()
    command = _example("driving_command")
    command.update({"command_id": "slow", "intent": "TURN", "source_text": "前方路口右转"})
    command["parameters"] = {"direction": "RIGHT"}
    scene = _example("perception_state")

    def infer(_request):
        release.wait(1.0)
        raise RuntimeError("offline")

    runtime = PipelineOrchestrator(
        infer=infer,
        config=OrchestratorConfig(model_timeout_ms=5.0),
    )
    try:
        started = time.perf_counter()
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)
        elapsed = time.perf_counter() - started
        assert queued.disposition == "SLOW_PENDING"
        assert elapsed < 0.05
        time.sleep(0.02)
        timeout = runtime.poll_slow(now_ns=1_120_000_000)
        assert any(item.reason_code == "QWEN_TIMEOUT" for item in timeout)
    finally:
        release.set()
        runtime.close()


def test_qwen_timeout_emits_only_one_terminal_when_backend_returns_late() -> None:
    release = threading.Event()
    started = threading.Event()
    command = _example("driving_command")
    command.update({"command_id": "late", "intent": "TURN", "source_text": "前方路口右转"})
    command["parameters"] = {"direction": "RIGHT"}
    scene = _example("perception_state")

    def infer(request):
        started.set()
        release.wait(1.0)
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": "TURN",
            "target_id": None,
            "behavior": "TURN_RIGHT",
            "parameters": {"target_speed_mps": 2.0},
            "confidence": 0.95,
            "reason_code": "TEST_LATE",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": "test-backend",
        }

    runtime = PipelineOrchestrator(
        infer=infer,
        config=OrchestratorConfig(model_timeout_ms=5.0),
    )
    try:
        runtime.submit_command(command, scene, now_ns=1_100_000_000)
        assert started.wait(0.5)
        time.sleep(0.02)
        terminal = runtime.poll_slow(now_ns=1_120_000_000)
        assert [item.reason_code for item in terminal] == ["QWEN_TIMEOUT"]
        release.set()
        deadline = time.monotonic() + 0.5
        late = ()
        while time.monotonic() < deadline and not late:
            late = runtime.poll_slow(now_ns=1_120_000_000)
            time.sleep(0.001)
        assert late == ()
    finally:
        release.set()
        runtime.close()


def test_evicted_qwen_request_gets_explicit_queue_overflow_terminal() -> None:
    release = threading.Event()
    started = threading.Event()
    scene = _example("perception_state")

    def infer(_request):
        started.set()
        release.wait(1.0)
        raise RuntimeError("released")

    runtime = PipelineOrchestrator(
        infer=infer,
        config=OrchestratorConfig(qwen_queue_size=1, model_timeout_ms=500.0),
    )
    try:
        commands = []
        for index in range(3):
            command = _example("driving_command")
            command.update({
                "command_id": f"slow-{index}",
                "intent": "TURN",
                "source_text": "前方路口右转",
            })
            command["parameters"] = {"direction": "RIGHT"}
            commands.append(command)
        runtime.submit_command(commands[0], scene, now_ns=1_100_000_000)
        assert started.wait(0.5)
        runtime.submit_command(commands[1], scene, now_ns=1_100_000_000)
        runtime.submit_command(commands[2], scene, now_ns=1_100_000_000)
        overflow = runtime.poll_slow(now_ns=1_110_000_000)
        assert len(overflow) == 1
        assert overflow[0].command_id == "slow-1"
        assert overflow[0].feedback["status"] == "REJECTED"
        assert overflow[0].reason_code == "QUEUE_OVERFLOW"
        snapshot = runtime.queue_snapshot()
        assert snapshot.qwen_overflow == 1
        assert snapshot.qwen_depth == 1
    finally:
        release.set()
        runtime.close()


def test_all_queues_are_bounded_and_report_overflow() -> None:
    scene = _example("perception_state")
    with PipelineOrchestrator(config=OrchestratorConfig(sensor_queue_size=1, log_queue_size=1)) as runtime:
        runtime.publish_perception(scene)
        assert runtime.publish_perception(scene) is False
        runtime.publish_log({"frame": 1})
        assert runtime.publish_log({"frame": 2}) is False
        snapshot = runtime.queue_snapshot()
        assert snapshot.sensor_depth == 1 and snapshot.sensor_overflow == 1
        assert snapshot.log_depth == 1 and snapshot.log_overflow == 1
        assert runtime.latest_perception()["frame_id"] == scene["frame_id"]
        assert runtime.drain_logs() == ({"frame": 2},)


def test_latency_trace_reports_required_percentiles(tmp_path: Path) -> None:
    collector = LatencyCollector()
    for index, duration_ms in enumerate((100, 120, 140, 160, 180)):
        trace = StageTrace(f"cmd-{index}", "FAST")
        trace.mark("audio_start", timestamp_ns=1_000_000_000)
        trace.mark("asr_end", timestamp_ns=1_010_000_000)
        trace.mark("nlu_end", timestamp_ns=1_020_000_000)
        trace.mark("planning_end", timestamp_ns=1_030_000_000)
        trace.mark("arbitration_end", timestamp_ns=1_031_000_000)
        trace.mark("action_apply", timestamp_ns=1_000_000_000 + duration_ms * 1_000_000)
        trace.finish("SUCCEEDED")
        collector.add(trace)
    report = collector.report()
    assert report["metrics_ms"]["end_to_end"] == {
        "count": 5, "mean": 140.0, "p95": 176.0, "p99": 179.2, "max": 180.0,
    }
    assert report["metrics_ms"]["control_and_safety"]["p95"] == 1.0
    written = collector.write(tmp_path / "latency.json")
    assert json.loads(written.read_text(encoding="utf-8"))["trace_count"] == 5


def test_latency_trace_rejects_out_of_order_marks() -> None:
    trace = StageTrace("cmd", "FAST")
    trace.mark("nlu_end", timestamp_ns=10)
    with pytest.raises(ValueError, match="out of order"):
        trace.mark("asr_end", timestamp_ns=11)
