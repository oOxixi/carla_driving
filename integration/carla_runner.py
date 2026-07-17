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
from car_control_A.watchdog import RuntimeWatchdog
from car_control_B.pure_pursuit import PurePursuitController, PurePursuitParams
from car_control_D import SafetyConfig, SafetySupervisor

from .carla_perception import (
    CarlaPerceptionBridge,
    PerceptionAcquisitionError,
    attach_default_sensors,
)
from .contracts import PerceptionFrame
from .route_planner import build_route_reference, command_turn_direction
from .runtime_loop import ControlRuntime
from .scenario_evidence import FrameTiming, ScenarioEvidenceRecorder


def _speed_mps(vector: Any) -> float:
    # Longitudinal control consumes ground speed. Including vertical spawn
    # settling makes a stationary vehicle appear to accelerate under gravity.
    return math.hypot(vector.x, vector.y)


def _acceptance_lateral_controller() -> PurePursuitController:
    """Conservative CARLA tuning that cannot snap directly to full steering."""
    return PurePursuitController(PurePursuitParams(
        base_lookahead_m=3.5,
        min_lookahead_m=3.5,
        max_lookahead_m=10.0,
        speed_gain_s=0.60,
        max_steer=0.60,
        max_steer_delta_per_step=0.04,
        # Calibrated against a CARLA 0.9.16 Model 3 closed-loop route run.
        steer_sign=1.0,
    ))


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


def _evidence_recorder(args: argparse.Namespace) -> ScenarioEvidenceRecorder | None:
    if args.no_log:
        return None
    directory = Path(args.log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = directory / f"{args.scenario}_{stamp}.jsonl"
    recorder = ScenarioEvidenceRecorder(path)
    recorder.start_run(scenario_id=args.scenario, config={
        key: value for key, value in vars(args).items()
        if type(value) in (str, int, float, bool) or value is None
    })
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


def run(args: argparse.Namespace) -> None:
    import carla

    recorder = _evidence_recorder(args)
    ego: Any | None = None
    frames_completed = 0
    final_state: RuntimeVehicleState | None = None
    final_scene: PerceptionFrame | None = None
    min_gap_m: float | None = None
    collision_seen = False
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
        world_map = world.get_map()
        blueprints = world.get_blueprint_library().filter("vehicle.*model3*")
        if not blueprints:
            raise RuntimeError("no Tesla Model 3 vehicle blueprint is available")
        bp = blueprints[0]
        spawn_points = world_map.get_spawn_points()
        if not spawn_points:
            raise RuntimeError("map has no vehicle spawn points")
        fsm_timeout_s = 15.0 if args.test_command_ttl_s is None else args.test_command_ttl_s + 1.0
        scenario_safety = SafetySupervisor(SafetyConfig(stop_line_guard_m=args.stop_line_guard_m))
        runtime = ControlRuntime(_acceptance_lateral_controller(), default_speed_mps=args.default_speed_mps,
                                 command_timeout_s=fsm_timeout_s, safety=scenario_safety)
        spawn_transform = spawn_points[args.spawn_index % len(spawn_points)]
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
                perception_bridge = CarlaPerceptionBridge(world, world_map, ego, session, sensors)
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
            command: dict[str, object] | None
            try:
                command = _load_command(args)
            except Exception as error:
                command = _rejected_load_envelope(error)
                print(f"warning: voice input rejected without changing vehicle control: {error}")
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
                    )
                    if adapted.feedback is not None:
                        recorder.record_feedback(adapted.feedback)

            turn_direction = "STRAIGHT"
            if adapted is not None and adapted.control_authorized and not adapted.command.requires_confirmation:
                turn_direction = command_turn_direction(command)
            route = build_route_reference(
                world_map, ego, runtime.requested_speed_mps,
                turn_direction=turn_direction, distance_m=args.route_distance_m,
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
                if step_index and step_index % args.route_refresh_frames == 0 and not runtime.safety_latched:
                    route = build_route_reference(
                        world_map, ego, runtime.requested_speed_mps,
                        distance_m=args.route_distance_m,
                    )
                    runtime.lateral.reset()

                perception_sources: dict[str, str] = {}
                watchdog_alerts: list[str] = []
                sensor_startup_grace = False
                try:
                    if perception_bridge is not None:
                        sample = perception_bridge.acquire(
                            frame, state.sim_time_s, route=route, timeout_s=args.sensor_timeout_s,
                        )
                        scene = sample.frame
                        perception_sources = dict(sample.source_by_field)
                    else:
                        scene = _scene_from_world(
                            world, ego, frame, state.sim_time_s, scenario_lead=scenario_lead,
                        )
                        if args.perception_mode == "virtual":
                            scene = _apply_virtual_scenario(scene, ego, origin, args)
                            perception_sources = {"scenario": "VIRTUAL_ACCEPTANCE_TRUTH"}
                        else:
                            perception_sources = {"scenario": "CARLA_WORLD_TRUTH"}
                    watchdog.heartbeat("perception", now_s=time.monotonic())
                except PerceptionAcquisitionError as error:
                    scene = PerceptionFrame(frame, state.sim_time_s)
                    perception_sources = {"failure": type(error).__name__}
                    sensor_startup_grace = step_index < args.sensor_startup_grace_frames
                    if not sensor_startup_grace:
                        watchdog_alerts.append(f"PERCEPTION_{type(error).__name__.upper()}")
                sensor_ready_ns = time.monotonic_ns()
                if not sensor_startup_grace and watchdog.check(now_s=time.monotonic()) is not None:
                    watchdog_alerts.append("RUNTIME_WATCHDOG_TIMEOUT")

                command_id = runtime.active_command_id
                decision_start_ns = time.monotonic_ns()
                result = runtime.step(
                    state, scene, route, dt_s=args.fixed_delta_s,
                    watchdog_alerts=tuple(watchdog_alerts),
                )
                if sensor_startup_grace:
                    result = replace(
                        result,
                        final_control=ControlOutput(0.0, 1.0, 0.0),
                        safety_reason="PERCEPTION_STARTUP_GRACE",
                        safety_override=True,
                    )
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
                    )

                frames_completed += 1
                final_state, final_scene = state, scene
                collision_seen = collision_seen or scene.collision
                if scene.lead_distance_m is not None:
                    min_gap_m = scene.lead_distance_m if min_gap_m is None else min(min_gap_m, scene.lead_distance_m)
                record = {
                    "record_type": "frame", "scenario": args.scenario,
                    "perception_mode": args.perception_mode, "frame": frame,
                    "sim_time_s": state.sim_time_s, "speed_mps": state.speed_mps,
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
        completion = command_finished and _scenario_completed(
            args, frames=frames_completed,
            final_speed_mps=None if final_state is None else final_state.speed_mps,
            final_scene=final_scene, min_gap_m=min_gap_m,
            collision_seen=collision_seen,
        )
        if recorder is not None:
            recorder.complete(completion=completion, detail="scenario acceptance criteria evaluated")
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
    args = parser.parse_args()
    if args.print_every < 1:
        parser.error("--print-every must be >= 1")
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
    run(args)


if __name__ == "__main__":
    main()
