import ast
from argparse import Namespace
import math
from pathlib import Path

import numpy as np
import pytest

from car_control_A import RuntimeVehicleState
from car_control_B.schemas import RouteReference, VehiclePose

import integration.carla_runner as carla_runner
from integration.carla_perception import EventLedger, PerceptionTimeoutError
from integration.carla_runner import (
    _DeferredCommand,
    _acceptance_lateral_controller,
    _active_actor_route_context,
    _actor_activation_due,
    _actor_deactivation_due,
    _actor_bbox_clearance_m,
    _actor_signed_route_clearance_m,
    _actor_signed_longitudinal_clearance_m,
    _apply_compiled_plan_route,
    _apply_scenario_speed_limit,
    _bind_scenario_actor_ids,
    _build_resume_segment_spec,
    _load_command,
    _lead_vehicle_travel_m,
    _lane_change_route_parameters,
    _map_contract_name,
    _maneuver_target_distance_m,
    _maneuver_target_passed,
    _maneuver_target_visible,
    _maneuver_target_gap_s,
    _minimum_gap_contract_completed,
    _intentional_qwen_failure_completed,
    _note_safety_feedback,
    _planner_runtime_state,
    _build_qwen_context,
    _c_safety_speed_cap_mps,
    _c_speed_cap_control_override,
    _qwen_desired_speed_mps,
    _qwen_resolution_reason,
    _qwen_voice_command,
    _save_qwen_rgb_image,
    _select_load_map,
    _select_deferred_commands,
    _expected_safety_completed,
    _rejected_load_envelope,
    _remaining_route_distances,
    _route_contract_completed,
    _route_recovery_hold_reference,
    _route_local_reference_needs_refresh,
    _route_run_can_end_early,
    _route_stop_trigger_m,
    _runtime_health_completed,
    _declared_scenario_runtime_completed,
    _scene_from_world,
    _scenario_actor,
    _scenario_actors,
    _scenario_clean_world_on_start,
    _scenario_raw_control_fault,
    _scenario_requires_adjacent_lane_anchor,
    _scenario_uses_dynamic_out_and_back,
    _scenario_maneuver,
    _scenario_local_transform,
    _scenario_traffic_light_observation,
    _scenario_traffic_light_distance_to_stop_line_m,
    _scenario_target_lane_occupied_count,
    _cleanup_stale_scenario_actors,
    _single_sensor_fault_speed_cap_mps,
    _scenario_vehicle_speed_mps,
    _update_scenario_walker,
    _update_scenario_vehicle,
    _select_scene_facts,
    _select_scenario_lead,
    _scenario_completed,
    _signed_forward_speed_mps,
    _speed_mps,
    _warm_up_sensor_bridge,
    _warm_up_loaded_map,
)
from integration.scenario_execution import ScenarioSpec


def test_scenario_commands_are_latched_and_serialized_behind_active_plan() -> None:
    first = _DeferredCommand({"command_id": "scenario_cmd_003"}, 1, "SCENARIO")
    second = _DeferredCommand({"command_id": "scenario_cmd_004"}, 2, "SCENARIO")

    selected, retained = _select_deferred_commands(
        (first, second), scenario_plan_active=True,
    )
    assert selected == ()
    assert retained == [first, second]

    selected, retained = _select_deferred_commands(
        retained, scenario_plan_active=False,
    )
    assert selected == (first,)
    assert retained == [second]


def test_active_actor_route_context_rebases_only_after_global_replan() -> None:
    original_route = object()
    current_reference = object()
    actor = {
        "route_position": {"s_m": 150.0},
        "activation_trigger": {
            "type": "route_progress_greater_than_m", "value": 130.0,
        },
    }

    route, rebased = _active_actor_route_context(
        actor,
        original_route,
        Namespace(reference=current_reference),
        100.0,
    )

    assert route is current_reference
    assert rebased["route_position"]["s_m"] == pytest.approx(50.0)
    assert rebased["activation_trigger"]["value"] == pytest.approx(130.0)

    route, unchanged = _active_actor_route_context(
        actor, original_route, None, 100.0,
    )
    assert route is original_route
    assert unchanged is actor


def test_resume_segment_keeps_only_unfinished_commands_and_live_actors() -> None:
    spec = ScenarioSpec.load(
        Path("scenarios/official_competition/S2_complex_avoidance_8km.json")
    )

    resumed, restored_phases = _build_resume_segment_spec(
        spec,
        route_progress_m=4100.0,
        completed_command_count=3,
        target_speed_kph=40.0,
    )

    assert [command.phase_id for command in resumed.commands] == [
        "S2_P4_BICYCLE_CLEARANCE",
        "S2_P5_INTERSECTION_MIXED_FLOW",
        "S2_P6_LATE_PEDESTRIAN_YIELD",
    ]
    assert restored_phases[-1] == "S2_P3_PEDESTRIAN_OVERTAKE_RETURN"
    assert {actor["actor_id"] for actor in resumed.actors} == {
        "bicycle_right", "intersection_cut_in_car", "late_crossing_pedestrian",
    }
    proposed = resumed.extensions["proposed_acceptance"]
    assert proposed["qwen_request_count"] == 3
    assert proposed["actor_activation_progress_windows_m"]["bicycle_right"] == [
        4099.0, 4101.0,
    ]
    assert "S2_P2_BUS_STOP" not in proposed["minimum_approach_speed_kph_by_phase"]


def test_terminal_resume_keeps_no_commands_actors_or_qwen_contract() -> None:
    spec = ScenarioSpec.load(
        Path("scenarios/official_competition/S2_complex_avoidance_8km.json")
    )

    resumed, restored_phases = _build_resume_segment_spec(
        spec,
        route_progress_m=8034.0,
        completed_command_count=len(spec.commands),
        target_speed_kph=0.0,
    )

    assert resumed.commands == ()
    assert resumed.actors == ()
    assert resumed.qwen_expected is None
    assert len(restored_phases) == len(spec.commands)
    proposed = resumed.extensions["proposed_acceptance"]
    assert proposed["qwen_request_count"] == 0
    assert proposed["expected_phase_count"] == 0
    assert "all_phases_must_complete" not in proposed
    assert "actor_activation_progress_windows_m" not in proposed
    assert "minimum_actor_distances_m" not in proposed


def test_targeted_scenario_command_waits_for_sensor_target() -> None:
    targeted = _DeferredCommand({
        "command_id": "scenario_cmd_targeted",
        "intent": "AVOID_OBSTACLE",
    }, 1, "SCENARIO")

    selected, retained = _select_deferred_commands(
        (targeted,), scenario_plan_active=False,
        perception_target_available=False,
    )
    assert selected == ()
    assert retained == [targeted]

    selected, retained = _select_deferred_commands(
        retained, scenario_plan_active=False,
        perception_target_available=True,
    )
    assert selected == (targeted,)
    assert retained == []


def test_scenario_vehicle_spawn_does_not_require_traffic_manager() -> None:
    source = Path(carla_runner.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    spawn_body = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_spawn_scenario_vehicle"
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "set_autopilot"
        for node in ast.walk(spawn_body)
    )


def test_actor_bbox_clearance_is_body_to_body_and_conservative() -> None:
    class Location:
        def __init__(self, x: float, y: float) -> None:
            self.x, self.y = x, y

        def distance(self, other) -> float:
            return math.hypot(self.x - other.x, self.y - other.y)

    ego = Namespace(
        get_location=lambda: Location(0.0, 0.0),
        bounding_box=Namespace(extent=Namespace(x=2.0, y=1.0)),
    )
    bicycle = Namespace(
        get_location=lambda: Location(8.0, 0.0),
        bounding_box=Namespace(extent=Namespace(x=1.0, y=0.5)),
    )

    assert _actor_bbox_clearance_m(ego, bicycle) == pytest.approx(
        8.0 - math.hypot(2.0, 1.0) - math.hypot(1.0, 0.5)
    )


