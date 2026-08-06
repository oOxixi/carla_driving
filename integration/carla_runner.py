"""CARLA 0.9.16 acceptance runner with one synchronous tick/control apply.

The default path consumes frame-aligned RGB/LiDAR and event sensors. Explicit
``world`` and ``virtual`` perception modes remain test-only diagnostic paths.
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
import time
import zipfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from car_control_A import CarlaSession, ControlOutput, RuntimeVehicleState
from car_control_A.maneuver_fsm import ManeuverFSM, ManeuverUpdate, TERMINAL_STATES
from car_control_A.high_level_command import HighLevelCommandAdapter, is_high_level_command
from car_control_A.routing import RouteReference
from car_control_A.watchdog import RuntimeWatchdog
from car_control_B.pure_pursuit import PurePursuitController, PurePursuitParams
from car_control_C import ConservativeSensorFusion, SafetyStateParameters
from car_control_D import SafetyConfig, SafetySupervisor
from qwen_service.client import QwenServiceClient
from runtime import (
    CompiledManeuverPlan,
    CompiledPlanStep,
    OrchestratorConfig,
    PipelineOrchestrator,
)

from .carla_perception import (
    CarlaPerceptionBridge,
    EventLedger,
    PerceptionAcquisitionError,
    actor_speed_limit_mps,
    attach_default_sensors,
    attach_event_sensors,
    lane_metrics,
    sensor_specs_for_profile,
    traffic_light_and_stop_distance,
)
from .contracts import DetectedObject, PerceptionFrame
from .qwen_async import AsyncQwenDecisionBridge
from .qwen_boundary import QwenInputContext
from .qwen_remote_backend import OpenAICompatibleQwenVLBackend
from .qwen_vl_adapter import StrictQwenVLAdapter
from .live_voice import LiveVoiceConfig, LiveVoiceSource
from .route_planner import (
    build_lane_change_route_reference,
    build_route_reference,
    command_turn_direction,
    select_topology_route_anchor,
    warm_heading_waypoint_cache,
)
from .qwen_image_stager import QwenImageStager
from .qwen_fault_injection import ScenarioQwenFaultInjector
from .qwen_scenario_monitor import QwenScenarioMonitor
from .runtime_loop import ControlRuntime
from .rgb_detector import OnnxYoloDetector, carla_rgb_array
from .scenario_execution import (
    CommandTimeline,
    ScenarioSpec,
    resolve_scenario_command,
    scenario_trigger_satisfied,
)
from .scenario_evidence import FrameTiming, ScenarioEvidenceRecorder
from .scenario_extensions import ScenarioExtensionRuntime
from .second_group_runtime import CanonicalRuntimeBridge


@dataclass(frozen=True, slots=True)
class _DeferredCommand:
    envelope: dict[str, object]
    received_ns: int
    origin: str
    audio_duration_s: float | None = None


def _compiled_plan_from_payload(payload: Mapping[str, Any]) -> CompiledManeuverPlan:
    """Rebuild the typed A/FSM contract from an orchestrator audit payload."""
    if not isinstance(payload, Mapping):
        raise TypeError("compiled plan payload must be a mapping")
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("compiled plan payload must contain steps")
    steps = tuple(
        CompiledPlanStep(
            step_id=str(step["step_id"]),
            source_step_id=str(step["source_step_id"]),
            behavior=str(step["behavior"]),
            target=dict(step["target"]),
            preconditions=tuple(str(item) for item in step["preconditions"]),
            completion=dict(step["completion"]),
            timeout_s=float(step["timeout_s"]),
            on_failure=str(step["on_failure"]),
        )
        for step in raw_steps
        if isinstance(step, Mapping)
    )
    if len(steps) != len(raw_steps):
        raise TypeError("every compiled plan step must be a mapping")
    return CompiledManeuverPlan(
        command_id=str(payload["command_id"]),
        plan_id=str(payload["plan_id"]),
        steps=steps,
        replan_conditions=tuple(str(item) for item in payload.get("replan_conditions", ())),
        valid_until_ns=int(payload["valid_until_ns"]),
    )


def _maneuver_target_visible(
    step: CompiledPlanStep | None,
    scene: PerceptionFrame,
) -> bool:
    """Match a legacy planner target by semantic class, not any detection."""
    if step is None:
        return False
    target_id = str(step.target.get("target_id") or "")
    if not target_id.startswith("legacy-"):
        return bool(scene.detected_objects) if target_id else False
    target_class = target_id.removeprefix("legacy-").rsplit("-", 1)[0]
    aliases = {
        "vehicle": {"car", "truck", "bus", "vehicle"},
        "pedestrian": {"person", "pedestrian"},
        "cyclist": {"bicycle", "motorcycle", "cyclist"},
        "obstacle": {"obstacle"},
    }
    accepted = aliases.get(target_class, {target_class})
    return any(item.class_name.lower() in accepted for item in scene.detected_objects)


def _record_maneuver_update(
    update: ManeuverUpdate,
    *,
    monitor: QwenScenarioMonitor | None,
    recorder: ScenarioEvidenceRecorder | None,
) -> None:
    """Persist step/terminal events and feed only plan-owned terminals to acceptance."""
    for event in update.events:
        payload = asdict(event)
        print(json.dumps({"record_type": event.event_type, **payload}, ensure_ascii=False), flush=True)
        if recorder is not None:
            recorder.record_canonical_routing(
                phase="MANEUVER_EVENT",
                command_id=event.command_id,
                payload=payload,
            )
        if event.event_type == "qwen_replan_triggered" and monitor is not None:
            monitor.record_replan()
        if event.event_type == "qwen_terminal":
            if monitor is not None:
                monitor.record_terminal(
                    event.state,
                    command_id=event.command_id,
                    reason_code=event.reason_code,
                )
            if recorder is not None and event.state in {
                "SUCCEEDED", "FAILED", "SAFETY_OVERRIDE",
            }:
                recorder.record_feedback({
                    "command_id": event.command_id,
                    "status": event.state,
                    "completed_at_s": event.now_s,
                    "detail": event.reason_code,
                })


def _note_extension_terminal(
    runtime: ScenarioExtensionRuntime | None,
    feedback: Mapping[str, object] | object,
) -> None:
    if runtime is None:
        return
    status = (
        feedback.get("status") if isinstance(feedback, Mapping)
        else getattr(feedback, "status", None)
    )
    normalized = str(getattr(status, "value", status)).upper()
    if normalized not in {
        "SUCCEEDED", "FAILED", "REJECTED", "EXPIRED", "TIMED_OUT",
        "SAFETY_OVERRIDE",
    }:
        return
    command_id = (
        feedback.get("command_id") if isinstance(feedback, Mapping)
        else getattr(feedback, "command_id", "")
    )
    runtime.note_terminal(str(command_id), status)


def _speed_mps(vector: Any) -> float:
    # Longitudinal control consumes ground speed. Including vertical spawn
    # settling makes a stationary vehicle appear to accelerate under gravity.
    return math.hypot(vector.x, vector.y)


def _acceptance_lateral_controller() -> PurePursuitController:
    """Conservative CARLA tuning that cannot snap directly to full steering."""
    return PurePursuitController(PurePursuitParams(
        base_lookahead_m=2.5,
        min_lookahead_m=2.5,
        max_lookahead_m=8.0,
        speed_gain_s=0.45,
        max_steer=0.60,
        max_steer_delta_per_step=0.04,
        # Calibrated against a CARLA 0.9.16 Model 3 closed-loop route run.
        steer_sign=1.0,
    ))


def _follow_ego_spectator(world: Any, ego: Any, carla: Any) -> None:
    """Keep the graphical spectator behind the ego during live demonstrations."""
    transform = ego.get_transform()
    location = transform.location
    forward = transform.get_forward_vector()
    world.get_spectator().set_transform(carla.Transform(
        carla.Location(
            x=location.x - 8.0 * forward.x,
            y=location.y - 8.0 * forward.y,
            z=location.z + 4.0,
        ),
        carla.Rotation(pitch=-15.0, yaw=transform.rotation.yaw),
    ))


def _scenario_maneuver(spec: ScenarioSpec) -> str:
    for item in spec.commands:
        intent = str(item.envelope.get("intent", "")).upper()
        if intent in {"TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT"}:
            return intent
        if intent in {"TURN", "CHANGE_LANE"}:
            parameters = item.envelope.get("parameters", {})
            direction = (
                str(parameters.get("direction", "")).upper()
                if isinstance(parameters, Mapping) else ""
            )
            if direction in {"LEFT", "RIGHT"}:
                return f"{intent}_{direction}"
        if intent == "AVOID_OBSTACLE":
            # Pick a straight multi-lane topology. The active route remains in
            # the current lane until a validated plan selects the avoid side.
            return "CHANGE_LANE_LEFT"
    start_x, start_y = spec.local_route_xy_m[0]
    end_x, end_y = spec.local_route_xy_m[-1]
    forward_m = abs(end_x - start_x)
    lateral_m = end_y - start_y
    if forward_m > 1.0 and abs(lateral_m) >= 0.12 * forward_m:
        # Scenario files use the conventional positive-left lateral axis;
        # CARLA yaw is negative for a physical left curve.
        return "FOLLOW_LEFT" if lateral_m > 0.0 else "FOLLOW_RIGHT"
    return "FOLLOW"


def _scenario_route_distance_m(spec: ScenarioSpec) -> float:
    return sum(
        math.dist(first, second)
        for first, second in zip(spec.local_route_xy_m, spec.local_route_xy_m[1:])
    )


def _traffic_light_stop_points(world: Any) -> tuple[tuple[float, float], ...]:
    """Collect signal stop locations so deterministic routes can avoid them."""
    actors = world.get_actors()
    lights = actors.filter("traffic.traffic_light*") if callable(getattr(actors, "filter", None)) else ()
    points: list[tuple[float, float]] = []
    for light in lights:
        getter = getattr(light, "get_stop_waypoints", None)
        if not callable(getter):
            continue
        for waypoint in getter() or ():
            location = waypoint.transform.location
            points.append((float(location.x), float(location.y)))
    return tuple(points)


def _vehicle_state(ego: Any, frame: int, sim_time_s: float, world_map: Any) -> RuntimeVehicleState:
    transform, velocity = ego.get_transform(), ego.get_velocity()
    location = transform.location
    waypoint = world_map.get_waypoint(location, project_to_road=True)
    return RuntimeVehicleState(frame, sim_time_s, _speed_mps(velocity), location.x, location.y, location.z,
                               transform.rotation.yaw, str(waypoint.lane_id if waypoint else "0"))


def _planner_runtime_state(
    world_map: Any,
    ego: Any,
    scene: PerceptionFrame,
    route: RouteReference,
) -> dict[str, object]:
    """Expose only deterministic lane/route facts needed by Planner V2."""
    waypoint = world_map.get_waypoint(ego.get_location(), project_to_road=True)
    left = waypoint.get_left_lane() if waypoint is not None else None
    right = waypoint.get_right_lane() if waypoint is not None else None

    def driving(candidate: Any | None) -> bool:
        if candidate is None:
            return False
        return str(getattr(candidate, "lane_type", "Driving")).split(".")[-1].upper() == "DRIVING"

    left_exists, right_exists = driving(left), driving(right)
    available = ["CURRENT"]
    if left_exists:
        available.append("LEFT_ADJACENT")
    if right_exists:
        available.append("RIGHT_ADJACENT")
    close_visual_object = any(
        item.distance_m is not None and item.distance_m < 12.0
        for item in scene.detected_objects
    )
    intersection_ahead = bool(getattr(waypoint, "is_junction", False))
    if waypoint is not None and not intersection_ahead:
        frontier = (waypoint,)
        for _ in range(10):
            frontier = tuple(
                next_waypoint
                for current in frontier
                for next_waypoint in (current.next(2.0) or ())
            )
            if any(bool(getattr(item, "is_junction", False)) for item in frontier):
                intersection_ahead = True
                break
            if not frontier:
                break
    return {
        "available_lanes": available,
        "left_lane_exists": left_exists,
        "right_lane_exists": right_exists,
        # The legacy detector has no side-specific tracker.  A nearby object
        # therefore closes both gaps; this is conservative and never grants a
        # lane change based on missing lateral evidence.
        "left_gap_safe": left_exists and not close_visual_object,
        "right_gap_safe": right_exists and not close_visual_object,
        "route_available": len(route.points_xy_m) >= 2,
        "intersection_ahead": intersection_ahead,
        "stop_line_clear": (
            scene.traffic_light not in {"RED", "YELLOW"}
            or scene.distance_to_stop_line_m is None
        ),
        "current_lane": str(getattr(waypoint, "lane_id", "unknown")),
    }


def _apply_compiled_plan_route(
    compiled_plan: Mapping[str, Any],
    *,
    world_map: Any,
    ego: Any,
    current_route: RouteReference,
    requested_speed_mps: float,
    distance_m: float,
    prevalidated_maneuver_route: RouteReference | None = None,
) -> tuple[RouteReference, float, str | None]:
    """Apply validated route semantics; B still generates the actual reference."""
    steps = compiled_plan.get("steps")
    if not isinstance(steps, list):
        raise ValueError("compiled plan steps must be a list")
    target_speed = float(requested_speed_mps)
    route_behavior: str | None = None
    for step in steps:
        if not isinstance(step, Mapping):
            raise ValueError("compiled plan step must be an object")
        behavior = str(step.get("behavior", "")).upper()
        target = step.get("target", {})
        if isinstance(target, Mapping) and target.get("target_speed_mps") is not None:
            target_speed = float(target["target_speed_mps"])
        if route_behavior is None and behavior in {
            "TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT",
        }:
            route_behavior = behavior
    if route_behavior is None:
        return replace(current_route, target_speed_mps=target_speed), target_speed, None
    if prevalidated_maneuver_route is not None:
        return (
            replace(prevalidated_maneuver_route, target_speed_mps=target_speed),
            target_speed,
            route_behavior,
        )
    if route_behavior.startswith("TURN_"):
        route = build_route_reference(
            world_map,
            ego,
            target_speed,
            turn_direction=route_behavior.rsplit("_", 1)[-1],
            distance_m=distance_m,
        )
    else:
        route = build_lane_change_route_reference(
            world_map,
            ego,
            target_speed,
            direction=route_behavior.rsplit("_", 1)[-1],
            distance_m=min(distance_m, 80.0),
        )
    return route, target_speed, route_behavior


def _scene_from_world(
    world_map: Any,
    ego: Any,
    frame: int,
    sim_time_s: float,
    *,
    route: RouteReference | None = None,
    scenario_lead: Any | None = None,
    scenario_vehicles: Sequence[Any] = (),
    events: EventLedger | None = None,
) -> tuple[PerceptionFrame, dict[str, str]]:
    """Build scene truth; synthetic scenarios may nominate their only lead actor.

    Acceptance scenarios must not accidentally follow an unrelated vehicle
    left by another CARLA client, so they never select the globally nearest
    actor when a scenario-owned lead is supplied (or explicitly absent).
    """
    ego_location = ego.get_location()
    sources: dict[str, str] = {}
    if scenario_lead is not None and getattr(scenario_lead, "is_alive", False):
        distance, lead_speed = (scenario_lead.get_location().distance(ego_location),
                                _speed_mps(scenario_lead.get_velocity()))
        sources["lead_distance_m"] = "CARLA_SCENARIO_ACTOR_DISTANCE"
        sources["lead_speed_mps"] = "CARLA_SCENARIO_ACTOR_VELOCITY"
    else:
        distance = lead_speed = None
    traffic_light, stop_distance, traffic_source = traffic_light_and_stop_distance(ego)
    sources["traffic_light"] = traffic_source
    if stop_distance is not None:
        sources["distance_to_stop_line_m"] = traffic_source
    speed_limit = actor_speed_limit_mps(ego)
    if speed_limit is not None:
        sources["speed_limit_mps"] = "CARLA_MAP_SPEED_LIMIT"
    lane_offset, route_deviation = lane_metrics(world_map, ego, route)
    if lane_offset is not None:
        sources["lane_offset_m"] = "CARLA_MAP_WAYPOINT"
    if route_deviation is not None:
        sources["route_deviation_m"] = (
            "ROUTE_REFERENCE_NEAREST_SEGMENT" if route is not None else "CARLA_MAP_WAYPOINT"
        )
    if events is None:
        collision = lane_invasion = False
        sources["collision"] = "UNOBSERVED_NO_EVENT_SENSOR"
        sources["lane_invasion"] = "UNOBSERVED_NO_EVENT_SENSOR"
    else:
        collision, lane_invasion = events.flags_for_frame(frame)
        sources["collision"] = "CARLA_COLLISION_EVENT"
        sources["lane_invasion"] = "CARLA_LANE_INVASION_EVENT"
    red_light_violation = (
        traffic_light == "RED" and stop_distance is not None and stop_distance <= 0.5
        and _speed_mps(ego.get_velocity()) > 0.5
    )
    sources["red_light_violation"] = (
        "CARLA_RED_LIGHT_STOP_LINE_CROSSING"
        if stop_distance is not None
        else "UNOBSERVED_NO_STOP_LINE_DISTANCE"
    )
    detections = (
        _world_vehicle_detections(ego, scenario_vehicles)
        if scenario_vehicles else ()
    )
    if detections:
        sources["detected_objects"] = "CARLA_SCENARIO_ACTOR_DEBUG_TRUTH"
    scene = PerceptionFrame(
        frame,
        sim_time_s,
        distance,
        lead_speed,
        traffic_light=traffic_light,
        distance_to_stop_line_m=stop_distance,
        speed_limit_mps=speed_limit,
        lane_offset_m=lane_offset,
        route_deviation_m=route_deviation,
        collision=collision,
        red_light_violation=red_light_violation,
        lane_invasion=lane_invasion,
        detected_objects=detections,
    )
    return scene, sources


def _world_vehicle_detections(
    ego: Any,
    vehicles: Sequence[Any],
) -> tuple[DetectedObject, ...]:
    """Expose scenario-owned actors only in the explicit world debug mode."""
    if isinstance(vehicles, (str, bytes)):
        raise TypeError("vehicles must be an actor sequence")
    transform = ego.get_transform()
    origin = transform.location
    forward = transform.get_forward_vector()
    right = transform.get_right_vector()
    detections: list[tuple[float, DetectedObject]] = []
    for actor in vehicles:
        if actor is ego or not getattr(actor, "is_alive", False):
            continue
        location = actor.get_location()
        dx = float(location.x) - float(origin.x)
        dy = float(location.y) - float(origin.y)
        longitudinal = dx * float(forward.x) + dy * float(forward.y)
        lateral = dx * float(right.x) + dy * float(right.y)
        distance = math.hypot(dx, dy)
        if longitudinal < -2.0 or distance > 80.0:
            continue
        center_x = max(0.1, min(0.9, 0.5 + lateral / max(10.0, 2.0 * distance)))
        half_width = max(0.025, min(0.12, 1.2 / max(distance, 5.0)))
        detections.append((distance, DetectedObject(
            2,
            "car",
            1.0,
            (
                max(0.0, center_x - half_width), 0.35,
                min(1.0, center_x + half_width), 0.75,
            ),
            distance,
        )))
    detections.sort(key=lambda item: item[0])
    return tuple(item for _distance, item in detections)


def _spawn_static_lead(session: CarlaSession, world: Any, world_map: Any, ego: Any, blueprint: Any,
                       distance_m: float) -> Any:
    """Spawn a deterministic stationary lead vehicle in ego's current lane."""
    ego_transform = ego.get_transform()
    forward = ego_transform.get_forward_vector()
    # Place directly along ego's current forward axis. Projecting the candidate
    # through a Town05 waypoint can jump to a parallel road hundreds of metres
    # away near junctions, invalidating a following scenario.
    for offset_m in range(0, 31, 2):
        candidate_distance = distance_m + offset_m
        transform = ego.get_transform()
        origin = ego_transform.location
        transform.location = type(origin)(
            x=origin.x + forward.x * candidate_distance,
            y=origin.y + forward.y * candidate_distance,
            z=origin.z + 0.5,
        )
        lead = world.try_spawn_actor(blueprint, transform)
        if lead is None:
            continue
        lead = session.track_actor(lead)
        lead.set_simulate_physics(False)
        actual_distance = lead.get_location().distance(ego.get_location())
        print(f"lead vehicle placed at {actual_distance:.1f} m")
        return lead
    raise RuntimeError("cannot place lead vehicle: all forward candidate positions are occupied")


