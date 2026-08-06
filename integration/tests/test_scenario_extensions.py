from __future__ import annotations

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