def test_actor_signed_longitudinal_clearance_changes_sign_only_after_full_pass() -> None:
    class Location:
        def __init__(self, x: float, y: float) -> None:
            self.x, self.y, self.z = x, y, 0.0

    def actor_at(x: float):
        return Namespace(
            get_location=lambda: Location(x, 0.0),
            bounding_box=Namespace(extent=Namespace(x=1.0, y=0.5)),
        )

    ego = Namespace(
        get_location=lambda: Location(0.0, 0.0),
        get_transform=lambda: Namespace(
            location=Location(0.0, 0.0),
            get_forward_vector=lambda: Namespace(x=1.0, y=0.0),
        ),
        bounding_box=Namespace(extent=Namespace(x=2.0, y=1.0)),
    )

    radius = math.hypot(2.0, 1.0) + math.hypot(1.0, 0.5)
    assert _actor_signed_longitudinal_clearance_m(
        ego, actor_at(8.0),
    ) == pytest.approx(8.0 - radius)
    assert _actor_signed_longitudinal_clearance_m(
        ego, actor_at(-8.0),
    ) == pytest.approx(-8.0 + radius)

    assert _actor_signed_route_clearance_m(
        100.0, 108.0, ego, actor_at(999.0),
    ) == pytest.approx(8.0 - radius)
    assert _actor_signed_route_clearance_m(
        108.0, 100.0, ego, actor_at(999.0),
    ) == pytest.approx(-8.0 + radius)
from integration.contracts import DetectedObject, PerceptionFrame
from integration.scenario_execution import ScenarioSpec
from integration.voice_adapter import VoiceCommandAdapter


def _args(scenario):
    return Namespace(scenario=scenario, frames=100)


def test_blocked_lane_change_requires_real_adjacent_lane_anchor() -> None:
    spec = ScenarioSpec.load(
        Path("scenarios/acceptance_suite/supplemental/advanced/SUP_A15_lane_change_blocked.json")
    )

    assert _scenario_requires_adjacent_lane_anchor(spec) is True


def test_qwen_resolution_reason_preserves_object_feedback_detail() -> None:
    orchestration = Namespace(
        reason_code="QWEN_ERROR",
        feedback=Namespace(
            action_summary="ConnectionError: scenario-injected Qwen service disconnect",
        ),
    )

    reason = _qwen_resolution_reason(orchestration)

    assert reason is not None
    assert "QWEN_ERROR" in reason
    assert "disconnect" in reason


def test_scenario_speed_limit_caps_model_perception_constraint() -> None:
    scene = PerceptionFrame(1, 0.05, speed_limit_mps=30.0 / 3.6)
    sources: dict[str, str] = {}

    capped = _apply_scenario_speed_limit(scene, 20.0 / 3.6, sources)

    assert capped.speed_limit_mps == pytest.approx(20.0 / 3.6)
    assert sources["speed_limit_mps"] == "SCENARIO_SPEED_POLICY"


def test_explicit_competition_speed_contract_can_replace_map_metadata() -> None:
    scene = PerceptionFrame(1, 0.05, speed_limit_mps=30.0 / 3.6)
    sources: dict[str, str] = {}

    replaced = _apply_scenario_speed_limit(
        scene, 40.0 / 3.6, sources, override_map_limit=True,
    )

    assert replaced.speed_limit_mps == pytest.approx(40.0 / 3.6)
    assert sources["speed_limit_mps"] == "SCENARIO_SPEED_POLICY_OVERRIDE"


def test_deferred_actor_activation_uses_monotonic_route_progress() -> None:
    actor = {
        "activation_trigger": {
            "type": "route_progress_greater_than_m", "value": 820.0,
        },
    }

    assert _actor_activation_due(actor, elapsed_s=100.0, route_progress_m=819.9) is False
    assert _actor_activation_due(actor, elapsed_s=100.1, route_progress_m=820.0) is True
    assert _actor_activation_due({}, elapsed_s=0.0, route_progress_m=0.0) is True


def test_temporary_actor_deactivation_uses_monotonic_route_progress() -> None:
    actor = {
        "deactivation_trigger": {
            "type": "route_progress_greater_than_m", "value": 1250.0,
        },
    }

    assert _actor_deactivation_due(actor, elapsed_s=200.0, route_progress_m=1249.9) is False
    assert _actor_deactivation_due(actor, elapsed_s=200.1, route_progress_m=1250.0) is True
    assert _actor_deactivation_due({}, elapsed_s=999.0, route_progress_m=9999.0) is False


def test_completed_walker_may_be_reclaimed_but_early_death_still_fails() -> None:
    class DeadWalker:
        is_alive = False

    actor_spec = {
        "spawn": {"x": 22.0, "y": -3.4},
        "behavior": {
            "target_xy_m": [22.0, 3.4],
            "start_time_s": 4.0,
            "speed_mps": 1.5,
        },
    }

    _update_scenario_walker(DeadWalker(), actor_spec, 16.0, None, None)
    with pytest.raises(RuntimeError, match="not alive"):
        _update_scenario_walker(DeadWalker(), actor_spec, 5.0, None, None)


def test_scenario_vehicle_applies_updated_timeline_speed() -> None:
    class Vector:
        x = 0.0
        y = 0.0
        z = 0.0

    class Transform:
        @staticmethod
        def get_forward_vector():
            return Vector()

    class Vehicle:
        is_alive = True
        applied = None

        @staticmethod
        def get_velocity():
            return Vector()

        @staticmethod
        def get_transform():
            return Transform()

        def apply_control(self, control):
            self.applied = control

    class CarlaApi:
        @staticmethod
        def VehicleControl(**values):
            return values

    vehicle = Vehicle()
    _update_scenario_vehicle(
        vehicle,
        {"behavior": {"initial_speed_mps": 0.3}},
        elapsed_s=10.0,
        carla_api=CarlaApi(),
        desired_speed_mps=3.0,
    )

    assert vehicle.applied is not None
    assert vehicle.applied["throttle"] > 0.0
    assert vehicle.applied["brake"] == 0.0


def test_lead_vehicle_enforces_declared_speed_for_bicycle_physics() -> None:
    class Vector:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x, self.y, self.z = x, y, z

    class Transform:
        @staticmethod
        def get_forward_vector():
            return Vector(-1.0, 0.0, 0.0)

    class Vehicle:
        is_alive = True
        target_velocity = None

        @staticmethod
        def get_velocity():
            return Vector()

        @staticmethod
        def get_transform():
            return Transform()

        def apply_control(self, control):
            self.applied = control

        def set_target_velocity(self, velocity):
            self.target_velocity = velocity

    class CarlaApi:
        Vector3D = Vector

        @staticmethod
        def VehicleControl(**values):
            return values

    vehicle = Vehicle()
    _update_scenario_vehicle(
        vehicle,
        {"behavior": {"mode": "lead_vehicle", "target_speed_mps": 5.5}},
        elapsed_s=10.0,
        carla_api=CarlaApi(),
        desired_speed_mps=5.5,
    )

    assert vehicle.target_velocity.x == pytest.approx(-5.5)
    assert vehicle.target_velocity.y == pytest.approx(0.0)


