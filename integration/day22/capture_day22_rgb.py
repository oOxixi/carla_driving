"""Capture one real CARLA RGB frame for Day22 multimodal validation.

This utility:
- connects to an already running CARLA server;
- finds the existing ego/hero vehicle;
- attaches a temporary RGB camera;
- saves one PNG image;
- destroys only the temporary camera it created.

It does not spawn/control the ego vehicle and does not call apply_control().
"""

from __future__ import annotations

import argparse
import queue
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture one RGB frame from the current CARLA world."
    )

    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout-s", type=float, default=20.0)

    parser.add_argument(
        "--output",
        required=True,
        help="Output PNG path.",
    )

    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    parser.add_argument("--fov", type=float, default=90.0)

    parser.add_argument(
        "--warmup-frames",
        type=int,
        default=5,
        help="Discard this many camera frames before saving.",
    )

    parser.add_argument(
        "--ego-role-name",
        default="hero",
        help="Preferred CARLA role_name for the ego vehicle.",
    )

    parser.add_argument(
        "--camera-x",
        type=float,
        default=1.5,
    )
    parser.add_argument(
        "--camera-z",
        type=float,
        default=2.2,
    )
    parser.add_argument(
        "--camera-pitch",
        type=float,
        default=-5.0,
    )

    return parser.parse_args()


def find_ego_vehicle(world, preferred_role_name: str):
    vehicles = list(world.get_actors().filter("vehicle.*"))

    if not vehicles:
        raise RuntimeError(
            "No vehicle actor exists in the CARLA world. "
            "Start the scenario/runner first."
        )

    for vehicle in vehicles:
        if vehicle.attributes.get("role_name") == preferred_role_name:
            return vehicle

    for role_name in ("ego", "hero", "autopilot"):
        for vehicle in vehicles:
            if vehicle.attributes.get("role_name") == role_name:
                return vehicle

    print(
        "WARNING: no hero/ego role_name found; "
        f"using first vehicle actor id={vehicles[0].id}"
    )

    return vehicles[0]


def main() -> None:
    args = parse_args()

    if args.width <= 0 or args.height <= 0:
        raise ValueError("image width and height must be positive")

    if args.warmup_frames < 0:
        raise ValueError("warmup-frames must be non-negative")

    try:
        import carla
    except ImportError as exc:
        raise RuntimeError(
            "The CARLA Python package is unavailable in this environment."
        ) from exc

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = carla.Client(args.host, args.port)
    client.set_timeout(args.timeout_s)

    world = client.get_world()
    ego = find_ego_vehicle(world, args.ego_role_name)

    blueprint_library = world.get_blueprint_library()
    camera_bp = blueprint_library.find("sensor.camera.rgb")

    camera_bp.set_attribute("image_size_x", str(args.width))
    camera_bp.set_attribute("image_size_y", str(args.height))
    camera_bp.set_attribute("fov", str(args.fov))
    camera_bp.set_attribute("sensor_tick", "0.0")

    transform = carla.Transform(
        carla.Location(
            x=args.camera_x,
            y=0.0,
            z=args.camera_z,
        ),
        carla.Rotation(
            pitch=args.camera_pitch,
            yaw=0.0,
            roll=0.0,
        ),
    )

    camera = None
    frame_queue: queue.Queue = queue.Queue(maxsize=32)

    try:
        camera = world.spawn_actor(
            camera_bp,
            transform,
            attach_to=ego,
            attachment_type=carla.AttachmentType.Rigid,
        )

        camera.listen(frame_queue.put)

        selected_image = None

        for frame_index in range(args.warmup_frames + 1):
            try:
                image = frame_queue.get(timeout=args.timeout_s)
            except queue.Empty as exc:
                raise RuntimeError(
                    "Timed out waiting for a CARLA RGB frame. "
                    "Ensure the scenario runner is ticking the world."
                ) from exc

            if frame_index >= args.warmup_frames:
                selected_image = image
                break

        if selected_image is None:
            raise RuntimeError("No RGB frame was selected")

        selected_image.save_to_disk(str(output_path))

        print(f"saved: {output_path}")
        print(f"frame: {selected_image.frame}")
        print(f"resolution: {selected_image.width}x{selected_image.height}")
        print(f"ego_actor_id: {ego.id}")
        print(
            "ego_role_name:",
            ego.attributes.get("role_name", ""),
        )

    finally:
        if camera is not None:
            try:
                camera.stop()
            except Exception:
                pass

            try:
                camera.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    main()
