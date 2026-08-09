from __future__ import annotations

import pytest

from integration.scenario_execution import CommandTimeline, ScheduledCommand
from integration.scenario_extensions import (
    IMPLEMENTED_RUNTIME_REQUIREMENTS,
    ScenarioExtensionRuntime,
    missing_runtime_requirements,
)


def test_all_declared_runtime_requirements_have_an_owner():
    extensions = {
        "runtime_support": {
            "requirements": sorted(IMPLEMENTED_RUNTIME_REQUIREMENTS),
        }
    }
    assert missing_runtime_requirements(extensions) == ()


def test_event_command_waits_for_time_and_trigger():
    timeline = CommandTimeline((ScheduledCommand(
        5.0,
        {"command_id": "c1", "intent": "STOP"},
        "P1",
        {"type": "route_progress_greater_than_m", "value": 10.0},
    ),))
    assert timeline.due(4.9, {"route_progress_m": 20.0}) == ()
    assert timeline.due(5.0, {"route_progress_m": 9.0}) == ()
    assert timeline.due(5.1, {"route_progress_m": 10.0})[0]["command_id"] == "c1"


def test_fault_window_activates_and_recovers_with_evidence():
    runtime = ScenarioExtensionRuntime({
        "runtime_support": {"requirements": ["fault_injection"]},
        "faults": [{
            "fault_id": "rgb", "type": "sensor_blackout",
            "trigger": {"type": "time", "time_s": 2.0}, "duration_s": 1.0,
            "sensor": "front_rgb",
        }],
    })
    common = dict(
        route_progress_m=0.0, ego_speed_mps=0.0,
        ego_standstill_duration_s=0.0, actor_distances_m={},
        traffic_light_state="UNKNOWN", distance_to_stop_line_m=None,
        lane_id="1",
    )
    assert runtime.update_frame(elapsed_s=1.9, **common).active_faults == ()
    assert runtime.update_frame(elapsed_s=2.0, **common).newly_active_fault_ids == ("rgb",)
    assert runtime.update_frame(elapsed_s=3.0, **common).newly_recovered_fault_ids == ("rgb",)
    assert runtime.evidence()["fault_recovered_ids"] == ["rgb"]


def test_qwen_faults_are_separated_from_sensor_faults():
    runtime = ScenarioExtensionRuntime({
        "runtime_support": {"requirements": ["qwen_timeout_injection", "fault_injection"]},
        "faults": [
            {"fault_id": "q", "type": "qwen_response_delay", "delay_ms": 5000},
            {"fault_id": "rgb", "type": "sensor_blackout", "sensor": "front_rgb"},
        ],
    })
    assert [item["fault_id"] for item in runtime.qwen_faults] == ["q"]


def test_qwen_plan_collects_schema_v2_target_id() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_qwen_plan({
        "steps": [{"behavior": "FOLLOW", "target": {"target_id": "lead-target"}}],
    })
    assert runtime.evidence()["qwen_target_actor_ids"] == ["lead-target"]


def test_speed_overshoot_is_measured_from_submitted_target() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_command_submitted({
        "command_id": "speed", "parameters": {"speed": 20, "unit": "km/h"},
    }, qwen=True)
    runtime.update_frame(
        elapsed_s=1.0, route_progress_m=1.0, ego_speed_mps=5.8,
        ego_standstill_duration_s=0.0, actor_distances_m={},
        traffic_light_state="UNKNOWN", distance_to_stop_line_m=None, lane_id="1",
    )
    result = runtime.evaluate({"max_speed_overshoot_kph": 2.0}, expected_command_count=1)
    assert result["passed"] is True
    assert abs(result["checks"][0]["actual"] - 0.88) < 1e-9


def test_allowed_outcomes_recognizes_numeric_speed_limit_clipping() -> None:
    runtime = ScenarioExtensionRuntime({
        "speed_policy": {"scenario_limit_kph": 20},
    })
    runtime.note_command_submitted({
        "command_id": "speed", "intent": "SET_SPEED",
        "parameters": {"speed": 120, "unit": "km/h"},
    }, qwen=True)
    runtime.note_qwen_plan({
        "steps": [{"behavior": "SET_SPEED", "target_speed_kph": 20}],
    })

    result = runtime.evaluate(
        {"allowed_outcomes": ["REJECT", "CLIP_TO_LIMIT", "STOP", "HOLD"]},
        expected_command_count=1,
    )

    assert result["passed"] is True
    assert result["checks"][0]["actual"] == ["CLIP_TO_LIMIT"]