def test_lead_vehicle_continues_on_map_after_finite_route_endpoint() -> None:
    class Vector:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x, self.y, self.z = x, y, z

    class Location(Vector):
        pass

    class Transform:
        def __init__(self, location=None, yaw=0.0):
            self.location = location or Location(1.0, 0.0, 0.0)
            self.rotation = Namespace(yaw=yaw)

        @staticmethod
        def get_forward_vector():
            return Vector(1.0, 0.0, 0.0)

    class Vehicle:
        is_alive = True

        def __init__(self):
            self.transform = Transform()
            self.target_velocity = None

        @staticmethod
        def get_velocity():
            return Vector()

        def get_transform(self):
            return self.transform

        def get_location(self):
            return self.transform.location

        def apply_control(self, control):
            self.applied = control

        def set_target_velocity(self, velocity):
            self.target_velocity = velocity

    class Waypoint:
        @staticmethod
        def next(_distance):
            return [Namespace(transform=Transform(Location(1.0, 5.0, 0.0), yaw=90.0))]

    class CarlaApi:
        Vector3D = Vector

        @staticmethod
        def VehicleControl(**values):
            return values

    vehicle = Vehicle()
    _update_scenario_vehicle(
        vehicle,
        {"behavior": {"mode": "lead_vehicle", "target_speed_mps": 5.5}},
        elapsed_s=10.0,
        carla_api=CarlaApi(),
        desired_speed_mps=5.5,
        world_map=Namespace(get_waypoint=lambda *_args, **_kwargs: Waypoint()),
        route_points_xy_m=((0.0, 0.0), (1.0, 0.0)),
    )

    assert vehicle.target_velocity.x == pytest.approx(0.0, abs=1e-9)
    assert vehicle.target_velocity.y == pytest.approx(5.5)


def test_event_driven_cut_in_waits_then_steers_and_recenters() -> None:
    class Vector:
        x = 0.0
        y = 0.0
        z = 0.0

    class Transform:
        @staticmethod
        def get_forward_vector():
            return Vector()

    class Vehicle:
        is_alive = True

        @staticmethod
        def get_velocity():
            return Vector()

        @staticmethod
        def get_transform():
            return Transform()

        def apply_control(self, control):
            self.applied = control

    class CarlaApi:
        @staticmethod
        def VehicleControl(**values):
            return values

    actor = {"behavior": {
        "mode": "cut_in", "cut_in_on_first_event": True,
        "cut_in_duration_s": 3.0, "cut_in_steer": 0.18, "direction": "RIGHT",
    }}
    vehicle = Vehicle()
    _update_scenario_vehicle(
        vehicle, actor, 20.0, CarlaApi(), desired_speed_mps=4.0,
        behavior_elapsed_s=None,
    )
    assert vehicle.applied["steer"] == 0.0

    _update_scenario_vehicle(
        vehicle, actor, 21.0, CarlaApi(), desired_speed_mps=4.0,
        behavior_elapsed_s=0.5,
    )
    assert vehicle.applied["steer"] > 0.0

    _update_scenario_vehicle(
        vehicle, actor, 23.0, CarlaApi(), desired_speed_mps=4.0,
        behavior_elapsed_s=2.0,
    )
    assert vehicle.applied["steer"] < 0.0

    _update_scenario_vehicle(
        vehicle, actor, 25.0, CarlaApi(), desired_speed_mps=4.0,
        behavior_elapsed_s=4.0,
    )
    assert vehicle.applied["steer"] == 0.0


def test_voice_load_failure_becomes_rejected_no_op() -> None:
    envelope = _rejected_load_envelope(FileNotFoundError("missing.wav"))
    adapted = VoiceCommandAdapter().adapt(envelope, now_s=1.0)
    assert not adapted.control_authorized
    assert adapted.command.action == "NO_OP"
    assert adapted.feedback is not None


def test_canonical_safety_feedback_is_available_to_scenario_completion() -> None:
    reasons: set[str] = set()

    _note_safety_feedback(reasons, {
        "safety_event": {"reason_code": "TRAFFIC_LIGHT_STOP"},
    })

    assert reasons == {"TRAFFIC_LIGHT_STOP"}


def test_c_vru_speed_cap_is_temporary_and_requires_a_valid_slow_down_summary() -> None:
    assert _c_safety_speed_cap_mps({
        "recommended_action": "SLOW_DOWN", "recommended_speed_cap_mps": 2.0,
    }) == pytest.approx(2.0)
    assert _c_safety_speed_cap_mps({
        "recommended_action": "KEEP_SPEED", "recommended_speed_cap_mps": 2.0,
    }) is None
    assert _c_safety_speed_cap_mps({
        "recommended_action": "SLOW_DOWN", "recommended_speed_cap_mps": float("nan"),
    }) is None
    assert _c_speed_cap_control_override(2.05, 2.0) is None
    assert _c_speed_cap_control_override(5.0, 2.0) == {
        "throttle": 0.0, "brake": 1.0, "steer": 0.0,
    }


def test_single_sensor_fault_applies_degraded_speed_cap_only_while_partially_available() -> None:
    assert _single_sensor_fault_speed_cap_mps({"front_rgb"}, 4.2) == pytest.approx(2.0)
    assert _single_sensor_fault_speed_cap_mps({"lidar"}, 1.5) == pytest.approx(1.5)
    assert _single_sensor_fault_speed_cap_mps(set(), 4.2) is None
    assert _single_sensor_fault_speed_cap_mps({"front_rgb", "lidar"}, 4.2) is None


def test_compiled_maneuver_applies_only_the_first_step_before_fsm_advances() -> None:
    current = RouteReference([(0.0, 0.0), (10.0, 0.0)], target_speed_mps=2.0)
    validated = RouteReference([(0.0, 0.0), (10.0, 3.5)], target_speed_mps=2.0)
    compiled = {
        "steps": [
            {"behavior": "CHANGE_LANE_LEFT", "target": {}},
            {"behavior": "SET_SPEED", "target": {"target_speed_mps": 5.0}},
        ],
    }

    route, speed, behavior = _apply_compiled_plan_route(
        compiled,
        world_map=None,
        ego=None,
        current_route=current,
        requested_speed_mps=2.0,
        distance_m=60.0,
        prevalidated_maneuver_route=validated,
    )

    assert route.points_xy_m == validated.points_xy_m
    assert route.target_speed_mps == pytest.approx(2.0)
    assert speed == pytest.approx(2.0)
    assert behavior == "CHANGE_LANE_LEFT"


def test_compiled_longitudinal_sequence_does_not_apply_resume_speed_early() -> None:
    current = RouteReference([(0.0, 0.0), (10.0, 0.0)], target_speed_mps=8.0)
    compiled = {
        "steps": [
            {"behavior": "SLOW_DOWN", "target": {"target_speed_mps": 3.0}},
            {"behavior": "KEEP_LANE", "target": {"target_speed_mps": 8.0}},
        ],
    }

    route, speed, behavior = _apply_compiled_plan_route(
        compiled,
        world_map=None,
        ego=None,
        current_route=current,
        requested_speed_mps=8.0,
        distance_m=60.0,
    )

    assert route.target_speed_mps == pytest.approx(3.0)
    assert speed == pytest.approx(3.0)
    assert behavior is None


def test_s2_dynamic_lane_change_profile_has_outbound_stabilization_segment() -> None:
    parameters = _lane_change_route_parameters({
        "route_distance_m": 72.0,
        "step_m": 1.0,
        "transition_start_m": 8.0,
        "transition_length_m": 30.0,
        "target_lane_offset_m": 0.0,
    }, mission_distance_m=8000.0)

    assert parameters == {
        "distance_m": 72.0,
        "step_m": 1.0,
        "transition_start_m": 8.0,
        "transition_length_m": 30.0,
        "target_lane_offset_m": 0.0,
    }
    assert _scenario_uses_dynamic_out_and_back(Namespace(
        extensions={"maneuver_route_mode": "dynamic_out_and_back"},
    )) is True