def _scenario_actor(spec: ScenarioSpec | None, actor_type: str) -> dict[str, object] | None:
    """Return the unique configured actor of ``actor_type``.

    Submission scenarios deliberately support one owned lead vehicle and one
    owned traffic light.  Failing on duplicates is safer than silently binding
    perception evidence to an arbitrary actor.
    """
    matches = _scenario_actors(spec, actor_type)
    if len(matches) > 1:
        raise ValueError(
            f"scenario {spec.scenario_id!r} declares multiple {actor_type!r} actors"
        )
    return matches[0] if matches else None


def _scenario_actors(
    spec: ScenarioSpec | None,
    actor_type: str,
) -> tuple[dict[str, object], ...]:
    """Return all declared actors of one exact type.

    ``_scenario_actor`` remains deliberately strict for singleton resources
    such as the traffic light selected for a stop-line contract.  Dynamic
    traffic, however, is naturally plural; callers that own it must use this
    collection rather than silently binding to an arbitrary vehicle.
    """
    if spec is None:
        return ()
    expected = actor_type.strip().lower()
    return tuple(
        actor for actor in spec.actors
        if str(actor.get("type", "")).strip().lower() == expected
    )


def _scenario_walkers(spec: ScenarioSpec | None) -> tuple[dict[str, object], ...]:
    """Return all walker/pedestrian declarations, preserving scenario order."""
    if spec is None:
        return ()
    return tuple(
        actor for actor in spec.actors
        if str(actor.get("type", "")).strip().lower().startswith("walker")
    )


def _scenario_static_props(spec: ScenarioSpec | None) -> tuple[dict[str, object], ...]:
    """Return declarative static obstacles used for construction/occlusion tests."""
    if spec is None:
        return ()
    return tuple(
        actor for actor in spec.actors
        if str(actor.get("type", "")).strip().lower() in {
            "static.prop", "obstacle", "construction",
        }
    )


def _scenario_local_transform(
    carla_api: Any,
    anchor_transform: Any,
    spawn: Mapping[str, object],
    *,
    forward_offset_m: float = 0.0,
) -> Any:
    """Convert a scenario-local actor pose to a CARLA world transform."""
    local_x = float(spawn.get("x", 0.0)) + float(forward_offset_m)
    local_y = float(spawn.get("y", 0.0))
    local_z = float(spawn.get("z", 0.5))
    local_yaw = float(spawn.get("yaw_deg", 0.0))
    yaw_rad = math.radians(float(anchor_transform.rotation.yaw))
    cos_yaw, sin_yaw = math.cos(yaw_rad), math.sin(yaw_rad)
    origin = anchor_transform.location
    return carla_api.Transform(
        carla_api.Location(
            x=float(origin.x) + local_x * cos_yaw - local_y * sin_yaw,
            y=float(origin.y) + local_x * sin_yaw + local_y * cos_yaw,
            z=float(origin.z) + max(0.0, local_z - 0.5),
        ),
        carla_api.Rotation(
            pitch=float(getattr(anchor_transform.rotation, "pitch", 0.0)),
            yaw=float(anchor_transform.rotation.yaw) + local_yaw,
            roll=float(getattr(anchor_transform.rotation, "roll", 0.0)),
        ),
    )


def _scenario_vehicle_speed_mps(
    actor_spec: Mapping[str, object],
    elapsed_s: float,
) -> float:
    behavior = actor_spec.get("behavior", {})
    if not isinstance(behavior, Mapping):
        raise TypeError("scenario vehicle behavior must be an object")
    initial = max(0.0, float(behavior.get("initial_speed_mps", 0.0)))
    brake_at = float(behavior.get("brake_at_s", math.inf))
    target = max(0.0, float(behavior.get("target_speed_mps", initial)))
    return initial if float(elapsed_s) < brake_at else target


def _signed_forward_speed_mps(actor: Any) -> float:
    """Return actor velocity projected onto its current forward direction."""
    velocity = actor.get_velocity()
    forward = actor.get_transform().get_forward_vector()
    return (
        float(velocity.x) * float(forward.x)
        + float(velocity.y) * float(forward.y)
        + float(velocity.z) * float(forward.z)
    )


def _spawn_scenario_vehicle(
    session: CarlaSession,
    world: Any,
    carla_api: Any,
    ego: Any,
    fallback_blueprint: Any,
    actor_spec: Mapping[str, object],
) -> Any:
    """Spawn a real CARLA lead vehicle from a scenario actor declaration."""
    spawn = actor_spec.get("spawn", {})
    if not isinstance(spawn, Mapping):
        raise TypeError("scenario vehicle spawn must be an object")
    library = world.get_blueprint_library()
    blueprint_id = actor_spec.get("blueprint_id")
    if isinstance(blueprint_id, str) and blueprint_id:
        blueprint = library.find(blueprint_id)
    else:
        fallback_id = getattr(fallback_blueprint, "id", None)
        blueprint = library.find(fallback_id) if fallback_id and callable(getattr(library, "find", None)) else fallback_blueprint
    if blueprint is None:
        raise LookupError(f"scenario vehicle blueprint not found: {blueprint_id!r}")
    if callable(getattr(blueprint, "has_attribute", None)) and blueprint.has_attribute("role_name"):
        blueprint.set_attribute(
            "role_name",
            str(actor_spec.get("actor_id", "scenario_lead")),
        )

    ego_transform = ego.get_transform()
    world_map = world.get_map()
    lead = None
    for offset_m in (0.0, 2.0, 4.0, 6.0):
        transform = _scenario_local_transform(
            carla_api, ego_transform, spawn, forward_offset_m=offset_m,
        )
        # The ego has already settled onto the road before scenario actors are
        # created, so its transform Z is near zero.  Preserve the declarative
        # 0.5 m spawn clearance relative to the road surface; otherwise CARLA
        # rejects the vehicle because its collision box intersects the road.
        road_waypoint = world_map.get_waypoint(
            transform.location, project_to_road=True,
        )
        if road_waypoint is not None:
            road_location = road_waypoint.transform.location
            transform.location.z = max(
                float(transform.location.z), float(road_location.z) + 0.5,
            )
        lead = world.try_spawn_actor(blueprint, transform)
        if lead is not None:
            break
    if lead is None:
        raise RuntimeError("cannot spawn configured scenario lead vehicle")

    lead = session.track_actor(lead)
    set_physics = getattr(lead, "set_simulate_physics", None)
    if callable(set_physics):
        set_physics(True)
    set_autopilot = getattr(lead, "set_autopilot", None)
    if callable(set_autopilot):
        set_autopilot(False)
    desired_speed = _scenario_vehicle_speed_mps(actor_spec, 0.0)
    set_velocity = getattr(lead, "set_target_velocity", None)
    if callable(set_velocity):
        # A newly spawned CARLA actor can report its default transform until
        # the next world tick.  The transform used for spawning is already
        # authoritative and prevents an initial velocity in the wrong world
        # direction during sensor warm-up.
        forward = transform.get_forward_vector()
        set_velocity(carla_api.Vector3D(
            x=float(forward.x) * desired_speed,
            y=float(forward.y) * desired_speed,
            z=0.0,
        ))
    intended_distance = transform.location.distance(ego.get_location())
    print(
        "scenario actor: spawned real lead "
        f"id={actor_spec.get('actor_id', 'scenario_lead')} "
        f"distance_m={intended_distance:.2f}",
        flush=True,
    )
    return lead


def _update_scenario_vehicle(
    lead: Any,
    actor_spec: Mapping[str, object],
    elapsed_s: float,
    carla_api: Any,
    *,
    desired_speed_mps: float | None = None,
) -> None:
    """Apply a small deterministic speed controller to a scenario vehicle."""
    if lead is None or not getattr(lead, "is_alive", True):
        raise RuntimeError("configured scenario lead vehicle is not alive")
    desired = (
        _scenario_vehicle_speed_mps(actor_spec, elapsed_s)
        if desired_speed_mps is None else max(0.0, float(desired_speed_mps))
    )
    current = _signed_forward_speed_mps(lead)
    error = desired - current
    if error < -0.15:
        throttle, brake = 0.0, min(1.0, 0.25 + (-error / 3.0))
    elif error > 0.15:
        throttle, brake = min(0.45, 0.12 + error / 6.0), 0.0
    else:
        throttle, brake = (0.08 if desired > 0.1 else 0.0), 0.0
    lead.apply_control(carla_api.VehicleControl(
        throttle=throttle,
        brake=brake,
        steer=0.0,
        hand_brake=False,
        reverse=False,
        manual_gear_shift=False,
    ))


def _spawn_scenario_walker(
    session: CarlaSession,
    world: Any,
    carla_api: Any,
    ego: Any,
    actor_spec: Mapping[str, object],
) -> tuple[Any, Any]:
    """Spawn a real pedestrian and return it with its world-space target.

    The target is anchored to the ego's actual map pose, just as vehicles are.
    This avoids a Town-specific world coordinate and makes crossing scenarios
    portable across the maps used by the evaluation harness.
    """
    spawn = actor_spec.get("spawn", {})
    behavior = actor_spec.get("behavior", {})
    if not isinstance(spawn, Mapping) or not isinstance(behavior, Mapping):
        raise TypeError("scenario walker requires spawn and behavior objects")
    library = world.get_blueprint_library()
    blueprint_id = actor_spec.get("blueprint_id")
    if isinstance(blueprint_id, str) and blueprint_id:
        blueprint = library.find(blueprint_id)
    else:
        candidates = list(library.filter("walker.pedestrian.*"))
        blueprint = candidates[0] if candidates else None
    if blueprint is None:
        raise LookupError(f"scenario walker blueprint not found: {blueprint_id!r}")
    has_attribute = getattr(blueprint, "has_attribute", None)
    if callable(has_attribute):
        if has_attribute("is_invincible"):
            blueprint.set_attribute("is_invincible", "false")

    anchor = ego.get_transform()
    transform = _scenario_local_transform(carla_api, anchor, spawn)
    walker = world.try_spawn_actor(blueprint, transform)
    if walker is None:
        raise RuntimeError("cannot spawn configured scenario walker")
    walker = session.track_actor(walker)
    set_physics = getattr(walker, "set_simulate_physics", None)
    if callable(set_physics):
        set_physics(True)
    target_xy = behavior.get("target_xy_m", [spawn.get("x", 0.0), spawn.get("y", 0.0)])
    if not isinstance(target_xy, (list, tuple)) or len(target_xy) != 2:
        raise TypeError("scenario walker target_xy_m must be [x, y]")
    target = _scenario_local_transform(
        carla_api,
        anchor,
        {"x": target_xy[0], "y": target_xy[1], "z": spawn.get("z", 0.5)},
    ).location
    print(
        "scenario actor: spawned real walker "
        f"id={actor_spec.get('actor_id', 'scenario_walker')}",
        flush=True,
    )
    return walker, target


def _update_scenario_walker(
    walker: Any,
    actor_spec: Mapping[str, object],
    elapsed_s: float,
    target_location: Any,
    carla_api: Any,
    *,
    trigger_ready: bool = True,
) -> None:
    """Move a scenario pedestrian with CARLA's public WalkerControl API."""
    if walker is None or not getattr(walker, "is_alive", True):
        raise RuntimeError("configured scenario walker is not alive")
    behavior = actor_spec.get("behavior", {})
    if not isinstance(behavior, Mapping):
        raise TypeError("scenario walker behavior must be an object")
    start_time_s = float(behavior.get("start_time_s", 0.0))
    speed_mps = max(0.0, float(behavior.get("speed_mps", 0.0)))
    location = walker.get_location()
    dx = float(target_location.x) - float(location.x)
    dy = float(target_location.y) - float(location.y)
    distance = math.hypot(dx, dy)
    speed = speed_mps if trigger_ready and elapsed_s >= start_time_s and distance > 0.2 else 0.0
    direction = carla_api.Vector3D(
        x=0.0 if distance <= 1e-6 else dx / distance,
        y=0.0 if distance <= 1e-6 else dy / distance,
        z=0.0,
    )
    walker.apply_control(carla_api.WalkerControl(
        direction=direction,
        speed=speed,
        jump=False,
    ))


def _spawn_scenario_static_prop(
    session: CarlaSession,
    world: Any,
    carla_api: Any,
    ego: Any,
    actor_spec: Mapping[str, object],
) -> Any:
    """Spawn a declared static obstacle for construction/occlusion coverage."""
    spawn = actor_spec.get("spawn", {})
    if not isinstance(spawn, Mapping):
        raise TypeError("scenario static prop spawn must be an object")
    blueprint_id = actor_spec.get("blueprint_id")
    if not isinstance(blueprint_id, str) or not blueprint_id:
        raise ValueError("scenario static prop requires blueprint_id")
    try:
        blueprint = world.get_blueprint_library().find(blueprint_id)
    except (IndexError, KeyError) as error:
        raise LookupError(f"scenario static prop blueprint not found: {blueprint_id!r}") from error
    if blueprint is None:
        raise LookupError(f"scenario static prop blueprint not found: {blueprint_id!r}")
    prop = world.try_spawn_actor(
        blueprint, _scenario_local_transform(carla_api, ego.get_transform(), spawn),
    )
    if prop is None:
        raise RuntimeError("cannot spawn configured scenario static prop")
    prop = session.track_actor(prop)
    set_physics = getattr(prop, "set_simulate_physics", None)
    if callable(set_physics):
        set_physics(False)
    print(
        "scenario actor: spawned static prop "
        f"id={actor_spec.get('actor_id', blueprint_id)}",
        flush=True,
    )
    return prop


def _select_scenario_lead(ego: Any, vehicles: Sequence[Any]) -> Any | None:
    """Choose the closest owned vehicle ahead of ego, never map background traffic."""
    ego_location = ego.get_location()
    forward = ego.get_transform().get_forward_vector()
    candidates: list[tuple[float, float, Any]] = []
    for vehicle in vehicles:
        if vehicle is None or not getattr(vehicle, "is_alive", True):
            continue
        location = vehicle.get_location()
        dx = float(location.x) - float(ego_location.x)
        dy = float(location.y) - float(ego_location.y)
        longitudinal = dx * float(forward.x) + dy * float(forward.y)
        lateral = abs(dx * float(forward.y) - dy * float(forward.x))
        if longitudinal >= -0.5 and lateral <= 4.5:
            candidates.append((longitudinal, math.hypot(dx, dy), vehicle))
    return min(candidates, default=(0.0, 0.0, None), key=lambda item: item[:2])[2]


def _scenario_traffic_light_distance(spec: ScenarioSpec | None) -> float | None:
    actor = _scenario_actor(spec, "traffic_light")
    if actor is None:
        return None
    distance = float(actor.get("distance_to_stop_line_m", 0.0))
    if not math.isfinite(distance) or distance <= 0.0:
        raise ValueError("scenario traffic-light distance_to_stop_line_m must be positive")
    return distance