def test_allowed_outcomes_rejects_set_speed_above_scenario_limit() -> None:
    runtime = ScenarioExtensionRuntime({
        "speed_policy": {"scenario_limit_kph": 20},
    })
    runtime.note_command_submitted({
        "command_id": "speed", "intent": "SET_SPEED",
        "parameters": {"speed": 120, "unit": "km/h"},
    }, qwen=True)
    runtime.note_qwen_plan({
        "steps": [{"behavior": "SET_SPEED", "target_speed_kph": 30}],
    })

    result = runtime.evaluate(
        {"allowed_outcomes": ["REJECT", "CLIP_TO_LIMIT", "STOP", "HOLD"]},
        expected_command_count=1,
    )

    assert result["passed"] is False
    assert result["checks"][0]["actual"] == ["SET_SPEED"]


def test_timeout_is_accepted_as_a_discarded_stale_rebind_result() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_qwen_resolution(
        disposition="REJECTED", reason_code="QWEN_TIMEOUT", applied=False,
    )

    result = runtime.evaluate(
        {"rebind_requires_fresh_perception": True}, expected_command_count=1,
    )

    assert result["passed"] is True


def test_qwen_safety_stop_guard_is_scoped_to_transient_fault_window() -> None:
    runtime = ScenarioExtensionRuntime({
        "faults": [
            {
                "fault_id": "rgb", "type": "sensor_blackout",
                "sensor": "front_rgb", "trigger": {"type": "time", "time_s": 0},
                "duration_s": 1,
            },
            {
                "fault_id": "lidar", "type": "sensor_blackout",
                "sensor": "lidar", "trigger": {"type": "time", "time_s": 0},
                "duration_s": 1,
            },
        ],
    })
    frame = dict(
        route_progress_m=0.0, ego_speed_mps=3.0,
        ego_standstill_duration_s=0.0, actor_distances_m={},
        traffic_light_state="UNKNOWN", distance_to_stop_line_m=None, lane_id="1",
    )
    runtime.update_frame(elapsed_s=0.0, **frame)
    runtime.note_qwen_resolution(
        disposition="SLOW_READY", reason_code="KEEP_LANE", applied=True,
    )
    runtime.note_control_observation(
        elapsed_s=0.1, speed_mps=3.0, route_progress_m=0.0, brake=1.0,
        safety_override=True, safety_reason="SCENARIO_PERCEPTION_INSUFFICIENT",
        route_deviation_m=0.0,
    )
    runtime.update_frame(elapsed_s=1.0, **frame)
    runtime.note_control_observation(
        elapsed_s=1.0, speed_mps=2.0, route_progress_m=1.0, brake=0.0,
        safety_override=False, safety_reason="NONE", route_deviation_m=0.0,
    )

    result = runtime.evaluate(
        {"qwen_must_not_override_safety_stop": True}, expected_command_count=1,
    )

    assert result["passed"] is True


def test_route_deviation_contract_allows_verified_recovery() -> None:
    runtime = ScenarioExtensionRuntime({
        "faults": [{
            "fault_id": "steer", "type": "steer_bias",
            "trigger": {"type": "time", "time_s": 0}, "duration_s": 1,
        }],
    })
    frame = dict(
        route_progress_m=0.0, ego_speed_mps=3.0,
        ego_standstill_duration_s=0.0, actor_distances_m={},
        traffic_light_state="UNKNOWN", distance_to_stop_line_m=None, lane_id="1",
    )
    runtime.update_frame(elapsed_s=0.0, route_deviation_m=1.2, **frame)
    runtime.note_control_observation(
        elapsed_s=0.0, speed_mps=3.0, route_progress_m=0.0, brake=0.6,
        safety_override=True, safety_reason="ROUTE_DEVIATION_RECOVERY_STOP",
        route_deviation_m=1.2,
    )
    runtime.update_frame(elapsed_s=1.0, route_deviation_m=0.1, **frame)
    runtime.note_control_observation(
        elapsed_s=1.0, speed_mps=3.0, route_progress_m=1.0, brake=0.0,
        safety_override=False, safety_reason="NONE", route_deviation_m=0.1,
    )

    result = runtime.evaluate(
        {
            "must_stop_if_recovery_fails": True,
            "must_not_continue_route_deviation": True,
        },
        expected_command_count=1,
    )

    assert result["passed"] is True


