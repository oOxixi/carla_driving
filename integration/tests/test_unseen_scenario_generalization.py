from argparse import Namespace
import json
from pathlib import Path

import numpy as np
import pytest

from integration.carla_runner import (
    _runtime_profile,
    _scenario_actor,
    _scenario_completed,
)
from integration.scenario_execution import ScenarioSpec
from integration.scenario_runner_agent import (
    CarlaDrivingScenarioAgent,
    OfficialAgentConfig,
    OfficialAgentCore,
    OfficialSensorFrame,
    get_entry_point,
)


ROOT = Path(__file__).resolve().parents[2]


def _runner_args() -> Namespace:
    return Namespace(
        scenario="cruise",
        stop_line_m=20.0,
        lead_distance_m=18.0,
        emergency_distance_m=6.0,
    )


def _renamed_spec(tmp_path: Path, relative_path: str, unseen_id: str) -> ScenarioSpec:
    payload = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    payload["scenario_id"] = unseen_id
    target = tmp_path / f"{unseen_id}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return ScenarioSpec.load(target)


def test_unseen_vehicle_scenario_uses_actor_and_contract_not_id(tmp_path: Path) -> None:
    spec = _renamed_spec(
        tmp_path,
        "scenarios/safety_D/D03_front_vehicle_brake.json",
        "EVALUATOR_PRIVATE_SCENE_ALPHA",
    )
    profile = _runtime_profile(_runner_args(), spec)

    assert profile.label == "EVALUATOR_PRIVATE_SCENE_ALPHA"
    assert profile.minimum_gap_m == pytest.approx(2.5)
    assert profile.require_progress
    assert _scenario_actor(spec, "vehicle") is not None
    assert _scenario_completed(
        profile,
        expected_frames=spec.frame_count,
        frames=spec.frame_count,
        final_speed_mps=2.0,
        final_scene=None,
        min_gap_m=2.6,
        collision_seen=False,
        max_speed_mps=4.0,
    )


def test_unseen_stop_scenario_is_inferred_from_command_contract(tmp_path: Path) -> None:
    spec = _renamed_spec(
        tmp_path,
        "scenarios/smoke/S04_emergency_stop.json",
        "HIDDEN_STOP_VARIANT_927",
    )
    profile = _runtime_profile(_runner_args(), spec)

    assert profile.require_stop
    assert not profile.require_progress
    assert _scenario_completed(
        profile,
        expected_frames=spec.frame_count,
        frames=spec.frame_count,
        final_speed_mps=0.1,
        final_scene=None,
        min_gap_m=None,
        collision_seen=False,
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
