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
    return FrameTiming(
        base + 10,
        base + 20,
        base + 30,
        sensor_ready_ns=base,
        simulator_tick_start_ns=base - 20,
        simulator_tick_end_ns=base - 10,
        perception_start_ns=base - 5,
    )


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
        c_safety_state={"visual_valid": True, "lidar_valid": True, "fusion_mode": "RGB_LIDAR"},
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
    assert frame["c_safety_state"]["fusion_mode"] == "RGB_LIDAR"
    assert frame["latency"]["decision_ms"] == pytest.approx(0.00001)
    assert frame["latency"]["simulator_tick_ms"] == pytest.approx(0.00001)
    assert frame["latency"]["perception_acquire_ms"] == pytest.approx(0.000005)
    assert frame["latency"]["pipeline_active_ms"] == pytest.approx(0.00004)
    assert records[1]["latency"] == {
        "asr_ms": 0.0002, "intent_ms": 0.0002, "intent_to_submit_ms": 0.0005,
    }
    assert summary["completion"] is True
    assert summary["stop_error_m"] == 0.7
    assert summary["min_gap_m"] == 7.0
    assert summary["min_ttc_s"] == 2.5
    assert summary["safety_override_episodes"] == 1
    assert summary["score"]["scenario_id"] == "S04"
    assert summary["latency"]["decision_p95_ms"] == pytest.approx(0.00001)
    assert summary["latency"]["decision_p99_ms"] == pytest.approx(0.00001)
    assert summary["latency"]["sensor_to_control_p95_ms"] == pytest.approx(0.00003)
    assert summary["latency"]["sensor_to_control_p99_ms"] == pytest.approx(0.00003)
    assert summary["score_report"]["latency"]["asr_avg_ms"] == pytest.approx(0.0002)
    assert path.with_suffix(".summary.json").is_file()


def test_qwen_trajectory_records_official_end_to_end_boundary(tmp_path):
    path = tmp_path / "qwen-e2e.jsonl"
    recorder = ScenarioEvidenceRecorder(path)
    recorder.start_run(scenario_id="ACC_A01")
    recorder.record_qwen_trajectory(
        command_id="cmd-1", request_id="req-1",
        sensor_ready_ns=1_000_000_000,
        model_completed_ns=1_080_000_000,
        trajectory_ready_ns=1_095_000_000,
        breakdown={"queue_wait_ms": 2.0, "infer_callback_ms": 70.0},
    )
    summary = recorder.complete(completion=True)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    trajectory = next(row for row in rows if row["record_type"] == "qwen_trajectory")
    assert trajectory["latency"]["model_ms"] == 80.0
    assert trajectory["latency"]["sensor_to_trajectory_ms"] == 95.0
    assert trajectory["latency"]["breakdown"]["infer_callback_ms"] == 70.0
    assert summary["latency"]["sensor_to_trajectory_p95_ms"] == 95.0


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


def test_expected_lateral_offset_is_not_scored_as_serious_route_deviation(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "offset.jsonl")
    recorder.start_run(scenario_id="B02")
    for frame, deviation in ((1, 1.1), (2, 0.4), (3, 3.1)):
        recorder.record_frame(
            vehicle=_vehicle(frame, 2.0),
            scene=PerceptionFrame(frame, frame * 0.05, route_deviation_m=deviation),
            raw_control=ControlOutput(0.1, 0.0, 0.0),
            final_control=ControlOutput(0.1, 0.0, 0.0),
            safety_reason="NONE",
            safety_override=False,
            timing=_timing(frame * 100),
        )
    summary = recorder.complete(completion=True)
    assert summary["route_deviation_count"] == 1


def test_expected_route_deviation_remains_evidence_without_score_deduction(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "expected-deviation.jsonl")
    recorder.start_run(scenario_id="D04", expected_route_deviation=True)
    recorder.record_frame(
        vehicle=_vehicle(1, 0.0),
        scene=PerceptionFrame(1, 0.05, route_deviation_m=4.0),
        raw_control=ControlOutput(0.0, 0.0, 0.0),
        final_control=ControlOutput(0.0, 1.0, 0.0),
        safety_reason="SEVERE_ROUTE_DEVIATION",
        safety_override=True,
        timing=_timing(100),
    )
    summary = recorder.complete(completion=True)
    assert summary["route_deviation_count"] == 1
    assert summary["serious_route_deviation"] == 0
    assert summary["score"]["final_score"] == 25.0