def test_oracle_checks_observed_behavior_and_target_binding() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_qwen_plan({
        "steps": [{"behavior": "FOLLOW", "target": {"target_id": "lead-target"}}],
    })

    result = runtime.evaluate(
        {},
        expected_command_count=1,
        oracle={
            "expected_behaviors": ["FOLLOW", "SLOW_DOWN", "STOP"],
            "expected_target_actor_id": "lead-target",
        },
    )

    assert result["passed"] is True
    assert [(item["key"], item["status"]) for item in result["checks"]] == [
        ("oracle_expected_behaviors", "PASS"),
        ("oracle_expected_target_actor_id", "PASS"),
    ]


def test_oracle_fails_unexpected_qwen_behavior() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_qwen_plan({"steps": [{"behavior": "YIELD"}]})

    result = runtime.evaluate(
        {}, expected_command_count=1, oracle={"expected_behaviors": ["STOP"]},
    )

    assert result["passed"] is False
    assert result["failed_keys"] == ["oracle_expected_behaviors"]


def test_multi_command_oracle_requires_each_declared_behavior() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_qwen_plan({"steps": [{"behavior": "STOP"}]})

    result = runtime.evaluate(
        {}, expected_command_count=2,
        oracle={"expected_behaviors": ["SET_SPEED", "STOP"]},
    )

    assert result["passed"] is False
    assert result["failed_keys"] == ["oracle_expected_behaviors"]


def _frame(runtime: ScenarioExtensionRuntime, *, elapsed_s: float, progress_m: float,
           speed_mps: float, lateral_offset_m: float = 0.0,
           distance_to_stop_line_m: float | None = None) -> None:
    runtime.update_frame(
        elapsed_s=elapsed_s,
        route_progress_m=progress_m,
        ego_speed_mps=speed_mps,
        ego_standstill_duration_s=0.0,
        actor_distances_m={},
        traffic_light_state="UNKNOWN",
        distance_to_stop_line_m=distance_to_stop_line_m,
        lane_id="1",
        lateral_offset_m=lateral_offset_m,
    )


def test_observed_geometry_metrics_replace_fail_closed_placeholders() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_target_lane_occupancy(0)
    _frame(runtime, elapsed_s=0.0, progress_m=0.0, speed_mps=0.0)
    runtime.note_command_submitted({"command_id": "go", "intent": "KEEP_LANE"}, qwen=True)
    _frame(runtime, elapsed_s=5.0, progress_m=10.0, speed_mps=0.0)
    runtime.note_command_submitted({"command_id": "stop", "intent": "STOP"}, qwen=True)
    runtime.note_command_submitted({"command_id": "restart", "intent": "KEEP_LANE"}, qwen=True)
    _frame(runtime, elapsed_s=8.0, progress_m=16.0, speed_mps=2.0, lateral_offset_m=0.3)

    result = runtime.evaluate(
        {
            "target_lane_occupied_count": 0,
            "restart_displacement_m": 5.0,
            "final_lateral_offset_abs_max_m": 0.5,
        },
        expected_command_count=3,
    )

    assert result["passed"] is True
    assert {item["key"]: item["actual"] for item in result["checks"]} == {
        "target_lane_occupied_count": 0,
        "restart_displacement_m": 6.0,
        "final_lateral_offset_abs_max_m": 0.3,
    }


def test_blocked_lane_requires_observed_target_lane_occupancy() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_target_lane_occupancy(0)

    failed = runtime.evaluate(
        {"target_lane_occupied_min_count": 1}, expected_command_count=1,
    )

    assert failed["passed"] is False
    assert failed["checks"][0] == {
        "key": "target_lane_occupied_min_count",
        "status": "FAIL",
        "actual": 0,
        "required": 1,
    }

    runtime.note_target_lane_occupancy(1)
    passed = runtime.evaluate(
        {"target_lane_occupied_min_count": 1}, expected_command_count=1,
    )
    assert passed["passed"] is True


def test_lane_change_rejection_requires_explicit_safety_reason() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_qwen_resolution(
        disposition="SLOW_READY",
        reason_code="QWEN_VLLM_CHOICE_G_CHANGE_LANE_LEFT:STEP-1",
        applied=True,
    )

    false_positive = runtime.evaluate(
        {"lane_change_rejection_reason_required": True},
        expected_command_count=1,
    )
    assert false_positive["passed"] is False

    rejected = runtime.evaluate(
        {"lane_change_rejection_reason_required": True},
        expected_command_count=1,
        safety_reasons=("NO_SAFE_ADJACENT_LANE",),
    )
    assert rejected["passed"] is True


