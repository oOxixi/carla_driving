from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Iterable, Optional

import carla

from rgb_group.camera_sensor import FrontRGBCamera
from rgb_group.carla_gt_backend import CarlaGroundTruthBackend
from rgb_group.service import RGBPerceptionService
from rgb_group.visualize import draw_observation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Controlled CARLA RGB perception scenarios"
    )
    parser.add_argument(
        "--scenario",
        choices=[
            "empty",
            "front_vehicle",
            "pedestrian",
            "sensor_unavailable",
        ],
        required=True,
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--fov", type=float, default=90.0)
    parser.add_argument("--fixed-delta", type=float, default=0.05)
    parser.add_argument("--sensor-timeout", type=float, default=10.0)
    parser.add_argument("--warmup-ticks", type=int, default=10)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def offset_transform(
    base: carla.Transform,
    forward_m: float = 0.0,
    right_m: float = 0.0,
    z_m: float = 0.0,
) -> carla.Transform:
    yaw_rad = math.radians(base.rotation.yaw)

    forward_x = math.cos(yaw_rad)
    forward_y = math.sin(yaw_rad)
    right_x = -math.sin(yaw_rad)
    right_y = math.cos(yaw_rad)

    return carla.Transform(
        carla.Location(
            x=base.location.x + forward_x * forward_m + right_x * right_m,
            y=base.location.y + forward_y * forward_m + right_y * right_m,
            z=base.location.z + z_m,
        ),
        carla.Rotation(
            pitch=base.rotation.pitch,
            yaw=base.rotation.yaw,
            roll=base.rotation.roll,
        ),
    )


def choose_vehicle_blueprint(world) -> carla.ActorBlueprint:
    candidates = list(world.get_blueprint_library().filter("vehicle.*"))

    for bp in candidates:
        try:
            if (
                bp.has_attribute("number_of_wheels")
                and int(bp.get_attribute("number_of_wheels")) == 4
            ):
                return bp
        except Exception:
            continue

    if not candidates:
        raise RuntimeError("No vehicle blueprint available")

    return candidates[0]


def destroy_actors(client: carla.Client, actors: Iterable[carla.Actor]) -> None:
    actor_ids = []

    for actor in actors:
        try:
            if actor is not None and actor.is_alive:
                actor_ids.append(actor.id)
        except Exception:
            pass

    if not actor_ids:
        return

    try:
        responses = client.apply_batch_sync(
            [carla.command.DestroyActor(actor_id) for actor_id in actor_ids],
            True,
        )
        for actor_id, response in zip(actor_ids, responses):
            if response.has_error():
                print(
                    f"[cleanup warning] actor={actor_id}: {response.error}",
                    file=sys.stderr,
                )
    except Exception as exc:
        print(f"[cleanup warning] destroy failed: {exc}", file=sys.stderr)


def build_unavailable_record(
    world,
    width: int,
    height: int,
) -> dict:
    snapshot = world.get_snapshot()

    return {
        "schema_version": "1.0",
        "frame": int(snapshot.frame),
        "sim_time_s": float(snapshot.timestamp.elapsed_seconds),
        "sensor_id": "front_rgb",
        "image_width": int(width),
        "image_height": int(height),
        "objects": [],
        "traffic_light": {
            "state": "UNKNOWN",
            "confidence": 0.0,
            "visible": False,
            "bbox_xyxy": None,
            "source": "NONE",
        },
        "perception_status": "UNAVAILABLE",
        "latency_ms": 0.0,
        "warnings": ["RGB_SENSOR_UNAVAILABLE"],
        "scene_summary": {
            "front_vehicle": False,
            "front_pedestrian": False,
            "front_obstacle": False,
            "red_light": False,
        },
    }


def spawn_ego(world) -> tuple[carla.Vehicle, carla.Transform]:
    bp = choose_vehicle_blueprint(world)

    for transform in world.get_map().get_spawn_points():
        actor = world.try_spawn_actor(bp, transform)
        if actor is not None:
            actor.set_simulate_physics(False)
            return actor, transform

    raise RuntimeError("Failed to spawn ego vehicle")


def main() -> None:
    args = parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "vision_observations.jsonl"

    client = carla.Client(args.host, args.port)
    client.set_timeout(60.0)

    world = client.get_world()
    original_settings = world.get_settings()

    camera: Optional[FrontRGBCamera] = None
    spawned_actors = []

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = float(args.fixed_delta)
        settings.no_rendering_mode = False
        world.apply_settings(settings)

        # IMPORTANT:
        # The unavailable case deliberately does not create a CARLA camera actor.
        # This avoids leaving a live sensor stream behind merely to simulate failure.
        if args.scenario == "sensor_unavailable":
            world.tick()
            row = build_unavailable_record(
                world=world,
                width=args.width,
                height=args.height,
            )
            jsonl_path.write_text(
                json.dumps(row, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(row, ensure_ascii=False))
            print("results:", jsonl_path)
            return

        ego, ego_transform = spawn_ego(world)
        spawned_actors.append(ego)

        if args.scenario == "front_vehicle":
            target_bp = choose_vehicle_blueprint(world)
            target = world.try_spawn_actor(
                target_bp,
                offset_transform(ego_transform, forward_m=15.0),
            )
            if target is None:
                raise RuntimeError("Failed to spawn controlled front vehicle")
            target.set_simulate_physics(False)
            spawned_actors.append(target)
            print(f"front vehicle: ego={ego.id}, target={target.id}")

        elif args.scenario == "pedestrian":
            walker_bps = list(
                world.get_blueprint_library().filter("walker.pedestrian.*")
            )
            if not walker_bps:
                raise RuntimeError("No pedestrian blueprint available")

            walker = world.try_spawn_actor(
                walker_bps[0],
                offset_transform(
                    ego_transform,
                    forward_m=7.0,
                    right_m=0.0,
                    z_m=0.5,
                ),
            )
            if walker is None:
                raise RuntimeError("Failed to spawn controlled pedestrian")
            walker.set_simulate_physics(False)
            spawned_actors.append(walker)
            print(f"pedestrian: ego={ego.id}, walker={walker.id}")

        # empty: only ego is spawned.
        world.tick()

        camera = FrontRGBCamera(
            world=world,
            vehicle=ego,
            width=args.width,
            height=args.height,
            fov_deg=args.fov,
        )

        first_frame = None

        for warmup_index in range(max(1, args.warmup_ticks)):
            expected_frame = world.tick()
            try:
                first_frame = camera.get_for_frame(
                    expected_frame=expected_frame,
                    timeout_s=args.sensor_timeout,
                    max_frame_lag=2,
                )
                break
            except TimeoutError:
                print(
                    f"warmup timeout {warmup_index + 1}/{args.warmup_ticks}"
                )

        if first_frame is None:
            raise RuntimeError("RGB camera produced no image")

        backend = CarlaGroundTruthBackend(
            world=world,
            ego_vehicle=ego,
            width=args.width,
            height=args.height,
            fov_deg=args.fov,
            max_distance_m=50.0,
        )
        service = RGBPerceptionService(backend)

        import cv2

        with jsonl_path.open("w", encoding="utf-8") as fp:
            pending_frame = first_frame

            for index in range(args.frames):
                if pending_frame is not None:
                    rgb_frame = pending_frame
                    pending_frame = None
                else:
                    expected_frame = world.tick()
                    rgb_frame = camera.get_for_frame(
                        expected_frame=expected_frame,
                        timeout_s=args.sensor_timeout,
                        max_frame_lag=2,
                    )

                observation = service.process(rgb_frame)
                row = observation.to_dict()

                fp.write(json.dumps(row, ensure_ascii=False) + "\n")
                fp.flush()

                annotated = draw_observation(
                    rgb_frame.image_bgr,
                    observation,
                )
                image_path = (
                    output_dir / f"frame_{observation.frame:06d}.jpg"
                )
                if not cv2.imwrite(str(image_path), annotated):
                    raise RuntimeError(f"Failed to save {image_path}")

                print(
                    json.dumps(
                        {
                            "index": index,
                            "frame": observation.frame,
                            "objects": len(observation.objects),
                            "categories": [
                                item.category for item in observation.objects
                            ],
                            "summary": observation.scene_summary,
                        },
                        ensure_ascii=False,
                    )
                )

        print("results:", jsonl_path)

    except Exception:
        traceback.print_exc()
        raise

    finally:
        # Strict cleanup order:
        # 1) stop sensor callback
        # 2) advance one synchronous tick
        # 3) destroy sensor actor
        # 4) destroy spawned scene actors
        # 5) restore original world settings
        if camera is not None:
            try:
                camera.stop()
            except Exception as exc:
                print(f"[cleanup warning] camera.stop: {exc}", file=sys.stderr)

        try:
            if world.get_settings().synchronous_mode:
                world.tick()
        except Exception:
            pass

        if camera is not None and camera.actor is not None:
            sensor_actor = camera.actor
            camera.actor = None
            destroy_actors(client, [sensor_actor])

        destroy_actors(client, reversed(spawned_actors))

        try:
            world.apply_settings(original_settings)
        except Exception as exc:
            print(
                f"[cleanup warning] restore world settings: {exc}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
