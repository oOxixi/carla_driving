from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import time
import traceback

import carla

from rgb_group.camera_sensor import FrontRGBCamera
from rgb_group.carla_gt_backend import CarlaGroundTruthBackend
from rgb_group.onnx_backend import YoloV8OnnxBackend
from rgb_group.service import RGBPerceptionService
from rgb_group.visualize import draw_observation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CARLA 0.9.16 RGB perception demo"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--tm-port", type=int, default=8000)

    parser.add_argument(
        "--backend",
        choices=["carla_gt", "onnx"],
        default="carla_gt",
    )
    parser.add_argument("--model", default="models/yolov8n.onnx")

    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fov", type=float, default=90.0)
    parser.add_argument("--fixed-delta", type=float, default=0.05)

    parser.add_argument("--output", default="outputs/rgb_demo")
    parser.add_argument("--save-every", type=int, default=20)
    parser.add_argument("--spawn-npc", type=int, default=20)

    parser.add_argument(
        "--sensor-timeout",
        type=float,
        default=10.0,
        help="Timeout waiting for each RGB frame.",
    )
    parser.add_argument(
        "--warmup-ticks",
        type=int,
        default=10,
        help="World ticks used to warm up the RGB sensor.",
    )
    parser.add_argument(
        "--client-timeout",
        type=float,
        default=60.0,
    )
    return parser.parse_args()


def choose_vehicle_blueprint(world) -> carla.ActorBlueprint:
    blueprints = list(
        world.get_blueprint_library().filter("vehicle.*")
    )

    preferred = []
    for bp in blueprints:
        try:
            if (
                bp.has_attribute("number_of_wheels")
                and int(bp.get_attribute("number_of_wheels")) == 4
            ):
                preferred.append(bp)
        except Exception:
            continue

    candidates = preferred or blueprints
    if not candidates:
        raise RuntimeError("No vehicle blueprint found")

    bp = random.choice(candidates)

    if bp.has_attribute("color"):
        colors = bp.get_attribute("color").recommended_values
        if colors:
            bp.set_attribute("color", random.choice(colors))

    return bp


def destroy_actors(client, actors) -> None:
    ids = []

    for actor in actors:
        try:
            if actor is not None and actor.is_alive:
                ids.append(actor.id)
        except Exception:
            pass

    if not ids:
        return

    try:
        commands = [carla.command.DestroyActor(actor_id) for actor_id in ids]
        responses = client.apply_batch_sync(commands, False)

        for actor_id, response in zip(ids, responses):
            if response.has_error():
                print(
                    f"[cleanup warning] actor={actor_id}: "
                    f"{response.error}",
                    file=sys.stderr,
                )
    except Exception as exc:
        print(
            f"[cleanup warning] batch actor destruction failed: {exc}",
            file=sys.stderr,
        )