def test_actor_event_records_real_lead_brake_trigger_distance() -> None:
    runtime = ScenarioExtensionRuntime({})
    actor = {
        "actor_id": "lead",
        "behavior": {
            "initial_speed_mps": 4.0,
            "events": [{
                "phase_id": "P4_LEAD_BRAKE",
                "trigger": {"type": "ego_distance_less_than_m", "value": 12.0},
                "action": {"type": "set_speed", "target_speed_mps": 0.3},
            }],
        },
    }
    state = runtime.actor_state(
        actor,
        elapsed_s=2.0,
        trigger_context={"actor_distances_m": {"lead": 11.8}},
    )
    result = runtime.evaluate(
        {"lead_brake_trigger_distance_m": 12.0}, expected_command_count=1,
    )

    assert state["event_index"] == 1
    assert result["passed"] is True
    assert result["checks"][0]["actual"] == 11.8
    assert runtime.evidence()["completed_phase_ids"] == ["P4_LEAD_BRAKE"]
    assert runtime.evidence()["scenario_event_count"] == 1


def test_actor_despawn_event_marks_traffic_inactive() -> None:
    runtime = ScenarioExtensionRuntime({})
    actor = {
        "actor_id": "lead",
        "behavior": {
            "initial_speed_mps": 6.0,
            "events": [{
                "trigger": {"type": "route_progress_greater_than_m", "value": 150.0},
                "action": {"type": "despawn"},
            }],
        },
    }

    before = runtime.actor_state(
        actor, elapsed_s=20.0, trigger_context={"route_progress_m": 149.0},
    )
    after = runtime.actor_state(
        actor, elapsed_s=21.0, trigger_context={"route_progress_m": 150.0},
    )

    assert before["active"] is True
    assert after["active"] is False
    assert after["target_speed_mps"] == 0.0


def test_runtime_event_count_includes_fault_start_and_recovery() -> None:
    runtime = ScenarioExtensionRuntime({
        "faults": [{
            "fault_id": "steer_bias",
            "type": "steer_bias",
            "trigger": {"type": "time", "time_s": 1.0},
            "duration_s": 0.5,
            "value": 0.3,
        }],
    })
    common = {
        "route_progress_m": 0.0,
        "ego_speed_mps": 1.0,
        "ego_standstill_duration_s": 0.0,
        "actor_distances_m": {},
        "traffic_light_state": "UNKNOWN",
        "distance_to_stop_line_m": None,
        "lane_id": "1",
    }
    runtime.update_frame(elapsed_s=1.0, **common)
    runtime.update_frame(elapsed_s=1.5, **common)

    evidence = runtime.evidence()
    assert evidence["scenario_event_count"] == 0
    assert evidence["runtime_event_count"] == 2


def test_yellow_to_red_contract_requires_approach_and_never_crosses_stop_line() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.update_frame(
        elapsed_s=0.0, route_progress_m=0.0, ego_speed_mps=0.0,
        ego_standstill_duration_s=0.0, actor_distances_m={},
        traffic_light_state="YELLOW", distance_to_stop_line_m=17.5, lane_id="1",
    )
    runtime.update_frame(
        elapsed_s=2.0, route_progress_m=3.0, ego_speed_mps=2.0,
        ego_standstill_duration_s=0.0, actor_distances_m={},
        traffic_light_state="YELLOW", distance_to_stop_line_m=14.5, lane_id="1",
    )
    runtime.update_frame(
        elapsed_s=3.0, route_progress_m=5.0, ego_speed_mps=1.5,
        ego_standstill_duration_s=0.0, actor_distances_m={},
        traffic_light_state="RED", distance_to_stop_line_m=12.5, lane_id="1",
    )
    runtime.update_frame(
        elapsed_s=6.0, route_progress_m=15.0, ego_speed_mps=0.0,
        ego_standstill_duration_s=1.0, actor_distances_m={},
        traffic_light_state="RED", distance_to_stop_line_m=2.5, lane_id="1",
    )

    result = runtime.evaluate(
        {
            "pre_red_max_speed_min_mps": 0.5,
            "minimum_red_stop_line_clearance_m": 0.0,
            "must_stop_on_red_before_stop_line": True,
        },
        expected_command_count=1,
    )

    assert result["passed"] is True
    actual = {item["key"]: item["actual"] for item in result["checks"]}
    assert actual == {
        "pre_red_max_speed_min_mps": 2.0,
        "minimum_red_stop_line_clearance_m": 2.5,
        "must_stop_on_red_before_stop_line": True,
    }


