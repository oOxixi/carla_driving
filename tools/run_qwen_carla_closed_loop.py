"""Run one auditable RGB/LiDAR -> Qwen -> A/B/C/D -> CARLA loop."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np

from car_control_A import CarlaSession, RuntimeVehicleState
from car_control_B.pure_pursuit import PurePursuitController, PurePursuitParams
from integration.carla_perception import (
    CarlaPerceptionBridge,
    PerceptionAcquisitionError,
    attach_default_sensors,
    sensor_specs_for_profile,
)
from integration.day22.command_adapter import build_command
from integration.qwen_boundary import QwenInputContext
from integration.qwen_vl_adapter import StrictQwenVLAdapter
from integration.route_planner import build_route_reference
from integration.runtime_loop import ControlRuntime


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--expected-map", default="Town03_Opt")
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--command", default="请以每秒4米的速度沿当前道路直行")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--fixed-delta", type=float, default=0.05)
    parser.add_argument("--sensor-timeout", type=float, default=10.0)
    parser.add_argument("--target-speed-mps", type=float, default=4.0)
    parser.add_argument("--media-stride", type=int, default=10)
    parser.add_argument("--sensor-profile", choices=("low", "default"), default="low")
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument(
        "--awq-backend",
        choices=("auto", "torch_awq", "gemm", "gemm_triton"),
        default="auto",
    )
    return parser


def _map_leaf(name: str) -> str:
    return str(name).replace("\\", "/").rstrip("/").split("/")[-1]


def _speed_mps(vector: Any) -> float:
    return math.hypot(float(vector.x), float(vector.y))


def _vehicle_state(ego: Any, frame: int, sim_time_s: float, world_map: Any) -> RuntimeVehicleState:
    transform = ego.get_transform()
    location = transform.location
    waypoint = world_map.get_waypoint(location, project_to_road=True)
    return RuntimeVehicleState(
        frame=frame,
        sim_time_s=sim_time_s,
        speed_mps=_speed_mps(ego.get_velocity()),
        x_m=float(location.x),
        y_m=float(location.y),
        z_m=float(location.z),
        yaw_deg=float(transform.rotation.yaw),
        lane_id=str(waypoint.lane_id if waypoint is not None else "0"),
    )


def _lateral_controller() -> PurePursuitController:
    return PurePursuitController(PurePursuitParams(
        base_lookahead_m=2.5,
        min_lookahead_m=2.5,
        max_lookahead_m=8.0,
        speed_gain_s=0.45,
        max_steer=0.60,
        max_steer_delta_per_step=0.04,
        steer_sign=1.0,
    ))


def _spawn_ego(session: CarlaSession, world: Any) -> Any:
    library = world.get_blueprint_library()
    candidates = list(library.filter("vehicle.*model3*")) or list(library.filter("vehicle.*"))
    if not candidates:
        raise RuntimeError("CARLA has no vehicle blueprint")
    blueprint = candidates[0]
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", "qwen_closed_loop")
    for transform in world.get_map().get_spawn_points():
        ego = world.try_spawn_actor(blueprint, transform)
        if ego is not None:
            return session.track_actor(ego)
    raise RuntimeError("unable to spawn the closed-loop ego vehicle")


def _acquire_ready_sample(
    session: CarlaSession,
    world: Any,
    bridge: CarlaPerceptionBridge,
    *,
    attempts: int = 12,
    timeout_s: float = 10.0,
) -> Any:
    last_error: Exception | None = None
    for _ in range(attempts):
        frame = session.tick(20.0)
        snapshot = world.get_snapshot()
        try:
            return bridge.acquire(
                frame,
                snapshot.timestamp.elapsed_seconds,
                timeout_s=timeout_s,
            )
        except PerceptionAcquisitionError as error:
            last_error = error
    raise RuntimeError(f"RGB/LiDAR did not become ready: {last_error}")


def _save_sensor_pair(sample: Any, media_dir: Path) -> dict[str, object]:
    media_dir.mkdir(parents=True, exist_ok=True)
    frame = int(sample.frame.frame)
    rgb_path = media_dir / f"rgb_{frame:08d}.png"
    lidar_path = media_dir / f"lidar_{frame:08d}.npy"
    sample.rgb.save_to_disk(str(rgb_path))
    points = np.frombuffer(sample.lidar.raw_data, dtype=np.float32)
    if points.size % 4:
        raise ValueError("CARLA LiDAR buffer is not XYZI float32")
    np.save(lidar_path, points.reshape((-1, 4)))
    return {
        "frame": frame,
        "rgb_path": str(rgb_path),
        "rgb_sha256": _sha256(rgb_path),
        "lidar_path": str(lidar_path),
        "lidar_sha256": _sha256(lidar_path),
        "lidar_points": int(points.size // 4),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _json_line(stream: Any, value: object) -> None:
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    stream.flush()


def run(args: argparse.Namespace) -> dict[str, object]:
    if args.frames < 1 or args.media_stride < 1:
        raise ValueError("frames and media-stride must be positive")
    if (
        args.fixed_delta <= 0.0
        or args.sensor_timeout <= 0.0
        or args.target_speed_mps < 0.0
    ):
        raise ValueError(
            "fixed-delta and sensor-timeout must be positive; "
            "target speed must be non-negative"
        )

    import carla

    output_dir = args.output_dir.expanduser().resolve()
    media_dir = output_dir / "media"
    output_dir.mkdir(parents=True, exist_ok=True)
    client = carla.Client(args.host, args.port)
    client.set_timeout(30.0)
    world = client.get_world()
    world_map = world.get_map()
    if _map_leaf(world_map.name).lower() != _map_leaf(args.expected_map).lower():
        raise RuntimeError(
            f"current CARLA map is {world_map.name!r}; expected {args.expected_map!r}"
        )

    model_path = args.model_path.expanduser().resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"Qwen model not found: {model_path}")

    run_started = datetime.now(timezone.utc).isoformat()
    frame_log_path = output_dir / "closed_loop_frames.jsonl"
    media_records: list[dict[str, object]] = []
    qwen_report: dict[str, object] | None = None
    final_state: RuntimeVehicleState | None = None
    safety_overrides = 0
    collision = False
    red_light_violation = False
    max_speed_mps = 0.0
    start_location: tuple[float, float] | None = None

    with CarlaSession(world, fixed_delta_seconds=args.fixed_delta) as session:
        ego = _spawn_ego(session, world)
        location = ego.get_location()
        start_location = (float(location.x), float(location.y))
        sensors = attach_default_sensors(
            session,
            world,
            ego,
            carla,
            specs=sensor_specs_for_profile(args.sensor_profile),
            sensor_tick_s=args.fixed_delta,
        )
        bridge = CarlaPerceptionBridge(world, world_map, ego, session, sensors)
        initial_sample = _acquire_ready_sample(
            session,
            world,
            bridge,
            timeout_s=args.sensor_timeout,
        )
        initial_media = _save_sensor_pair(initial_sample, media_dir)
        media_records.append(initial_media)

        perception_payload = asdict(initial_sample.frame)
        safety_payload = initial_sample.safety_summary.to_dict()
        safety_payload.update({
            "traffic_light": initial_sample.frame.traffic_light,
            "distance_to_stop_line_m": initial_sample.frame.distance_to_stop_line_m,
            "input_confidence": 1.0,
        })
        context = QwenInputContext(
            request_id=f"qwen-carla-{initial_sample.frame.frame}",
            frame=initial_sample.frame.frame,
            sim_time_s=initial_sample.frame.sim_time_s,
            voice_command=args.command,
            rgb_ref=Path(str(initial_media["rgb_path"])).name,
            scene_state={
                "map": world_map.name,
                "weather": str(world.get_weather()),
                "ego_speed_mps": _speed_mps(ego.get_velocity()),
            },
            perception=perception_payload,
            safety_state=safety_payload,
        )
        context_path = output_dir / "qwen_context.json"
        _json_dump(context_path, context.to_payload())

        adapter = StrictQwenVLAdapter.from_local_checkpoint(
            model_path,
            image_root=media_dir,
            max_new_tokens=args.max_new_tokens,
            awq_backend=args.awq_backend,
        )
        decision = adapter(context)
        trace = adapter.last_trace
        if trace is None or trace.image_path is None:
            raise RuntimeError("Qwen completed without a trace backed by a real RGB image")
        qwen_report = {
            "request_id": context.request_id,
            "decision": dict(decision),
            "raw_output": trace.raw_output,
            "latency_ms": trace.latency_ms,
            "image_path": trace.image_path,
            "image_sha256": initial_media["rgb_sha256"],
        }
        _json_dump(output_dir / "qwen_decision.json", qwen_report)

        # Qwen and CARLA share GPU 0.  The first rendered frame after a long
        # inference pause may be a pipeline bubble, so reacquire two valid
        # aligned pairs before granting the model decision control authority.
        _acquire_ready_sample(
            session,
            world,
            bridge,
            timeout_s=args.sensor_timeout,
        )
        _acquire_ready_sample(
            session,
            world,
            bridge,
            timeout_s=args.sensor_timeout,
        )
        settled_location = ego.get_location()
        start_location = (
            float(settled_location.x),
            float(settled_location.y),
        )

        command = build_command(decision, args.command)
        command["valid_duration_s"] = max(
            3.0,
            args.frames * args.fixed_delta + 2.0,
        )
        runtime = ControlRuntime(
            _lateral_controller(),
            default_speed_mps=0.0,
            command_timeout_s=max(15.0, args.frames * args.fixed_delta + 2.0),
        )
        adapted = runtime.submit_voice(
            command,
            now_s=initial_sample.frame.sim_time_s,
        )
        if not adapted.control_authorized:
            raise RuntimeError(f"Qwen command rejected by A: {adapted.feedback}")
        route = build_route_reference(
            world_map,
            ego,
            runtime.requested_speed_mps,
            distance_m=max(60.0, args.target_speed_mps * args.frames * args.fixed_delta * 1.5),
        )

        with frame_log_path.open("w", encoding="utf-8") as frame_log:
            for index in range(args.frames):
                frame = session.tick(20.0)
                snapshot = world.get_snapshot()
                state = _vehicle_state(
                    ego,
                    frame,
                    snapshot.timestamp.elapsed_seconds,
                    world_map,
                )
                sample = bridge.acquire(
                    frame,
                    state.sim_time_s,
                    route=route,
                    timeout_s=args.sensor_timeout,
                )
                collision = collision or sample.frame.collision
                red_light_violation = (
                    red_light_violation or sample.frame.red_light_violation
                )
                max_speed_mps = max(max_speed_mps, state.speed_mps)
                if index and index % 40 == 0 and not runtime.safety_latched:
                    route = build_route_reference(
                        world_map,
                        ego,
                        runtime.requested_speed_mps,
                        distance_m=60.0,
                    )
                    runtime.lateral.reset()
                started_ns = time.monotonic_ns()
                result = runtime.step(
                    state,
                    sample.frame,
                    route,
                    dt_s=args.fixed_delta,
                )
                decision_end_ns = time.monotonic_ns()
                ego.apply_control(carla.VehicleControl(
                    throttle=result.final_control.throttle,
                    brake=result.final_control.brake,
                    steer=result.final_control.steer,
                    hand_brake=False,
                    reverse=False,
                    manual_gear_shift=False,
                ))
                if result.safety_override:
                    safety_overrides += 1
                media = None
                if index % args.media_stride == 0 or index == args.frames - 1:
                    media = _save_sensor_pair(sample, media_dir)
                    media_records.append(media)
                _json_line(frame_log, {
                    "record_type": "closed_loop_frame",
                    "index": index,
                    "frame": frame,
                    "vehicle": state.to_dict(),
                    "perception": asdict(sample.frame),
                    "perception_sources": dict(sample.source_by_field),
                    "safety_state": sample.safety_summary.to_dict(),
                    "qwen_request_id": context.request_id,
                    "qwen_action": decision["action"],
                    "command_id": command["command_id"],
                    "control": result.final_control.to_dict(),
                    "safety_override": result.safety_override,
                    "safety_reason": result.safety_reason,
                    "decision_latency_ms": (decision_end_ns - started_ns) / 1e6,
                    "media": media,
                })
                final_state = state

        ego.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0))

    if final_state is None or start_location is None or qwen_report is None:
        raise RuntimeError("closed loop produced no final evidence")
    distance_m = math.hypot(
        final_state.x_m - start_location[0],
        final_state.y_m - start_location[1],
    )
    trajectory_plausible = (
        distance_m
        <= max_speed_mps * args.frames * args.fixed_delta * 1.5 + 2.0
    )
    task_success = (
        qwen_report["decision"]["action"] == "SET_SPEED"
        and distance_m >= 5.0
        and max_speed_mps >= min(2.0, args.target_speed_mps)
        and abs(final_state.speed_mps - args.target_speed_mps) <= 1.0
        and trajectory_plausible
        and not collision
        and not red_light_violation
    )
    report = {
        "schema_version": "1.0",
        "status": "SUCCEEDED" if task_success else "FAILED",
        "started_at_utc": run_started,
        "map": world_map.name,
        "carla_version": client.get_server_version(),
        "model_path": str(model_path),
        "command": args.command,
        "qwen": qwen_report,
        "frames": args.frames,
        "media_samples": len(media_records),
        "media_manifest": media_records,
        "final_speed_mps": final_state.speed_mps,
        "max_speed_mps": max_speed_mps,
        "distance_travelled_m": distance_m,
        "trajectory_plausible": trajectory_plausible,
        "safety_override_frames": safety_overrides,
        "collision": collision,
        "red_light_violation": red_light_violation,
        "task_success": task_success,
        "frame_log": str(frame_log_path),
    }
    _json_dump(output_dir / "closed_loop_report.json", report)
    return report


def main() -> int:
    args = _parser().parse_args()
    try:
        report = run(args)
    except Exception as error:
        failure = {
            "status": "ERROR",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        _json_dump(args.output_dir / "closed_loop_failure.json", failure)
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