def test_expected_contract_failure_downgrades_explicit_completion(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "strict.jsonl")
    recorder.start_run(scenario_id="B01")
    recorder.record_frame(
        vehicle=_vehicle(1, 2.0),
        scene=PerceptionFrame(1, 0.05, route_deviation_m=0.5),
        raw_control=ControlOutput(0.1, 0.0, 0.0),
        final_control=ControlOutput(0.1, 0.0, 0.0),
        safety_reason="NONE",
        safety_override=False,
        timing=_timing(100),
        lateral={"cross_track_error_m": 0.8, "steer": 0.1},
    )
    summary = recorder.complete(
        completion=True,
        expected={"max_cross_track_error_m": 0.5, "must_no_collision": True},
    )
    assert summary["status"] == "FAILED"
    assert summary["acceptance"]["failed_keys"] == ["max_cross_track_error_m"]
    assert summary["unfinished_task_count"] == 1


def test_command_order_accepts_applied_command_that_is_later_superseded(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "ordered.jsonl", clock_ns=lambda: 1_000)
    recorder.start_run(scenario_id="REG_011")
    for index, sim_time in enumerate((0.0, 7.0, 14.0)):
        command_id = f"scenario_cmd_{index:03d}"
        recorder.record_command(
            {"command_id": command_id, "intent": "SET_SPEED" if index < 2 else "STOP"},
            disposition="ACCEPTED_SCENARIO",
            submitted_sim_time_s=sim_time,
        )
        recorder.record_frame(
            vehicle=RuntimeVehicleState(index + 1, sim_time + 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, "1"),
            scene=PerceptionFrame(index + 1, sim_time + 0.05),
            raw_control=ControlOutput(0.0, 0.5, 0.0),
            final_control=ControlOutput(0.0, 0.5, 0.0),
            safety_reason="NONE",
            safety_override=False,
            timing=_timing((index + 1) * 100),
            command_id=command_id,
        )
    summary = recorder.complete(
        completion=True,
        expected={"must_execute_commands_in_order": True, "must_stop_after_last_command": True},
        acceptance_context={"expected_command_count": 3},
    )
    assert summary["acceptance"]["passed"] is True


def test_command_order_ignores_internal_qwen_commands(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "ordered-qwen.jsonl", clock_ns=lambda: 1_000)
    recorder.start_run(scenario_id="SUP_B03")
    for index, command_id in enumerate((
        "scenario_cmd_000",
        "qwen-step-scenario_cmd_000-step-1",
    ), start=1):
        recorder.record_command(
            {"command_id": command_id, "intent": "SET_SPEED"},
            disposition="SCENARIO_SLOW_PENDING" if index == 1 else "ACCEPTED_QWEN_PLAN",
            submitted_sim_time_s=(index - 1) * 0.1,
        )
        if index > 1:
            recorder.record_frame(
                vehicle=_vehicle(index, 1.0), scene=PerceptionFrame(index, index * 0.05),
                raw_control=ControlOutput(0.1, 0.0, 0.0),
                final_control=ControlOutput(0.1, 0.0, 0.0),
                safety_reason="NONE", safety_override=False, timing=_timing(index * 100),
                command_id=command_id,
            )
    recorder.record_feedback(ExecutionFeedback(
        "qwen-step-scenario_cmd_000-step-1", ExecutionStatus.FAILED, 0.1, "internal",
    ))
    recorder.record_feedback(ExecutionFeedback(
        "scenario_cmd_000", ExecutionStatus.SUCCEEDED, 0.1, "done",
    ))

    summary = recorder.complete(
        completion=True,
        expected={"must_execute_commands_in_order": True},
        acceptance_context={"expected_command_count": 1},
    )

    assert summary["acceptance"]["passed"] is True


def test_invalid_timing_and_non_finite_evidence_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="monotonic"):
        FrameTiming(20, 10, 30)
    recorder = ScenarioEvidenceRecorder(tmp_path / "invalid.jsonl")
    recorder.start_run(scenario_id="S01")
    with pytest.raises(ValueError, match="finite"):
        recorder.record_command({"command_id": "cmd", "confidence": float("nan")}, disposition="REJECTED")
    recorder.fail("invalid command")


def test_qwen_request_and_result_are_recorded_without_credentials(tmp_path):
    path = tmp_path / "qwen.jsonl"
    recorder = ScenarioEvidenceRecorder(path, clock_ns=lambda: 1_000)
    recorder.start_run(
        scenario_id="QWEN_REMOTE",
        config={"qwen_model": "qwen2.5-vl"},
    )
    recorder.record_qwen_event(
        request_id="qwen-1",
        status="PENDING",
        context={"voice_command": "停车", "rgb_ref": "qwen-1.jpg"},
    )
    recorder.record_qwen_event(
        request_id="qwen-1",
        status="READY",
        high_level_command={"action": "STOP", "decision_source": "SAFETY_RULE"},
        runtime_command={"command_id": "qwen_async_00000001", "intent": "STOP"},
        trace={"latency_ms": 1911.74, "raw_output": '{"action":"STOP"}'},
    )
    summary = recorder.complete(
        completion=True,
        expected={"expected_reason_contains": ["safety"]},
    )

    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    qwen_records = [item for item in records if item["record_type"] == "qwen_decision"]
    assert [item["status"] for item in qwen_records] == ["PENDING", "READY"]
    assert qwen_records[1]["trace"]["latency_ms"] == 1911.74
    assert summary["acceptance"]["passed"] is True
    assert "api_key" not in path.read_text(encoding="utf-8").lower()


