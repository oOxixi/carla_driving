"""CARLA 0.9.16 acceptance runner with one synchronous tick/control apply.

The default path consumes frame-aligned RGB/LiDAR and event sensors. Explicit
``world`` and ``virtual`` perception modes remain test-only diagnostic paths.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from car_control_A import CarlaSession, ControlOutput, RuntimeVehicleState
from car_control_A.routing import RouteReference
from car_control_A.watchdog import RuntimeWatchdog
from car_control_B.pure_pursuit import PurePursuitController, PurePursuitParams
from car_control_D import SafetyConfig, SafetySupervisor

from .carla_perception import (
    CarlaPerceptionBridge,
    PerceptionAcquisitionError,
    attach_default_sensors,
    route_deviation_m,
)
from .contracts import PerceptionFrame
from .route_planner import (
    build_route_reference,
    command_turn_direction,
    select_topology_route_anchor,
)
from .runtime_loop import ControlRuntime
from .rgb_detector import OnnxYoloDetector
from .scenario_execution import CommandTimeline, ScenarioSpec, resolve_scenario_command
from .scenario_evidence import FrameTiming, ScenarioEvidenceRecorder


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


def _scenario_maneuver(spec: ScenarioSpec) -> str:
    intents = tuple(str(item.envelope.get("intent", "")).upper() for item in spec.commands)
    for intent in intents:
        if intent in {"TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT"}:
            return intent
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


def _scene_from_world(world: Any, ego: Any, frame: int, sim_time_s: float, *, scenario_lead: Any | None = None) -> PerceptionFrame:
    """Build scene truth; synthetic scenarios may nominate their only lead actor.

    Acceptance scenarios must not accidentally follow an unrelated vehicle
    left by another CARLA client, so they never select the globally nearest
    actor when a scenario-owned lead is supplied (or explicitly absent).
    """
    ego_location = ego.get_location()
    if scenario_lead is not None and getattr(scenario_lead, "is_alive", False):
        distance, lead_speed = (scenario_lead.get_location().distance(ego_location),
                                _speed_mps(scenario_lead.get_velocity()))
    else:
        distance = lead_speed = None
    traffic_light = "UNKNOWN"
    if ego.is_at_traffic_light():
        traffic_light = str(ego.get_traffic_light_state()).split(".")[-1].upper()
    return PerceptionFrame(frame, sim_time_s, distance, lead_speed, traffic_light=traffic_light)


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
            updates["lead_distance_m"] = max(0.1, initial_gap + lead_travel_m - travelled_m)
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
                updates["lead_distance_m"] = max(0.1, float(spawn.get("x", 0.0)) - travelled_m)
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
        if args.test_command_ttl_s is not None:
            command["valid_duration_s"] = args.test_command_ttl_s
        return command
    if args.audio:
        audio_path = Path(args.audio)
        if not audio_path.is_file():
            raise FileNotFoundError(
                f"audio file not found: {audio_path}. Pass an existing 16 kHz mono WAV path via --audio."
            )
        from voice_group.pipeline import audio_to_command
        command = audio_to_command(str(audio_path))
        if not isinstance(command, Mapping):
            raise TypeError("voice pipeline result must be an object")
        command = dict(command)
        if args.test_command_ttl_s is not None:
            command["valid_duration_s"] = args.test_command_ttl_s
        return command
    return None


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
    """Wait for the first aligned RGB/LiDAR frame before command execution."""
    last_error: PerceptionAcquisitionError | None = None
    for _ in range(attempts):
        frame = session.tick(tick_timeout_s)
        snapshot = world.get_snapshot()
        sim_time_s = snapshot.timestamp.elapsed_seconds
        try:
            bridge.acquire(frame, sim_time_s, timeout_s=sensor_timeout_s)
            return
        except PerceptionAcquisitionError as error:
            last_error = error
    if last_error is not None:
        raise last_error
    raise RuntimeError("sensor warm-up requires at least one attempt")


def _scenario_completed(args: argparse.Namespace, *, frames: int, final_speed_mps: float | None,
                        final_scene: PerceptionFrame | None, min_gap_m: float | None,
                        collision_seen: bool) -> bool:
    if frames != args.frames or final_speed_mps is None or collision_seen:
        return False
    if args.scenario == "red_stop":
        return (final_scene is not None and final_scene.distance_to_stop_line_m is not None
                and final_speed_mps <= 0.15 and final_scene.distance_to_stop_line_m <= 1.0)
    if args.scenario == "follow":
        return min_gap_m is not None and min_gap_m >= 3.0
    if args.scenario == "emergency":
        return final_speed_mps <= 0.15
    return True


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
    requires_route_event = expected.get("expected_route_deviation_event") is True
    requires_emergency = expected.get("must_emergency_brake") is True
    if not (requires_override or requires_route_event or requires_emergency):
        return None
    if frames != spec.frame_count or final_speed_mps is None or collision_seen:
        return False
    meaningful = {reason for reason in safety_reasons if reason not in {"NONE", "PERCEPTION_STARTUP_GRACE"}}
    if requires_override and not meaningful:
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


def run(args: argparse.Namespace) -> None:
    spec = ScenarioSpec.load(args.scenario_file) if args.scenario_file else None
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

    import carla

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
    runtime: ControlRuntime | None = None
    last_sim_time_s = 0.0
    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(args.timeout_s)
        world = client.get_world()
        if args.map:
            current_map = world.get_map().name.rsplit("/", maxsplit=1)[-1]
            requested_map = args.map.rsplit("/", maxsplit=1)[-1]
            if current_map.lower() != requested_map.lower():
                world = client.load_world(args.map)
        if spec is not None:
            weather = getattr(carla.WeatherParameters, spec.weather, None)
            if weather is None:
                raise ValueError(f"CARLA has no WeatherParameters preset named {spec.weather!r}")
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
        runtime = ControlRuntime(_acceptance_lateral_controller(), default_speed_mps=args.default_speed_mps,
                                 command_timeout_s=fsm_timeout_s, safety=scenario_safety)
        route_anchor = spawn_points[args.spawn_index % len(spawn_points)]
        topology_route: RouteReference | None = None
        road_fit_required = (
            spec is not None
            and (spec.category == "lateral_B" or spec.expected.get("must_finish_route") is True)
        )
        if road_fit_required:
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
            print(
                f"route anchor: spawn_index={anchor_index} maneuver={maneuver} "
                f"topology_score={anchor_score:.3f}"
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
            ego.set_autopilot(False)
            session.tick(args.timeout_s)
            start_location = ego.get_location()
            origin = (start_location.x, start_location.y, start_location.z)

            scenario_lead = None
            if args.perception_mode in {"sensors", "world"} and args.scenario in {"follow", "emergency"}:
                lead_distance = args.lead_distance_m if args.scenario == "follow" else args.emergency_distance_m
                scenario_lead = _spawn_static_lead(session, world, world_map, ego, bp, lead_distance)

            perception_bridge = None
            if args.perception_mode == "sensors":
                sensors = attach_default_sensors(
                    session, world, ego, carla, sensor_tick_s=args.fixed_delta_s,
                )
                perception_bridge = CarlaPerceptionBridge(
                    world, world_map, ego, session, sensors, detector=detector,
                )
                _warm_up_sensor_bridge(
                    session, world, perception_bridge,
                    attempts=args.sensor_warmup_frames,
                    tick_timeout_s=args.timeout_s,
                    sensor_timeout_s=args.sensor_timeout_s,
                )

            # Do not accept a command until required sensors are ready. This
            # guarantees that every accepted command can enter the frame loop
            # and receive an auditable terminal status.
            initial = world.get_snapshot()
            last_sim_time_s = initial.timestamp.elapsed_seconds
            episode_start_s = last_sim_time_s
            timeline = CommandTimeline(spec.commands) if spec is not None else None
            command: dict[str, object] | None
            if spec is None:
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

            watchdog = RuntimeWatchdog(
                timeout_s=args.watchdog_timeout_s,
                required_modules=("perception", "control"),
                startup_grace_s=args.watchdog_startup_grace_s,
                started_at_s=time.monotonic(),
            )
            for step_index in range(args.frames):
                frame = session.tick(args.timeout_s)
                snapshot = world.get_snapshot()
                state = _vehicle_state(ego, frame, snapshot.timestamp.elapsed_seconds, world_map)
                last_sim_time_s = state.sim_time_s
                elapsed_s = state.sim_time_s - episode_start_s
                if timeline is not None:
                    for scheduled in timeline.due(elapsed_s):
                        scenario_command = resolve_scenario_command(
                            scheduled,
                            requested_speed_mps=runtime.requested_speed_mps,
                        )
                        received_ns = time.monotonic_ns()
                        scenario_adapted = runtime.submit_voice(scenario_command, now_s=state.sim_time_s)
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
                refresh_live_route = spec is None and step_index and step_index % args.route_refresh_frames == 0
                extend_finished_scenario_route = (
                    spec is not None
                    and spec.category != "lateral_B"
                    and spec.expected.get("must_finish_route") is not True
                    and distance_to_route_end_m <= 10.0
                )
                if ((refresh_live_route or extend_finished_scenario_route) and not runtime.safety_latched):
                    route = build_route_reference(
                        world_map, ego, runtime.requested_speed_mps,
                        distance_m=args.route_distance_m,
                    )
                    runtime.lateral.reset()

                perception_sources: dict[str, str] = {}
                c_safety_state: dict[str, object] | None = None
                watchdog_alerts: list[str] = []
                sensor_startup_grace = False
                try:
                    if perception_bridge is not None:
                        sample = perception_bridge.acquire(
                            frame, state.sim_time_s, route=route, timeout_s=args.sensor_timeout_s,
                        )
                        scene = sample.frame
                        perception_sources = dict(sample.source_by_field)
                        c_safety_state = sample.safety_summary.to_dict()
                        if sample.safety_summary.fail_closed:
                            watchdog_alerts.append(
                                "C_FUSION_" + sample.safety_summary.reason.upper()
                            )
                    else:
                        scene = _scene_from_world(
                            world, ego, frame, state.sim_time_s, scenario_lead=scenario_lead,
                        )
                        if args.perception_mode == "virtual":
                            scene = _apply_virtual_scenario(scene, ego, origin, args)
                            perception_sources = {"scenario": "VIRTUAL_ACCEPTANCE_TRUTH"}
                        else:
                            perception_sources = {"scenario": "CARLA_WORLD_TRUTH"}
                    if spec is not None and perception_bridge is None:
                        scene = replace(
                            scene,
                            route_deviation_m=route_deviation_m(state.x_m, state.y_m, route),
                        )
                        perception_sources["route_deviation_m"] = "ROUTE_REFERENCE_NEAREST_SEGMENT"
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
                    watchdog.heartbeat("perception", now_s=time.monotonic())
                except PerceptionAcquisitionError as error:
                    scene = PerceptionFrame(frame, state.sim_time_s)
                    perception_sources = {"failure": type(error).__name__}
                    sensor_startup_grace = step_index < args.sensor_startup_grace_frames
                    if not sensor_startup_grace:
                        watchdog_alerts.append(f"PERCEPTION_{type(error).__name__.upper()}")
                if spec is not None:
                    truth = _scenario_facts(ego, origin, spec, frame=frame, sim_time_s=state.sim_time_s, elapsed_s=elapsed_s)
                    scene, fact_sources = _select_scene_facts(scene, truth, args.scenario_facts_mode)
                    perception_sources.update(fact_sources)
                sensor_ready_ns = time.monotonic_ns()
                if not sensor_startup_grace and watchdog.check(now_s=time.monotonic()) is not None:
                    watchdog_alerts.append("RUNTIME_WATCHDOG_TIMEOUT")

                command_id = runtime.active_command_id
                decision_start_ns = time.monotonic_ns()
                raw_control_override = None
                if not raw_control_fault_injected:
                    raw_control_override = _scenario_raw_control_fault(spec, elapsed_s)
                    raw_control_fault_injected = raw_control_override is not None
                result = runtime.step(
                    state, scene, route, dt_s=args.fixed_delta_s,
                    watchdog_alerts=tuple(watchdog_alerts),
                    raw_control_override=raw_control_override,
                )
                if sensor_startup_grace:
                    result = replace(
                        result,
                        final_control=ControlOutput(0.0, 1.0, 0.0),
                        safety_reason="PERCEPTION_STARTUP_GRACE",
                        safety_override=True,
                    )
                if result.safety_override:
                    safety_reasons.add(result.safety_reason)
                decision_end_ns = time.monotonic_ns()
                ego.apply_control(carla.VehicleControl(
                    throttle=result.final_control.throttle,
                    brake=result.final_control.brake,
                    steer=result.final_control.steer,
                    hand_brake=False, reverse=False, manual_gear_shift=False,
                ))
                control_applied_ns = time.monotonic_ns()
                watchdog.heartbeat("control", now_s=time.monotonic())
                timing = FrameTiming(
                    sensor_ready_ns=sensor_ready_ns,
                    decision_start_ns=decision_start_ns,
                    decision_end_ns=decision_end_ns,
                    control_applied_ns=control_applied_ns,
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
                }
                if step_index % args.print_every == 0 or step_index == args.frames - 1:
                    print(json.dumps(record, ensure_ascii=False))
                if args.realtime:
                    time.sleep(args.fixed_delta_s)

        command_finished = runtime is None or runtime.active_command_id is None
        if not command_finished and runtime is not None:
            feedback = runtime.fail_active(
                now_s=last_sim_time_s,
                detail="scenario frame budget ended before command completion",
            )
            if feedback is not None and recorder is not None:
                recorder.record_feedback(feedback)
        final_speed = None if final_state is None else final_state.speed_mps
        expected_completion = None if spec is None else _expected_safety_completed(
            spec,
            frames=frames_completed,
            final_speed_mps=final_speed,
            collision_seen=collision_seen,
            safety_reasons=safety_reasons,
        )
        completion = expected_completion if expected_completion is not None else (
            command_finished and _scenario_completed(
                args, frames=frames_completed,
                final_speed_mps=final_speed,
                final_scene=final_scene, min_gap_m=min_gap_m,
                collision_seen=collision_seen,
            )
        )
        route_contract_completion = _route_contract_completed(spec, final_route_end_distance_m)
        if route_contract_completion is not None:
            completion = completion and route_contract_completion
        gap_contract_completion = _minimum_gap_contract_completed(spec, min_gap_m)
        if gap_contract_completion is not None:
            completion = completion and gap_contract_completion
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
        if recorder is not None:
            recorder.close()


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
    parser.add_argument("--warmup-frames", type=int, default=40,
                        help="synchronous ticks used to stream a tiled map before spawning ego")
    parser.add_argument("--map", help="optional CARLA map name, e.g. Town05; omit to use current world")
    parser.add_argument("--default-speed-mps", type=float, default=5.0)
    parser.add_argument("--perception-mode", choices=("sensors", "world", "virtual"), default="sensors",
                        help="sensors uses aligned RGB/LiDAR; world is a debug truth bridge; virtual is deterministic test-only input")
    parser.add_argument("--sensor-timeout-s", type=float, default=0.5,
                        help="wall-clock wait for one aligned RGB/LiDAR frame")
    parser.add_argument("--sensor-warmup-frames", type=int, default=10,
                        help="maximum ticks used to obtain the first aligned RGB/LiDAR frame")
    parser.add_argument("--sensor-startup-grace-frames", type=int, default=2,
                        help="initial perception misses that brake without permanently latching watchdog")
    parser.add_argument("--rgb-detector-model",
                        help="optional Ultralytics-style ONNX model for RGB vehicle/person detection")
    parser.add_argument("--rgb-detector-confidence", type=float, default=0.35,
                        help="minimum RGB detector confidence")
    parser.add_argument("--rgb-detector-iou", type=float, default=0.45,
                        help="class-aware NMS IoU threshold")
    parser.add_argument("--rgb-detector-input-size", type=int, default=640,
                        help="fallback square input size for dynamic ONNX models")
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
    if not 0.0 < args.rgb_detector_confidence <= 1.0:
        parser.error("--rgb-detector-confidence must be in (0, 1]")
    if not 0.0 < args.rgb_detector_iou <= 1.0:
        parser.error("--rgb-detector-iou must be in (0, 1]")
    if args.rgb_detector_input_size < 32:
        parser.error("--rgb-detector-input-size must be >= 32")
    run(args)


if __name__ == "__main__":
    main()