def test_lane_change_profile_rejects_transition_without_stabilization() -> None:
    with pytest.raises(ValueError, match="stabilization"):
        _lane_change_route_parameters({
            "route_distance_m": 35.0,
            "transition_start_m": 10.0,
            "transition_length_m": 25.0,
        }, mission_distance_m=8000.0)


def test_maneuver_target_visibility_does_not_confuse_generic_lidar_obstacles() -> None:
    vehicle_step = Namespace(target={"target_id": "legacy-vehicle-000"})
    vehicle = DetectedObject(2, "car", 0.9, (0.1, 0.2, 0.4, 0.8), 12.0)
    generic = DetectedObject(0, "obstacle", 1.0, (0.4, 0.3, 0.6, 0.8), 13.0)

    assert _maneuver_target_visible(
        vehicle_step, PerceptionFrame(1, 0.05, detected_objects=(vehicle,)),
    )
    assert not _maneuver_target_visible(
        vehicle_step, PerceptionFrame(2, 0.10, detected_objects=(generic,)),
    )


def test_maneuver_target_gap_uses_bound_actor_distance() -> None:
    step = Namespace(target={"target_id": "lead_001"})
    scene = PerceptionFrame(1, 0.05, detected_objects=(
        DetectedObject(2, "car", 0.9, (0.4, 0.2, 0.6, 0.8), 12.0, "lead_001"),
        DetectedObject(0, "obstacle", 1.0, (0.4, 0.2, 0.6, 0.8), 3.0, "other"),
    ))

    assert _maneuver_target_visible(step, scene)
    assert _maneuver_target_distance_m(step, scene) == pytest.approx(12.0)
    assert _maneuver_target_gap_s(step, scene, 4.0) == pytest.approx(3.0)


def test_maneuver_target_gap_falls_back_to_real_scenario_actor() -> None:
    step = Namespace(target={"target_id": "bicycle_lead"})
    scene = PerceptionFrame(1, 0.05)

    assert _maneuver_target_gap_s(
        step, scene, 5.0, {"bicycle_lead": 15.0},
    ) == pytest.approx(3.0)


def test_maneuver_target_distance_falls_back_to_real_scenario_actor() -> None:
    step = Namespace(target={"target_id": "slow_vehicle"})
    unrelated = PerceptionFrame(1, 0.05, detected_objects=(
        DetectedObject(
            1, "pedestrian", 0.9, (0.4, 0.2, 0.6, 0.8), 10.0,
            "crossing_pedestrian",
        ),
    ))

    assert _maneuver_target_distance_m(
        step, unrelated, {"slow_vehicle": 34.5},
    ) == pytest.approx(34.5)


def test_maneuver_target_distance_grounds_legacy_id_to_lidar_class() -> None:
    step = Namespace(target={"target_id": "legacy-obstacle-000"})
    scene = PerceptionFrame(1, 0.05, detected_objects=(
        DetectedObject(0, "obstacle", 1.0, (0.4, 0.2, 0.6, 0.8), 21.9),
    ))

    assert _maneuver_target_distance_m(step, scene) == pytest.approx(21.9)


def test_maneuver_target_pass_requires_measured_clearance_when_available() -> None:
    assert not _maneuver_target_passed(
        target_seen=True,
        target_visible=False,
        distance_from_plan_start_m=20.0,
        pass_after_m=42.0,
    )
    assert _maneuver_target_passed(
        target_seen=True,
        target_visible=False,
        distance_from_plan_start_m=42.0,
        pass_after_m=42.0,
    )


def test_maneuver_target_pass_fallback_requires_target_to_leave_view() -> None:
    assert not _maneuver_target_passed(
        target_seen=True,
        target_visible=True,
        distance_from_plan_start_m=25.0,
        pass_after_m=None,
    )
    assert _maneuver_target_passed(
        target_seen=True,
        target_visible=False,
        distance_from_plan_start_m=20.0,
        pass_after_m=None,
    )


def test_scenario_actor_binding_uses_image_position_when_only_one_range_is_known() -> None:
    class Location:
        def __init__(self, x, y):
            self.x, self.y, self.z = x, y, 0.0

        def distance(self, other):
            return math.hypot(self.x - other.x, self.y - other.y)

    class Transform:
        location = Location(0.0, 0.0)

        @staticmethod
        def get_forward_vector():
            return Namespace(x=1.0, y=0.0)

    class Actor:
        is_alive = True

        def __init__(self, x, y):
            self.location = Location(x, y)

        def get_location(self):
            return self.location

    ego = Namespace(get_transform=lambda: Transform())
    left = Actor(20.0, -6.0)
    right = Actor(20.0, 6.0)
    detections = (
        DetectedObject(2, "car", 0.9, (0.20, 0.20, 0.40, 0.80), None),
        DetectedObject(2, "car", 0.9, (0.60, 0.20, 0.80, 0.80), 20.9),
    )
    scene = PerceptionFrame(1, 0.05, detected_objects=detections)

    bound = _bind_scenario_actor_ids(
        scene, ego,
        ((left, {"actor_id": "left-car", "type": "vehicle"}),
         (right, {"actor_id": "right-car", "type": "vehicle"})),
    )

    assert [item.track_id for item in bound.detected_objects] == ["left-car", "right-car"]


def test_generic_lidar_obstacle_binds_nearest_geometric_scenario_actor() -> None:
    class Location:
        def __init__(self, x, y):
            self.x, self.y, self.z = x, y, 0.0

        def distance(self, other):
            return math.hypot(self.x - other.x, self.y - other.y)

    class Transform:
        location = Location(0.0, 0.0)

        @staticmethod
        def get_forward_vector():
            return Namespace(x=1.0, y=0.0)

    class Actor:
        is_alive = True

        def __init__(self, x, y):
            self.location = Location(x, y)

        def get_location(self):
            return self.location

    ego = Namespace(get_transform=lambda: Transform())
    scene = PerceptionFrame(1, 0.05, detected_objects=(
        DetectedObject(0, "obstacle", 1.0, (0.45, 0.2, 0.55, 0.8), 20.0),
    ))

    bound = _bind_scenario_actor_ids(
        scene,
        ego,
        (
            (Actor(20.0, 0.0), {"actor_id": "lead-car", "type": "vehicle"}),
            (Actor(20.0, 5.0), {"actor_id": "warning-prop", "type": "static.prop"}),
        ),
    )

    assert bound.detected_objects[0].track_id == "lead-car"
    assert bound.detected_objects[0].class_id == 2
    assert bound.detected_objects[0].class_name == "car"


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


def test_requested_town_prefers_optimized_map_when_available() -> None:
    available = ("/Game/Carla/Maps/Town01", "/Game/Carla/Maps/Town03_Opt")

    assert _map_contract_name("Carla/Maps/Town03_Opt") == "Town03"
    assert _select_load_map("Town03", available) == "Town03_Opt"
    assert _select_load_map("Town02", available) == "Town02"


def test_qwen_helpers_use_scenario_command_and_target_speed() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "scenarios"
        / "smoke"
        / "S01_set_speed_20.json"
    )
    spec = ScenarioSpec.load(scenario_path)
    args = Namespace(qwen_voice_command=None, default_speed_mps=2.0)

    assert _qwen_voice_command(args, spec) == "设置速度到20公里每小时"
    assert _qwen_desired_speed_mps(args, spec) == pytest.approx(20.0 / 3.6)

    args.qwen_voice_command = "显式指令"
    assert _qwen_voice_command(args, spec) == "显式指令"