def test_feedback_safety_event_is_included_in_acceptance_reasons(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "safety-feedback.jsonl")
    recorder.start_run(scenario_id="ACC_C03")
    recorder.record_feedback({
        "schema_version": "1.0",
        "command_id": "cmd-red",
        "status": "RECEIVED",
        "action_summary": "slow request queued behind deterministic safety stop",
        "emitted_at_ns": 1,
        "t_action_apply_ns": None,
        "latency_ms": None,
        "safety_event": {
            "reason_code": "TRAFFIC_LIGHT_STOP",
            "raw_control": {"throttle": 0.0, "brake": 1.0, "steer": 0.0},
            "final_control": {"throttle": 0.0, "brake": 1.0, "steer": 0.0},
        },
        "terminal_reason": None,
    })
    recorder.record_frame(
        vehicle=_vehicle(1, 0.0),
        scene=PerceptionFrame(
            1, 0.05, traffic_light="RED", distance_to_stop_line_m=17.0,
        ),
        raw_control=ControlOutput(0.0, 0.55, 0.0),
        final_control=ControlOutput(0.0, 0.55, 0.0),
        safety_reason="NONE",
        safety_override=False,
        timing=_timing(100),
    )

    summary = recorder.complete(
        completion=True,
        expected={
            "expected_reason_contains": ["stop"],
            "expected_safety_override": True,
            "safety_priority_over_command": True,
            "must_generate_event": True,
        },
    )

    assert "TRAFFIC_LIGHT_STOP" in summary["safety_reasons"]
    assert summary["acceptance"]["passed"] is True


@pytest.mark.parametrize(
    ("end_y", "end_yaw", "expected_shift", "expected_turn"),
    [(-3.5, -45.0, 3.5, "LEFT"), (3.5, 45.0, -3.5, "RIGHT")],
)
def test_carla_left_handed_pose_metrics_use_scenario_left_positive_convention(
    tmp_path, end_y, end_yaw, expected_shift, expected_turn,
):
    recorder = ScenarioEvidenceRecorder(tmp_path / f"pose-{expected_turn}.jsonl")
    recorder.start_run(scenario_id=f"POSE_{expected_turn}")
    poses = ((0.0, 0.0, 0.0), (20.0, end_y, end_yaw))
    for frame, (x_m, y_m, yaw_deg) in enumerate(poses, start=1):
        vehicle = RuntimeVehicleState(frame, frame * 0.05, 2.0, x_m, y_m, 0.0, yaw_deg, "1")
        recorder.record_frame(
            vehicle=vehicle,
            scene=PerceptionFrame(frame, frame * 0.05, lane_offset_m=end_y / 2.0),
            raw_control=ControlOutput(0.1, 0.0, 0.0),
            final_control=ControlOutput(0.1, 0.0, 0.0),
            safety_reason="NONE",
            safety_override=False,
            timing=_timing(frame * 100),
            lateral={"cross_track_error_m": 0.0, "steer": 0.0},
        )
    summary = recorder.complete(
        expected={
            "final_lateral_shift_m": expected_shift,
            "turn_direction": expected_turn,
            "max_lane_center_offset_m": 2.0,
        },
    )
    metrics = {item["key"]: item for item in summary["acceptance"]["checks"]}
    assert metrics["final_lateral_shift_m"]["status"] == "PASS"
    assert metrics["turn_direction"]["status"] == "PASS"
    assert metrics["max_lane_center_offset_m"]["actual"] == pytest.approx(abs(end_y) / 2.0)


def test_commanded_full_brake_is_emergency_evidence_without_safety_override(tmp_path) -> None:
    recorder = ScenarioEvidenceRecorder(tmp_path / "commanded-emergency.jsonl")
    recorder.start_run(scenario_id="commanded-emergency")
    recorder.record_frame(
        vehicle=RuntimeVehicleState(1, 0.05, 2.0, 0.0, 0.0, 0.0, 0.0, "1"),
        scene=PerceptionFrame(1, 0.05),
        raw_control=ControlOutput(0.0, 1.0, 0.0),
        final_control=ControlOutput(0.0, 1.0, 0.0),
        safety_reason="NONE",
        safety_override=False,
        timing=_timing(100),
        lateral={"cross_track_error_m": 0.0, "steer": 0.0},
    )

    summary = recorder.complete(completion=True, expected={"must_emergency_brake": True})

    assert summary["acceptance"]["passed"] is True
