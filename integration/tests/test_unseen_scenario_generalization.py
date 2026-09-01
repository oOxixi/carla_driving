import json
from pathlib import Path

import numpy as np
from integration.scenario_runner_agent import (
    CarlaDrivingScenarioAgent,
    OfficialAgentConfig,
    OfficialAgentCore,
    OfficialSensorFrame,
    get_entry_point,
)


def test_official_agent_exposes_scenario_runner_entry_and_sensor_contract() -> None:
    agent = CarlaDrivingScenarioAgent("")
    sensor_ids = {sensor["id"] for sensor in agent.sensors()}

    assert get_entry_point() == "ScenarioRunnerAgent"
    assert sensor_ids == {"front_rgb", "lidar", "gnss"}

    control = agent.run_step({}, 0.0)
    assert control.throttle == 0.0 and control.brake == 1.0
    assert agent.last_interface_error is not None


def test_official_agent_core_generalizes_to_unseen_route_and_stops_for_lidar() -> None:
    core = OfficialAgentCore(OfficialAgentConfig(target_speed_mps=4.0))
    plan = (
        ({"lat": 31.0000, "lon": 121.0000}, "LANEFOLLOW"),
        ({"lat": 31.0002, "lon": 121.0000}, "LANEFOLLOW"),
    )
    clear = OfficialSensorFrame(
        speed_mps=1.0,
        compass_rad=0.0,
        latitude=31.0,
        longitude=121.0,
        lidar_xyz=np.empty((0, 3), dtype=np.float32),
    )
    throttle, brake, steer, reason = core.step(clear, plan)
    assert throttle > 0.0 and brake == 0.0
    assert abs(steer) < 0.05
    assert reason == "NONE"

    blocked = OfficialSensorFrame(
        speed_mps=3.0,
        compass_rad=0.0,
        latitude=31.0,
        longitude=121.0,
        lidar_xyz=np.array([[4.0, 0.1, -1.0]], dtype=np.float32),
    )
    throttle, brake, steer, reason = core.step(blocked, plan)
    assert (throttle, brake, steer) == (0.0, 1.0, 0.0)
    assert reason == "OFFICIAL_LIDAR_OBSTACLE_GUARD"


def test_official_command_boundary_fails_closed(tmp_path: Path) -> None:
    command = tmp_path / "command.json"
    command.write_text(
        json.dumps({
            "schema_version": "1.0",
            "command_id": "hidden-command",
            "intent": "CHANGE_LANE",
            "intent_confidence": 0.99,
            "status": "valid",
        }),
        encoding="utf-8",
    )
    core = OfficialAgentCore(OfficialAgentConfig(command_file=command))
    frame = OfficialSensorFrame(
        speed_mps=2.0,
        compass_rad=0.0,
        latitude=0.0,
        longitude=0.0,
        lidar_xyz=np.empty((0, 3), dtype=np.float32),
    )

    throttle, brake, _, reason = core.step(frame, ())
    assert throttle == 0.0 and brake == 1.0
    assert reason == "WATCHDOG_ALERT"
    assert core.last_command_error is not None


def test_agent_setup_resolves_task_two_profile_for_live_qwen_requests() -> None:
    agent = CarlaDrivingScenarioAgent("")

    assert agent.qwen_profile.name == "qwen3vl-2b-int4"
    assert agent.qwen_service_url == "http://127.0.0.1:8001"


def test_official_agent_core_applies_live_qwen_action_through_safety() -> None:
    core = OfficialAgentCore(OfficialAgentConfig(target_speed_mps=4.0))
    frame = OfficialSensorFrame(
        speed_mps=3.0,
        compass_rad=0.0,
        latitude=0.0,
        longitude=0.0,
        lidar_xyz=np.empty((0, 3), dtype=np.float32),
    )

    throttle, brake, steer, reason = core.step(
        frame,
        (),
        high_level_command={
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": False,
        },
    )

    assert throttle == 0.0
    assert brake > 0.0
    assert steer == 0.0
    assert reason in {"NONE", "WATCHDOG_ALERT"}
