from __future__ import annotations

import json

import pytest

from car_control_A import ControlOutput, ExecutionFeedback, ExecutionStatus, LongitudinalOutput, RiskMetrics, RuntimeVehicleState
from integration.contracts import PerceptionFrame
from integration.scenario_evidence import FrameTiming, ScenarioEvidenceRecorder


def _vehicle(frame: int, speed_mps: float) -> RuntimeVehicleState:
    return RuntimeVehicleState(frame, frame * 0.05, speed_mps, 0.0, 0.0, 0.0, 0.0, "1")


def _longitudinal(ttc_s: float | None = None) -> LongitudinalOutput:
    return LongitudinalOutput(
        ControlOutput(0.0, 0.4, 0.0), -1.0, 0.0, "BRAKE", "STOP_CONSTRAINT",
        RiskMetrics(ttc_s, 5.0, False),
    )


def _timing(base: int) -> FrameTiming:
    return FrameTiming(base + 10, base + 20, base + 30, sensor_ready_ns=base)


def test_unified_evidence_is_auditable_and_scored(tmp_path):
    path = tmp_path / "red-stop.jsonl"
    recorder = ScenarioEvidenceRecorder(path, clock_ns=lambda: 1_000)
    run_id = recorder.start_run(scenario_id="S04", config={"map": "Town05"}, run_id="run-1")
    assert run_id == "run-1"
    recorder.record_command({
        "command_id": "cmd-1", "intent": "STOP", "t_audio_start_ns": 100,
        "t_asr_end_ns": 300, "t_intent_end_ns": 500,
    }, disposition="ACCEPTED", received_ns=1_000)
    scene = PerceptionFrame(1, 0.05, lead_distance_m=7.0, lead_speed_mps=0.0,
                            traffic_light="RED", distance_to_stop_line_m=0.7)
    recorder.record_frame(
        vehicle=_vehicle(1, 0.1), scene=scene,
        raw_control=ControlOutput(0.0, 0.4, 0.1), final_control=ControlOutput(0.0, 1.0, 0.0),
        safety_reason="STOP_LINE_GUARD", safety_override=True, timing=_timing(1_000),
        command_id="cmd-1", fsm_state="APPROACH_STOP", longitudinal=_longitudinal(2.5),
    )
    recorder.record_feedback(ExecutionFeedback("cmd-1", ExecutionStatus.SUCCEEDED, 0.05, "stopped"))
    summary = recorder.complete()

    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [record["record_type"] for record in records] == [
        "run_start", "command", "frame", "feedback", "run_complete",
    ]
    assert [record["sequence"] for record in records] == list(range(5))
    frame = records[2]
    assert frame["raw_control"]["brake"] == 0.4
    assert frame["final_control"]["brake"] == 1.0
    assert frame["safety"] == {"override": True, "reason": "STOP_LINE_GUARD"}
    assert frame["latency"]["decision_ms"] == pytest.approx(0.00001)
    assert records[1]["latency"] == {
        "asr_ms": 0.0002, "intent_ms": 0.0002, "intent_to_submit_ms": 0.0005,
    }
    assert summary["completion"] is True
    assert summary["stop_error_m"] == 0.7
    assert summary["min_gap_m"] == 7.0
    assert summary["min_ttc_s"] == 2.5
    assert summary["safety_override_episodes"] == 1
    assert summary["score"]["scenario_id"] == "S04"
    assert summary["score_report"]["latency"]["asr_avg_ms"] == pytest.approx(0.0002)
    assert path.with_suffix(".summary.json").is_file()


def test_collision_and_override_are_counted_as_episodes(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "follow.jsonl")
    recorder.start_run(scenario_id="S06")
    for frame, collision, override in ((1, True, True), (2, True, True), (3, False, False), (4, True, True)):
        scene = PerceptionFrame(frame, frame * 0.05, lead_distance_m=10.0 - frame,
                                collision=collision)
        recorder.record_frame(
            vehicle=_vehicle(frame, 2.0), scene=scene,
            raw_control=ControlOutput(0.1, 0.0, 0.0), final_control=ControlOutput(0.0, 0.8, 0.0),
            safety_reason="TEST", safety_override=override, timing=_timing(frame * 100),
        )
    summary = recorder.complete(completion=False)
    assert summary["collision_count"] == 2
    assert summary["safety_override_frames"] == 3
    assert summary["safety_override_episodes"] == 2
    assert summary["unfinished_task_count"] == 1
    assert summary["score"]["final_score"] == 0.0


def test_failure_always_emits_terminal_record_and_summary(tmp_path):
    path = tmp_path / "failed.jsonl"
    recorder = ScenarioEvidenceRecorder(path)
    recorder.start_run(scenario_id="S01")
    summary = recorder.fail(ValueError("sensor timeout"))
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["record_type"] == "run_failed"
    assert records[-1]["error"] == {"type": "ValueError", "message": "sensor timeout"}
    assert summary["status"] == "FAILED"
    with pytest.raises(RuntimeError):
        recorder.record_feedback(ExecutionFeedback("cmd", ExecutionStatus.FAILED, 0.0, "late"))


def test_invalid_timing_and_non_finite_evidence_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="monotonic"):
        FrameTiming(20, 10, 30)
    recorder = ScenarioEvidenceRecorder(tmp_path / "invalid.jsonl")
    recorder.start_run(scenario_id="S01")
    with pytest.raises(ValueError, match="finite"):
        recorder.record_command({"command_id": "cmd", "confidence": float("nan")}, disposition="REJECTED")
    recorder.fail("invalid command")
