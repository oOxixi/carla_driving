"""Generate and capture real CARLA RGB scenes for Day22 validation."""

from __future__ import annotations

import argparse
import queue
import random
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scene",
        required=True,
        choices=(
            "empty",
            "front_vehicle",
            "pedestrian",
            "red_light",
        ),
    )

    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout-s", type=float, default=20.0)

    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    parser.add_argument("--fov", type=float, default=90.0)

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--spawn-index",
        type=int,
        default=0,
    )

    return parser.parse_args()


def shifted_location(
    transform: Any,
    forward_m: float,
    right_m: float = 0.0,
):
    location = transform.location
    forward = transform.get_forward_vector()
    right = transform.get_right_vector()

    return type(location)(
        x=(
            location.x
            + forward.x * forward_m
            + right.x * right_m
        ),
        y=(
            location.y
            + forward.y * forward_m
            + right.y * right_m
        ),
        z=location.z,
    )


def choose_vehicle_blueprint(world):
    blueprints = list(
        world.get_blueprint_library().filter("vehicle.*")
    )

    preferred = [
        bp
        for bp in blueprints
        if int(bp.get_attribute("number_of_wheels")) == 4
        and not bp.id.endswith("isetta")
        and not bp.id.endswith("carlacola")
        and not bp.id.endswith("cybertruck")
    ]

    return random.choice(preferred or blueprints)


def spawn_ego(world, carla, spawn_index: int):
    spawn_points = world.get_map().get_spawn_points()

    if not spawn_points:
        raise RuntimeError("CARLA map has no spawn points")

    start = spawn_index % len(spawn_points)

    for offset in range(len(spawn_points)):
        transform = spawn_points[
            (start + offset) % len(spawn_points)
        ]

        transform.location.z += 0.3

        blueprint = choose_vehicle_blueprint(world)
        blueprint.set_attribute("role_name", "hero")

        actor = world.try_spawn_actor(
            blueprint,
            transform,
        )

        if actor is not None:
            return actor

    raise RuntimeError("Unable to spawn ego vehicle")


def spawn_front_vehicle(world, carla, ego):
    transform = ego.get_transform()

    target_transform = carla.Transform(
        shifted_location(
            transform,
            forward_m=12.0,
        ),
        transform.rotation,
    )

    target_transform.location.z += 0.3

    blueprint = choose_vehicle_blueprint(world)

    actor = world.try_spawn_actor(
        blueprint,
        target_transform,
    )

    if actor is None:
        raise RuntimeError(
            "Unable to spawn front vehicle"
        )

    return actor


def spawn_pedestrian(world, carla, ego):
    transform = ego.get_transform()

    target_location = shifted_location(
        transform,
        forward_m=10.0,
        right_m=0.5,
    )

    target_location.z += 0.8

    walker_blueprints = list(
        world.get_blueprint_library().filter(
            "walker.pedestrian.*"
        )
    )

    random.shuffle(walker_blueprints)

    for blueprint in walker_blueprints:
        actor = world.try_spawn_actor(
            blueprint,
            carla.Transform(
                target_location,
                carla.Rotation(
                    yaw=transform.rotation.yaw + 90.0
                ),
            ),
        )

        if actor is not None:
            return actor

    raise RuntimeError("Unable to spawn pedestrian")


def setup_red_light_scene(world, carla):
    traffic_lights = list(
        world.get_actors().filter("traffic.traffic_light*")
    )

    random.shuffle(traffic_lights)

    for traffic_light in traffic_lights:
        try:
            stop_waypoints = (
                traffic_light.get_stop_waypoints()
            )
        except Exception:
            continue

        if not stop_waypoints:
            continue

        stop_waypoint = stop_waypoints[0]
        previous = stop_waypoint.previous(8.0)

        ego_waypoint = (
            previous[0]
            if previous
            else stop_waypoint
        )

        transform = ego_waypoint.transform
        transform.location.z += 0.3

        blueprint = choose_vehicle_blueprint(world)
        blueprint.set_attribute("role_name", "hero")

        ego = world.try_spawn_actor(
            blueprint,
            transform,
        )

        if ego is None:
            continue

        original_state = traffic_light.get_state()

        traffic_light.set_state(
            carla.TrafficLightState.Red
        )

        try:
            traffic_light.freeze(True)
        except Exception:
            pass

        return ego, traffic_light, original_state

    raise RuntimeError(
        "Unable to create red-light scene. "
        "No usable traffic light/stop waypoint found."
    )


def attach_camera(
    world,
    carla,
    ego,
    width: int,
    height: int,
    fov: float,
):
    blueprint = world.get_blueprint_library().find(
        "sensor.camera.rgb"
    )

    blueprint.set_attribute(
        "image_size_x",
        str(width),
    )
    blueprint.set_attribute(
        "image_size_y",
        str(height),
    )
    blueprint.set_attribute(
        "fov",
        str(fov),
    )

    transform = carla.Transform(
        carla.Location(
            x=1.5,
            y=0.0,
            z=2.2,
        ),
        carla.Rotation(
            pitch=-5.0,
        ),
    )

    return world.spawn_actor(
        blueprint,
        transform,
        attach_to=ego,
        attachment_type=carla.AttachmentType.Rigid,
    )


def main() -> None:
    args = parse_args()

    try:
        import carla
    except ImportError as exc:
        raise RuntimeError(
            "CARLA Python package is unavailable"
        ) from exc

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    client = carla.Client(args.host, args.port)
    client.set_timeout(args.timeout_s)

    world = client.get_world()
    original_settings = world.get_settings()

    created_actors = []
    traffic_light = None
    original_light_state = None

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05
        world.apply_settings(settings)

        if args.scene == "red_light":
            ego, traffic_light, original_light_state = (
                setup_red_light_scene(world, carla)
            )
        else:
            ego = spawn_ego(
                world,
                carla,
                args.spawn_index,
            )

        created_actors.append(ego)

        if args.scene == "front_vehicle":
            created_actors.append(
                spawn_front_vehicle(
                    world,
                    carla,
                    ego,
                )
            )

        elif args.scene == "pedestrian":
            created_actors.append(
                spawn_pedestrian(
                    world,
                    carla,
                    ego,
                )
            )

        camera = attach_camera(
            world,
            carla,
            ego,
            args.width,
            args.height,
            args.fov,
        )

        created_actors.append(camera)

        frame_queue: queue.Queue = queue.Queue()
        camera.listen(frame_queue.put)

        selected_image = None

        for _ in range(10):
            world.tick()

            try:
                selected_image = frame_queue.get(
                    timeout=args.timeout_s
                )
            except queue.Empty:
                continue

        if selected_image is None:
            raise RuntimeError(
                "No CARLA camera frame received"
            )

        selected_image.save_to_disk(str(output))

        print(f"saved: {output}")
        print(f"scene: {args.scene}")
        print(
            "resolution:",
            f"{selected_image.width}x"
            f"{selected_image.height}",
        )

    finally:
        if traffic_light is not None:
            try:
                traffic_light.set_state(
                    original_light_state
                )
                traffic_light.freeze(False)
            except Exception:
                pass

        for actor in reversed(created_actors):
            try:
                if "sensor." in actor.type_id:
                    actor.stop()
            except Exception:
                pass

            try:
                actor.destroy()
            except Exception:
                pass

        world.apply_settings(original_settings)


if __name__ == "__main__":
    main()
