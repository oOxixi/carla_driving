from argparse import Namespace
import math
from pathlib import Path

import pytest

from car_control_B.schemas import RouteReference, VehiclePose

from integration.carla_perception import EventLedger, PerceptionTimeoutError
from integration.carla_runner import (
    _acceptance_lateral_controller,
    _load_command,
    _lead_vehicle_travel_m,
    _minimum_gap_contract_completed,
    _expected_safety_completed,
    _rejected_load_envelope,
    _route_contract_completed,
    _route_stop_trigger_m,
    _runtime_health_completed,
    _scene_from_world,
    _scenario_raw_control_fault,
    _scenario_maneuver,
    _select_scene_facts,
    _scenario_completed,
    _speed_mps,
    _warm_up_sensor_bridge,
)
from integration.contracts import PerceptionFrame
from integration.voice_adapter import VoiceCommandAdapter


def _args(scenario):
    return Namespace(scenario=scenario, frames=100)


def test_voice_load_failure_becomes_rejected_no_op() -> None:
    envelope = _rejected_load_envelope(FileNotFoundError("missing.wav"))
    adapted = VoiceCommandAdapter().adapt(envelope, now_s=1.0)
    assert not adapted.control_authorized
    assert adapted.command.action == "NO_OP"
    assert adapted.feedback is not None


def test_scenario_facts_can_override_or_only_fill_missing_perception() -> None:
    perceived = PerceptionFrame(1, 0.05, lead_distance_m=8.0, traffic_light="UNKNOWN")
    configured = PerceptionFrame(
        1,
        0.05,
        lead_distance_m=15.0,
        lead_speed_mps=0.0,
        traffic_light="RED",
        distance_to_stop_line_m=20.0,
    )

    fused, fused_sources = _select_scene_facts(perceived, configured, "fuse")
    assert fused.lead_distance_m == 8.0
    assert fused.lead_speed_mps == 0.0
    assert fused.traffic_light == "RED"
    assert fused_sources["lead_speed_mps"] == "SCENARIO_CONFIG_FALLBACK"

    truth, truth_sources = _select_scene_facts(perceived, configured, "scenario")
    assert truth.lead_distance_m == 15.0
    assert truth.traffic_light == "RED"
    assert truth_sources["lead_distance_m"] == "SCENARIO_CONFIG_TRUTH"


def test_scenario_facts_clear_unconfigured_map_hazards() -> None:
    perceived = PerceptionFrame(
        1,
        0.05,
        lead_distance_m=7.0,
        lead_speed_mps=0.0,
        traffic_light="RED",
        distance_to_stop_line_m=5.0,
    )
    configured = PerceptionFrame(1, 0.05)

    selected, sources = _select_scene_facts(perceived, configured, "scenario")

    assert selected.lead_distance_m is None
    assert selected.lead_speed_mps is None
    assert selected.traffic_light == "UNKNOWN"
    assert selected.distance_to_stop_line_m is None
    assert sources["traffic_light"] == "SCENARIO_CONFIG_TRUTH"


def test_perception_mode_ignores_scenario_facts() -> None:
    perceived = PerceptionFrame(1, 0.05, lead_distance_m=8.0)
    configured = PerceptionFrame(1, 0.05, lead_distance_m=15.0)
    selected, sources = _select_scene_facts(perceived, configured, "perception")
    assert selected is perceived
    assert sources == {}


def test_world_scene_populates_lane_offset_and_route_deviation_from_map() -> None:
    class Location:
        x = 10.0
        y = 1.5
        z = 0.0

        def distance(self, other):
            return math.sqrt(
                (self.x - other.x) ** 2
                + (self.y - other.y) ** 2
                + (self.z - other.z) ** 2
            )

    class Ego:
        def get_location(self):
            return Location()

        def is_at_traffic_light(self):
            return False

        def get_speed_limit(self):
            return 36.0

        def get_velocity(self):
            return Namespace(x=0.0, y=0.0, z=0.0)

    class WorldMap:
        def get_waypoint(self, location, project_to_road=True):
            assert project_to_road is True
            return Namespace(
                transform=Namespace(
                    location=Namespace(x=10.0, y=1.0, z=0.0),
                    get_right_vector=lambda: Namespace(x=0.0, y=1.0, z=0.0),
                ),
            )

    route = RouteReference([(0.0, 0.0), (20.0, 0.0)])
    events = EventLedger()
    events.collision_callback(Namespace(frame=42))
    scene, sources = _scene_from_world(
        WorldMap(), Ego(), 42, 2.1, route=route, events=events,
    )

    assert scene.lane_offset_m == pytest.approx(0.5)
    assert scene.route_deviation_m == pytest.approx(1.5)
    assert scene.speed_limit_mps == pytest.approx(10.0)
    assert scene.collision is True
    assert sources["lane_offset_m"] == "CARLA_MAP_WAYPOINT"
    assert sources["route_deviation_m"] == "ROUTE_REFERENCE_NEAREST_SEGMENT"
    assert sources["speed_limit_mps"] == "CARLA_MAP_SPEED_LIMIT"
    assert sources["collision"] == "CARLA_COLLISION_EVENT"
    for field in (
        "traffic_light",
        "speed_limit_mps",
        "lane_offset_m",
        "route_deviation_m",
        "collision",
        "red_light_violation",
        "lane_invasion",
    ):
        assert field in sources