def _traffic_light_scenario_anchor(
    world: Any,
    world_map: Any,
    carla_api: Any,
    distance_to_stop_line_m: float,
    *,
    candidate_index: int = 0,
) -> tuple[Any, Any]:
    """Return a real signal and a driving-lane transform behind its stop line."""
    actors = world.get_actors()
    lights = list(
        actors.filter("traffic.traffic_light*")
        if callable(getattr(actors, "filter", None))
        else ()
    )
    lights.sort(key=lambda actor: int(getattr(actor, "id", 0)))
    candidates: list[tuple[int, Any, Any]] = []
    for light in lights:
        getter = getattr(light, "get_stop_waypoints", None)
        if not callable(getter):
            continue
        for waypoint in getter() or ():
            transform = waypoint.transform
            forward = transform.get_forward_vector()
            stop_location = transform.location
            behind = carla_api.Location(
                x=float(stop_location.x) - float(forward.x) * distance_to_stop_line_m,
                y=float(stop_location.y) - float(forward.y) * distance_to_stop_line_m,
                z=float(stop_location.z),
            )
            driving = world_map.get_waypoint(behind, project_to_road=True)
            if driving is None:
                continue
            driving_transform = driving.transform
            spawn_transform = carla_api.Transform(
                carla_api.Location(
                    x=float(driving_transform.location.x),
                    y=float(driving_transform.location.y),
                    z=float(driving_transform.location.z) + 0.5,
                ),
                carla_api.Rotation(
                    pitch=float(getattr(driving_transform.rotation, "pitch", 0.0)),
                    yaw=float(driving_transform.rotation.yaw),
                    roll=float(getattr(driving_transform.rotation, "roll", 0.0)),
                ),
            )
            candidates.append((int(getattr(light, "id", 0)), light, spawn_transform))
    if not candidates:
        raise RuntimeError("current map has no usable traffic-light stop waypoint")
    candidates.sort(key=lambda item: item[0])
    _, light, transform = candidates[candidate_index % len(candidates)]
    return light, transform


def _scenario_traffic_light_observation(
    scene: PerceptionFrame,
    ego: Any,
    light: Any,
) -> tuple[PerceptionFrame, dict[str, str]]:
    """Bind D08 to the selected real CARLA signal and map stop waypoint."""
    state = str(light.get_state()).split(".")[-1].upper()
    if state not in {"RED", "YELLOW", "GREEN"}:
        raise RuntimeError(f"selected CARLA traffic light has unsupported state {state!r}")
    ego_location = ego.get_location()
    forward = ego.get_transform().get_forward_vector()
    distances: list[float] = []
    getter = getattr(light, "get_stop_waypoints", None)
    if callable(getter):
        for waypoint in getter() or ():
            location = waypoint.transform.location
            along = (
                (float(location.x) - float(ego_location.x)) * float(forward.x)
                + (float(location.y) - float(ego_location.y)) * float(forward.y)
            )
            if along >= -0.5:
                distances.append(max(0.0, along))
    if not distances:
        raise RuntimeError("selected CARLA traffic light has no forward stop waypoint")
    source = "CARLA_SCENARIO_TRAFFIC_LIGHT_ACTOR_STOP_WAYPOINT"
    return replace(
        scene,
        traffic_light=state,
        distance_to_stop_line_m=min(distances),
    ), {
        "traffic_light": source,
        "distance_to_stop_line_m": source,
    }


def _apply_virtual_scenario(scene: PerceptionFrame, ego: Any, origin: tuple[float, float, float], args: argparse.Namespace) -> PerceptionFrame:
    location = ego.get_location()
    travelled_m = math.sqrt((location.x - origin[0]) ** 2 + (location.y - origin[1]) ** 2 + (location.z - origin[2]) ** 2)
    if args.scenario == "red_stop":
        return replace(scene, traffic_light="RED", distance_to_stop_line_m=max(0.0, args.stop_line_m - travelled_m))
    if args.scenario in {"follow", "emergency"}:
        initial_gap_m = args.lead_distance_m if args.scenario == "follow" else args.emergency_distance_m
        # Deterministic simulator truth used until the RGB/LiDAR tracker is
        # available. It represents a stationary lead on the active route and
        # cannot be displaced by CARLA's map-dependent spawn relocation.
        return replace(scene, lead_distance_m=max(0.1, initial_gap_m - travelled_m), lead_speed_mps=0.0)
    return scene


def _scenario_facts(
    ego: Any,
    origin: tuple[float, float, float],
    spec: ScenarioSpec,
    *,
    frame: int,
    sim_time_s: float,
    elapsed_s: float,
) -> PerceptionFrame:
    """Build deterministic configured actors without mutating perception."""
    location = ego.get_location()
    travelled_m = math.sqrt(
        (location.x - origin[0]) ** 2
        + (location.y - origin[1]) ** 2
        + (location.z - origin[2]) ** 2
    )
    updates: dict[str, object] = {}
    for actor in spec.actors:
        actor_type = str(actor.get("type", "")).lower()
        if actor_type == "traffic_light":
            stop_line = float(actor.get("distance_to_stop_line_m", 0.0))
            updates["traffic_light"] = str(actor.get("state", "UNKNOWN")).upper()
            updates["distance_to_stop_line_m"] = max(0.0, stop_line - travelled_m)
            continue
        if actor_type == "vehicle":
            spawn = actor.get("spawn", {})
            behavior = actor.get("behavior", {})
            if not isinstance(spawn, dict) or not isinstance(behavior, dict):
                continue
            initial_gap = float(spawn.get("x", 18.0))
            initial_speed = float(behavior.get("initial_speed_mps", 0.0))
            brake_at_s = float(behavior.get("brake_at_s", math.inf))
            target_speed = float(behavior.get("target_speed_mps", initial_speed))
            lead_speed = initial_speed if elapsed_s < brake_at_s else target_speed
            lead_travel_m = _lead_vehicle_travel_m(
                elapsed_s, initial_speed, brake_at_s, target_speed,
            )
            candidate_gap = max(0.1, initial_gap + lead_travel_m - travelled_m)
            if candidate_gap < float(updates.get("lead_distance_m", math.inf)):
                updates["lead_distance_m"] = candidate_gap
                updates["lead_speed_mps"] = lead_speed
            continue
        if actor_type.startswith("walker"):
            spawn = actor.get("spawn", {})
            behavior = actor.get("behavior", {})
            if not isinstance(spawn, dict) or not isinstance(behavior, dict):
                continue
            start_s = float(behavior.get("start_time_s", 0.0))
            speed_mps = float(behavior.get("speed_mps", 0.0))
            target = behavior.get("target_xy_m", [spawn.get("x", 0.0), spawn.get("y", 0.0)])
            if not isinstance(target, list) or len(target) != 2 or elapsed_s < start_s:
                continue
            spawn_y = float(spawn.get("y", 0.0))
            target_y = float(target[1])
            direction = 1.0 if target_y >= spawn_y else -1.0
            current_y = spawn_y + direction * speed_mps * (elapsed_s - start_s)
            if min(spawn_y, target_y) - 1e-6 <= current_y <= max(spawn_y, target_y) + 1e-6 and abs(current_y) <= 2.0:
                candidate_gap = max(0.1, float(spawn.get("x", 0.0)) - travelled_m)
                if candidate_gap < float(updates.get("lead_distance_m", math.inf)):
                    updates["lead_distance_m"] = candidate_gap
                    updates["lead_speed_mps"] = 0.0
    return PerceptionFrame(frame, sim_time_s, **updates)


def _lead_vehicle_travel_m(
    elapsed_s: float,
    initial_speed_mps: float,
    brake_at_s: float,
    target_speed_mps: float,
) -> float:
    """Integrate the scenario lead's piecewise speed without a position jump at braking."""
    before_brake_s = min(elapsed_s, brake_at_s)
    after_brake_s = max(0.0, elapsed_s - brake_at_s)
    return initial_speed_mps * before_brake_s + target_speed_mps * after_brake_s


def _select_scene_facts(
    perception: PerceptionFrame,
    scenario: PerceptionFrame | None,
    mode: str,
) -> tuple[PerceptionFrame, dict[str, str]]:
    """Select perception, scenario truth, or perception-first fallback."""
    if mode not in {"perception", "scenario", "fuse"}:
        raise ValueError(f"unsupported scenario facts mode: {mode!r}")
    if scenario is None or mode == "perception":
        return perception, {}

    fact_fields = ("lead_distance_m", "lead_speed_mps", "distance_to_stop_line_m")
    if mode == "scenario":
        # Scenario-truth mode is authoritative, including explicit absence.
        # Keeping a perceived value when the scenario field is None lets
        # unrelated Town traffic lights/actors contaminate deterministic
        # controller acceptance runs.
        values = {name: getattr(scenario, name) for name in fact_fields}
        values["traffic_light"] = scenario.traffic_light
        return replace(perception, **values), {
            name: "SCENARIO_CONFIG_TRUTH" for name in values
        }

    values = {
        name: getattr(scenario, name)
        for name in fact_fields
        if getattr(perception, name) is None and getattr(scenario, name) is not None
    }
    if perception.traffic_light == "UNKNOWN" and scenario.traffic_light != "UNKNOWN":
        values["traffic_light"] = scenario.traffic_light
    return replace(perception, **values), {
        name: "SCENARIO_CONFIG_FALLBACK" for name in values
    }


def _load_command(args: argparse.Namespace) -> dict[str, object] | None:
    if args.command_json:
        command = json.loads(Path(args.command_json).read_text(encoding="utf-8"))
        if not isinstance(command, Mapping):
            raise TypeError("voice command JSON root must be an object")
        command = dict(command)
        if is_high_level_command(command):
            command = HighLevelCommandAdapter().adapt(command)
        if args.test_command_ttl_s is not None:
            command["valid_duration_s"] = args.test_command_ttl_s
        return command
    if args.audio:
        audio_path = Path(args.audio)
        if not audio_path.is_file():
            raise FileNotFoundError(
                f"audio file not found: {audio_path}. Pass an existing 16 kHz mono WAV path via --audio."
            )
        from voice_group.pipeline import audio_to_command, preload_voice_models

        preload = preload_voice_models()
        print(f"voice model preload: {preload}", flush=True)
        command = audio_to_command(str(audio_path))
        if not isinstance(command, Mapping):
            raise TypeError("voice pipeline result must be an object")
        command = dict(command)
        if args.test_command_ttl_s is not None:
            command["valid_duration_s"] = args.test_command_ttl_s
        return command
    return None


def _qwen_voice_command(args: argparse.Namespace, spec: ScenarioSpec | None) -> str:
    explicit = str(getattr(args, "qwen_voice_command", "") or "").strip()
    if explicit:
        return explicit
    if spec is None:
        raise ValueError("--qwen-remote requires --qwen-voice-command or a scenario file")
    if len(spec.commands) != 1 or spec.commands[0].time_s > 1e-9:
        raise ValueError(
            "remote Qwen scenario mode currently requires exactly one command at time_s=0"
        )
    source_text = str(spec.commands[0].envelope.get("source_text", "")).strip()
    if not source_text:
        raise ValueError("scenario command must provide source_text for remote Qwen")
    return source_text


def _qwen_desired_speed_mps(args: argparse.Namespace, spec: ScenarioSpec | None) -> float:
    fallback = float(args.default_speed_mps)
    if spec is None or len(spec.commands) != 1:
        return fallback
    resolved = resolve_scenario_command(
        spec.commands[0].envelope,
        requested_speed_mps=fallback,
    )
    parameters = resolved.get("parameters")
    if not isinstance(parameters, Mapping):
        return fallback
    speed = parameters.get("speed")
    if type(speed) not in (int, float) or isinstance(speed, bool):
        return fallback
    value = float(speed)
    unit = str(parameters.get("unit", "m/s")).strip().lower().replace(" ", "")
    if unit in {"m/s", "mps", "米/秒"}:
        return value
    if unit in {"km/h", "kph", "kmh", "公里/小时", "千米/小时"}:
        return value / 3.6
    raise ValueError(f"unsupported Qwen desired-speed unit: {unit!r}")


