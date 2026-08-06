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