def test_qwen_rgb_image_and_context_are_replayable(tmp_path: Path) -> None:
    measurement = Namespace(
        rgb_array=np.full((8, 12, 3), [10, 20, 30], dtype=np.uint8)
    )
    rgb_ref = _save_qwen_rgb_image(
        measurement,
        tmp_path,
        request_id="request-1",
    )
    assert rgb_ref == "request-1.jpg"
    assert (tmp_path / rgb_ref).is_file()

    state = RuntimeVehicleState(7, 1.25, 2.5, 1.0, 2.0, 0.0, 5.0, "1")
    detection = DetectedObject(2, "car", 0.9, (0.1, 0.2, 0.4, 0.8), 12.0)
    scene = PerceptionFrame(
        7,
        1.25,
        lead_distance_m=12.0,
        lead_speed_mps=2.0,
        traffic_light="GREEN",
        detected_objects=(detection,),
    )
    context = _build_qwen_context(
        request_id="request-1",
        voice_command="设置速度到每秒五米",
        rgb_ref=rgb_ref,
        state=state,
        scene=scene,
        behavior_state="STOPPED",
        desired_speed_mps=5.0,
        route_end_distance_m=50.0,
        c_safety_state={"ttc_s": 6.0, "fusion_mode": "RGB_LIDAR"},
    )

    payload = context.to_payload()
    assert payload["rgb_ref"] == "request-1.jpg"
    assert payload["scene_state"]["desired_speed_mps"] == 5.0
    assert payload["perception"]["detected_objects"][0]["class_name"] == "car"
    assert payload["safety_state"]["minimum_ttc_s"] == 6.0


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


def test_traffic_light_anchor_uses_seeded_candidate_index() -> None:
    from integration.carla_runner import _traffic_light_scenario_anchor

    class Location:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x, self.y, self.z = x, y, z

    class Rotation:
        def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
            self.pitch, self.yaw, self.roll = pitch, yaw, roll

    class Transform:
        def __init__(self, location, rotation=None):
            self.location = location
            self.rotation = rotation or Rotation()

        def get_forward_vector(self):
            return Namespace(x=1.0, y=0.0)

    def light(actor_id: int, x: float):
        waypoint = Namespace(transform=Transform(Location(x=x)))
        return Namespace(id=actor_id, get_stop_waypoints=lambda: [waypoint])

    lights = [light(20, 20.0), light(10, 10.0)]
    world = Namespace(
        get_actors=lambda: Namespace(filter=lambda pattern: lights),
    )
    world_map = Namespace(
        get_waypoint=lambda location, project_to_road=True: Namespace(
            transform=Transform(location),
        ),
    )
    carla_api = Namespace(Location=Location, Rotation=Rotation, Transform=Transform)

    selected, _ = _traffic_light_scenario_anchor(
        world, world_map, carla_api, 12.0, candidate_index=1,
    )

    assert selected.id == 20


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


def test_allowed_safety_override_continuous_contract_counts_as_scenario_success() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "safety_D" / "D03_front_vehicle_brake.json"
    spec = ScenarioSpec.load(path)
    assert _expected_safety_completed(
        spec,
        frames=spec.frame_count,
        final_speed_mps=3.0,
        collision_seen=False,
        safety_reasons={"EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE"},
    ) is True


def test_allowed_safety_override_does_not_hide_runtime_failure() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "safety_D" / "D03_front_vehicle_brake.json"
    spec = ScenarioSpec.load(path)
    assert _expected_safety_completed(
        spec,
        frames=spec.frame_count,
        final_speed_mps=0.0,
        collision_seen=False,
        safety_reasons={"WATCHDOG_ALERT", "EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE"},
    ) is False