def main() -> None:
    args = parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    jsonl_path = output / "vision_observations.jsonl"
    run_info_path = output / "run_info.json"

    client = carla.Client(args.host, args.port)
    client.set_timeout(float(args.client_timeout))

    world = None
    traffic_manager = None
    original_settings = None

    ego = None
    actors = []
    camera = None

    success_frames = 0
    start_wall = time.monotonic()

    try:
        print(
            f"[1/8] Connecting to CARLA "
            f"{args.host}:{args.port} ..."
        )
        print("[CARLA] server version:", client.get_server_version())

        world = client.get_world()
        print("[CARLA] map:", world.get_map().name)

        traffic_manager = client.get_trafficmanager(args.tm_port)
        traffic_manager.set_synchronous_mode(True)

        original_settings = world.get_settings()

        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = float(args.fixed_delta)
        settings.no_rendering_mode = False

        applied_frame = world.apply_settings(settings)
        print(
            "[2/8] Synchronous mode enabled, "
            f"apply_settings frame={applied_frame}"
        )

        spawn_points = list(world.get_map().get_spawn_points())
        if not spawn_points:
            raise RuntimeError("Current CARLA map has no spawn points")

        random.shuffle(spawn_points)

        print("[3/8] Spawning ego vehicle ...")
        ego_bp = choose_vehicle_blueprint(world)
        ego_bp.set_attribute("role_name", "hero")

        ego = None
        ego_spawn_index = None

        for index, transform in enumerate(spawn_points):
            ego = world.try_spawn_actor(ego_bp, transform)
            if ego is not None:
                ego_spawn_index = index
                break

        if ego is None:
            raise RuntimeError(
                "Failed to spawn ego vehicle at all available spawn points"
            )

        actors.append(ego)
        print(f"[CARLA] ego actor id={ego.id}")

        ego.set_autopilot(True, args.tm_port)

        print(f"[4/8] Spawning up to {args.spawn_npc} NPC vehicles ...")
        npc_count = 0

        for index, transform in enumerate(spawn_points):
            if npc_count >= args.spawn_npc:
                break
            if index == ego_spawn_index:
                continue

            try:
                bp = choose_vehicle_blueprint(world)
                bp.set_attribute("role_name", "autopilot")
                npc = world.try_spawn_actor(bp, transform)

                if npc is None:
                    continue

                npc.set_autopilot(True, args.tm_port)
                actors.append(npc)
                npc_count += 1
            except Exception as exc:
                print(
                    f"[spawn warning] NPC spawn failed: {exc}",
                    file=sys.stderr,
                )

        print(f"[CARLA] spawned NPCs={npc_count}")

        # Advance the world once so that vehicle registration and autopilot
        # state are visible before creating the sensor.
        world.tick()

        print("[5/8] Creating front RGB camera ...")
        camera = FrontRGBCamera(
            world,
            ego,
            width=args.width,
            height=args.height,
            fov_deg=args.fov,
            sensor_tick=args.fixed_delta,
        )
        print(f"[CARLA] camera actor id={camera.actor.id}")

        print(
            f"[6/8] Warming up camera for "
            f"{args.warmup_ticks} ticks ..."
        )

        first_frame = None

        for warmup_index in range(max(1, args.warmup_ticks)):
            expected_frame = world.tick()

            try:
                received = camera.get_for_frame(
                    expected_frame=expected_frame,
                    timeout_s=args.sensor_timeout,
                    max_frame_lag=2,
                )
                first_frame = received
                print(
                    "[CARLA] RGB ready: "
                    f"world_frame={expected_frame}, "
                    f"camera_frame={received.frame}, "
                    f"shape={received.image_bgr.shape}"
                )
                break
            except TimeoutError:
                print(
                    f"[warmup] no RGB image at tick "
                    f"{warmup_index + 1}/{args.warmup_ticks}",
                    file=sys.stderr,
                )

        if first_frame is None:
            raise RuntimeError(
                "RGB camera did not produce any image during warmup. "
                "Check CARLA rendering, GPU selection and server logs."
            )

        if args.backend == "carla_gt":
            backend = CarlaGroundTruthBackend(
                world,
                ego,
                args.width,
                args.height,
                args.fov,
            )
        else:
            backend = YoloV8OnnxBackend(args.model)

        service = RGBPerceptionService(backend)

        run_info = {
            "carla_server_version": client.get_server_version(),
            "map": world.get_map().name,
            "backend": args.backend,
            "width": args.width,
            "height": args.height,
            "fov_deg": args.fov,
            "fixed_delta_s": args.fixed_delta,
            "requested_frames": args.frames,
            "spawned_npc": npc_count,
            "ego_actor_id": ego.id,
            "camera_actor_id": camera.actor.id,
        }

        run_info_path.write_text(
            json.dumps(run_info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("[7/8] Running perception loop ...")

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

                fp.write(
                    json.dumps(
                        observation.to_dict(),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                fp.flush()

                if args.save_every > 0 and index % args.save_every == 0:
                    import cv2

                    annotated = draw_observation(
                        rgb_frame.image_bgr,
                        observation,
                    )

                    image_path = (
                        output
                        / f"frame_{observation.frame:06d}.jpg"
                    )

                    ok = cv2.imwrite(str(image_path), annotated)
                    if not ok:
                        print(
                            f"[warning] failed to save {image_path}",
                            file=sys.stderr,
                        )

                print(
                    json.dumps(
                        {
                            "index": index,
                            "frame": observation.frame,
                            "status": observation.perception_status,
                            "objects": len(observation.objects),
                            "traffic_light": (
                                observation.traffic_light.state
                            ),
                            "summary": observation.scene_summary,
                            "latency_ms": observation.latency_ms,
                        },
                        ensure_ascii=False,
                    )
                )

                success_frames += 1

        print(
            f"[8/8] Completed: "
            f"{success_frames}/{args.frames} frames"
        )

    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)

    except Exception:
        print("\n[FATAL] RGB demo failed:", file=sys.stderr)
        traceback.print_exc()
        raise

    finally:
        print("[cleanup] stopping RGB camera ...")

        if camera is not None:
            try:
                camera.stop()
            except Exception as exc:
                print(
                    f"[cleanup warning] camera stop failed: {exc}",
                    file=sys.stderr,
                )

        # Advance one synchronous frame after stop when possible, allowing
        # pending sensor callbacks to finish before actor destruction.
        if world is not None:
            try:
                settings_now = world.get_settings()
                if settings_now.synchronous_mode:
                    world.tick()
            except Exception:
                pass

        print("[cleanup] destroying actors ...")

        sensor_actors = []
        if camera is not None and camera.actor is not None:
            sensor_actors.append(camera.actor)
            camera.actor = None

        destroy_actors(client, sensor_actors)
        destroy_actors(client, list(reversed(actors)))

        if traffic_manager is not None:
            try:
                traffic_manager.set_synchronous_mode(False)
            except Exception as exc:
                print(
                    f"[cleanup warning] traffic manager restore failed: {exc}",
                    file=sys.stderr,
                )

        if world is not None and original_settings is not None:
            try:
                world.apply_settings(original_settings)
            except Exception as exc:
                print(
                    f"[cleanup warning] world settings restore failed: {exc}",
                    file=sys.stderr,
                )

        elapsed_s = time.monotonic() - start_wall

        print(f"Results: {jsonl_path}")
        print(f"Successful frames: {success_frames}")
        print(f"Wall time: {elapsed_s:.2f}s")


if __name__ == "__main__":
    main()
