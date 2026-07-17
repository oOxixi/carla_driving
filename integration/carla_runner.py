"""Minimal CARLA 0.9.16 runner with one synchronous tick and one control apply.

This runner deliberately uses CARLA actor/traffic-light truth only to establish
the initial control-loop acceptance test.  Swap ``_scene_from_world`` for the
RGB/LiDAR perception implementation without changing ControlRuntime's API.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from car_control_A import CarlaSession, RuntimeVehicleState
from car_control_A.routing import RouteReference
from car_control_B.pure_pursuit import PurePursuitController
from car_control_D import SafetyConfig, SafetySupervisor

from .contracts import PerceptionFrame
from .runtime_loop import ControlRuntime


def _speed_mps(vector: Any) -> float:
    return math.sqrt(vector.x * vector.x + vector.y * vector.y + vector.z * vector.z)


def _vehicle_state(ego: Any, frame: int, sim_time_s: float, world_map: Any) -> RuntimeVehicleState:
    transform, velocity = ego.get_transform(), ego.get_velocity()
    location = transform.location
    waypoint = world_map.get_waypoint(location, project_to_road=True)
    return RuntimeVehicleState(frame, sim_time_s, _speed_mps(velocity), location.x, location.y, location.z,
                               transform.rotation.yaw, str(waypoint.lane_id if waypoint else "0"))


def _route(world_map: Any, ego: Any, target_speed_mps: float) -> RouteReference:
    waypoint = world_map.get_waypoint(ego.get_location(), project_to_road=True)
    points: list[tuple[float, float]] = []
    for _ in range(120):
        if waypoint is None:
            break
        loc = waypoint.transform.location
        points.append((loc.x, loc.y))
        next_points = waypoint.next(2.0)
        waypoint = next_points[0] if next_points else None
    if len(points) < 2:
        loc = ego.get_location()
        points = [(loc.x, loc.y), (loc.x + 10.0, loc.y)]
    return RouteReference(tuple(points), 0.0, target_speed_mps)


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
        if args.test_command_ttl_s is not None:
            command["valid_duration_s"] = args.test_command_ttl_s
        return command
    return None


def _open_run_log(args: argparse.Namespace) -> tuple[Path | None, Any | None]:
    """Create a JSONL evidence file for every scenario run unless disabled."""
    if args.no_log:
        return None, None
    directory = Path(args.log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"{args.scenario}_{stamp}.jsonl"
    handle = path.open("x", encoding="utf-8")
    metadata = {"record_type": "run_start", "timestamp_local": datetime.now().isoformat(timespec="seconds"),
                "scenario": args.scenario, "map": args.map, "frames": args.frames,
                "fixed_delta_s": args.fixed_delta_s, "realtime": args.realtime,
                "lead_distance_m": args.lead_distance_m, "emergency_distance_m": args.emergency_distance_m,
                "stop_line_m": args.stop_line_m, "command_json": args.command_json,
                "audio": args.audio}
    handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
    handle.flush()
    print(f"run log: {path}")
    return path, handle


def run(args: argparse.Namespace) -> None:
    import carla

    client = carla.Client(args.host, args.port)
    client.set_timeout(args.timeout_s)
    world = client.get_world()
    if args.map:
        current_map = world.get_map().name.rsplit("/", maxsplit=1)[-1]
        requested_map = args.map.rsplit("/", maxsplit=1)[-1]
        if current_map.lower() != requested_map.lower():
            world = client.load_world(args.map)
    world_map = world.get_map()
    bp = world.get_blueprint_library().filter("vehicle.*model3*")[0]
    spawn_points = world_map.get_spawn_points()
    if not spawn_points:
        raise RuntimeError("map has no vehicle spawn points")
    fsm_timeout_s = 15.0 if args.test_command_ttl_s is None else args.test_command_ttl_s + 1.0
    scenario_safety = SafetySupervisor(SafetyConfig(stop_line_guard_m=args.stop_line_guard_m))
    runtime = ControlRuntime(PurePursuitController(), default_speed_mps=args.default_speed_mps,
                             command_timeout_s=fsm_timeout_s, safety=scenario_safety)
    log_path, log_handle = _open_run_log(args)
    spawn_transform = spawn_points[args.spawn_index % len(spawn_points)]
    # Town12 and other tiled maps activate physics only for streamed tiles. The
    # spectator is the portable streaming anchor in CARLA 0.9.16, so move it to
    # the selected spawn before switching to synchronous stepping.
    spectator_transform = carla.Transform(
        carla.Location(x=spawn_transform.location.x, y=spawn_transform.location.y, z=spawn_transform.location.z + 25.0),
        carla.Rotation(pitch=-45.0, yaw=spawn_transform.rotation.yaw),
    )
    world.get_spectator().set_transform(spectator_transform)
    try:
        world.wait_for_tick(args.timeout_s)
    except RuntimeError:
        # The following synchronous warm-up ticks are still able to finish a
        # slow tile load; the warning is emitted only through normal CLI output.
        print("warning: map warm-up wait timed out; continuing with synchronous warm-up")
    try:
        with CarlaSession(world, fixed_delta_seconds=args.fixed_delta_s) as session:
            for _ in range(args.warmup_frames):
                session.tick(args.timeout_s)
            ego = session.spawn_ego(bp, spawn_transform)
            ego.set_simulate_physics(True)
            ego.set_autopilot(False)
            # CARLA actor transforms are authoritative only after one server
            # tick following spawn. Establish every scenario reference from
            # that frame, not from the transient spawn response.
            session.tick(args.timeout_s)
            # Keep one local reference for the episode. Rebuilding it from the
            # nearest waypoint every frame can jump backwards at intersections and
            # falsely drive the lateral controller into steering saturation.
            route = _route(world_map, ego, runtime.requested_speed_mps)
            start_location = ego.get_location()
            origin = (start_location.x, start_location.y, start_location.z)
            initial = world.get_snapshot()
            command = _load_command(args)
            if command is not None:
                runtime.submit_voice(command, now_s=initial.timestamp.elapsed_seconds)
                if log_handle is not None:
                    log_handle.write(json.dumps({"record_type": "command_accepted", "command_id": command.get("command_id"),
                                                 "intent": command.get("intent"), "effective_valid_duration_s": command.get("valid_duration_s")},
                                                 ensure_ascii=False) + "\n")
            for step_index in range(args.frames):
                frame = session.tick(args.timeout_s)
                snapshot = world.get_snapshot()
                state = _vehicle_state(ego, frame, snapshot.timestamp.elapsed_seconds, world_map)
                scene = _apply_virtual_scenario(
                    _scene_from_world(world, ego, frame, snapshot.timestamp.elapsed_seconds), ego, origin, args
                )
                result = runtime.step(state, scene, route, dt_s=args.fixed_delta_s)
                ego.apply_control(carla.VehicleControl(throttle=result.final_control.throttle, brake=result.final_control.brake,
                                                       steer=result.final_control.steer, hand_brake=False,
                                                       reverse=False, manual_gear_shift=False))
                record = {"record_type": "frame", "scenario": args.scenario, "frame": frame,
                          "sim_time_s": state.sim_time_s, "speed_mps": state.speed_mps,
                          "target_speed_mps": None if result.longitudinal is None else result.longitudinal.target_speed_mps,
                          "longitudinal_state": None if result.longitudinal is None else result.longitudinal.state,
                          "ttc_s": None if result.longitudinal is None else result.longitudinal.risk.ttc_s,
                          "lead_distance_m": scene.lead_distance_m,
                          "distance_to_stop_line_m": scene.distance_to_stop_line_m,
                          "scene_source": "virtual_truth" if args.scenario != "cruise" else "world_truth",
                          "control": result.final_control.to_dict(), "safety": result.safety_reason,
                          "safety_override": result.safety_override}
                if log_handle is not None:
                    log_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                if step_index % args.print_every == 0 or step_index == args.frames - 1:
                    print(json.dumps(record, ensure_ascii=False))
                if args.realtime:
                    time.sleep(args.fixed_delta_s)
            if log_handle is not None:
                log_handle.write(json.dumps({"record_type": "run_complete", "frames": args.frames,
                                             "timestamp_local": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
    finally:
        if log_handle is not None:
            log_handle.close()


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
    for name in ("lead_distance_m", "emergency_distance_m", "stop_line_m", "stop_line_guard_m"):
        if getattr(args, name) <= 0.0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.test_command_ttl_s is not None and args.test_command_ttl_s <= 0.0:
        parser.error("--test-command-ttl-s must be positive")
    run(args)


if __name__ == "__main__":
    main()
