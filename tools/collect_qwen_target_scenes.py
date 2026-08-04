"""Collect real CARLA RGB frames with deterministic multi-vehicle annotations."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import queue
import random
from typing import Any

import carla
import numpy as np


def _jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_direction(first: carla.Waypoint, second: carla.Waypoint) -> bool:
    a = first.transform.get_forward_vector()
    b = second.transform.get_forward_vector()
    return a.x * b.x + a.y * b.y + a.z * b.z > 0.8


def _adjacent_waypoint(waypoint: carla.Waypoint) -> tuple[carla.Waypoint | None, str]:
    for candidate, relation in (
        (waypoint.get_left_lane(), "left_adjacent"),
        (waypoint.get_right_lane(), "right_adjacent"),
    ):
        if (
            candidate is not None
            and candidate.lane_type == carla.LaneType.Driving
            and _same_direction(waypoint, candidate)
        ):
            return candidate, relation
    return None, ""


def _lifted(transform: carla.Transform, z_offset: float = 0.35) -> carla.Transform:
    location = transform.location
    return carla.Transform(
        carla.Location(x=location.x, y=location.y, z=location.z + z_offset),
        transform.rotation,
    )


def _distance(first: carla.Location, second: carla.Location) -> float:
    dx = first.x - second.x
    dy = first.y - second.y
    dz = first.z - second.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _camera_intrinsic(width: int, height: int, fov_degrees: float) -> np.ndarray:
    focal = width / (2.0 * math.tan(math.radians(fov_degrees) / 2.0))
    matrix = np.identity(3)
    matrix[0, 0] = matrix[1, 1] = focal
    matrix[0, 2] = width / 2.0
    matrix[1, 2] = height / 2.0
    return matrix


def _project_bbox(
    actor: carla.Actor,
    camera: carla.Sensor,
    width: int,
    height: int,
    fov_degrees: float,
) -> list[float] | None:
    inverse = np.array(camera.get_transform().get_inverse_matrix())
    intrinsic = _camera_intrinsic(width, height, fov_degrees)
    pixels: list[tuple[float, float]] = []
    for vertex in actor.bounding_box.get_world_vertices(actor.get_transform()):
        world = np.array([vertex.x, vertex.y, vertex.z, 1.0])
        sensor = inverse @ world
        conventional = np.array([sensor[1], -sensor[2], sensor[0]])
        if conventional[2] <= 0.1:
            continue
        projected = intrinsic @ conventional
        x = float(projected[0] / projected[2])
        y = float(projected[1] / projected[2])
        pixels.append((x, y))
    if not pixels:
        return None
    left = max(0.0, min(x for x, _ in pixels))
    top = max(0.0, min(y for _, y in pixels))
    right = min(float(width - 1), max(x for x, _ in pixels))
    bottom = min(float(height - 1), max(y for _, y in pixels))
    if right - left < 2.0 or bottom - top < 2.0:
        return None
    return [
        round(left / width, 6),
        round(top / height, 6),
        round(right / width, 6),
        round(bottom / height, 6),
    ]


def _spawn_actor(
    world: carla.World,
    blueprint: carla.ActorBlueprint,
    transform: carla.Transform,
) -> carla.Actor:
    actor = world.try_spawn_actor(blueprint, _lifted(transform))
    if actor is None:
        raise RuntimeError(f"could not spawn actor at {transform.location}")
    actor.set_simulate_physics(False)
    return actor


def _select_layout(
    world_map: carla.Map,
    spawn_points: list[carla.Transform],
    seed: int,
    *,
    occlusion: bool,
) -> tuple[carla.Transform, carla.Waypoint, carla.Waypoint, str]:
    start = seed % len(spawn_points)
    for offset in range(len(spawn_points)):
        ego_transform = spawn_points[(start + offset) % len(spawn_points)]
        ego_waypoint = world_map.get_waypoint(
            ego_transform.location,
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        ahead = ego_waypoint.next(12.0 if occlusion else 16.0)
        if not ahead:
            continue
        center = ahead[0]
        if occlusion:
            farther = ego_waypoint.next(24.0)
            if farther:
                return ego_transform, center, farther[0], "far_ahead_occluded"
            continue
        adjacent, relation = _adjacent_waypoint(center)
        if adjacent is not None:
            return ego_transform, center, adjacent, relation
        farther = ego_waypoint.next(27.0)
        if farther:
            return ego_transform, center, farther[0], "far_ahead"
    raise RuntimeError("no usable two-target road layout found")


def _collect_one(
    world: carla.World,
    seed: int,
    image_dir: Path,
    width: int,
    height: int,
    fov: float,
    actors: list[carla.Actor],
    *,
    weather_profile: str,
    pedestrian_second: bool,
    occlusion: bool,
    dense_target_count: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rng = random.Random(seed)
    blueprints = world.get_blueprint_library()
    vehicle_blueprints = sorted(
        blueprints.filter("vehicle.*"),
        key=lambda item: item.id,
    )
    preferred = [
        blueprint
        for blueprint in vehicle_blueprints
        if int(blueprint.get_attribute("number_of_wheels").as_int()) == 4
    ]
    ego_blueprint = blueprints.find("vehicle.tesla.model3")
    target_blueprints = preferred or vehicle_blueprints
    walker_blueprints = sorted(
        blueprints.filter("walker.pedestrian.*"),
        key=lambda item: item.id,
    )
    spawn_points = world.get_map().get_spawn_points()
    ego_transform, center_waypoint, second_waypoint, second_relation = _select_layout(
        world.get_map(), spawn_points, seed, occlusion=occlusion,
    )

    ego = _spawn_actor(world, ego_blueprint, ego_transform)
    actors.append(ego)
    center = _spawn_actor(
        world,
        target_blueprints[rng.randrange(len(target_blueprints))],
        center_waypoint.transform,
    )
    actors.append(center)
    if pedestrian_second:
        if not walker_blueprints:
            raise RuntimeError("no pedestrian blueprint is available")
        second_blueprint = walker_blueprints[rng.randrange(len(walker_blueprints))]
    else:
        second_blueprint = target_blueprints[rng.randrange(len(target_blueprints))]
    second = _spawn_actor(
        world,
        second_blueprint,
        second_waypoint.transform,
    )
    actors.append(second)
    target_specs: list[tuple[str, carla.Actor, str, str]] = [
        ("center", center, "center_ahead", "vehicle"),
        (
            "second",
            second,
            second_relation,
            "pedestrian" if pedestrian_second else "vehicle",
        ),
    ]
    ego_waypoint = world.get_map().get_waypoint(
        ego_transform.location,
        project_to_road=True,
        lane_type=carla.LaneType.Driving,
    )
    for dense_index in range(max(0, dense_target_count - 2)):
        dense_actor = None
        for retry in range(6):
            distance_m = 30.0 + dense_index * 8.0 + retry * 1.5
            candidates = ego_waypoint.next(distance_m)
            if not candidates:
                continue
            dense_actor = world.try_spawn_actor(
                target_blueprints[rng.randrange(len(target_blueprints))],
                _lifted(candidates[0].transform),
            )
            if dense_actor is not None:
                dense_actor.set_simulate_physics(False)
                break
        if dense_actor is None:
            continue
        actors.append(dense_actor)
        target_specs.append(
            (
                f"dense_{dense_index}",
                dense_actor,
                f"dense_ahead_{dense_index + 1}",
                "vehicle",
            )
        )

    camera_blueprint = blueprints.find("sensor.camera.rgb")
    camera_blueprint.set_attribute("image_size_x", str(width))
    camera_blueprint.set_attribute("image_size_y", str(height))
    camera_blueprint.set_attribute("fov", str(fov))
    camera_blueprint.set_attribute("sensor_tick", "0.05")
    camera = world.spawn_actor(
        camera_blueprint,
        carla.Transform(carla.Location(x=1.5, z=1.7)),
        attach_to=ego,
    )
    actors.append(camera)
    frames: queue.Queue[carla.Image] = queue.Queue()
    camera.listen(frames.put)
    lidar_blueprint = blueprints.find("sensor.lidar.ray_cast")
    lidar_blueprint.set_attribute("sensor_tick", "0.05")
    lidar_blueprint.set_attribute("range", "50")
    lidar_blueprint.set_attribute("channels", "32")
    lidar_blueprint.set_attribute("points_per_second", "120000")
    lidar = world.spawn_actor(
        lidar_blueprint,
        carla.Transform(carla.Location(x=0.0, z=2.2)),
        attach_to=ego,
    )
    actors.append(lidar)
    lidar_frames: queue.Queue[carla.LidarMeasurement] = queue.Queue()
    lidar.listen(lidar_frames.put)
    for _ in range(4):
        world.tick()
    image = frames.get(timeout=10.0)
    while not frames.empty():
        image = frames.get_nowait()
    lidar_measurement = lidar_frames.get(timeout=10.0)
    while lidar_measurement.frame < image.frame:
        lidar_measurement = lidar_frames.get(timeout=10.0)
    while image.frame < lidar_measurement.frame:
        image = frames.get(timeout=10.0)
    if lidar_measurement.frame != image.frame:
        raise RuntimeError(
            f"could not align RGB/LiDAR frames: rgb={image.frame}, "
            f"lidar={lidar_measurement.frame}"
        )

    image_name = f"town03opt_target_seed_{seed:02d}.png"
    image_path = image_dir / image_name
    image.save_to_disk(str(image_path))
    lidar_name = f"town03opt_target_seed_{seed:02d}.npy"
    lidar_path = image_dir.parent / "lidar"
    lidar_path.mkdir(parents=True, exist_ok=True)
    lidar_file = lidar_path / lidar_name
    lidar_points = np.frombuffer(
        lidar_measurement.raw_data,
        dtype=np.float32,
    ).reshape((-1, 4)).copy()
    np.save(lidar_file, lidar_points)

    ego_location = ego.get_location()
    ids: dict[str, str] = {
        "center": f"vehicle_center_seed_{seed:02d}",
        "second": (
            f"pedestrian_{second_relation}_seed_{seed:02d}"
            if pedestrian_second
            else f"vehicle_{second_relation}_seed_{seed:02d}"
        ),
    }
    for dense_index in range(max(0, len(target_specs) - 2)):
        ids[f"dense_{dense_index}"] = (
            f"vehicle_dense_ahead_{dense_index + 1}_seed_{seed:02d}"
        )
    objects = []
    for label, actor, relation, class_name in target_specs:
        bbox = _project_bbox(actor, camera, width, height, fov)
        if bbox is None:
            raise RuntimeError(
                f"target {label} is not visible for seed {seed}"
            )
        objects.append(
            {
                "track_id": ids[label],
                "carla_actor_id": actor.id,
                "class": class_name,
                "relation": relation,
                "distance_m": round(_distance(ego_location, actor.get_location()), 3),
                "bbox_xyxy_norm": bbox,
                "blueprint": actor.type_id,
                "source": "carla_ground_truth_projection",
            }
        )

    scene_id = f"town03opt_multi_target_seed_{seed:02d}"
    relative_ref = f"images/{image_name}"
    scene = {
        "scene_id": scene_id,
        "seed": seed,
        "map": world.get_map().name,
        "weather_profile": weather_profile,
        "frame": image.frame,
        "rgb_ref": relative_ref,
        "rgb_sha256": _sha256(image_path),
        "lidar_ref": f"lidar/{lidar_name}",
        "lidar_sha256": _sha256(lidar_file),
        "lidar_point_count": int(lidar_points.shape[0]),
        "image_size": [width, height],
        "ego_actor_id": ego.id,
        "objects": objects,
    }
    vehicle_phrases = {
        "left_adjacent": "左侧相邻车道的车辆",
        "right_adjacent": "右侧相邻车道的车辆",
        "far_ahead": "较远的前车",
        "far_ahead_occluded": "被前车部分遮挡的较远车辆",
    }
    pedestrian_phrases = {
        "left_adjacent": "左侧相邻车道的行人",
        "right_adjacent": "右侧相邻车道的行人",
        "far_ahead": "前方较远的行人",
        "far_ahead_occluded": "被前车部分遮挡的较远行人",
    }
    second_phrase = (
        pedestrian_phrases if pedestrian_second else vehicle_phrases
    )[second_relation]
    second_command = (
        f"减速并避让{second_phrase}"
        if pedestrian_second
        else f"减速并跟随{second_phrase}"
    )
    cases = [
        {
            "case_id": f"{scene_id}_center",
            "category": "target_association",
            "rgb_ref": relative_ref,
            "voice_command": "减速并跟随正前方的车辆",
            "scene_state": {"weather_profile": weather_profile},
            "perception": {
                "detected_objects": objects,
                "lidar_summary": {
                    "valid": True,
                    "point_count": int(lidar_points.shape[0]),
                    "front_corridor_min_m": _front_corridor_min(lidar_points),
                    "source": "raw_carla_lidar",
                },
            },
            "expected": {
                "actions": ["SLOW_DOWN", "FOLLOW_VEHICLE"],
                "requires_confirmation": False,
                "target_track_id": ids["center"],
            },
        },
        {
            "case_id": f"{scene_id}_second",
            "category": "target_association",
            "rgb_ref": relative_ref,
            "voice_command": second_command,
            "scene_state": {"weather_profile": weather_profile},
            "perception": {
                "detected_objects": objects,
                "lidar_summary": {
                    "valid": True,
                    "point_count": int(lidar_points.shape[0]),
                    "front_corridor_min_m": _front_corridor_min(lidar_points),
                    "source": "raw_carla_lidar",
                },
            },
            "expected": {
                "actions": (
                    ["SLOW_DOWN"]
                    if pedestrian_second
                    else ["SLOW_DOWN", "FOLLOW_VEHICLE"]
                ),
                "requires_confirmation": False,
                "target_track_id": ids["second"],
            },
        },
    ]
    return scene, cases


def _front_corridor_min(points: np.ndarray) -> float | None:
    """Summarize raw CARLA LiDAR for the high-level four-modal context."""
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError("LiDAR points must be an Nx4-like array")
    mask = (
        (points[:, 0] > 0.5)
        & (points[:, 0] < 50.0)
        & (np.abs(points[:, 1]) <= 2.0)
        & (points[:, 2] > -2.5)
        & (points[:, 2] < 2.5)
    )
    if not np.any(mask):
        return None
    return round(float(np.min(points[mask, 0])), 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=450)
    parser.add_argument("--fov", type=float, default=90.0)
    parser.add_argument(
        "--weather-profiles",
        default="clear_day",
        help="comma-separated cycle: clear_day,hard_rain,night,fog,sunset",
    )
    parser.add_argument(
        "--pedestrian-seeds",
        default="",
        help="comma-separated seeds whose second target is a pedestrian",
    )
    parser.add_argument(
        "--occlusion-seeds",
        default="",
        help="comma-separated seeds using two same-lane vehicles",
    )
    parser.add_argument(
        "--dense-target-count",
        type=int,
        default=2,
        help="total projected actors per scene; values above two add same-lane distractors",
    )
    args = parser.parse_args()

    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    weather_profiles = [
        item.strip() for item in args.weather_profiles.split(",") if item.strip()
    ]
    pedestrian_seeds = {
        int(item.strip())
        for item in args.pedestrian_seeds.split(",")
        if item.strip()
    }
    occlusion_seeds = {
        int(item.strip())
        for item in args.occlusion_seeds.split(",")
        if item.strip()
    }
    if not weather_profiles:
        raise ValueError("at least one weather profile is required")
    if args.dense_target_count < 2 or args.dense_target_count > 8:
        raise ValueError("dense-target-count must be in [2, 8]")
    output_dir = args.output_dir.resolve()
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    client = carla.Client(args.host, args.port)
    client.set_timeout(20.0)
    world = client.get_world()
    original_settings = world.get_settings()
    original_weather = world.get_weather()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    scenes: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    try:
        for seed in seeds:
            actors: list[carla.Actor] = []
            try:
                weather_profile = weather_profiles[len(scenes) % len(weather_profiles)]
                weather_options = {
                    "clear_day": carla.WeatherParameters.ClearNoon,
                    "hard_rain": carla.WeatherParameters.HardRainNoon,
                    "sunset": carla.WeatherParameters.ClearSunset,
                    "night": carla.WeatherParameters(
                        cloudiness=20.0,
                        precipitation=0.0,
                        sun_altitude_angle=-25.0,
                        fog_density=5.0,
                    ),
                    "fog": carla.WeatherParameters(
                        cloudiness=80.0,
                        precipitation=10.0,
                        sun_altitude_angle=15.0,
                        fog_density=65.0,
                        fog_distance=5.0,
                        fog_falloff=1.0,
                    ),
                }
                try:
                    world.set_weather(weather_options[weather_profile])
                except KeyError as error:
                    raise ValueError(
                        f"unknown weather profile: {weather_profile!r}"
                    ) from error
                scene, scene_cases = _collect_one(
                    world,
                    seed,
                    image_dir,
                    args.width,
                    args.height,
                    args.fov,
                    actors,
                    weather_profile=weather_profile,
                    pedestrian_second=seed in pedestrian_seeds,
                    occlusion=seed in occlusion_seeds,
                    dense_target_count=args.dense_target_count,
                )
                scenes.append(scene)
                cases.extend(scene_cases)
                print(json.dumps(scene, ensure_ascii=False), flush=True)
            finally:
                for actor in reversed(actors):
                    if actor.is_alive:
                        actor.destroy()
                world.tick()
    finally:
        world.set_weather(original_weather)
        world.apply_settings(original_settings)

    _jsonl(output_dir / "scenes.jsonl", scenes)
    _jsonl(output_dir / "cases.jsonl", cases)
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "real_carla_0.9.16_rgb_and_actor_ground_truth",
        "map": world.get_map().name,
        "seeds": seeds,
        "weather_profiles": weather_profiles,
        "pedestrian_seeds": sorted(pedestrian_seeds),
        "occlusion_seeds": sorted(occlusion_seeds),
        "dense_target_count": args.dense_target_count,
        "scene_count": len(scenes),
        "case_count": len(cases),
        "distinct_rgb_refs": len({scene["rgb_ref"] for scene in scenes}),
        "all_targets_projected": True,
    }
    (output_dir / "collection_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