def test_c_perception_fail_closed_reason_counts_as_front_pedestrian_evidence() -> None:
    import integration.carla_runner as runner
    from integration.scenario_execution import ScenarioSpec

    reason = runner._c_perception_safety_reason({
        "recommended_action": "FULL_BRAKE",
        "object_class": "PERSON",
        "reason": "visual_hazard_without_range",
    })

    assert reason == "C_FRONT_PEDESTRIAN_VISUAL_HAZARD_WITHOUT_RANGE"

    path = Path(__file__).resolve().parents[2] / "scenarios" / "safety_D" / "D02_pedestrian_crossing.json"
    spec = ScenarioSpec.load(path)
    assert _expected_safety_completed(
        spec,
        frames=spec.frame_count,
        final_speed_mps=0.0,
        collision_seen=False,
        safety_reasons={reason, "RED_LIGHT_STOP_LINE_GUARD"},
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


def test_normal_acceptance_safety_assertion_does_not_inject_a_control_fault() -> None:
    spec = ScenarioSpec.load(
        Path(__file__).resolve().parents[2]
        / "scenarios" / "acceptance_suite" / "basic" / "ACC_B01_start_keep_lane.json"
    )

    assert spec.expected["final_control_no_throttle_brake_overlap"] is True
    assert _scenario_raw_control_fault(spec, 5.0) is None


def test_regression_finish_route_is_a_hard_completion_contract() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "regression" / "REG_001_basic_clear_seed0.json"
    spec = ScenarioSpec.load(path)
    assert _route_contract_completed(spec, spec.finish_radius_m - 0.01) is True
    assert _route_contract_completed(spec, spec.finish_radius_m + 0.01) is False
    assert _route_contract_completed(None, 0.0) is None


def test_route_contract_uses_along_route_progress_for_overlapping_endpoint() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    spec = ScenarioSpec.load(path)
    assert _route_contract_completed(spec, 0.0, 100.0) is False
    assert _route_contract_completed(spec, 100.0, spec.finish_radius_m) is True


def test_route_contract_accepts_physical_finish_inside_last_coarse_sample() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    spec = ScenarioSpec.load(path)

    assert _route_contract_completed(spec, 3.15, 6.0) is True
    assert _route_contract_completed(spec, 3.15, 100.0) is False


def test_remaining_route_distance_distinguishes_repeated_coordinates() -> None:
    remaining = _remaining_route_distances(((0.0, 0.0), (10.0, 0.0), (0.0, 0.0)))
    assert remaining == pytest.approx((20.0, 10.0, 0.0))


def test_route_stop_trigger_scales_with_speed_without_stopping_early() -> None:
    assert _route_stop_trigger_m(0.0, 3.0) == pytest.approx(3.0)
    assert _route_stop_trigger_m(4.0, 3.0) == pytest.approx(5.0)
    assert _route_stop_trigger_m(6.0, 3.0) == pytest.approx(10.0)


def test_long_route_ends_after_real_contracts_not_only_frame_exhaustion() -> None:
    spec = carla_runner.ScenarioSpec.load(
        Path(__file__).resolve().parents[2]
        / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    )
    completed = {
        "elapsed_s": 1900.0,
        "speed_mps": 0.1,
        "route_remaining_m": spec.finish_radius_m,
        "distance_to_route_end_m": spec.finish_radius_m,
        "timeline_completed": True,
        "command_finished": True,
        "canonical_pending": False,
        "deferred_command_count": 0,
        "maneuver_active": False,
        "qwen_contract_completed": True,
        "extension_contract_completed": True,
        "collision_seen": False,
        "safety_reasons": set(),
    }
    assert _route_run_can_end_early(spec, **completed) is True
    for key, value in {
        "elapsed_s": 849.9,
        "speed_mps": 0.2,
        "route_remaining_m": spec.finish_radius_m * 2.0 + 0.1,
        "timeline_completed": False,
        "command_finished": False,
        "canonical_pending": True,
        "deferred_command_count": 1,
        "maneuver_active": True,
        "qwen_contract_completed": False,
        "extension_contract_completed": False,
        "collision_seen": True,
        "safety_reasons": {"WATCHDOG_ALERT"},
    }.items():
        rejected = {**completed, key: value}
        assert _route_run_can_end_early(spec, **rejected) is False, key


def test_lead_vehicle_position_is_continuous_when_it_brakes() -> None:
    assert _lead_vehicle_travel_m(7.9, 4.0, 8.0, 0.0) == pytest.approx(31.6)
    assert _lead_vehicle_travel_m(8.0, 4.0, 8.0, 0.0) == pytest.approx(32.0)
    assert _lead_vehicle_travel_m(8.1, 4.0, 8.0, 0.0) == pytest.approx(32.0)


def test_scenario_actor_lookup_is_unique_and_explicit() -> None:
    spec = Namespace(
        scenario_id="D03",
        actors=(
            {"type": "vehicle", "actor_id": "lead"},
            {"type": "traffic_light", "state": "red"},
        ),
    )
    assert _scenario_actor(spec, "vehicle")["actor_id"] == "lead"
    assert _scenario_actor(spec, "walker.pedestrian") is None

    duplicate = Namespace(
        scenario_id="bad",
        actors=({"type": "vehicle"}, {"type": "vehicle"}),
    )
    with pytest.raises(ValueError, match="multiple"):
        _scenario_actor(duplicate, "vehicle")


def test_plural_scenario_vehicle_collection_and_owned_lead_selection() -> None:
    spec = Namespace(
        actors=(
            {"type": "vehicle", "actor_id": "far"},
            {"type": "vehicle", "actor_id": "near"},
            {"type": "walker.pedestrian", "actor_id": "ped"},
        ),
    )
    assert [actor["actor_id"] for actor in _scenario_actors(spec, "vehicle")] == [
        "far", "near",
    ]

    class Actor:
        is_alive = True

        def __init__(self, x: float, y: float) -> None:
            self._location = Namespace(x=x, y=y)

        def get_location(self):
            return self._location

    ego = Namespace(
        get_location=lambda: Namespace(x=0.0, y=0.0),
        get_transform=lambda: Namespace(
            get_forward_vector=lambda: Namespace(x=1.0, y=0.0),
        ),
    )
    assert _select_scenario_lead(ego, [Actor(20.0, 0.0), Actor(8.0, 0.5)]) is not None
    assert _select_scenario_lead(ego, [Actor(-2.0, 0.0)]) is None


def test_submission_scenarios_declare_expected_real_actor_types() -> None:
    from integration.scenario_execution import ScenarioSpec

    root = Path(__file__).resolve().parents[2] / "scenarios"
    s01 = ScenarioSpec.load(root / "smoke" / "S01_set_speed_20.json")
    d03 = ScenarioSpec.load(root / "safety_D" / "D03_front_vehicle_brake.json")
    d08 = ScenarioSpec.load(
        root / "safety_D" / "D08_command_conflict_red_light_continue.json"
    )
    assert _scenario_actor(s01, "vehicle") is None
    assert _scenario_actor(s01, "traffic_light") is None
    assert _scenario_actor(d03, "vehicle")["actor_id"] == "lead_001"
    assert _scenario_actor(d08, "traffic_light")["state"].lower() == "red"


def test_scenario_vehicle_changes_to_braking_target_at_declared_time() -> None:
    actor = {
        "behavior": {
            "initial_speed_mps": 5.0,
            "brake_at_s": 6.0,
            "target_speed_mps": 0.5,
        }
    }
    assert _scenario_vehicle_speed_mps(actor, 5.99) == pytest.approx(5.0)
    assert _scenario_vehicle_speed_mps(actor, 6.0) == pytest.approx(0.5)


def test_scenario_vehicle_speed_is_signed_along_actor_heading() -> None:
    actor = Namespace(
        get_velocity=lambda: Namespace(x=3.0, y=4.0, z=0.0),
        get_transform=lambda: Namespace(
            get_forward_vector=lambda: Namespace(x=-0.6, y=-0.8, z=0.0),
        ),
    )
    assert _signed_forward_speed_mps(actor) == pytest.approx(-5.0)


def test_scenario_local_actor_transform_rotates_with_ego_heading() -> None:
    class Location:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x, self.y, self.z = x, y, z

    class Rotation:
        def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
            self.pitch, self.yaw, self.roll = pitch, yaw, roll

    class Transform:
        def __init__(self, location, rotation):
            self.location, self.rotation = location, rotation

    carla_api = Namespace(Location=Location, Rotation=Rotation, Transform=Transform)
    anchor = Transform(Location(10.0, 20.0, 1.0), Rotation(yaw=90.0))
    result = _scenario_local_transform(
        carla_api,
        anchor,
        {"x": 18.0, "y": 0.0, "z": 0.5, "yaw_deg": 0.0},
    )
    assert result.location.x == pytest.approx(10.0)
    assert result.location.y == pytest.approx(38.0)
    assert result.rotation.yaw == pytest.approx(90.0)


def test_real_traffic_light_observation_replaces_config_fallback_provenance() -> None:
    class Location:
        def __init__(self, x, y, z=0.0):
            self.x, self.y, self.z = x, y, z

    class Transform:
        def __init__(self, location):
            self.location = location

        def get_forward_vector(self):
            return Namespace(x=1.0, y=0.0, z=0.0)

    ego = Namespace(
        get_location=lambda: Location(0.0, 0.0),
        get_transform=lambda: Transform(Location(0.0, 0.0)),
    )
    light = Namespace(
        get_state=lambda: "TrafficLightState.Red",
        get_stop_waypoints=lambda: (
            Namespace(transform=Transform(Location(12.0, 0.0))),
        ),
    )
    observed, sources = _scenario_traffic_light_observation(
        PerceptionFrame(10, 0.5),
        ego,
        light,
    )
    assert observed.traffic_light == "RED"
    assert observed.distance_to_stop_line_m == pytest.approx(12.0)
    assert sources["traffic_light"] == "CARLA_SCENARIO_TRAFFIC_LIGHT_ACTOR_STOP_WAYPOINT"
    assert "FALLBACK" not in sources["traffic_light"]
    assert _scenario_traffic_light_distance_to_stop_line_m(ego, light) == pytest.approx(12.0)


def test_real_traffic_light_observation_marks_front_bumper_crossing_on_red() -> None:
    class Location:
        def __init__(self, x, y, z=0.0):
            self.x, self.y, self.z = x, y, z

    class Transform:
        def __init__(self, location):
            self.location = location

        def get_forward_vector(self):
            return Namespace(x=1.0, y=0.0, z=0.0)

    ego = Namespace(
        bounding_box=Namespace(extent=Namespace(x=2.0)),
        get_location=lambda: Location(10.1, 0.0),
        get_transform=lambda: Transform(Location(10.1, 0.0)),
    )
    light = Namespace(
        get_state=lambda: "TrafficLightState.Red",
        get_stop_waypoints=lambda: (
            Namespace(transform=Transform(Location(12.0, 0.0))),
        ),
    )

    observed, _ = _scenario_traffic_light_observation(
        PerceptionFrame(10, 0.5), ego, light,
    )

    assert observed.distance_to_stop_line_m == 0.0
    assert observed.red_light_violation is True


def test_target_lane_occupancy_uses_real_actor_lane_ids() -> None:
    left = Namespace(road_id=7, lane_id=2)
    ego_waypoint = Namespace(
        road_id=7,
        lane_id=1,
        get_left_lane=lambda: left,
        get_right_lane=lambda: None,
    )
    occupied_waypoint = Namespace(road_id=7, lane_id=2)
    current_waypoint = Namespace(road_id=7, lane_id=1)
    ego_location = object()
    occupied_location = object()
    current_location = object()
    world_map = Namespace(get_waypoint=lambda location, project_to_road=True: {
        id(ego_location): ego_waypoint,
        id(occupied_location): occupied_waypoint,
        id(current_location): current_waypoint,
    }[id(location)])
    ego = Namespace(get_location=lambda: ego_location)
    vehicles = (
        (Namespace(get_location=lambda: occupied_location), {}),
        (Namespace(get_location=lambda: current_location), {}),
    )

    assert _scenario_target_lane_occupied_count(
        world_map, ego, vehicles, "CHANGE_LANE_LEFT",
    ) == 1


def test_target_lane_occupancy_follows_adjacent_lane_across_road_segments() -> None:
    continuation = Namespace(road_id=6, lane_id=-1, next=lambda _distance: ())
    left = Namespace(road_id=5, lane_id=-1, next=lambda _distance: (continuation,))
    ego_waypoint = Namespace(
        road_id=5,
        lane_id=-2,
        get_left_lane=lambda: left,
        get_right_lane=lambda: None,
    )
    ego_location = object()
    actor_location = object()
    actor_waypoint = Namespace(road_id=6, lane_id=-1)
    world_map = Namespace(get_waypoint=lambda location, project_to_road=True: (
        ego_waypoint if location is ego_location else actor_waypoint
    ))

    assert _scenario_target_lane_occupied_count(
        world_map,
        Namespace(get_location=lambda: ego_location),
        ((Namespace(get_location=lambda: actor_location), {}),),
        "CHANGE_LANE_LEFT",
    ) == 1


def test_stale_acceptance_actors_are_removed_without_touching_external_vehicles() -> None:
    destroyed: list[str] = []

    def actor(role_name: str) -> Namespace:
        return Namespace(
            attributes={"role_name": role_name},
            destroy=lambda: destroyed.append(role_name),
        )

    actors = (
        actor("acceptance84:old_blocker"),
        actor("front_blocker"),
        actor("hero"),
        actor("autopilot"),
    )
    world = Namespace(get_actors=lambda: actors)
    spec = Namespace(actors=({"actor_id": "front_blocker"},))

    assert _cleanup_stale_scenario_actors(world, spec) == 2
    assert destroyed == ["acceptance84:old_blocker", "front_blocker"]


def test_clean_world_on_start_is_explicit_and_opt_in() -> None:
    assert _scenario_clean_world_on_start(None) is False
    assert _scenario_clean_world_on_start(Namespace(extensions={})) is False
    assert _scenario_clean_world_on_start(
        Namespace(extensions={"clean_world_on_start": True})
    ) is True


def test_route_recovery_hold_reference_is_forward_and_stationary() -> None:
    vehicle = RuntimeVehicleState(
        frame=1,
        sim_time_s=0.05,
        speed_mps=4.0,
        x_m=10.0,
        y_m=20.0,
        z_m=0.0,
        yaw_deg=90.0,
        lane_id="3",
    )

    route = _route_recovery_hold_reference(vehicle)

    assert route.points_xy_m[0] == pytest.approx((10.0, 20.0))
    assert route.points_xy_m[-1] == pytest.approx((10.0, 32.0))
    assert route.target_speed_mps == 0.0
    assert route.metadata["purpose"] == "safe_replan_hold"


def test_local_reference_at_global_end_is_not_refreshed_every_frame() -> None:
    global_reference = Namespace(route_id="mission-1")
    global_route = Namespace(reference=global_reference, total_length_m=75.0)
    local = Namespace(
        metadata={
            "global_route_id": "mission-1",
            "global_s_start_m": 10.0,
            "global_s_end_m": 75.0,
        },
    )

    assert _route_local_reference_needs_refresh(
        None, global_route, 20.0, 20.0,
    ) is True
    assert _route_local_reference_needs_refresh(
        local, global_route, 60.0, 20.0,
    ) is False
    local.metadata["global_s_end_m"] = 70.0
    assert _route_local_reference_needs_refresh(
        local, global_route, 55.0, 20.0,
    ) is True
    with pytest.raises(TypeError, match="clean_world_on_start"):
        _scenario_clean_world_on_start(
            Namespace(extensions={"clean_world_on_start": "yes"})
        )


def test_planner_closes_only_the_lidar_observed_adjacent_gap() -> None:
    left_lane = Namespace(lane_type="Driving")
    right_lane = Namespace(lane_type="Driving")
    waypoint = Namespace(
        lane_id=-2,
        lane_type="Driving",
        is_junction=False,
        get_left_lane=lambda: left_lane,
        get_right_lane=lambda: right_lane,
        next=lambda _distance: (),
    )
    world_map = Namespace(get_waypoint=lambda *_args, **_kwargs: waypoint)
    ego = Namespace(get_location=lambda: object())
    left_obstacle = DetectedObject(
        0, "obstacle", 1.0, (0.10, 0.30, 0.30, 0.80), 16.0,
    )

    state = _planner_runtime_state(
        world_map,
        ego,
        PerceptionFrame(1, 0.05, detected_objects=(left_obstacle,)),
        Namespace(points_xy_m=((0.0, 0.0), (20.0, 0.0))),
    )

    assert state["left_gap_safe"] is False
    assert state["right_gap_safe"] is True


def test_front_gap_expected_value_is_a_hard_completion_contract() -> None:
    from integration.scenario_execution import ScenarioSpec

    path = Path(__file__).resolve().parents[2] / "scenarios" / "regression" / "REG_007_advanced_front_vehicle.json"
    spec = ScenarioSpec.load(path)
    assert _minimum_gap_contract_completed(spec, 2.49) is False
    assert _minimum_gap_contract_completed(spec, 2.5) is True
    assert _minimum_gap_contract_completed(None, 10.0) is None


def test_intentional_invalid_qwen_probe_completes_on_safe_fail_closed_stop() -> None:
    spec = ScenarioSpec.load(
        Path(__file__).resolve().parents[2]
        / "scenarios" / "acceptance_suite" / "supplemental" / "system"
        / "SYS_02_qwen_invalid_token.json"
    )
    assert _intentional_qwen_failure_completed(
        spec, frames=spec.frame_count, final_speed_mps=0.0, collision_seen=False,
    ) is True
    assert _intentional_qwen_failure_completed(
        spec, frames=spec.frame_count, final_speed_mps=1.0, collision_seen=False,
    ) is False


def test_declared_stop_from_rest_does_not_require_artificial_motion() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "scenarios" / "acceptance_suite" / "supplemental" / "advanced"
        / "SUP_A12_double_static_obstacle_stop.json"
    )
    spec = ScenarioSpec.load(path)

    assert _declared_scenario_runtime_completed(
        spec,
        frames=spec.frame_count,
        final_speed_mps=0.0,
        collision_seen=False,
        command_finished=True,
        safety_reasons=set(),
    ) is True
    assert _declared_scenario_runtime_completed(
        spec,
        frames=spec.frame_count,
        final_speed_mps=0.0,
        collision_seen=False,
        command_finished=True,
        safety_reasons={"WATCHDOG_ALERT"},
    ) is False
    assert _intentional_qwen_failure_completed(
        None, frames=1, final_speed_mps=0.0, collision_seen=False,
    ) is None