def _save_qwen_rgb_image(
    measurement: Any,
    image_root: str | Path,
    *,
    request_id: str,
) -> str:
    """Persist one aligned CARLA RGB frame and return an image-root-relative ref."""
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("remote Qwen live mode requires Pillow") from error
    root = Path(image_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(character for character in request_id if character.isalnum() or character in "-_")
    if not safe_id:
        raise ValueError("request_id has no filesystem-safe characters")
    path = root / f"{safe_id}.jpg"
    Image.fromarray(carla_rgb_array(measurement), mode="RGB").save(
        path,
        format="JPEG",
        quality=90,
        optimize=True,
    )
    return path.relative_to(root).as_posix()


def _build_qwen_context(
    *,
    request_id: str,
    voice_command: str,
    rgb_ref: str,
    state: RuntimeVehicleState,
    scene: PerceptionFrame,
    behavior_state: str,
    desired_speed_mps: float,
    route_end_distance_m: float | None,
    c_safety_state: Mapping[str, object] | None,
) -> QwenInputContext:
    detected_objects = [
        {
            "class_name": item.class_name,
            "confidence": item.confidence,
            "distance_m": item.distance_m,
            "bbox_xyxy_norm": list(item.bbox_xyxy_norm),
        }
        for item in scene.detected_objects
    ]
    safety = dict(c_safety_state or {})
    return QwenInputContext(
        request_id=request_id,
        frame=state.frame,
        sim_time_s=state.sim_time_s,
        voice_command=voice_command,
        rgb_ref=rgb_ref,
        scene_state={
            "speed_mps": state.speed_mps,
            "behavior_state": behavior_state,
            "desired_speed_mps": desired_speed_mps,
            "route_end_distance_m": route_end_distance_m,
        },
        perception={
            "lead_distance_m": scene.lead_distance_m,
            "lead_speed_mps": scene.lead_speed_mps,
            "traffic_light": scene.traffic_light,
            "distance_to_stop_line_m": scene.distance_to_stop_line_m,
            "speed_limit_mps": scene.speed_limit_mps,
            "lane_offset_m": scene.lane_offset_m,
            "route_deviation_m": scene.route_deviation_m,
            "detected_objects": detected_objects,
            "visual_valid": True,
        },
        safety_state={
            "collision": scene.collision,
            "red_light_violation": scene.red_light_violation,
            "lane_invasion": scene.lane_invasion,
            "minimum_ttc_s": safety.get("ttc_s"),
            "recommended_action": safety.get("recommended_action"),
            "fusion_mode": safety.get("fusion_mode"),
            "fused_valid": safety.get("fused_valid"),
        },
    )


def _evidence_recorder(args: argparse.Namespace, spec: ScenarioSpec | None = None) -> ScenarioEvidenceRecorder | None:
    if args.no_log:
        return None
    directory = Path(args.log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = directory / f"{args.scenario}_{stamp}.jsonl"
    recorder = ScenarioEvidenceRecorder(path)
    recorder.start_run(scenario_id=args.scenario, difficulty=getattr(args, "scenario_difficulty", "basic"), config={
        key: value for key, value in vars(args).items()
        if type(value) in (str, int, float, bool) or value is None
    }, expected_route_deviation=(
        spec is not None and spec.expected.get("expected_route_deviation_event") is True
    ))
    print(f"run log: {path}")
    return recorder


def _rejected_load_envelope(error: BaseException) -> dict[str, object]:
    """Represent voice loading failures as a vehicle-side auditable NO_OP."""
    return {
        "schema_version": "1.0",
        "command_id": f"voice-load-error-{time.monotonic_ns()}",
        "source_text": "<voice input unavailable>",
        "intent": "UNKNOWN",
        "parameters": {},
        "intent_confidence": 0.0,
        "confidence": 0.0,
        "status": "invalid",
        "ambiguity_type": "INPUT_ERROR",
        "confirm_required": False,
        "errors": [{"code": "VOICE_INPUT_ERROR", "message": f"{type(error).__name__}: {error}"}],
        "warnings": [],
        "valid_duration_s": 3.0,
    }


def _warm_up_sensor_bridge(session: Any, world: Any, bridge: CarlaPerceptionBridge, *, attempts: int,
                           tick_timeout_s: float, sensor_timeout_s: float) -> None:
    """Wait for a stable aligned RGB/LiDAR stream before command execution."""
    last_error: PerceptionAcquisitionError | None = None
    required_streak = min(2, attempts)
    aligned_streak = 0
    for _ in range(attempts):
        frame = session.tick(tick_timeout_s)
        snapshot = world.get_snapshot()
        sim_time_s = snapshot.timestamp.elapsed_seconds
        try:
            bridge.acquire(frame, sim_time_s, timeout_s=sensor_timeout_s)
            aligned_streak += 1
        except PerceptionAcquisitionError as error:
            last_error = error
            aligned_streak = 0
    if aligned_streak >= required_streak:
        return
    if last_error is not None:
        raise last_error
    raise RuntimeError(
        f"sensor warm-up did not produce {required_streak} consecutive aligned frames"
    )


def _scenario_completed(args: argparse.Namespace, *, frames: int, final_speed_mps: float | None,
                        final_scene: PerceptionFrame | None, min_gap_m: float | None,
                        collision_seen: bool, max_speed_mps: float = 0.0) -> bool:
    if frames != args.frames or final_speed_mps is None or collision_seen:
        return False
    if args.scenario == "red_stop":
        return (final_scene is not None and final_scene.distance_to_stop_line_m is not None
                and final_speed_mps <= 0.15 and final_scene.distance_to_stop_line_m <= 1.0)
    if args.scenario == "follow":
        return min_gap_m is not None and min_gap_m >= 3.0 and max_speed_mps >= 0.2
    if args.scenario == "emergency":
        return final_speed_mps <= 0.15
    return max_speed_mps >= 0.2


def _runtime_health_completed(safety_reasons: set[str]) -> bool:
    """Reject ordinary scenario success after a runtime/integration fail-safe.

    Intentional D interventions are evaluated separately by
    ``_expected_safety_completed``.  The basic runner must not report success
    merely because a watchdog-latched vehicle stayed still and avoided impact.
    """
    return not any(
        reason in {"WATCHDOG_ALERT", "INTEGRATION_FAILURE"}
        or (reason.startswith("PERCEPTION_") and reason != "PERCEPTION_STARTUP_GRACE")
        for reason in safety_reasons
    )


def _c_perception_safety_reason(c_safety_state: Mapping[str, object] | None) -> str | None:
    """Convert C fail-closed perception summaries into acceptance evidence."""
    if not c_safety_state:
        return None
    action = str(c_safety_state.get("recommended_action", "")).strip().upper()
    if action not in {"FULL_BRAKE", "EMERGENCY_BRAKE"}:
        return None
    object_class = str(c_safety_state.get("object_class") or "HAZARD").strip().upper()
    if object_class in {"PERSON", "PEDESTRIAN"}:
        object_class = "PEDESTRIAN"
    reason = str(c_safety_state.get("reason") or "FAIL_CLOSED").strip().upper()
    reason = "".join(char if char.isalnum() else "_" for char in reason).strip("_")
    return f"C_FRONT_{object_class}_{reason or 'FAIL_CLOSED'}"


def _c_safety_speed_cap_mps(c_safety_state: Mapping[str, object] | None) -> float | None:
    """Accept only an explicit finite C-side temporary speed cap.

    A cap is intentionally transient: it is applied to the current control
    step's route reference and never overwrites the driver's requested speed
    or command FSM state.  D still arbitrates the resulting control.
    """
    if not c_safety_state:
        return None
    if str(c_safety_state.get("recommended_action", "")).upper() != "SLOW_DOWN":
        return None
    candidate = c_safety_state.get("recommended_speed_cap_mps")
    if type(candidate) not in (int, float) or isinstance(candidate, bool):
        return None
    cap = float(candidate)
    return cap if math.isfinite(cap) and cap >= 0.0 else None


def _c_speed_cap_control_override(
    current_speed_mps: float,
    speed_cap_mps: float | None,
) -> dict[str, float] | None:
    """Return a D-arbitrated braking request when a temporary C cap is exceeded."""
    if speed_cap_mps is None or not math.isfinite(current_speed_mps):
        return None
    excess = float(current_speed_mps) - speed_cap_mps
    if excess <= 0.10:
        return None
    # The request is deliberately bounded and remains a raw input to D; it is
    # not an alternate control owner.  A large excess requires prompt braking
    # because the cap was issued from an aligned VRU observation.
    brake = min(1.0, 0.35 + 0.25 * excess)
    return {"throttle": 0.0, "brake": brake, "steer": 0.0}


def _expected_safety_completed(
    spec: ScenarioSpec,
    *,
    frames: int,
    final_speed_mps: float | None,
    collision_seen: bool,
    safety_reasons: set[str],
) -> bool | None:
    """Evaluate scenario contracts whose success is an intentional D intervention."""
    expected = spec.expected
    requires_override = expected.get("expected_safety_override") is True
    allows_override = expected.get("expected_safety_override_allowed") is True
    requires_route_event = expected.get("expected_route_deviation_event") is True
    requires_emergency = expected.get("must_emergency_brake") is True
    if not (requires_override or allows_override or requires_route_event or requires_emergency):
        return None
    if frames != spec.frame_count or final_speed_mps is None or collision_seen:
        return False
    meaningful = {reason for reason in safety_reasons if reason not in {"NONE", "PERCEPTION_STARTUP_GRACE"}}
    if requires_override and not meaningful:
        return False
    if allows_override and not _runtime_health_completed(safety_reasons):
        return False
    if requires_route_event and not any("ROUTE_DEVIATION" in reason for reason in meaningful):
        return False
    if requires_emergency and not (
        any("TTC" in reason or "EMERGENCY" in reason for reason in meaningful)
        or final_speed_mps <= float(expected.get("stop_speed_threshold_mps", 0.3))
    ):
        return False
    tokens = expected.get("expected_reason_contains", [])
    if isinstance(tokens, list) and tokens:
        joined = " ".join(meaningful).lower()
        if not any(str(token).lower() in joined for token in tokens):
            return False
    return True


def _scenario_raw_control_fault(spec: ScenarioSpec | None, elapsed_s: float) -> dict[str, object] | None:
    """Build the one-shot pre-D fault required by D05/D06 contracts."""
    if spec is None or elapsed_s < 5.0:
        return None
    expected = spec.expected
    if expected.get("final_control_must_be_finite") is True:
        return {"throttle": 0.0, "brake": 0.0, "steer": "NaN", "fault_injected": True}
    if expected.get("final_control_no_throttle_brake_overlap") is True:
        return {"throttle": 0.5, "brake": 0.5, "steer": 0.0, "fault_injected": True}
    return None


def _route_contract_completed(spec: ScenarioSpec | None, distance_to_route_end_m: float | None) -> bool | None:
    """Evaluate explicit route-finish contracts instead of treating frame exhaustion as success."""
    if spec is None or spec.expected.get("must_finish_route") is not True:
        return None
    return distance_to_route_end_m is not None and distance_to_route_end_m <= spec.finish_radius_m


def _minimum_gap_contract_completed(spec: ScenarioSpec | None, min_gap_m: float | None) -> bool | None:
    """Evaluate a declared front-gap floor as a hard scenario contract."""
    if spec is None or "min_front_gap_m" not in spec.expected:
        return None
    required_m = float(spec.expected["min_front_gap_m"])
    return min_gap_m is not None and min_gap_m >= required_m


def _route_stop_trigger_m(speed_mps: float, finish_radius_m: float, decel_mps2: float = 2.0) -> float:
    """Choose an endpoint braking trigger from current speed and a conservative service deceleration."""
    if speed_mps < 0.0 or finish_radius_m < 0.0 or decel_mps2 <= 0.0:
        raise ValueError("speed/finish radius must be non-negative and deceleration positive")
    return max(finish_radius_m, speed_mps * speed_mps / (2.0 * decel_mps2) + 1.0)


def _map_short_name(map_name: str) -> str:
    return map_name.rsplit("/", maxsplit=1)[-1]


def _map_contract_name(map_name: str) -> str:
    short_name = _map_short_name(map_name)
    return short_name[:-4] if short_name.lower().endswith("_opt") else short_name


def _select_load_map(requested_map: str, available_maps: tuple[str, ...]) -> str:
    requested_short = _map_short_name(requested_map)
    if requested_short.lower().endswith("_opt"):
        return requested_map
    optimized_short = f"{requested_short}_Opt"
    for available in available_maps:
        if _map_short_name(available).lower() == optimized_short.lower():
            return optimized_short
    return requested_map


def _import_carla_api() -> Any:
    try:
        return importlib.import_module("carla")
    except ModuleNotFoundError as error:
        if error.name != "carla":
            raise

    py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    project_root = Path(__file__).resolve().parents[1]
    candidate_roots = (
        project_root / "simulator" / "carla0916" / "PythonAPI" / "carla" / "dist",
        project_root.parent / "simulator" / "carla0916" / "PythonAPI" / "carla" / "dist",
    )
    for root in candidate_roots:
        wheels = sorted(root.glob(f"carla-0.9.16-{py_tag}-{py_tag}-*.whl"))
        if not wheels:
            continue
        wheel = wheels[0]
        extract_root = Path("/tmp") / "carla_python_api" / wheel.stem
        if not extract_root.exists():
            extract_root.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(extract_root)
        sys.path.insert(0, str(extract_root))
        return importlib.import_module("carla")
    searched = ", ".join(str(root) for root in candidate_roots)
    raise ModuleNotFoundError(
        f"No CARLA Python API for {py_tag}; searched {searched}. "
        "Use Python 3.10/3.11/3.12 with the bundled CARLA 0.9.16 wheel."
    )


def run(args: argparse.Namespace) -> None:
    spec = ScenarioSpec.load(args.scenario_file) if args.scenario_file else None
    extension_runtime = (
        ScenarioExtensionRuntime(spec.extensions)
        if spec is not None and spec.extensions
        else None
    )
    qwen_scenario_monitor = (
        QwenScenarioMonitor(spec.qwen_expected)
        if spec is not None and spec.qwen_expected is not None
        else None
    )
    if args.validate_scenario_only:
        if spec is None:
            raise ValueError("--validate-scenario-only requires --scenario-file")
        print(json.dumps({
            "scenario_id": spec.scenario_id,
            "official_level": spec.official_level,
            "map": spec.map_name,
            "weather": spec.weather,
            "fixed_delta_s": spec.fixed_delta_s,
            "duration_s": spec.duration_s,
            "frame_count": spec.frame_count,
            "route_points": len(spec.local_route_xy_m),
            "commands": len(spec.commands),
            "actors": len(spec.actors),
            "validation": "PASS",
        }, ensure_ascii=False, indent=2))
        return

    if (
        extension_runtime is not None
        and isinstance(spec.extensions.get("qwen_policy"), Mapping)
        and spec.extensions["qwen_policy"].get("required_for_every_voice_event") is True
        and not args.qwen_service_url
    ):
        raise ValueError(
            "acceptance-suite v2 requires --qwen-service-url so every voice event is audited by Qwen"
        )

    qwen_enabled = bool(getattr(args, "qwen_remote", False))
    qwen_voice_text = _qwen_voice_command(args, spec) if qwen_enabled else ""
    qwen_desired_speed_mps = (
        _qwen_desired_speed_mps(args, spec) if qwen_enabled else float(args.default_speed_mps)
    )
    qwen_image_root = Path(
        getattr(args, "qwen_image_dir", "artifacts/runtime/qwen_live")
    ).expanduser().resolve()
    if args.live_mic and (args.audio or args.command_json or args.scenario_file):
        raise ValueError("--live-mic cannot be combined with --audio, --command-json, or --scenario-file")

    carla = _import_carla_api()

    detector = None
    detector_model = getattr(args, "rgb_detector_model", None)
    if detector_model:
        if args.perception_mode != "sensors":
            raise ValueError("--rgb-detector-model requires --perception-mode sensors")
        detector = OnnxYoloDetector(
            detector_model,
            confidence_threshold=args.rgb_detector_confidence,
            iou_threshold=args.rgb_detector_iou,
            input_size=args.rgb_detector_input_size,
        )

    if spec is not None:
        args.map = None if args.use_current_map else spec.map_name
        args.fixed_delta_s = spec.fixed_delta_s
        args.frames = spec.frame_count
        if args.max_frames is not None:
            args.frames = min(args.frames, args.max_frames)
        args.scenario = spec.scenario_id
        args.scenario_difficulty = spec.official_level
        args.evidence_seed = spec.seed if args.seed is None else args.seed
        if args.seed is not None:
            args.spawn_index = args.seed
        owns_real_scene_actor = bool(
            _scenario_actors(spec, "vehicle")
            or _scenario_actor(spec, "traffic_light") is not None
            or _scenario_walkers(spec)
            or _scenario_static_props(spec)
        )
        if owns_real_scene_actor and args.scenario_facts_mode != "perception":
            print(
                "scenario facts: forcing perception mode because the scenario "
                "owns real CARLA actors",
                flush=True,
            )
            args.scenario_facts_mode = "perception"

    recorder = _evidence_recorder(args, spec)
    ego: Any | None = None
    frames_completed = 0
    final_state: RuntimeVehicleState | None = None
    final_scene: PerceptionFrame | None = None
    min_gap_m: float | None = None
    collision_seen = False
    safety_reasons: set[str] = set()
    raw_control_fault_injected = False
    final_route_end_distance_m: float | None = None
    max_speed_mps = 0.0
    runtime: ControlRuntime | None = None
    last_sim_time_s = 0.0
    scenario_traffic_light: Any | None = None
    live_voice: LiveVoiceSource | None = None
    canonical_orchestrator: PipelineOrchestrator | None = None
    canonical_bridge: CanonicalRuntimeBridge | None = None
    qwen_image_stager: QwenImageStager | None = None
    deferred_commands: list[_DeferredCommand] = []
    traffic_light_original_state: Any | None = None
    traffic_light_original_frozen: bool | None = None
    qwen_backend: OpenAICompatibleQwenVLBackend | None = None
    qwen_adapter: StrictQwenVLAdapter | None = None
    qwen_bridge: AsyncQwenDecisionBridge | None = None
    qwen_submitted = False
    qwen_ready = False
    qwen_terminal_recorded = False
    qwen_request_id: str | None = None
    maneuver_fsm = ManeuverFSM()
    maneuver_lane_ids: dict[str, str] = {}
    maneuver_start_xy: tuple[float, float] | None = None
    maneuver_start_yaw_deg: float | None = None
    maneuver_junction_seen = False
    maneuver_target_seen = False
    maneuver_target_pass_after_m: float | None = None
    maneuver_route_steps_applied: set[str] = set()
    qwen_status = (
        "NOT_SUBMITTED" if qwen_enabled
        else "CANONICAL_READY" if args.qwen_service_url
        else "DISABLED"
    )
    ego_standstill_since_s: float | None = None
    extension_frame: Any | None = None
    try:
        if qwen_enabled:
            qwen_backend = OpenAICompatibleQwenVLBackend(
                base_url=args.qwen_base_url,
                api_key=os.environ.get("QWEN_API_KEY", "unused"),
                model=args.qwen_model,
                timeout_s=args.qwen_request_timeout_s,
                max_tokens=args.qwen_max_tokens,
                image_max_side=args.qwen_image_max_side,
                jpeg_quality=args.qwen_jpeg_quality,
            )
            qwen_adapter = StrictQwenVLAdapter(
                qwen_backend,
                image_root=qwen_image_root,
            )
            qwen_bridge = AsyncQwenDecisionBridge(
                qwen_adapter.infer,
                ttl_s=args.qwen_decision_ttl_s,
                max_inference_s=args.qwen_max_inference_s,
                command_ttl_s=args.qwen_command_ttl_s,
            )
            print(
                "qwen stage: remote backend ready "
                f"base_url={args.qwen_base_url} model={args.qwen_model}",
                flush=True,
            )
        if args.live_mic:
            live_voice = LiveVoiceSource(LiveVoiceConfig(source=args.live_mic_source))
            print("live voice: preloading ASR models", flush=True)
            print(f"live voice preload: {live_voice.preload()}", flush=True)
        client = carla.Client(args.host, args.port)
        client.set_timeout(args.timeout_s)
        world = client.get_world()
        if args.map:
            current_map = world.get_map().name
            requested_map = args.map
            if _map_contract_name(current_map).lower() != _map_contract_name(requested_map).lower():
                load_map = _select_load_map(requested_map, tuple(client.get_available_maps()))
                world = client.load_world(load_map)
        if spec is not None:
            weather = getattr(carla.WeatherParameters, spec.weather, None)
            if weather is None:
                raise ValueError(f"CARLA has no WeatherParameters preset named {spec.weather!r}")
            if extension_runtime is not None:
                for name, value in extension_runtime.weather_parameters.items():
                    if not hasattr(weather, name):
                        raise ValueError(f"CARLA weather has no parameter {name!r}")
                    setattr(weather, name, value)
            world.set_weather(weather)
        world_map = world.get_map()
        blueprints = world.get_blueprint_library().filter("vehicle.*model3*")
        if not blueprints:
            raise RuntimeError("no Tesla Model 3 vehicle blueprint is available")
        bp = blueprints[0]
        spawn_points = world_map.get_spawn_points()
        if not spawn_points:
            raise RuntimeError("map has no vehicle spawn points")
        if args.test_command_ttl_s is not None:
            fsm_timeout_s = args.test_command_ttl_s + 1.0
        elif spec is not None:
            fsm_timeout_s = max(15.0, spec.duration_s + 1.0)
        else:
            fsm_timeout_s = 15.0
        route_deviation_trigger_m = 3.0
        if spec is not None and "route_deviation_trigger_m" in spec.expected:
            route_deviation_trigger_m = float(spec.expected["route_deviation_trigger_m"])
        scenario_safety = SafetySupervisor(SafetyConfig(
            stop_line_guard_m=args.stop_line_guard_m,
            severe_route_deviation_m=route_deviation_trigger_m,
        ))
        runtime = ControlRuntime(_acceptance_lateral_controller(),
                                 default_speed_mps=0.0 if qwen_enabled else args.default_speed_mps,
                                 command_timeout_s=fsm_timeout_s, safety=scenario_safety)
        if args.qwen_service_url:
            qwen_image_stager = QwenImageStager(
                args.qwen_image_root,
                ref_prefix=args.qwen_image_prefix,
            )
            qwen_client = QwenServiceClient(
                args.qwen_service_url,
                timeout_s=max(0.1, args.qwen_timeout_ms / 1000.0 + 0.05),
                request_transform=qwen_image_stager.prepare_request,
            )
            qwen_faults: list[Mapping[str, Any]] = []
            if spec is not None and spec.qwen_fault is not None:
                qwen_faults.append(spec.qwen_fault)
            if extension_runtime is not None:
                qwen_faults.extend(extension_runtime.qwen_faults)
            qwen_infer = (
                ScenarioQwenFaultInjector(
                    qwen_client,
                    qwen_faults,
                    command_times_s=(
                        tuple(item.time_s for item in spec.commands)
                        if spec is not None else ()
                    ),
                )
                if qwen_faults else qwen_client
            )
            force_all_voice_qwen = bool(
                spec is not None
                and isinstance(spec.extensions.get("qwen_policy"), Mapping)
                and spec.extensions["qwen_policy"].get("required_for_every_voice_event") is True
            )
            canonical_orchestrator = PipelineOrchestrator(
                infer=qwen_infer,
                config=OrchestratorConfig(
                    qwen_queue_size=args.qwen_queue_size,
                    model_timeout_ms=args.qwen_timeout_ms,
                    qwen_mode=args.qwen_mode,
                    force_qwen_all_voice=force_all_voice_qwen,
                ),
            )
            canonical_bridge = CanonicalRuntimeBridge(runtime, canonical_orchestrator)
            print(json.dumps({
                "record_type": "canonical_routing_ready",
                "qwen_service_url": args.qwen_service_url,
                "qwen_timeout_ms": args.qwen_timeout_ms,
                "qwen_queue_size": args.qwen_queue_size,
                "qwen_mode": args.qwen_mode,
                "qwen_image_root": str(args.qwen_image_root),
                "qwen_image_prefix": args.qwen_image_prefix,
                "policy": "FAST_DIRECT_SLOW_ASYNC_FAIL_CLOSED",
            }, ensure_ascii=False), flush=True)
        route_anchor = spawn_points[args.spawn_index % len(spawn_points)]
        topology_route: RouteReference | None = None
        prevalidated_avoid_route: RouteReference | None = None
        road_fit_required = (
            spec is not None
            and (spec.category == "lateral_B" or spec.expected.get("must_finish_route") is True)
        )
        seeded_route_anchor = (
            spec is not None
            and args.seed is not None
            and _scenario_traffic_light_distance(spec) is None
        )
        if road_fit_required or seeded_route_anchor:
            maneuver = _scenario_maneuver(spec)
            anchor_index, topology_route, anchor_score = select_topology_route_anchor(
                world_map,
                spawn_points,
                maneuver=maneuver,
                target_speed_mps=args.default_speed_mps,
                distance_m=_scenario_route_distance_m(spec),
                forbidden_points_xy=_traffic_light_stop_points(world),
            )
            route_anchor = spawn_points[anchor_index]
            seed_offset_m = float(getattr(args, "evidence_seed", 0) % 5) * 2.0
            if seeded_route_anchor and seed_offset_m > 0.0:
                anchor_waypoint = world_map.get_waypoint(
                    route_anchor.location, project_to_road=True,
                )
                advanced = tuple(anchor_waypoint.next(seed_offset_m)) if anchor_waypoint else ()
                if advanced:
                    advanced_transform = advanced[0].transform
                    advanced_transform.location.z = route_anchor.location.z
                    route_anchor = advanced_transform
            if any(
                str(item.envelope.get("intent", "")).upper() == "AVOID_OBSTACLE"
                for item in spec.commands
            ):
                # Avoidance must leave the blocked corridor earlier than a
                # comfort-oriented ordinary lane change.  The topology anchor
                # has already proved that the adjacent lane is legal.
                prevalidated_avoid_route = build_lane_change_route_reference(
                    world_map,
                    route_anchor.location,
                    args.default_speed_mps,
                    direction="LEFT",
                    distance_m=min(80.0, _scenario_route_distance_m(spec)),
                    transition_start_m=4.0,
                    transition_length_m=20.0,
                )
                topology_route = build_route_reference(
                    world_map,
                    route_anchor.location,
                    args.default_speed_mps,
                    distance_m=_scenario_route_distance_m(spec),
                )
            print(
                f"route anchor: spawn_index={anchor_index} maneuver={maneuver} "
                f"topology_score={anchor_score:.3f} seed_offset_m={seed_offset_m:.1f}"
            )
        traffic_light_distance = _scenario_traffic_light_distance(spec)
        if traffic_light_distance is not None:
            seeded_stop_distance_m = traffic_light_distance + (
                (getattr(args, "evidence_seed", 0) % 5) - 2
            ) * 0.5
            scenario_traffic_light, route_anchor = _traffic_light_scenario_anchor(
                world,
                world_map,
                carla,
                seeded_stop_distance_m,
            )
            traffic_light_original_state = scenario_traffic_light.get_state()
            frozen_getter = getattr(scenario_traffic_light, "is_frozen", None)
            traffic_light_original_frozen = (
                bool(frozen_getter()) if callable(frozen_getter) else False
            )
            configured_light = _scenario_actor(spec, "traffic_light")
            assert configured_light is not None
            configured_state = str(configured_light.get("state", "RED")).strip().title()
            desired_state = getattr(carla.TrafficLightState, configured_state, None)
            if desired_state is None:
                raise ValueError(
                    f"CARLA has no TrafficLightState {configured_state!r}"
                )
            scenario_traffic_light.set_state(desired_state)
            scenario_traffic_light.freeze(True)
            print(
                "scenario actor: bound real traffic light "
                f"id={getattr(scenario_traffic_light, 'id', 'unknown')} "
                f"state={configured_state.upper()} "
                f"stop_distance_m={seeded_stop_distance_m:.2f}",
                flush=True,
            )
        spawn_transform = route_anchor
        if spec is not None:
            local_x, local_y, local_z, local_yaw = spec.ego_spawn_xyzyaw
            anchor_yaw_rad = math.radians(route_anchor.rotation.yaw)
            spawn_transform = carla.Transform(
                carla.Location(
                    x=route_anchor.location.x + local_x * math.cos(anchor_yaw_rad) - local_y * math.sin(anchor_yaw_rad),
                    y=route_anchor.location.y + local_x * math.sin(anchor_yaw_rad) + local_y * math.cos(anchor_yaw_rad),
                    z=route_anchor.location.z + max(0.0, local_z - 0.5),
                ),
                carla.Rotation(
                    pitch=route_anchor.rotation.pitch,
                    yaw=route_anchor.rotation.yaw + local_yaw,
                    roll=route_anchor.rotation.roll,
                ),
            )
        spectator_transform = carla.Transform(
            carla.Location(x=spawn_transform.location.x, y=spawn_transform.location.y,
                           z=spawn_transform.location.z + 25.0),
            carla.Rotation(pitch=-45.0, yaw=spawn_transform.rotation.yaw),
        )
        world.get_spectator().set_transform(spectator_transform)
        try:
            world.wait_for_tick(args.timeout_s)
        except RuntimeError:
            print("warning: map warm-up wait timed out; continuing with synchronous warm-up")

        with CarlaSession(world, fixed_delta_seconds=args.fixed_delta_s) as session:
            for _ in range(args.warmup_frames):
                session.tick(args.timeout_s)
            ego = session.spawn_ego(bp, spawn_transform)
            ego.set_simulate_physics(True)
            # A freshly spawned actor has autopilot disabled. Calling
            # set_autopilot(False) still asks CARLA 0.9.16 to create/connect a
            # Traffic Manager server and can fail when its default port is
            # already occupied, even though this runner never uses TM.
            session.tick(args.timeout_s)
            start_location = ego.get_location()
            origin = (start_location.x, start_location.y, start_location.z)

            scenario_lead = None
            scenario_vehicles: list[tuple[Any, Mapping[str, object]]] = []
            scenario_walkers: list[tuple[Any, Mapping[str, object], Any]] = []
            scenario_props: list[tuple[Any, Mapping[str, object]]] = []
            spawned_scenario_actor_types: list[str] = []
            for vehicle_spec in _scenario_actors(spec, "vehicle"):
                vehicle = _spawn_scenario_vehicle(
                    session, world, carla, ego, bp, vehicle_spec,
                )
                scenario_vehicles.append((vehicle, vehicle_spec))
                spawned_scenario_actor_types.append("vehicle")
            for walker_spec in _scenario_walkers(spec):
                walker, target = _spawn_scenario_walker(
                    session, world, carla, ego, walker_spec,
                )
                scenario_walkers.append((walker, walker_spec, target))
                spawned_scenario_actor_types.append(
                    str(walker_spec.get("type", "walker.pedestrian")).lower()
                )
            for prop_spec in _scenario_static_props(spec):
                prop = _spawn_scenario_static_prop(session, world, carla, ego, prop_spec)
                scenario_props.append((prop, prop_spec))
                spawned_scenario_actor_types.append(
                    str(prop_spec.get("type", "static.prop")).lower()
                )
            scenario_lead = _select_scenario_lead(
                ego, [vehicle for vehicle, _ in scenario_vehicles],
            )
            if args.perception_mode in {"sensors", "world"} and args.scenario in {"follow", "emergency"}:
                lead_distance = args.lead_distance_m if args.scenario == "follow" else args.emergency_distance_m
                scenario_lead = _spawn_static_lead(session, world, world_map, ego, bp, lead_distance)

            perception_bridge = None
            world_events: EventLedger | None = None
            if args.perception_mode == "sensors":
                sensor_profile = getattr(args, "sensor_profile", "default")
                print(
                    f"sensor stage: attaching profile={sensor_profile}",
                    flush=True,
                )
                sensors = attach_default_sensors(
                    session, world, ego, carla,
                    specs=sensor_specs_for_profile(sensor_profile),
                    sensor_tick_s=args.fixed_delta_s,
                )
                c_fusion = ConservativeSensorFusion(SafetyStateParameters(
                    visual_confidence_threshold=args.c_visual_confidence_threshold,
                ))
                perception_bridge = CarlaPerceptionBridge(
                    world, world_map, ego, session, sensors,
                    detector=detector, fusion=c_fusion,
                )
                print("sensor stage: warming up RGB/LiDAR", flush=True)
                _warm_up_sensor_bridge(
                    session, world, perception_bridge,
                    attempts=args.sensor_warmup_frames,
                    tick_timeout_s=args.timeout_s,
                    sensor_timeout_s=args.sensor_timeout_s,
                )
                print("sensor stage: RGB/LiDAR ready", flush=True)
            elif args.perception_mode == "world":
                world_events = attach_event_sensors(
                    session, world, ego, carla,
                ).events

            if live_voice is not None:
                live_voice.start()
                print(
                    "live voice: READY - speak a command, then pause briefly",
                    flush=True,
                )

            # Do not accept a command until required sensors are ready. This
            # guarantees that every accepted command can enter the frame loop
            # and receive an auditable terminal status.
            initial = world.get_snapshot()
            last_sim_time_s = initial.timestamp.elapsed_seconds
            episode_start_s = last_sim_time_s
            timeline = (
                CommandTimeline(spec.commands)
                if spec is not None and not qwen_enabled
                else None
            )
            command: dict[str, object] | None
            if qwen_enabled:
                command = None
            elif spec is None and live_voice is None:
                try:
                    command = _load_command(args)
                except Exception as error:
                    command = _rejected_load_envelope(error)
                    print(f"warning: voice input rejected without changing vehicle control: {error}")
            else:
                command = None
            adapted = None
            if command is not None:
                received_ns = time.monotonic_ns()
                if canonical_bridge is not None:
                    deferred_commands.append(_DeferredCommand(
                        dict(command), received_ns, "INITIAL",
                    ))
                else:
                    adapted = runtime.submit_voice(command, now_s=initial.timestamp.elapsed_seconds)
                    if recorder is not None:
                        recorder.record_command(
                            command,
                            disposition="ACCEPTED" if adapted.control_authorized else "REJECTED_NO_OP",
                            adapted_command=adapted.command,
                            received_ns=received_ns,
                            submitted_sim_time_s=initial.timestamp.elapsed_seconds,
                        )
                        if adapted.feedback is not None:
                            recorder.record_feedback(adapted.feedback)

            turn_direction = "STRAIGHT"
            if adapted is not None and adapted.control_authorized and not adapted.command.requires_confirmation:
                turn_direction = command_turn_direction(command)
            if spec is None:
                route = build_route_reference(
                    world_map, ego, runtime.requested_speed_mps,
                    turn_direction=turn_direction, distance_m=args.route_distance_m,
                )
            elif topology_route is not None:
                route = replace(topology_route, target_speed_mps=runtime.requested_speed_mps)
            else:
                route = RouteReference(
                    spec.world_route(
                        route_anchor.location.x,
                        route_anchor.location.y,
                        route_anchor.rotation.yaw,
                    ),
                    0.0,
                    runtime.requested_speed_mps,
                )

            if spec is None:
                route_index_started_ns = time.monotonic_ns()
                indexed_waypoints = warm_heading_waypoint_cache(world_map)
                print(json.dumps({
                    "record_type": "route_heading_index_ready",
                    "waypoints": indexed_waypoints,
                    "latency_ms": (
                        time.monotonic_ns() - route_index_started_ns
                    ) / 1e6,
                }, ensure_ascii=False), flush=True)

            watchdog = RuntimeWatchdog(
                timeout_s=args.watchdog_timeout_s,
                required_modules=("perception", "control"),
                startup_grace_s=args.watchdog_startup_grace_s,
                started_at_s=time.monotonic(),
            )
            # The synchronous simulator is frozen while ``world.tick()`` is
            # waiting for UE rendering/physics.  Exclude that external frame
            # source wait (and optional visual pacing) from module-health time.
            watchdog.pause(now_s=time.monotonic())
            for step_index in range(args.frames):
                simulator_tick_start_ns = time.monotonic_ns()
                frame = session.tick(args.timeout_s)
                simulator_tick_end_ns = time.monotonic_ns()
                watchdog.resume(now_s=time.monotonic())
                snapshot = world.get_snapshot()
                state = _vehicle_state(ego, frame, snapshot.timestamp.elapsed_seconds, world_map)
                max_speed_mps = max(max_speed_mps, state.speed_mps)
                last_sim_time_s = state.sim_time_s
                elapsed_s = state.sim_time_s - episode_start_s
                if state.speed_mps <= 0.15:
                    if ego_standstill_since_s is None:
                        ego_standstill_since_s = state.sim_time_s
                else:
                    ego_standstill_since_s = None
                standstill_duration_s = (
                    0.0 if ego_standstill_since_s is None
                    else state.sim_time_s - ego_standstill_since_s
                )
                actor_distances_m: dict[str, float] = {}
                for actor, actor_spec in [
                    *scenario_vehicles,
                    *((walker, walker_spec) for walker, walker_spec, _target in scenario_walkers),
                    *scenario_props,
                ]:
                    actor_id = str(actor_spec.get("actor_id", ""))
                    if actor_id:
                        actor_distances_m[actor_id] = float(
                            ego.get_location().distance(actor.get_location())
                        )
                route_progress_m = math.dist(
                    (origin[0], origin[1]), (state.x_m, state.y_m),
                )
                traffic_state = (
                    str(scenario_traffic_light.get_state()).rsplit(".", 1)[-1].upper()
                    if scenario_traffic_light is not None else "UNKNOWN"
                )
                if extension_runtime is not None:
                    extension_frame = extension_runtime.update_frame(
                        elapsed_s=elapsed_s,
                        route_progress_m=route_progress_m,
                        ego_speed_mps=state.speed_mps,
                        ego_standstill_duration_s=standstill_duration_s,
                        actor_distances_m=actor_distances_m,
                        traffic_light_state=traffic_state,
                        distance_to_stop_line_m=None,
                        lane_id=state.lane_id,
                    )
                    light_spec = _scenario_actor(spec, "traffic_light")
                    if light_spec is not None and scenario_traffic_light is not None:
                        light_state = extension_runtime.actor_state(
                            light_spec,
                            elapsed_s=elapsed_s,
                            trigger_context=extension_frame.trigger_context,
                        )["traffic_light_state"]
                        desired_state = getattr(
                            carla.TrafficLightState, str(light_state).title(), None,
                        )
                        if desired_state is not None:
                            scenario_traffic_light.set_state(desired_state)
                            extension_frame.trigger_context["traffic_light_state"] = str(light_state)
                    for fault_id in extension_frame.newly_active_fault_ids:
                        print(json.dumps({
                            "record_type": "scenario_fault",
                            "fault_id": fault_id,
                            "status": "ACTIVE",
                            "elapsed_s": elapsed_s,
                        }, ensure_ascii=False), flush=True)
                    for fault_id in extension_frame.newly_recovered_fault_ids:
                        print(json.dumps({
                            "record_type": "scenario_fault",
                            "fault_id": fault_id,
                            "status": "RECOVERED",
                            "elapsed_s": elapsed_s,
                        }, ensure_ascii=False), flush=True)
                for vehicle, vehicle_spec in scenario_vehicles:
                    actor_state = (
                        extension_runtime.actor_state(
                            vehicle_spec,
                            elapsed_s=elapsed_s,
                            trigger_context=extension_frame.trigger_context,
                        )
                        if extension_runtime is not None else {}
                    )
                    _update_scenario_vehicle(
                        vehicle, vehicle_spec, elapsed_s, carla,
                        desired_speed_mps=actor_state.get("target_speed_mps"),
                    )
                for walker, walker_spec, walker_target in scenario_walkers:
                    walker_behavior = walker_spec.get("behavior", {})
                    walker_trigger = (
                        walker_behavior.get("trigger")
                        if isinstance(walker_behavior, Mapping) else None
                    )
                    walker_ready = (
                        walker_trigger is None
                        or extension_frame is None
                        or scenario_trigger_satisfied(
                            walker_trigger,
                            elapsed_s=elapsed_s,
                            context=extension_frame.trigger_context,
                        )
                    )
                    _update_scenario_walker(
                        walker, walker_spec, elapsed_s, walker_target, carla,
                        trigger_ready=walker_ready,
                    )
                if scenario_vehicles:
                    scenario_lead = _select_scenario_lead(
                        ego, [vehicle for vehicle, _ in scenario_vehicles],
                    )
                if timeline is not None:
                    for scheduled in timeline.due(
                        elapsed_s,
                        None if extension_frame is None else extension_frame.trigger_context,
                    ):
                        scenario_command = resolve_scenario_command(
                            scheduled,
                            requested_speed_mps=runtime.requested_speed_mps,
                            preserve_high_level=(
                                spec is not None and spec.qwen_expected is not None
                            ),
                        )
                        received_ns = time.monotonic_ns()
                        if canonical_bridge is not None:
                            deferred_commands.append(_DeferredCommand(
                                dict(scenario_command), received_ns, "SCENARIO",
                            ))
                        else:
                            scenario_adapted = runtime.submit_voice(
                                scenario_command, now_s=state.sim_time_s,
                            )
                            if recorder is not None:
                                recorder.record_command(
                                    scenario_command,
                                    disposition=("ACCEPTED_SCENARIO" if scenario_adapted.control_authorized
                                                 else "REJECTED_SCENARIO_NO_OP"),
                                    adapted_command=scenario_adapted.command,
                                    received_ns=received_ns,
                                    submitted_sim_time_s=state.sim_time_s,
                                )
                                if scenario_adapted.feedback is not None:
                                    recorder.record_feedback(scenario_adapted.feedback)
                            route = replace(route, target_speed_mps=runtime.requested_speed_mps)
                if live_voice is not None:
                    for live_result in live_voice.poll():
                        if live_result.error is not None:
                            print(json.dumps({
                                "record_type": "live_voice_error",
                                "error": live_result.error,
                            }, ensure_ascii=False), flush=True)
                            continue
                        assert live_result.command is not None
                        live_command = dict(live_result.command)
                        if args.test_command_ttl_s is not None:
                            live_command["valid_duration_s"] = args.test_command_ttl_s
                        received_ns = time.monotonic_ns()
                        if canonical_bridge is not None:
                            deferred_commands.append(_DeferredCommand(
                                live_command, received_ns, "LIVE_MIC", live_result.duration_s,
                            ))
                        else:
                            live_adapted = runtime.submit_voice(
                                live_command, now_s=state.sim_time_s,
                            )
                            if recorder is not None:
                                recorder.record_command(
                                    live_command,
                                    disposition=("ACCEPTED_LIVE_MIC" if live_adapted.control_authorized
                                                 else "REJECTED_LIVE_MIC_NO_OP"),
                                    adapted_command=live_adapted.command,
                                    received_ns=received_ns,
                                    submitted_sim_time_s=state.sim_time_s,
                                )
                                if live_adapted.feedback is not None:
                                    recorder.record_feedback(live_adapted.feedback)
                            print(json.dumps({
                                "record_type": "live_voice_command",
                                "source_text": live_command.get("source_text"),
                                "intent": live_command.get("intent"),
                                "status": live_command.get("status"),
                                "confirm_required": live_command.get("confirm_required"),
                                "control_authorized": live_adapted.control_authorized,
                                "audio_duration_s": round(live_result.duration_s, 2),
                            }, ensure_ascii=False), flush=True)
                            route = replace(
                                route, target_speed_mps=runtime.requested_speed_mps,
                            )
                ego_location = ego.get_location()
                distance_to_route_end_m = math.hypot(
                    ego_location.x - route.points_xy_m[-1][0],
                    ego_location.y - route.points_xy_m[-1][1],
                )
                final_route_end_distance_m = distance_to_route_end_m
                finish_contract_route = (
                    spec is not None
                    and (
                        spec.category == "lateral_B"
                        or spec.expected.get("must_finish_route") is True
                    )
                    and distance_to_route_end_m <= _route_stop_trigger_m(
                        state.speed_mps, spec.finish_radius_m,
                    )
                )
                if finish_contract_route and runtime.requested_speed_mps > 0.0:
                    runtime.requested_speed_mps = 0.0
                    route = replace(route, target_speed_mps=0.0)
                # A live route is already 500 m by default. Re-projecting every
                # N frames can snap an ego at a crossing to a geometrically
                # nearer road whose heading points behind the vehicle. Extend
                # only near the route end and keep a rejected replacement from
                # corrupting the active reference.
                refresh_live_route = (
                    spec is None
                    and distance_to_route_end_m <= max(10.0, state.speed_mps * 5.0)
                )
                extend_finished_scenario_route = (
                    spec is not None
                    and spec.category != "lateral_B"
                    and spec.expected.get("must_finish_route") is not True
                    and distance_to_route_end_m <= 10.0
                )
                route_refresh_alerts: list[str] = []
                if ((refresh_live_route or extend_finished_scenario_route) and not runtime.safety_latched):
                    try:
                        candidate_route = build_route_reference(
                            world_map, ego, runtime.requested_speed_mps,
                            distance_m=args.route_distance_m,
                        )
                        route = candidate_route
                        runtime.lateral.reset()
                    except Exception as error:
                        route_refresh_alerts.append("ROUTE_REFRESH_INVALID")
                        print(json.dumps({
                            "record_type": "route_refresh_rejected",
                            "frame": frame,
                            "error_type": type(error).__name__,
                            "error": str(error),
                            "action": "KEEP_OLD_ROUTE_AND_FAIL_CLOSED",
                        }, ensure_ascii=False), flush=True)

                perception_sources: dict[str, str] = {}
                c_safety_state: dict[str, object] | None = None
                perception_control_override: dict[str, object] | None = None
                c_perception_override_reason: str | None = None
                c_speed_cap_mps: float | None = None
                watchdog_alerts: list[str] = list(route_refresh_alerts)
                sensor_startup_grace = False
                qwen_rgb_measurement: Any | None = None
                current_rgb: Any | None = None
                perception_start_ns = time.monotonic_ns()
                try:
                    if perception_bridge is not None:
                        sample = perception_bridge.acquire(
                            frame, state.sim_time_s, route=route, timeout_s=args.sensor_timeout_s,
                        )
                        scene = sample.frame
                        qwen_rgb_measurement = sample.rgb
                        current_rgb = sample.rgb
                        perception_sources = dict(sample.source_by_field)
                        c_safety_state = sample.safety_summary.to_dict()
                        c_speed_cap_mps = _c_safety_speed_cap_mps(c_safety_state)
                        if c_speed_cap_mps is not None:
                            perception_sources["c_speed_cap_mps"] = (
                                "C_FUSION_TEMPORARY_VRU_SPEED_CAP"
                            )
                            cap_override = _c_speed_cap_control_override(
                                state.speed_mps, c_speed_cap_mps,
                            )
                            if cap_override is not None:
                                perception_control_override = cap_override
                                c_perception_override_reason = "C_VRU_SPEED_CAP_BRAKE"
                                perception_sources["c_control_override"] = (
                                    "C_FUSION_VRU_SPEED_CAP_BRAKE"
                                )
                        if sample.safety_summary.fail_closed:
                            # C owns this perception-dependent control request;
                            # it is not a runtime-health failure.  Feed a full
                            # brake request through D for this frame without
                            # poisoning the persistent watchdog latch.
                            perception_control_override = {
                                "throttle": 0.0,
                                "brake": 1.0,
                                "steer": 0.0,
                            }
                            c_perception_override_reason = _c_perception_safety_reason(c_safety_state)
                            perception_sources["c_control_override"] = (
                                "C_FUSION_" + sample.safety_summary.reason.upper()
                            )
                    else:
                        scene, perception_sources = _scene_from_world(
                            world_map,
                            ego,
                            frame,
                            state.sim_time_s,
                            route=route,
                            scenario_lead=scenario_lead,
                            scenario_vehicles=tuple(
                                vehicle for vehicle, _spec in scenario_vehicles
                            ),
                            events=world_events,
                        )
                        if args.perception_mode == "virtual":
                            scene = _apply_virtual_scenario(scene, ego, origin, args)
                            perception_sources["scenario"] = "VIRTUAL_ACCEPTANCE_TRUTH"
                            if args.scenario == "red_stop":
                                perception_sources["traffic_light"] = "VIRTUAL_ACCEPTANCE_TRUTH"
                                perception_sources["distance_to_stop_line_m"] = "VIRTUAL_ACCEPTANCE_TRUTH"
                            elif args.scenario in {"follow", "emergency"}:
                                perception_sources["lead_distance_m"] = "VIRTUAL_ACCEPTANCE_TRUTH"
                                perception_sources["lead_speed_mps"] = "VIRTUAL_ACCEPTANCE_TRUTH"
                        else:
                            perception_sources["scenario"] = "CARLA_WORLD_TRUTH"
                    if scenario_traffic_light is not None:
                        scene, traffic_sources = _scenario_traffic_light_observation(
                            scene, ego, scenario_traffic_light,
                        )
                        perception_sources.update(traffic_sources)
                    if spec is not None:
                        configured_scene = _scenario_facts(
                            ego,
                            origin,
                            spec,
                            frame=frame,
                            sim_time_s=state.sim_time_s,
                            elapsed_s=elapsed_s,
                        )
                        scene, fact_sources = _select_scene_facts(
                            scene, configured_scene, args.scenario_facts_mode,
                        )
                        perception_sources.update(fact_sources)
                    if extension_frame is not None:
                        active_sensor_faults = {
                            str(item.get("sensor", ""))
                            for item in extension_frame.active_faults
                            if str(item.get("type", "")).lower() in {
                                "sensor_blackout", "sensor_stale",
                            }
                        }
                        for sensor_name in sorted(active_sensor_faults):
                            perception_sources[f"fault_{sensor_name}"] = "SCENARIO_FAULT_ACTIVE"
                        if {"front_rgb", "lidar"}.issubset(active_sensor_faults):
                            perception_control_override = {
                                "throttle": 0.0, "brake": 1.0, "steer": 0.0,
                            }
                            c_perception_override_reason = "SCENARIO_PERCEPTION_INSUFFICIENT"
                        if any(
                            str(item.get("type", "")).lower() == "actor_visibility"
                            and item.get("visible") is False
                            for item in extension_frame.active_faults
                        ):
                            scene = replace(scene, detected_objects=())
                            perception_sources["actor_visibility"] = "SCENARIO_TARGET_OCCLUDED"
                    watchdog.heartbeat("perception", now_s=time.monotonic())
                except PerceptionAcquisitionError as error:
                    scene = PerceptionFrame(frame, state.sim_time_s)
                    perception_sources = {"failure": type(error).__name__}
                    sensor_startup_grace = step_index < args.sensor_startup_grace_frames
                    if not sensor_startup_grace:
                        watchdog_alerts.append(f"PERCEPTION_{type(error).__name__.upper()}")

                if qwen_bridge is not None:
                    if not qwen_submitted and qwen_rgb_measurement is not None:
                        run_token = (
                            recorder.run_id
                            if recorder is not None and recorder.run_id is not None
                            else str(time.monotonic_ns())
                        )
                        qwen_request_id = f"qwen-{run_token}-{frame}"
                        rgb_ref = _save_qwen_rgb_image(
                            qwen_rgb_measurement,
                            qwen_image_root,
                            request_id=qwen_request_id,
                        )
                        qwen_context = _build_qwen_context(
                            request_id=qwen_request_id,
                            voice_command=qwen_voice_text,
                            rgb_ref=rgb_ref,
                            state=state,
                            scene=scene,
                            behavior_state=runtime.fsm.state.value,
                            desired_speed_mps=qwen_desired_speed_mps,
                            route_end_distance_m=distance_to_route_end_m,
                            c_safety_state=c_safety_state,
                        )
                        qwen_bridge.submit(qwen_context, now_s=state.sim_time_s)
                        qwen_submitted = True
                        qwen_status = "PENDING"
                        if recorder is not None:
                            recorder.record_qwen_event(
                                request_id=qwen_request_id,
                                status="PENDING",
                                context=qwen_context.to_payload(),
                            )
                        print(
                            f"qwen stage: submitted request_id={qwen_request_id} frame={frame}",
                            flush=True,
                        )

                    # A terminal result is consumed exactly once. Continuing to
                    # poll a READY result would eventually reclassify the
                    # already-submitted command as STALE after its decision TTL.
                    qwen_result = (
                        qwen_bridge.latest(now_s=state.sim_time_s)
                        if qwen_submitted and not qwen_terminal_recorded
                        else None
                    )
                    if qwen_result is not None:
                        qwen_status = qwen_result.status
                        if qwen_result.ready and not qwen_terminal_recorded:
                            runtime.clear_safety_alerts(("QWEN_PENDING",))
                            if qwen_result.runtime_command is None:
                                raise RuntimeError("ready Qwen result has no runtime command")
                            high_level = dict(qwen_result.high_level_command or {})
                            runtime_command = dict(qwen_result.runtime_command)
                            qwen_action = str(high_level.get("action", "")).strip().upper()
                            qwen_source = str(
                                high_level.get("decision_source", "")
                            ).strip().upper()
                            if (
                                qwen_source == "SAFETY_RULE"
                                and qwen_action in {"STOP", "EMERGENCY_STOP"}
                            ):
                                # This is a D-owned high-level safety
                                # intervention, even when no additional
                                # frame-level brake override is required.
                                safety_reasons.add("QWEN_SAFETY_RULE")
                            if str(high_level.get("action", "")).upper() == "START":
                                runtime.requested_speed_mps = qwen_desired_speed_mps
                            received_ns = time.monotonic_ns()
                            qwen_adapted = runtime.submit_voice(
                                runtime_command,
                                now_s=state.sim_time_s,
                            )
                            if not qwen_adapted.control_authorized:
                                qwen_status = "ERROR"
                                watchdog_alerts.append("QWEN_ERROR")
                            else:
                                qwen_ready = True
                                route = replace(
                                    route,
                                    target_speed_mps=runtime.requested_speed_mps,
                                )
                            if recorder is not None:
                                recorder.record_qwen_event(
                                    request_id=qwen_request_id or "unknown-qwen-request",
                                    status="READY" if qwen_ready else "ERROR",
                                    high_level_command=high_level,
                                    runtime_command=runtime_command,
                                    trace=None if qwen_adapter is None else qwen_adapter.last_trace,
                                    error=None if qwen_ready else "Qwen command rejected by A boundary",
                                )
                                recorder.record_command(
                                    runtime_command,
                                    disposition=(
                                        "ACCEPTED_QWEN_REMOTE"
                                        if qwen_adapted.control_authorized
                                        else "REJECTED_QWEN_REMOTE_NO_OP"
                                    ),
                                    adapted_command=qwen_adapted.command,
                                    received_ns=received_ns,
                                    submitted_sim_time_s=state.sim_time_s,
                                )
                                if qwen_adapted.feedback is not None:
                                    recorder.record_feedback(qwen_adapted.feedback)
                            qwen_terminal_recorded = True
                            print(
                                "qwen stage: decision "
                                + json.dumps(high_level, ensure_ascii=False, sort_keys=True),
                                flush=True,
                            )
                        elif not qwen_result.ready:
                            watchdog_alerts.extend(qwen_result.watchdog_alerts)
                            if (
                                qwen_result.status in {"TIMEOUT", "STALE", "ERROR"}
                                and not qwen_terminal_recorded
                            ):
                                if recorder is not None:
                                    recorder.record_qwen_event(
                                        request_id=qwen_request_id or "unknown-qwen-request",
                                        status=qwen_result.status,
                                        trace=None if qwen_adapter is None else qwen_adapter.last_trace,
                                        error=qwen_result.error,
                                    )
                                qwen_terminal_recorded = True
                                print(
                                    f"qwen stage: {qwen_result.status} error={qwen_result.error}",
                                    flush=True,
                                )
                    perception_sources["qwen_status"] = qwen_status
                sensor_ready_ns = time.monotonic_ns()
                if canonical_bridge is not None:
                    canonical_mode = (
                        "sensor_failure" if "failure" in perception_sources
                        else args.perception_mode
                    )
                    if (
                        canonical_mode == "sensors"
                        and perception_sources.get("radar_modality")
                        == "CARLA_RADAR_FRAME_ALIGNED"
                    ):
                        canonical_mode = "sensors_radar"
                    queued_now = tuple(deferred_commands)
                    deferred_commands.clear()
                    for deferred in queued_now:
                        rgb_ref = None
                        staged_command_id = str(
                            deferred.envelope.get("command_id", "")
                        )
                        if current_rgb is not None and qwen_image_stager is not None:
                            rgb_ref = qwen_image_stager.stage(
                                staged_command_id, current_rgb, frame_id=frame,
                            )
                        submission = canonical_bridge.submit(
                            deferred.envelope,
                            scene,
                            state,
                            sim_time_s=state.sim_time_s,
                            perception_mode=canonical_mode,
                            received_at_ns=deferred.received_ns,
                            rgb_ref=rgb_ref,
                            runtime_state=_planner_runtime_state(
                                world_map, ego, scene, route,
                            ),
                        )
                        if extension_runtime is not None:
                            extension_runtime.note_command_submitted(
                                deferred.envelope,
                                qwen=submission.orchestration.disposition == "SLOW_PENDING",
                            )
                            if submission.orchestration.feedback is not None:
                                _note_extension_terminal(
                                    extension_runtime, submission.orchestration.feedback,
                                )
                        if qwen_scenario_monitor is not None:
                            observed_route = (
                                "FAST_LOCAL"
                                if submission.orchestration.disposition == "FAST"
                                else "CONFIRM_SAFE"
                                if submission.orchestration.disposition == "CONFIRM_SAFE"
                                else "QWEN_PLAN"
                            )
                            qwen_scenario_monitor.record_routing(
                                observed_route,
                                qwen_submitted=(
                                    submission.orchestration.disposition == "SLOW_PENDING"
                                ),
                                command_id=submission.orchestration.command_id,
                            )
                            control_command = submission.orchestration.control_command
                            if control_command is not None:
                                qwen_scenario_monitor.record_behavior(
                                    control_command["behavior"],
                                )
                            elif submission.orchestration.disposition == "SLOW_PENDING":
                                # The bridge installs a deterministic STOP while
                                # Qwen is pending.  At the maneuver-contract level
                                # this is the observable HOLD behavior.
                                qwen_scenario_monitor.record_behavior("HOLD")
                            feedback = submission.orchestration.feedback
                            if feedback is not None:
                                qwen_scenario_monitor.record_terminal(
                                    feedback["status"], command_id=feedback["command_id"],
                                )
                        if (
                            qwen_image_stager is not None
                            and submission.orchestration.disposition != "SLOW_PENDING"
                        ):
                            qwen_image_stager.discard(staged_command_id)
                        runtime_adapted = submission.runtime_adapted
                        if recorder is not None:
                            recorder.record_command(
                                deferred.envelope,
                                disposition=(
                                    f"{deferred.origin}_{submission.orchestration.disposition}"
                                ),
                                adapted_command=(
                                    None if runtime_adapted is None
                                    else runtime_adapted.command
                                ),
                                received_ns=deferred.received_ns,
                                submitted_sim_time_s=state.sim_time_s,
                            )
                            recorder.record_canonical_routing(
                                phase="SUBMIT",
                                command_id=submission.orchestration.command_id,
                                payload={
                                    "canonical_command": submission.canonical_command,
                                    "perception_state": submission.perception_state,
                                    "orchestration": submission.orchestration,
                                },
                            )
                            if submission.safety_envelope is not None:
                                recorder.record_command(
                                    submission.safety_envelope,
                                    disposition="INTERNAL_QWEN_WAIT_STOP",
                                    adapted_command=(
                                        None if submission.safety_adapted is None
                                        else submission.safety_adapted.command
                                    ),
                                    received_ns=sensor_ready_ns,
                                    submitted_sim_time_s=state.sim_time_s,
                                )
                            for feedback in submission.feedbacks:
                                recorder.record_feedback(feedback)
                                _note_extension_terminal(extension_runtime, feedback)
                            if (
                                submission.safety_adapted is not None
                                and submission.safety_adapted.feedback is not None
                            ):
                                recorder.record_feedback(submission.safety_adapted.feedback)
                        queue_snapshot = submission.orchestration.queues
                        print(json.dumps({
                            "record_type": "canonical_command_route",
                            "origin": deferred.origin,
                            "command_id": submission.orchestration.command_id,
                            "source_text": deferred.envelope.get("source_text"),
                            "intent": submission.canonical_command["intent"],
                            "disposition": submission.orchestration.disposition,
                            "reason_code": submission.orchestration.reason_code,
                            "queues": (
                                None if queue_snapshot is None
                                else asdict(queue_snapshot)
                            ),
                        }, ensure_ascii=False), flush=True)
                        if deferred.origin == "LIVE_MIC":
                            print(json.dumps({
                                "record_type": "live_voice_command",
                                "source_text": deferred.envelope.get("source_text"),
                                "intent": deferred.envelope.get("intent"),
                                "status": deferred.envelope.get("status"),
                                "confirm_required": deferred.envelope.get("confirm_required"),
                                "control_authorized": (
                                    runtime_adapted is not None
                                    and runtime_adapted.control_authorized
                                ),
                                "routing_disposition": submission.orchestration.disposition,
                                "audio_duration_s": (
                                    None if deferred.audio_duration_s is None
                                    else round(deferred.audio_duration_s, 2)
                                ),
                            }, ensure_ascii=False), flush=True)

                    resolutions = canonical_bridge.poll(
                        scene,
                        state,
                        sim_time_s=state.sim_time_s,
                        perception_mode=canonical_mode,
                        captured_at_ns=sensor_ready_ns,
                    )
                    for resolution in resolutions:
                        if qwen_image_stager is not None:
                            qwen_image_stager.discard(resolution.command_id)
                        if recorder is not None:
                            recorder.record_canonical_routing(
                                phase="RESOLVE",
                                command_id=resolution.command_id,
                                payload=resolution,
                            )
                            for feedback in resolution.feedbacks:
                                recorder.record_feedback(feedback)
                                _note_extension_terminal(extension_runtime, feedback)
                            if resolution.vehicle_feedback is not None:
                                recorder.record_feedback(resolution.vehicle_feedback)
                        if qwen_scenario_monitor is not None:
                            orchestration = resolution.orchestration
                            if orchestration is not None and orchestration.decision_plan is not None:
                                qwen_scenario_monitor.record_plan(orchestration.decision_plan)
                            if orchestration is not None and orchestration.compiled_plan is not None:
                                for compiled_step in orchestration.compiled_plan.get("steps", ()):
                                    if isinstance(compiled_step, Mapping):
                                        qwen_scenario_monitor.record_behavior(
                                            compiled_step.get("behavior", ""),
                                        )
                            for feedback in resolution.feedbacks:
                                qwen_scenario_monitor.record_terminal(
                                    feedback["status"], command_id=feedback["command_id"],
                                )
                        for feedback in resolution.feedbacks:
                            _note_extension_terminal(extension_runtime, feedback)
                        orchestration = resolution.orchestration
                        if extension_runtime is not None and orchestration is not None:
                            if orchestration.decision_plan is not None:
                                extension_runtime.note_qwen_plan(orchestration.decision_plan)
                            if orchestration.compiled_plan is not None:
                                extension_runtime.note_qwen_plan(orchestration.compiled_plan)
                        if (
                            orchestration is not None
                            and orchestration.compiled_plan is not None
                            and resolution.disposition == "SLOW_READY"
                        ):
                            try:
                                compiled_contract = _compiled_plan_from_payload(
                                    orchestration.compiled_plan,
                                )
                                maneuver_update = maneuver_fsm.start(
                                    compiled_contract,
                                    now_s=state.sim_time_s,
                                )
                                maneuver_start_xy = (state.x_m, state.y_m)
                                maneuver_start_yaw_deg = state.yaw_deg
                                maneuver_junction_seen = False
                                maneuver_target_seen = _maneuver_target_visible(
                                    maneuver_fsm.current_step, scene,
                                )
                                grounded_distances = tuple(
                                    item.distance_m
                                    for item in scene.detected_objects
                                    if item.distance_m is not None
                                )
                                maneuver_target_pass_after_m = (
                                    max(10.0, min(grounded_distances) + 8.0)
                                    if grounded_distances
                                    else None
                                )
                                maneuver_route_steps_applied.clear()
                                maneuver_lane_ids = {"CURRENT": state.lane_id}
                                plan_waypoint = world_map.get_waypoint(
                                    ego.get_location(), project_to_road=True,
                                )
                                if plan_waypoint is not None:
                                    left_lane = plan_waypoint.get_left_lane()
                                    right_lane = plan_waypoint.get_right_lane()
                                    if left_lane is not None:
                                        maneuver_lane_ids["LEFT_ADJACENT"] = str(left_lane.lane_id)
                                    if right_lane is not None:
                                        maneuver_lane_ids["RIGHT_ADJACENT"] = str(right_lane.lane_id)
                                _record_maneuver_update(
                                    maneuver_update,
                                    monitor=qwen_scenario_monitor,
                                    recorder=recorder,
                                )
                                route, compiled_speed, route_behavior = _apply_compiled_plan_route(
                                    orchestration.compiled_plan,
                                    world_map=world_map,
                                    ego=ego,
                                    current_route=route,
                                    requested_speed_mps=runtime.requested_speed_mps,
                                    distance_m=(
                                        args.route_distance_m
                                        if spec is None
                                        else _scenario_route_distance_m(spec)
                                    ),
                                    prevalidated_maneuver_route=(
                                        prevalidated_avoid_route or topology_route
                                    ),
                                )
                                runtime.requested_speed_mps = compiled_speed
                                if route_behavior is not None:
                                    first_route_step = next(
                                        (
                                            step.step_id
                                            for step in compiled_contract.steps
                                            if step.behavior in {
                                                "TURN_LEFT", "TURN_RIGHT",
                                                "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT",
                                            }
                                        ),
                                        None,
                                    )
                                    if first_route_step is not None:
                                        maneuver_route_steps_applied.add(first_route_step)
                                print(json.dumps({
                                    "record_type": "qwen_plan_route_applied",
                                    "command_id": resolution.command_id,
                                    "plan_id": orchestration.compiled_plan.get("plan_id"),
                                    "route_behavior": route_behavior,
                                    "target_speed_mps": compiled_speed,
                                    "compiled_steps": len(
                                        orchestration.compiled_plan.get("steps", ())
                                    ),
                                }, ensure_ascii=False), flush=True)
                            except (AttributeError, KeyError, TypeError, ValueError, RuntimeError) as error:
                                watchdog_alerts.append("QWEN_PLAN_ROUTE_INFEASIBLE")
                                print(json.dumps({
                                    "record_type": "qwen_plan_route_rejected",
                                    "command_id": resolution.command_id,
                                    "error": f"{type(error).__name__}: {error}",
                                }, ensure_ascii=False), flush=True)
                        print(json.dumps({
                            "record_type": "canonical_slow_result",
                            "command_id": resolution.command_id,
                            "disposition": resolution.disposition,
                            "feedback": list(resolution.feedbacks),
                            "runtime_intent": (
                                None if resolution.runtime_envelope is None
                                else resolution.runtime_envelope.get("intent")
                            ),
                        }, ensure_ascii=False), flush=True)
                    if queued_now or resolutions:
                        route = replace(
                            route, target_speed_mps=runtime.requested_speed_mps,
                        )
                    perception_sources["canonical_state"] = (
                        "PERCEPTION_STATE_V1_" + canonical_mode.upper()
                    )
                if not sensor_startup_grace and watchdog.check(now_s=time.monotonic()) is not None:
                    watchdog_alerts.append("RUNTIME_WATCHDOG_TIMEOUT")

                command_id = runtime.active_command_id
                decision_start_ns = time.monotonic_ns()
                raw_control_override = None
                if not raw_control_fault_injected:
                    raw_control_override = _scenario_raw_control_fault(spec, elapsed_s)
                    raw_control_fault_injected = raw_control_override is not None
                if extension_frame is not None:
                    steer_fault = next((
                        item for item in extension_frame.active_faults
                        if str(item.get("type", "")).lower() == "steer_bias"
                    ), None)
                    if steer_fault is not None:
                        raw_control_override = {
                            "throttle": 0.10,
                            "brake": 0.0,
                            "steer": float(steer_fault.get("value", 0.0)),
                            "fault_injected": True,
                        }
                if raw_control_override is None:
                    raw_control_override = perception_control_override
                effective_route = route
                extension_speed_cap_mps = (
                    None if extension_frame is None else extension_frame.speed_limit_mps
                )
                active_speed_cap_mps = min(
                    value for value in (c_speed_cap_mps, extension_speed_cap_mps)
                    if value is not None
                ) if any(
                    value is not None for value in (c_speed_cap_mps, extension_speed_cap_mps)
                ) else None
                if active_speed_cap_mps is not None:
                    effective_route = replace(
                        route, target_speed_mps=min(route.target_speed_mps, active_speed_cap_mps),
                    )
                result = runtime.step(
                    state, scene, effective_route, dt_s=args.fixed_delta_s,
                    watchdog_alerts=tuple(watchdog_alerts),
                    raw_control_override=raw_control_override,
                    speed_cap_mps=active_speed_cap_mps,
                    safety_override_reason=c_perception_override_reason,
                )
                if qwen_scenario_monitor is not None:
                    for feedback in result.feedback:
                        qwen_scenario_monitor.record_terminal(
                            feedback.status,
                            command_id=feedback.command_id,
                            reason_code=(
                                result.safety_reason
                                if str(getattr(feedback.status, "value", feedback.status)).upper()
                                == "SAFETY_OVERRIDE"
                                else None
                            ),
                        )
                for feedback in result.feedback:
                    _note_extension_terminal(extension_runtime, feedback)
                if sensor_startup_grace:
                    result = replace(
                        result,
                        final_control=ControlOutput(0.0, 1.0, 0.0),
                        safety_reason="PERCEPTION_STARTUP_GRACE",
                        safety_override=True,
                    )
                elif c_perception_override_reason is not None and not result.safety_override:
                    result = replace(
                        result,
                        safety_reason=c_perception_override_reason,
                        safety_override=True,
                    )
                if (
                    maneuver_fsm.plan is not None
                    and maneuver_fsm.state not in TERMINAL_STATES
                ):
                    plan_capabilities = _planner_runtime_state(
                        world_map, ego, scene, route,
                    )
                    current_waypoint = world_map.get_waypoint(
                        ego.get_location(), project_to_road=True,
                    )
                    current_is_junction = bool(
                        getattr(current_waypoint, "is_junction", False)
                    )
                    maneuver_junction_seen = (
                        maneuver_junction_seen or current_is_junction
                    )
                    lane_label = next(
                        (
                            label
                            for label, lane_id in maneuver_lane_ids.items()
                            if lane_id == state.lane_id
                        ),
                        state.lane_id,
                    )
                    heading_change_deg = (
                        0.0
                        if maneuver_start_yaw_deg is None
                        else abs(
                            (state.yaw_deg - maneuver_start_yaw_deg + 180.0)
                            % 360.0 - 180.0
                        )
                    )
                    target_visible = _maneuver_target_visible(
                        maneuver_fsm.current_step, scene,
                    )
                    maneuver_target_seen = maneuver_target_seen or target_visible
                    distance_from_plan_start_m = (
                        0.0
                        if maneuver_start_xy is None
                        else math.dist(
                            maneuver_start_xy,
                            (state.x_m, state.y_m),
                        )
                    )
                    terminal_safety = (
                        result.safety_reason.startswith("C_FRONT_")
                        or result.safety_reason in {
                            "COLLISION_DETECTED",
                            "RISK_EMERGENCY_BRAKE_REQUESTED",
                            "LOW_TTC",
                            "EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE",
                            "RED_LIGHT_STOP_LINE_GUARD",
                        }
                    )
                    maneuver_update = maneuver_fsm.update(
                        {
                            **plan_capabilities,
                            "perception_fresh": not sensor_startup_grace,
                            "no_emergency_risk": not terminal_safety,
                            "emergency": terminal_safety,
                            "emergency_reason": result.safety_reason,
                            "risk_level": "EMERGENCY" if terminal_safety else "LOW",
                            "speed_mps": state.speed_mps,
                            "lane": lane_label,
                            "lateral_error_m": scene.lane_offset_m or 0.0,
                            "junction_exited": (
                                maneuver_junction_seen
                                and not current_is_junction
                                and heading_change_deg >= 25.0
                            ),
                            "target_visible": target_visible,
                            "target_seen": maneuver_target_seen,
                            "target_passed": (
                                maneuver_target_seen
                                and (
                                    (
                                        not target_visible
                                        and distance_from_plan_start_m >= 10.0
                                    )
                                    or (
                                        maneuver_target_pass_after_m is not None
                                        and distance_from_plan_start_m
                                        >= maneuver_target_pass_after_m
                                    )
                                )
                            ),
                            "hold_condition": True,
                        },
                        now_s=state.sim_time_s,
                    )
                    _record_maneuver_update(
                        maneuver_update,
                        monitor=qwen_scenario_monitor,
                        recorder=recorder,
                    )
                    started_route_step = (
                        maneuver_update.current_step
                        if any(
                            event.event_type == "qwen_step_started"
                            for event in maneuver_update.events
                        )
                        and maneuver_update.current_step is not None
                        and maneuver_update.current_step.behavior in {
                            "TURN_LEFT", "TURN_RIGHT",
                            "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT",
                        }
                        and maneuver_update.current_step.step_id
                        not in maneuver_route_steps_applied
                        else None
                    )
                    if started_route_step is not None:
                        try:
                            step_speed = started_route_step.target.get(
                                "target_speed_mps",
                            )
                            if step_speed is not None:
                                runtime.requested_speed_mps = float(step_speed)
                            if started_route_step.behavior.startswith("TURN_"):
                                route = build_route_reference(
                                    world_map,
                                    ego,
                                    runtime.requested_speed_mps,
                                    turn_direction=started_route_step.behavior.rsplit("_", 1)[-1],
                                    distance_m=(
                                        args.route_distance_m
                                        if spec is None
                                        else _scenario_route_distance_m(spec)
                                    ),
                                )
                            else:
                                route = build_lane_change_route_reference(
                                    world_map,
                                    ego,
                                    runtime.requested_speed_mps,
                                    direction=started_route_step.behavior.rsplit("_", 1)[-1],
                                    distance_m=min(
                                        80.0,
                                        args.route_distance_m
                                        if spec is None
                                        else _scenario_route_distance_m(spec),
                                    ),
                                )
                            maneuver_route_steps_applied.add(started_route_step.step_id)
                            print(json.dumps({
                                "record_type": "qwen_step_route_applied",
                                "command_id": maneuver_fsm.plan.command_id,
                                "plan_id": maneuver_fsm.plan.plan_id,
                                "step_id": started_route_step.step_id,
                                "route_behavior": started_route_step.behavior,
                            }, ensure_ascii=False), flush=True)
                        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                            failed_update = maneuver_fsm.fail(
                                "STEP_ROUTE_INFEASIBLE",
                                now_s=state.sim_time_s,
                            )
                            _record_maneuver_update(
                                failed_update,
                                monitor=qwen_scenario_monitor,
                                recorder=recorder,
                            )
                            watchdog_alerts.append("QWEN_STEP_ROUTE_INFEASIBLE")
                            print(json.dumps({
                                "record_type": "qwen_step_route_rejected",
                                "command_id": maneuver_fsm.plan.command_id,
                                "plan_id": maneuver_fsm.plan.plan_id,
                                "step_id": started_route_step.step_id,
                                "error": f"{type(error).__name__}: {error}",
                            }, ensure_ascii=False), flush=True)
                if result.safety_override and not (
                    qwen_enabled
                    and qwen_status == "PENDING"
                    and result.safety_reason == "WATCHDOG_ALERT"
                ):
                    safety_reasons.add(result.safety_reason)
                decision_end_ns = time.monotonic_ns()
                ego.apply_control(carla.VehicleControl(
                    throttle=result.final_control.throttle,
                    brake=result.final_control.brake,
                    steer=result.final_control.steer,
                    hand_brake=False, reverse=False, manual_gear_shift=False,
                ))
                if args.follow_spectator or args.live_mic:
                    _follow_ego_spectator(world, ego, carla)
                control_applied_ns = time.monotonic_ns()
                watchdog.heartbeat("control", now_s=time.monotonic())
                timing = FrameTiming(
                    sensor_ready_ns=sensor_ready_ns,
                    decision_start_ns=decision_start_ns,
                    decision_end_ns=decision_end_ns,
                    control_applied_ns=control_applied_ns,
                    simulator_tick_start_ns=simulator_tick_start_ns,
                    simulator_tick_end_ns=simulator_tick_end_ns,
                    perception_start_ns=perception_start_ns,
                )
                if recorder is not None:
                    recorder.record_runtime_frame(
                        result, scene,
                        raw_control=result.raw_control or result.final_control,
                        timing=timing,
                        command_id=command_id,
                        fsm_state=runtime.fsm.state.value,
                        perception_sources=perception_sources,
                        c_safety_state=c_safety_state,
                    )

                frames_completed += 1
                final_state, final_scene = state, scene
                collision_seen = collision_seen or scene.collision
                if scene.lead_distance_m is not None:
                    min_gap_m = scene.lead_distance_m if min_gap_m is None else min(min_gap_m, scene.lead_distance_m)
                record = {
                    "record_type": "frame", "scenario": args.scenario,
                    "perception_mode": args.perception_mode, "frame": frame,
                    "sim_time_s": state.sim_time_s, "elapsed_s": elapsed_s,
                    "speed_mps": state.speed_mps, "x_m": state.x_m, "y_m": state.y_m,
                    "z_m": state.z_m, "yaw_deg": state.yaw_deg, "lane_id": state.lane_id,
                    "target_speed_mps": None if result.longitudinal is None else result.longitudinal.target_speed_mps,
                    "longitudinal_state": None if result.longitudinal is None else result.longitudinal.state,
                    "ttc_s": None if result.longitudinal is None else result.longitudinal.risk.ttc_s,
                    "lead_distance_m": scene.lead_distance_m,
                    "distance_to_stop_line_m": scene.distance_to_stop_line_m,
                    "control": result.final_control.to_dict(), "safety": result.safety_reason,
                    "safety_override": result.safety_override,
                    "qwen_status": qwen_status,
                }
                if step_index % args.print_every == 0 or step_index == args.frames - 1:
                    print(json.dumps(record, ensure_ascii=False))
                watchdog.pause(now_s=time.monotonic())
                if args.realtime:
                    # ``--realtime`` targets one wall-clock period per frame;
                    # it must not add a full period after tick+control work.
                    active_wall_s = (
                        time.monotonic_ns() - simulator_tick_start_ns
                    ) / 1e9
                    remaining_s = args.fixed_delta_s - active_wall_s
                    if remaining_s > 0.0:
                        time.sleep(remaining_s)

        if canonical_bridge is not None:
            unresolved = canonical_bridge.fail_all_pending(
                sim_time_s=last_sim_time_s,
                emitted_at_ns=time.monotonic_ns(),
            )
            for resolution in unresolved:
                if qwen_image_stager is not None:
                    qwen_image_stager.discard(resolution.command_id)
                if recorder is not None:
                    recorder.record_canonical_routing(
                        phase="RUNTIME_END",
                        command_id=resolution.command_id,
                        payload=resolution,
                    )
                    for feedback in resolution.feedbacks:
                        recorder.record_feedback(feedback)
                    if resolution.vehicle_feedback is not None:
                        recorder.record_feedback(resolution.vehicle_feedback)
                if qwen_scenario_monitor is not None:
                    for feedback in resolution.feedbacks:
                        qwen_scenario_monitor.record_terminal(
                            feedback["status"], command_id=feedback["command_id"],
                        )
                print(json.dumps({
                    "record_type": "canonical_slow_result",
                    "command_id": resolution.command_id,
                    "disposition": resolution.disposition,
                    "feedback": list(resolution.feedbacks),
                    "runtime_intent": None,
                }, ensure_ascii=False), flush=True)

        if maneuver_fsm.plan is not None and maneuver_fsm.state not in TERMINAL_STATES:
            _record_maneuver_update(
                maneuver_fsm.fail("RUNTIME_ENDED", now_s=last_sim_time_s),
                monitor=qwen_scenario_monitor,
                recorder=recorder,
            )

        final_speed = None if final_state is None else final_state.speed_mps
        expected_completion = None if spec is None else _expected_safety_completed(
            spec,
            frames=frames_completed,
            final_speed_mps=final_speed,
            collision_seen=collision_seen,
            safety_reasons=safety_reasons,
        )
        command_finished = runtime is None or runtime.active_command_id is None
        if not command_finished and runtime is not None:
            detail = (
                "scenario safety constraints prevented command completion before frame budget ended"
                if expected_completion is True
                else "scenario frame budget ended before command completion"
            )
            feedback = runtime.fail_active(
                now_s=last_sim_time_s,
                detail=detail,
            )
            if feedback is not None and recorder is not None:
                recorder.record_feedback(feedback)
        completion = expected_completion if expected_completion is not None else (
            command_finished and _runtime_health_completed(safety_reasons) and _scenario_completed(
                args, frames=frames_completed,
                final_speed_mps=final_speed,
                final_scene=final_scene, min_gap_m=min_gap_m,
                collision_seen=collision_seen, max_speed_mps=max_speed_mps,
            )
        )
        route_contract_completion = _route_contract_completed(spec, final_route_end_distance_m)
        if route_contract_completion is not None:
            completion = completion and route_contract_completion
        gap_contract_completion = _minimum_gap_contract_completed(spec, min_gap_m)
        if gap_contract_completion is not None:
            completion = completion and gap_contract_completion
        if qwen_enabled:
            completion = completion and qwen_ready and qwen_status == "READY"
        if qwen_scenario_monitor is not None:
            qwen_contract_report = qwen_scenario_monitor.finalize()
            completion = completion and qwen_contract_report.passed
            print(json.dumps({
                "record_type": "qwen_scenario_acceptance",
                **qwen_contract_report.to_dict(),
            }, ensure_ascii=False), flush=True)
        extension_report = None
        if extension_runtime is not None:
            proposed = spec.extensions.get("proposed_acceptance", {})
            if not isinstance(proposed, Mapping):
                raise TypeError("extensions.proposed_acceptance must be an object")
            extension_report = extension_runtime.evaluate(
                proposed,
                expected_command_count=len(spec.commands),
                safety_reasons=tuple(sorted(safety_reasons)),
            )
            completion = completion and bool(extension_report["passed"])
            print(json.dumps({
                "record_type": "scenario_extension_acceptance",
                "scenario": spec.scenario_id,
                **extension_report,
            }, ensure_ascii=False), flush=True)
        if recorder is not None:
            expected_contract = None if spec is None else dict(spec.expected)
            if expected_contract is not None and road_fit_required:
                # A route-relative CTE can be small even when a bad reference
                # itself leaves the road. Bound distance to CARLA's nearest
                # driving-lane centre as an independent acceptance check.
                expected_contract.setdefault("max_lane_center_offset_m", 2.2)
            summary = recorder.complete(
                completion=completion,
                detail="scenario acceptance criteria evaluated",
                expected=expected_contract,
                acceptance_context={} if spec is None else {
                    "route_finished": (
                        final_route_end_distance_m is not None
                        and final_route_end_distance_m <= spec.finish_radius_m
                    ),
                    "route_end_distance_m": final_route_end_distance_m,
                    "expected_command_count": len(spec.commands),
                    "configured_route_deviation_trigger_m": route_deviation_trigger_m,
                    "spawned_scenario_actor_types": sorted(set(spawned_scenario_actor_types)),
                    "extension_acceptance": extension_report,
                },
            )
            acceptance = summary.get("acceptance")
            print(json.dumps({
                "record_type": "scenario_acceptance",
                "scenario": args.scenario,
                "status": summary["status"],
                "score": summary["score"]["final_score"],
                "checks": None if acceptance is None else acceptance["check_count"],
                "failed_keys": [] if acceptance is None else acceptance["failed_keys"],
                "unsupported_keys": [] if acceptance is None else acceptance["unsupported_keys"],
            }, ensure_ascii=False))
    except BaseException as error:
        if ego is not None and getattr(ego, "is_alive", True):
            try:
                ego.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0))
            except Exception:
                pass
        if runtime is not None:
            feedback = runtime.fail_active(
                now_s=last_sim_time_s,
                detail=f"outer runtime failure: {type(error).__name__}",
            )
            if feedback is not None and recorder is not None:
                try:
                    recorder.record_feedback(feedback)
                except RuntimeError:
                    pass
        if recorder is not None:
            try:
                recorder.fail(error)
            except RuntimeError:
                pass
        raise
    finally:
        if qwen_bridge is not None:
            qwen_bridge.close()
        if qwen_backend is not None:
            qwen_backend.close()
        if live_voice is not None:
            live_voice.stop()
        if canonical_orchestrator is not None:
            canonical_orchestrator.close()
        if recorder is not None:
            recorder.close()
        if scenario_traffic_light is not None:
            try:
                if traffic_light_original_state is not None:
                    scenario_traffic_light.set_state(traffic_light_original_state)
                scenario_traffic_light.freeze(
                    False if traffic_light_original_frozen is None
                    else traffic_light_original_frozen
                )
            except Exception as error:
                print(
                    f"warning: failed to restore scenario traffic light: {error}",
                    flush=True,
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="CARLA voice-to-control acceptance runner")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--fixed-delta-s", type=float, default=0.05)
    parser.add_argument("--frames", type=int, default=200)
    parser.add_argument("--max-frames", type=int,
                        help="debug cap applied after a scenario file computes its normal frame count")
    parser.add_argument("--realtime", action="store_true",
                        help="pace control frames in wall-clock time for visual observation")
    parser.add_argument("--print-every", type=int, default=10,
                        help="emit one telemetry line every N control frames")
    parser.add_argument("--log-dir", default="artifacts/logs",
                        help="directory for automatic per-run JSONL evidence logs")
    parser.add_argument("--no-log", action="store_true", help="disable automatic JSONL evidence logging")
    parser.add_argument("--spawn-index", type=int, default=0)
    parser.add_argument(
        "--seed",
        type=int,
        help="evidence seed override; selects deterministic spawn/signal candidates",
    )
    parser.add_argument("--warmup-frames", type=int, default=40,
                        help="synchronous ticks used to stream a tiled map before spawning ego")
    parser.add_argument("--map", help="optional CARLA map name, e.g. Town05; omit to use current world")
    parser.add_argument("--default-speed-mps", type=float, default=5.0)
    parser.add_argument("--perception-mode", choices=("sensors", "world", "virtual"), default="sensors",
                        help="sensors uses required RGB/LiDAR plus optional aligned Radar; world is a debug truth bridge; virtual is deterministic test-only input")
    parser.add_argument("--sensor-timeout-s", type=float, default=0.5,
                        help="wall-clock wait for one aligned RGB/LiDAR frame")
    parser.add_argument("--sensor-warmup-frames", type=int, default=10,
                        help="maximum ticks used to obtain the first aligned RGB/LiDAR frame")
    parser.add_argument("--sensor-startup-grace-frames", type=int, default=2,
                        help="initial perception misses that brake without permanently latching watchdog")
    parser.add_argument("--sensor-profile", choices=("default", "low"), default="default",
                        help="default uses full validation density; low reduces RGB/LiDAR/Radar load "
                             "for unstable Windows/UE4 hosts")
    parser.add_argument("--rgb-detector-model",
                        help="optional Ultralytics-style ONNX model for RGB vehicle/person detection")
    parser.add_argument("--rgb-detector-confidence", type=float, default=0.35,
                        help="minimum RGB detector confidence")
    parser.add_argument("--rgb-detector-iou", type=float, default=0.45,
                        help="class-aware NMS IoU threshold")
    parser.add_argument("--rgb-detector-input-size", type=int, default=640,
                        help="fallback square input size for dynamic ONNX models")
    parser.add_argument("--c-visual-confidence-threshold", type=float, default=0.60,
                        help="C-side minimum visual confidence accepted by safety fusion")
    parser.add_argument("--qwen-remote", action="store_true",
                        help="use an OpenAI-compatible remote Qwen2.5-VL backend for the high-level command")
    parser.add_argument("--qwen-voice-command",
                        help="Chinese command sent to Qwen; a one-command scenario can supply source_text")
    parser.add_argument("--qwen-base-url",
                        default=os.environ.get("QWEN_BASE_URL", "http://127.0.0.1:18000/v1"),
                        help="OpenAI-compatible /v1 endpoint; QWEN_API_KEY is read only from the environment")
    parser.add_argument("--qwen-model",
                        default=os.environ.get(
                            "QWEN_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct"
                        ),
                        help="exact remote Qwen2.5-VL-7B model id served by this branch")
    parser.add_argument("--qwen-request-timeout-s", type=float, default=15.0,
                        help="OpenAI client wall-clock timeout")
    parser.add_argument("--qwen-max-inference-s", type=float, default=10.0,
                        help="fail-closed wall-clock deadline enforced by the async bridge")
    parser.add_argument("--qwen-decision-ttl-s", type=float, default=12.0,
                        help="maximum simulation-time age of a usable Qwen result")
    parser.add_argument("--qwen-command-ttl-s", type=float, default=30.0,
                        help="maximum simulation-time duration for the accepted runtime command")
    parser.add_argument("--qwen-max-tokens", type=int, default=1,
                        help="fixed one-token budget for the A-E decision choice")
    parser.add_argument("--qwen-image-max-side", type=int, default=256,
                        help="square montage side sent to the remote Qwen model")
    parser.add_argument("--qwen-jpeg-quality", type=int, default=75)
    parser.add_argument("--qwen-image-dir", default="artifacts/runtime/qwen_live",
                        help="local replay images; this directory is gitignored")
    parser.add_argument("--watchdog-timeout-s", type=float, default=1.0)
    parser.add_argument("--watchdog-startup-grace-s", type=float, default=0.5)
    parser.add_argument("--route-distance-m", type=float, default=500.0)
    parser.add_argument("--route-refresh-frames", type=int, default=200)
    parser.add_argument("--scenario", choices=("cruise", "follow", "red_stop", "emergency"), default="cruise",
                        help="basic CARLA acceptance scenario; all use the same A/B/C/D control loop")
    parser.add_argument("--lead-distance-m", type=float, default=18.0,
                        help="initial stationary lead distance for --scenario follow")
    parser.add_argument("--emergency-distance-m", type=float, default=6.0,
                        help="initial stationary lead distance for --scenario emergency")
    parser.add_argument("--stop-line-m", type=float, default=20.0,
                        help="virtual red stop-line distance for --scenario red_stop")
    parser.add_argument("--stop-line-guard-m", type=float, default=1.0,
                        help="D safety fallback distance used by the acceptance runner; C plans the approach before it")
    parser.add_argument("--test-command-ttl-s", type=float,
                        help="explicit test-only command TTL override; keeps long acceptance runs from expiring early")
    parser.add_argument("--command-json")
    parser.add_argument("--audio")
    parser.add_argument("--live-mic", action="store_true",
                        help="continuously segment and recognize PulseAudio microphone commands")
    parser.add_argument("--live-mic-source", default="@DEFAULT_SOURCE@",
                        help="PulseAudio source name used by --live-mic")
    parser.add_argument("--qwen-service-url",
                        help="enable canonical async routing and use this Qwen service URL")
    parser.add_argument(
        "--qwen-mode", choices=("atomic_v1", "planner_v2"), default="atomic_v1",
        help="atomic_v1 keeps the five-action baseline; planner_v2 expects ManeuverPlan V2",
    )
    parser.add_argument("--qwen-timeout-ms", type=float, default=300.0,
                        help="wall-clock deadline for one complex Qwen request")
    parser.add_argument("--qwen-queue-size", type=int, default=1,
                        help="bounded pending Qwen request queue; newest request wins")
    parser.add_argument(
        "--qwen-image-root", type=Path,
        default=Path(__file__).resolve().parents[1],
        help="shared filesystem root configured on the Qwen service",
    )
    parser.add_argument(
        "--qwen-image-prefix", default="artifacts/second_group_20260731/qwen_images",
        help="safe relative subdirectory for asynchronously staged RGB frames",
    )
    parser.add_argument("--follow-spectator", action="store_true",
                        help="move the graphical spectator camera behind the ego each frame")
    parser.add_argument("--scenario-file",
                        help="run a scenarios/*.json contract; overrides map, fixed delta, frames and scenario id")
    parser.add_argument("--validate-scenario-only", action="store_true",
                        help="load and validate --scenario-file without connecting to CARLA")
    parser.add_argument("--use-current-map", action="store_true",
                        help="debug only: run a scenario contract on the current CARLA map without load_world")
    parser.add_argument("--scenario-facts-mode", choices=("perception", "scenario", "fuse"), default="fuse",
                        help="perception: measured facts only; scenario: configured actors override; "
                             "fuse: perception first, configured actors fill missing fields")
    args = parser.parse_args()
    if args.print_every < 1:
        parser.error("--print-every must be >= 1")
    if args.max_frames is not None and args.max_frames < 1:
        parser.error("--max-frames must be >= 1")
    if (args.frames < 1 or args.warmup_frames < 0 or args.route_refresh_frames < 1
            or args.sensor_warmup_frames < 1 or args.sensor_startup_grace_frames < 0):
        parser.error("--frames, --route-refresh-frames and --sensor-warmup-frames must be positive; "
                     "--warmup-frames and --sensor-startup-grace-frames must be non-negative")
    for name in ("fixed_delta_s", "timeout_s", "sensor_timeout_s", "watchdog_timeout_s",
                 "route_distance_m", "lead_distance_m", "emergency_distance_m",
                 "stop_line_m", "stop_line_guard_m"):
        if getattr(args, name) <= 0.0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.watchdog_startup_grace_s < 0.0:
        parser.error("--watchdog-startup-grace-s must be non-negative")
    if args.test_command_ttl_s is not None and args.test_command_ttl_s <= 0.0:
        parser.error("--test-command-ttl-s must be positive")
    if args.qwen_timeout_ms <= 0.0:
        parser.error("--qwen-timeout-ms must be positive")
    if args.qwen_queue_size < 1:
        parser.error("--qwen-queue-size must be >= 1")
    if not 0.0 < args.rgb_detector_confidence <= 1.0:
        parser.error("--rgb-detector-confidence must be in (0, 1]")
    if not 0.0 < args.rgb_detector_iou <= 1.0:
        parser.error("--rgb-detector-iou must be in (0, 1]")
    if args.rgb_detector_input_size < 32:
        parser.error("--rgb-detector-input-size must be >= 32")
    if not 0.0 <= args.c_visual_confidence_threshold <= 1.0:
        parser.error("--c-visual-confidence-threshold must be in [0, 1]")
    if args.qwen_remote and not args.validate_scenario_only:
        if args.perception_mode != "sensors":
            parser.error("--qwen-remote requires --perception-mode sensors")
        if not args.realtime:
            parser.error("--qwen-remote requires --realtime so remote latency tracks simulation time")
        if args.command_json or args.audio:
            parser.error("--qwen-remote cannot be combined with --command-json or --audio")
        if not args.qwen_voice_command and not args.scenario_file:
            parser.error("--qwen-remote requires --qwen-voice-command or --scenario-file")
        if not str(args.qwen_base_url).strip() or not str(args.qwen_model).strip():
            parser.error("--qwen-base-url and --qwen-model must be non-empty")
        if not str(args.qwen_image_dir).strip():
            parser.error("--qwen-image-dir must be non-empty")
    for name in (
        "qwen_request_timeout_s",
        "qwen_max_inference_s",
        "qwen_decision_ttl_s",
        "qwen_command_ttl_s",
    ):
        if getattr(args, name) <= 0.0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.qwen_max_tokens < 1 or args.qwen_image_max_side < 1:
        parser.error("--qwen-max-tokens and --qwen-image-max-side must be positive")
    if args.qwen_remote and args.qwen_max_tokens != 1:
        parser.error("--qwen-remote requires --qwen-max-tokens 1 for the A-E action boundary")
    if not 1 <= args.qwen_jpeg_quality <= 95:
        parser.error("--qwen-jpeg-quality must be in [1, 95]")
    run(args)


if __name__ == "__main__":
    main()