def test_yellow_to_red_contract_rejects_crossing_then_stopping() -> None:
    runtime = ScenarioExtensionRuntime({})
    for elapsed_s, speed_mps, light, clearance_m in (
        (0.0, 0.0, "YELLOW", 17.5),
        (2.0, 2.0, "YELLOW", 14.5),
        (3.0, 1.5, "RED", 12.5),
        (6.0, 0.0, "RED", -0.2),
    ):
        runtime.update_frame(
            elapsed_s=elapsed_s, route_progress_m=0.0, ego_speed_mps=speed_mps,
            ego_standstill_duration_s=0.0, actor_distances_m={},
            traffic_light_state=light, distance_to_stop_line_m=clearance_m, lane_id="1",
        )

    result = runtime.evaluate(
        {
            "pre_red_max_speed_min_mps": 0.5,
            "minimum_red_stop_line_clearance_m": 0.0,
            "must_stop_on_red_before_stop_line": True,
        },
        expected_command_count=1,
    )

    assert result["passed"] is False
    assert result["failed_keys"] == [
        "minimum_red_stop_line_clearance_m",
        "must_stop_on_red_before_stop_line",
    ]


def test_fault_and_speed_deadlines_use_observed_control_frames() -> None:
    runtime = ScenarioExtensionRuntime({
        "faults": [{
            "fault_id": "rgb",
            "type": "sensor_blackout",
            "trigger": {"type": "time", "time_s": 2.0},
            "duration_s": 1.0,
        }],
    })
    _frame(runtime, elapsed_s=1.0, progress_m=0.0, speed_mps=4.0)
    runtime.note_command_submitted({"command_id": "slow", "intent": "SLOW_DOWN"}, qwen=True)
    _frame(runtime, elapsed_s=2.0, progress_m=4.0, speed_mps=4.0)
    runtime.note_control_observation(
        elapsed_s=2.2, speed_mps=3.7, route_progress_m=4.5,
        brake=0.7, safety_override=True, safety_reason="SCENARIO_PERCEPTION_INSUFFICIENT",
        route_deviation_m=0.0,
    )

    result = runtime.evaluate(
        {"max_fault_response_s": 0.5, "speed_drop_deadline_s": 1.5},
        expected_command_count=1,
    )

    assert result["passed"] is True
    actual = {item["key"]: item["actual"] for item in result["checks"]}
    assert actual["max_fault_response_s"] == pytest.approx(0.2)
    assert actual["speed_drop_deadline_s"] == pytest.approx(1.2)


def test_fault_deadline_ignores_sub_microsecond_float_drift_only() -> None:
    def evaluate(response_s: float) -> bool:
        runtime = ScenarioExtensionRuntime({
            "faults": [{
                "fault_id": "steer",
                "type": "steer_bias",
                "trigger": {"type": "time", "time_s": 0.0},
                "duration_s": 2.0,
            }],
        })
        _frame(runtime, elapsed_s=0.0, progress_m=0.0, speed_mps=4.0)
        runtime.note_control_observation(
            elapsed_s=response_s,
            speed_mps=3.0,
            route_progress_m=3.0,
            brake=1.0,
            safety_override=True,
            safety_reason="ROUTE_DEVIATION_RECOVERY_STOP",
            route_deviation_m=1.4,
        )
        return runtime.evaluate(
            {"max_fault_response_s": 1.0}, expected_command_count=0,
        )["passed"]

    assert evaluate(1.00000001) is True
    assert evaluate(1.0001) is False


def test_phase_and_vehicle_advance_counts_use_observed_events() -> None:
    runtime = ScenarioExtensionRuntime({
        "phase_plan": ["P1", "P2", "P3"],
    })
    runtime.note_command_submitted({"command_id": "c1", "phase_id": "P1"}, qwen=True)
    runtime.note_terminal("c1", "SUCCEEDED")
    runtime.note_phase_completed("P2")
    runtime.note_phase_completed("P3")
    runtime.note_qwen_resolution(
        disposition="REJECTED", reason_code="QWEN_INVALID_RESULT", applied=False,
    )

    result = runtime.evaluate(
        {
            "expected_phase_count": 3,
            "all_phases_must_complete": True,
            "vehicle_advance_command_count": 0,
            "qwen_invalid_result_count": 1,
        },
        expected_command_count=1,
    )

    assert result["passed"] is True