def test_load_command_rejects_non_object_json_before_runtime_logging(tmp_path) -> None:
    path = tmp_path / "command.json"
    path.write_text("[]", encoding="utf-8")
    args = Namespace(command_json=str(path), audio=None, test_command_ttl_s=None)
    with pytest.raises(TypeError, match="JSON root must be an object"):
        _load_command(args)


def test_load_command_accepts_qwen_high_level_json(tmp_path) -> None:
    path = tmp_path / "qwen_command.json"
    path.write_text(
        """{
          "schema_version": "1.0",
          "command_id": "qwen-keep-lane",
          "action": "KEEP_LANE",
          "confidence": 0.92,
          "reason": "clear lane",
          "visual_valid": true,
          "valid_duration_s": 3.0
        }""",
        encoding="utf-8",
    )
    args = Namespace(command_json=str(path), audio=None, test_command_ttl_s=None)
    command = _load_command(args)

    assert command["intent"] == "KEEP_LANE"
    assert command["source_text"] == "KEEP_LANE: clear lane"


def test_sensor_warmup_retries_until_two_consecutive_aligned_frames_arrive() -> None:
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
    assert bridge.calls == 3


def test_sensor_warmup_resets_streak_after_pipeline_bubble() -> None:
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
            if self.calls == 2:
                raise PerceptionTimeoutError("pipeline bubble")
            return object()

    session = Session()
    bridge = Bridge()
    _warm_up_sensor_bridge(session, World(session), bridge, attempts=4,
                           tick_timeout_s=60.0, sensor_timeout_s=0.5)
    assert bridge.calls == 4