def test_world_scene_leaves_lane_offset_unknown_without_map_waypoint() -> None:
    ego = Namespace(
        get_location=lambda: Namespace(x=1.0, y=2.0, z=0.0),
        is_at_traffic_light=lambda: False,
        get_velocity=lambda: Namespace(x=0.0, y=0.0, z=0.0),
    )
    world_map = Namespace(get_waypoint=lambda location, project_to_road=True: None)

    scene, sources = _scene_from_world(world_map, ego, 1, 0.05)

    assert scene.lane_offset_m is None
    assert scene.route_deviation_m is None
    assert sources["collision"] == "UNOBSERVED_NO_EVENT_SENSOR"
    assert sources["lane_invasion"] == "UNOBSERVED_NO_EVENT_SENSOR"


def test_invalid_scenario_facts_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported scenario facts mode"):
        _select_scene_facts(PerceptionFrame(1, 0.05), None, "invalid")


def test_expected_route_deviation_intervention_counts_as_scenario_success() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "safety_D" / "D04_lane_deviation.json"
    spec = ScenarioSpec.load(path)
    assert _expected_safety_completed(
        spec,
        frames=spec.frame_count,
        final_speed_mps=0.0,
        collision_seen=False,
        safety_reasons={"SEVERE_ROUTE_DEVIATION"},
    ) is True


def test_d_fault_contracts_create_one_shot_raw_control_payloads() -> None:
    from integration.scenario_execution import ScenarioSpec

    root = Path(__file__).resolve().parents[2] / "scenarios" / "safety_D"
    d05 = ScenarioSpec.load(root / "D05_invalid_control_nan.json")
    d06 = ScenarioSpec.load(root / "D06_throttle_brake_conflict.json")
    assert _scenario_raw_control_fault(d05, 4.99) is None
    assert _scenario_raw_control_fault(d05, 5.0)["steer"] == "NaN"
    assert _scenario_raw_control_fault(d06, 5.0) == {
        "throttle": 0.5, "brake": 0.5, "steer": 0.0, "fault_injected": True,
    }


def test_regression_finish_route_is_a_hard_completion_contract() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "regression" / "REG_001_basic_clear_seed0.json"
    spec = ScenarioSpec.load(path)
    assert _route_contract_completed(spec, spec.finish_radius_m - 0.01) is True
    assert _route_contract_completed(spec, spec.finish_radius_m + 0.01) is False
    assert _route_contract_completed(None, 0.0) is None


def test_route_stop_trigger_scales_with_speed_without_stopping_early() -> None:
    assert _route_stop_trigger_m(0.0, 3.0) == pytest.approx(3.0)
    assert _route_stop_trigger_m(4.0, 3.0) == pytest.approx(5.0)
    assert _route_stop_trigger_m(6.0, 3.0) == pytest.approx(10.0)


def test_lead_vehicle_position_is_continuous_when_it_brakes() -> None:
    assert _lead_vehicle_travel_m(7.9, 4.0, 8.0, 0.0) == pytest.approx(31.6)
    assert _lead_vehicle_travel_m(8.0, 4.0, 8.0, 0.0) == pytest.approx(32.0)
    assert _lead_vehicle_travel_m(8.1, 4.0, 8.0, 0.0) == pytest.approx(32.0)


def test_front_gap_expected_value_is_a_hard_completion_contract() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "regression" / "REG_007_advanced_front_vehicle.json"
    spec = ScenarioSpec.load(path)
    assert _minimum_gap_contract_completed(spec, 2.49) is False
    assert _minimum_gap_contract_completed(spec, 2.5) is True
    assert _minimum_gap_contract_completed(None, 10.0) is None


def test_load_command_rejects_non_object_json_before_runtime_logging(tmp_path) -> None:
    path = tmp_path / "command.json"
    path.write_text("[]", encoding="utf-8")
    args = Namespace(command_json=str(path), audio=None, test_command_ttl_s=None)
    with pytest.raises(TypeError, match="JSON root must be an object"):
        _load_command(args)