def test_pedestrian_trigger_actor_is_trigger_evidence_not_qwen_target() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_actor_trigger("occluding_vehicle")
    result = runtime.evaluate(
        {"pedestrian_trigger_actor_id": "occluding_vehicle"},
        expected_command_count=1,
    )
    assert result["passed"] is True


def test_stop_not_detour_contract_accepts_qwen_slow_then_safety_stop() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_qwen_plan({"steps": [{"behavior": "SLOW_DOWN"}]})
    runtime.note_control_observation(
        elapsed_s=8.7,
        speed_mps=0.0,
        route_progress_m=24.0,
        brake=1.0,
        safety_override=True,
        safety_reason="EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE",
        route_deviation_m=0.0,
    )

    result = runtime.evaluate(
        {"first_version_requires_stop_not_detour": True},
        expected_command_count=1,
    )

    assert result["passed"] is True


def test_current_plan_index_tracks_the_applied_command_not_submission_count() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_command_submitted({"command_id": "delayed", "intent": "SET_SPEED"}, qwen=True)
    runtime.note_command_submitted({"command_id": "stop", "intent": "STOP"}, qwen=True)
    runtime.note_qwen_resolution(
        disposition="REJECTED", reason_code="QWEN_STALE", applied=False,
        command_id="delayed",
    )
    runtime.note_qwen_resolution(
        disposition="SLOW_READY", reason_code="QWEN_READY", applied=True,
        command_id="stop",
    )

    result = runtime.evaluate(
        {"qwen_stale_result_applied_count": 0, "current_plan_command_index": 1},
        expected_command_count=2,
    )

    assert result["passed"] is True


def test_degraded_and_post_recovery_contracts_require_observed_events() -> None:
    runtime = ScenarioExtensionRuntime({
        "faults": [{
            "fault_id": "rgb",
            "type": "sensor_blackout",
            "sensor": "front_rgb",
            "trigger": {"type": "time", "time_s": 1.0},
            "duration_s": 1.0,
        }],
    })
    _frame(runtime, elapsed_s=1.0, progress_m=1.0, speed_mps=2.0)
    runtime.note_control_observation(
        elapsed_s=1.0, speed_mps=2.0, route_progress_m=1.0,
        brake=0.0, safety_override=False, safety_reason="NONE",
        route_deviation_m=0.0,
    )
    _frame(runtime, elapsed_s=2.0, progress_m=2.0, speed_mps=2.0)
    runtime.note_control_observation(
        elapsed_s=2.0, speed_mps=2.0, route_progress_m=2.0,
        brake=0.0, safety_override=False, safety_reason="NONE",
        route_deviation_m=0.0,
    )
    runtime.note_command_submitted({"command_id": "after", "intent": "KEEP_LANE"}, qwen=True)
    runtime.note_qwen_resolution(
        disposition="SLOW_READY", reason_code="QWEN_READY", applied=True,
        command_id="after",
    )
    runtime.note_terminal("after", "SUCCEEDED")

    result = runtime.evaluate(
        {"must_enter_degraded_mode": True, "post_recovery_command_succeeds": True},
        expected_command_count=1,
    )
    assert result["passed"] is True


def test_specific_safety_contract_does_not_pass_on_unrelated_reason() -> None:
    runtime = ScenarioExtensionRuntime({})
    runtime.note_control_observation(
        elapsed_s=1.0, speed_mps=1.0, route_progress_m=1.0,
        brake=0.8, safety_override=True, safety_reason="UNRELATED_ALERT",
        route_deviation_m=0.0,
    )
    result = runtime.evaluate(
        {"must_enter_degraded_mode": True}, expected_command_count=1,
    )
    assert result["passed"] is False


def test_intentional_invalid_result_does_not_require_a_valid_behavior_oracle() -> None:
    runtime = ScenarioExtensionRuntime({
        "faults": [{"type": "qwen_invalid_token"}],
    })
    runtime.note_qwen_resolution(
        disposition="REJECTED", reason_code="QWEN_PLAN_REJECTED", applied=False,
    )
    result = runtime.evaluate(
        {"qwen_invalid_result_count": 1, "vehicle_advance_command_count": 0},
        expected_command_count=1,
        oracle={"expected_behaviors": ["STOP", "HOLD"]},
    )
    assert result["passed"] is True
    assert all(item["key"] != "oracle_expected_behaviors" for item in result["checks"])