def test_sensor_warmup_consumes_configured_frames_after_early_stability() -> None:
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
            return object()

    session = Session()
    bridge = Bridge()
    _warm_up_sensor_bridge(session, World(session), bridge, attempts=5,
                           tick_timeout_s=60.0, sensor_timeout_s=0.5)
    assert bridge.calls == 5


def test_vehicle_speed_ignores_vertical_spawn_settling() -> None:
    velocity = Namespace(x=3.0, y=4.0, z=-9.8)
    assert _speed_mps(velocity) == pytest.approx(5.0)


def test_acceptance_lateral_tuning_limits_steer_and_rate() -> None:
    controller = _acceptance_lateral_controller()
    assert controller.params.steer_sign == 1.0
    assert controller.params.max_steer == pytest.approx(0.60)
    assert controller.params.max_steer_delta_per_step == pytest.approx(0.04)
    assert controller.params.min_lookahead_m >= 2.5
    assert controller.params.nearest_search_window == 2
    assert controller.params.route_reacquire_search_window == 50


def test_map_warmup_restores_async_mode_left_by_interrupted_run() -> None:
    settings = Namespace(synchronous_mode=True, fixed_delta_seconds=0.05)

    class World:
        applied = None
        waited = None

        def get_settings(self):
            return settings

        def apply_settings(self, value):
            self.applied = value

        def wait_for_tick(self, timeout_s):
            self.waited = timeout_s

    world = World()
    _warm_up_loaded_map(world, 2.0)

    assert world.applied.synchronous_mode is False
    assert world.applied.fixed_delta_seconds is None
    assert world.waited == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    [
        ("lateral_B/B04_smooth_left_curve.json", "FOLLOW_LEFT"),
        ("lateral_B/B05_smooth_right_curve.json", "FOLLOW_RIGHT"),
        ("regression/REG_003_basic_clear_seed2.json", "FOLLOW_RIGHT"),
        ("regression/REG_001_basic_clear_seed0.json", "FOLLOW"),
        ("qwen_fullchain/QWF_01_turn_then_speed.json", "TURN_RIGHT"),
        ("qwen_fullchain/QWF_02_lane_change_then_speed.json", "CHANGE_LANE_LEFT"),
        ("qwen_faults/QWX_06_pedestrian_safety_override.json", "CHANGE_LANE_LEFT"),
        ("acceptance_suite/supplemental/advanced/SUP_A16_detour_right_static_vehicle.json", "CHANGE_LANE_RIGHT"),
    ],
)
def test_scenario_maneuver_preserves_declared_curve_direction(relative_path, expected):
    from integration.scenario_execution import ScenarioSpec

    root = Path(__file__).resolve().parents[2] / "scenarios"
    assert _scenario_maneuver(ScenarioSpec.load(root / relative_path)) == expected


def test_sup_a16_detour_reaches_adjacent_lane_before_static_vehicle() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(
        root / "acceptance_suite/supplemental/advanced/SUP_A16_detour_right_static_vehicle.json"
    )
    full_offset_x = next(x for x, y in spec.local_route_xy_m if abs(y) >= 3.0)
    static_vehicle_x = float(spec.actors[0]["spawn"]["x"])

    assert full_offset_x <= static_vehicle_x - 15.0
    assert spec.extensions["route_anchor_spawn_index"] == 134
    assert max(y for _, y in spec.local_route_xy_m) > 3.0


def test_acc_a05_uses_verified_clear_lane_change_anchor() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(
        root / "acceptance_suite/advanced/ACC_A05_lane_change_left.json"
    )

    assert spec.extensions["route_anchor_spawn_index"] == 135


def test_acc_a06_declares_left_avoidance_on_verified_multilane_anchor() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(
        root / "acceptance_suite/advanced/ACC_A06_obstacle_detour_return.json"
    )

    assert spec.commands[0].envelope["intent"] == "AVOID_OBSTACLE"
    assert spec.commands[0].envelope["parameters"]["direction"] == "LEFT"
    assert spec.extensions["route_anchor_spawn_index"] == 135
    assert spec.expected["must_finish_route"] is True
    assert _scenario_maneuver(spec) == "CHANGE_LANE_LEFT"
    full_offset_x = next(x for x, y in spec.local_route_xy_m if y <= -3.0)
    static_vehicle_x = float(spec.actors[0]["spawn"]["x"])
    assert full_offset_x <= static_vehicle_x - 15.0
    assert min(y for _, y in spec.local_route_xy_m) < -3.0


def test_cx03_detour_uses_verified_lane_and_clears_bicycle_before_passing() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(
        root / "acceptance_suite/complex/CX03_construction_bicycle_detour.json"
    )

    assert spec.commands[0].envelope["intent"] == "AVOID_OBSTACLE"
    assert spec.commands[0].envelope["parameters"]["direction"] == "LEFT"
    assert spec.extensions["route_anchor_spawn_index"] == 135
    assert spec.expected["must_finish_route"] is True
    assert _scenario_maneuver(spec) == "CHANGE_LANE_LEFT"
    full_offset_x = next(x for x, y in spec.local_route_xy_m if y <= -3.0)
    bicycle_x = float(next(
        actor["spawn"]["x"] for actor in spec.actors
        if actor["actor_id"] == "bicycle_lead"
    ))
    assert full_offset_x <= bicycle_x - 10.0


def test_acc_c01_keep_lane_route_stays_in_same_town03_lane_corridor() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(
        root / "acceptance_suite/challenge/ACC_C01_heavy_rain_fog.json"
    )

    assert spec.commands[0].envelope["intent"] == "KEEP_LANE"
    assert max(abs(y) for _, y in spec.local_route_xy_m) <= 1.5
    assert spec.local_route_xy_m[-1][1] == pytest.approx(1.27, abs=0.05)


def test_var_c01_keep_lane_route_stays_in_same_town03_lane_corridor() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(
        root / "acceptance_suite/variants/VAR_C01_night_rain.json"
    )

    assert spec.commands[0].envelope["intent"] == "KEEP_LANE"
    assert max(abs(y) for _, y in spec.local_route_xy_m) <= 1.5
    assert spec.local_route_xy_m[-1][1] == pytest.approx(1.27, abs=0.05)


def test_acc_b03_oracle_matches_its_two_declared_set_speed_commands() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(root / "acceptance_suite/basic/ACC_B03_slow_to_10.json")

    assert [item.envelope["intent"] for item in spec.commands] == ["SET_SPEED", "SET_SPEED"]
    assert spec.extensions["oracle"] == {"expected_behaviors": ["SET_SPEED"]}


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