def test_sensor_warmup_retries_until_an_aligned_frame_arrives() -> None:
    class Session:
        def __init__(self):
            self.frame = 10

        def tick(self, timeout):
            self.frame += 1
            return self.frame

    class World:
        def __init__(self, session):
            self.session = session

        def get_snapshot(self):
            return Namespace(timestamp=Namespace(elapsed_seconds=self.session.frame * 0.05))

    class Bridge:
        def __init__(self):
            self.calls = 0

        def acquire(self, frame, sim_time_s, timeout_s):
            self.calls += 1
            if self.calls == 1:
                raise PerceptionTimeoutError("not ready")
            return object()

    session = Session()
    bridge = Bridge()
    _warm_up_sensor_bridge(session, World(session), bridge, attempts=3,
                           tick_timeout_s=60.0, sensor_timeout_s=0.5)
    assert bridge.calls == 2


def test_vehicle_speed_ignores_vertical_spawn_settling() -> None:
    velocity = Namespace(x=3.0, y=4.0, z=-9.8)
    assert _speed_mps(velocity) == pytest.approx(5.0)


def test_acceptance_lateral_tuning_limits_steer_and_rate() -> None:
    controller = _acceptance_lateral_controller()
    assert controller.params.steer_sign == 1.0
    assert controller.params.max_steer == pytest.approx(0.60)
    assert controller.params.max_steer_delta_per_step == pytest.approx(0.04)
    assert controller.params.min_lookahead_m >= 2.5


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    [
        ("lateral_B/B04_smooth_left_curve.json", "FOLLOW_LEFT"),
        ("lateral_B/B05_smooth_right_curve.json", "FOLLOW_RIGHT"),
        ("regression/REG_003_basic_clear_seed2.json", "FOLLOW_RIGHT"),
        ("regression/REG_001_basic_clear_seed0.json", "FOLLOW"),
    ],
)
def test_scenario_maneuver_preserves_declared_curve_direction(relative_path, expected):
    from integration.scenario_execution import ScenarioSpec

    root = Path(__file__).resolve().parents[2] / "scenarios"
    assert _scenario_maneuver(ScenarioSpec.load(root / relative_path)) == expected


def test_carla_left_handed_closed_loop_converges_to_straight_route() -> None:
    controller = _acceptance_lateral_controller()
    reference = RouteReference([(float(x), 0.0) for x in range(100)])
    x, y, yaw, speed, dt = 0.0, 1.0, 0.0, 4.0, 0.05
    for frame in range(80):
        output = controller.step(VehiclePose(x, y, yaw, speed, frame=frame), reference)
        steer_angle = output.steer * controller.params.max_steer_angle_rad
        yaw += speed / controller.params.wheel_base_m * math.tan(steer_angle) * dt
        x += speed * math.cos(yaw) * dt
        y += speed * math.sin(yaw) * dt
    assert abs(y) < 0.25
    assert abs(y) < 1.0


def test_scenario_completion_uses_safety_acceptance_conditions() -> None:
    red = PerceptionFrame(100, 5.0, traffic_light="RED", distance_to_stop_line_m=0.8)
    assert _scenario_completed(_args("red_stop"), frames=100, final_speed_mps=0.1,
                               final_scene=red, min_gap_m=None, collision_seen=False)
    assert not _scenario_completed(_args("red_stop"), frames=100, final_speed_mps=0.1,
                                   final_scene=PerceptionFrame(100, 5.0, traffic_light="RED",
                                                               distance_to_stop_line_m=2.0),
                                   min_gap_m=None, collision_seen=False)
    assert _scenario_completed(_args("follow"), frames=100, final_speed_mps=2.0,
                               final_scene=None, min_gap_m=3.1, collision_seen=False,
                               max_speed_mps=2.0)
    assert not _scenario_completed(_args("follow"), frames=100, final_speed_mps=0.0,
                                   final_scene=None, min_gap_m=10.0, collision_seen=False,
                                   max_speed_mps=0.0)
    assert not _scenario_completed(_args("emergency"), frames=100, final_speed_mps=0.5,
                                   final_scene=None, min_gap_m=4.0, collision_seen=False)


def test_basic_scenario_rejects_runtime_health_fail_safe() -> None:
    assert _runtime_health_completed({"NONE", "PERCEPTION_STARTUP_GRACE"})
    assert not _runtime_health_completed({"WATCHDOG_ALERT"})
    assert not _runtime_health_completed({"INTEGRATION_FAILURE"})
    assert not _runtime_health_completed({"PERCEPTION_PERCEPTIONTIMEOUTERROR"})
