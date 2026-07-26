from __future__ import annotations

import argparse
import queue
from pathlib import Path
from typing import Optional

import carla
import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 CARLA 前视 RGB 相机采集一张 Qwen 测试图"
    )

    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout-s", type=float, default=30.0)

    parser.add_argument(
        "--map",
        default=None,
        help="可选地图名，例如 Town03_Opt；省略时使用当前地图",
    )
    parser.add_argument("--spawn-index", type=int, default=0)

    parser.add_argument(
        "--output",
        default="artifacts/runtime/qwen_test.jpg",
    )

    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=450)
    parser.add_argument("--fov", type=float, default=100.0)

    parser.add_argument(
        "--map-warmup-frames",
        type=int,
        default=40,
        help="优化地图瓦片加载预热帧数",
    )
    parser.add_argument(
        "--sensor-warmup-frames",
        type=int,
        default=10,
        help="相机挂载后的预热帧数",
    )

    parser.add_argument(
        "--lead-distance-m",
        type=float,
        default=18.0,
        help="在自车前方生成一辆静止前车；小于等于0表示不生成",
    )

    return parser.parse_args()


def save_carla_image_as_jpeg(
    carla_image: carla.Image,
    output_path: Path,
) -> None:
    """把 CARLA BGRA 图像转换成标准 RGB JPEG。"""

    raw = np.frombuffer(carla_image.raw_data, dtype=np.uint8)

    expected_size = (
        carla_image.width
        * carla_image.height
        * 4
    )

    if raw.size != expected_size:
        raise RuntimeError(
            f"图像数据大小异常：实际 {raw.size}，"
            f"预期 {expected_size}"
        )

    bgra = raw.reshape(
        (
            carla_image.height,
            carla_image.width,
            4,
        )
    )

    # CARLA 原始格式为 BGRA，Pillow 需要 RGB。
    rgb = bgra[:, :, :3][:, :, ::-1]

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    Image.fromarray(rgb).save(
        output_path,
        format="JPEG",
        quality=90,
        optimize=True,
    )


def find_spawn_transform(
    world: carla.World,
    spawn_index: int,
) -> carla.Transform:
    spawn_points = world.get_map().get_spawn_points()

    if not spawn_points:
        raise RuntimeError("当前地图没有可用车辆出生点")

    return spawn_points[
        spawn_index % len(spawn_points)
    ]


def spawn_ego(
    world: carla.World,
    preferred_transform: carla.Transform,
) -> carla.Vehicle:
    blueprint_library = world.get_blueprint_library()

    candidates = list(
        blueprint_library.filter("vehicle.tesla.model3")
    )

    if not candidates:
        candidates = list(
            blueprint_library.filter("vehicle.*")
        )

    if not candidates:
        raise RuntimeError("没有找到车辆蓝图")

    vehicle_bp = candidates[0]

    if vehicle_bp.has_attribute("role_name"):
        vehicle_bp.set_attribute("role_name", "hero")

    spawn_points = world.get_map().get_spawn_points()

    ordered_points = [preferred_transform]

    ordered_points.extend(
        point
        for point in spawn_points
        if point != preferred_transform
    )

    for transform in ordered_points:
        ego = world.try_spawn_actor(
            vehicle_bp,
            transform,
        )

        if ego is not None:
            return ego

    raise RuntimeError(
        "所有出生点都被占用，无法生成自车。"
        "请确认没有残留车辆。"
    )


def spawn_static_lead_vehicle(
    world: carla.World,
    ego: carla.Vehicle,
    distance_m: float,
) -> Optional[carla.Vehicle]:
    if distance_m <= 0:
        return None

    world_map = world.get_map()

    ego_waypoint = world_map.get_waypoint(
        ego.get_location(),
        project_to_road=True,
        lane_type=carla.LaneType.Driving,
    )

    if ego_waypoint is None:
        print("warning: 找不到自车道路 waypoint，不生成前车")
        return None

    next_waypoints = ego_waypoint.next(distance_m)

    if not next_waypoints:
        print("warning: 自车前方没有足够长的道路，不生成前车")
        return None

    lead_transform = next_waypoints[0].transform

    # 略微抬高，避免车型初始轮胎陷入地面。
    lead_transform.location.z += 0.3

    blueprint_library = world.get_blueprint_library()

    candidates = list(
        blueprint_library.filter("vehicle.audi.tt")
    )

    if not candidates:
        candidates = list(
            blueprint_library.filter("vehicle.*")
        )

    if not candidates:
        print("warning: 没有可用车辆蓝图，不生成前车")
        return None

    lead_bp = candidates[0]

    if lead_bp.has_attribute("role_name"):
        lead_bp.set_attribute(
            "role_name",
            "qwen_test_lead",
        )

    lead = world.try_spawn_actor(
        lead_bp,
        lead_transform,
    )

    if lead is None:
        print(
            "warning: 前车生成失败，"
            "仍继续采集无前车图像"
        )
        return None

    # 不调用 set_autopilot：会强制启动 Traffic Manager（默认绑 8000），
    # 本机常被 SSH 隧道/其他服务占用。静止车只需 apply_control 即可。
    lead.apply_control(
        carla.VehicleControl(
            throttle=0.0,
            brake=1.0,
            hand_brake=True,
        )
    )

    return lead


def create_front_camera(
    world: carla.World,
    ego: carla.Vehicle,
    *,
    width: int,
    height: int,
    fov: float,
) -> carla.Sensor:
    camera_bp = world.get_blueprint_library().find(
        "sensor.camera.rgb"
    )

    camera_bp.set_attribute(
        "image_size_x",
        str(width),
    )
    camera_bp.set_attribute(
        "image_size_y",
        str(height),
    )
    camera_bp.set_attribute(
        "fov",
        str(fov),
    )
    camera_bp.set_attribute(
        "sensor_tick",
        "0.05",
    )

    # 与仓库 7.25 分支默认前视 RGB 相机保持一致：
    # x=1.5, y=0, z=2.2, pitch=-8°
    camera_transform = carla.Transform(
        carla.Location(
            x=1.5,
            y=0.0,
            z=2.2,
        ),
        carla.Rotation(
            pitch=-8.0,
            yaw=0.0,
            roll=0.0,
        ),
    )

    return world.spawn_actor(
        camera_bp,
        camera_transform,
        attach_to=ego,
        attachment_type=carla.AttachmentType.Rigid,
    )


def drain_latest_image(
    image_queue: queue.Queue,
    latest: Optional[carla.Image],
) -> Optional[carla.Image]:
    while True:
        try:
            latest = image_queue.get_nowait()
        except queue.Empty:
            break

    return latest


def main() -> None:
    args = parse_args()

    output_path = Path(args.output).expanduser().resolve()

    client = carla.Client(
        args.host,
        args.port,
    )
    client.set_timeout(args.timeout_s)

    print(
        f"[1/8] 连接 CARLA："
        f"{args.host}:{args.port}"
    )

    world = client.get_world()

    current_map_name = world.get_map().name

    print(
        f"[2/8] 当前地图："
        f"{current_map_name}"
    )

    if args.map:
        normalized_current = current_map_name.split("/")[-1]

        if normalized_current != args.map:
            print(
                f"[3/8] 加载地图："
                f"{args.map}"
            )
            world = client.load_world(args.map)
        else:
            print(
                f"[3/8] 已经位于地图："
                f"{args.map}"
            )
    else:
        print("[3/8] 使用当前地图，不执行 load_world")

    original_settings = world.get_settings()
    original_weather = world.get_weather()

    actors: list[carla.Actor] = []
    camera: Optional[carla.Sensor] = None

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05

        # 强制确保 RGB 渲染打开。
        settings.no_rendering_mode = False

        world.apply_settings(settings)

        spawn_transform = find_spawn_transform(
            world,
            args.spawn_index,
        )

        spectator = world.get_spectator()

        spectator.set_transform(
            carla.Transform(
                carla.Location(
                    x=spawn_transform.location.x,
                    y=spawn_transform.location.y,
                    z=spawn_transform.location.z + 25.0,
                ),
                carla.Rotation(
                    pitch=-45.0,
                    yaw=spawn_transform.rotation.yaw,
                    roll=0.0,
                ),
            )
        )

        print(
            f"[4/8] 地图预热："
            f"{args.map_warmup_frames} 帧"
        )

        for _ in range(args.map_warmup_frames):
            world.tick()

        ego = spawn_ego(
            world,
            spawn_transform,
        )
        actors.append(ego)

        # 不调用 set_autopilot：避免 Traffic Manager 绑 8000 失败。
        ego.apply_control(
            carla.VehicleControl(
                throttle=0.0,
                brake=1.0,
                hand_brake=True,
            )
        )

        ego_transform = ego.get_transform()

        print(
            "[5/8] 已生成自车："
            f"id={ego.id}, "
            f"x={ego_transform.location.x:.2f}, "
            f"y={ego_transform.location.y:.2f}"
        )

        lead = spawn_static_lead_vehicle(
            world,
            ego,
            args.lead_distance_m,
        )

        if lead is not None:
            actors.append(lead)
            lead_transform = lead.get_transform()
            print(
                "[6/8] 已生成前车："
                f"id={lead.id}, "
                f"x={lead_transform.location.x:.2f}, "
                f"y={lead_transform.location.y:.2f}"
            )
        else:
            print("[6/8] 未生成前车")

        camera = create_front_camera(
            world,
            ego,
            width=args.width,
            height=args.height,
            fov=args.fov,
        )
        actors.append(camera)

        image_queue: queue.Queue = queue.Queue()

        camera.listen(
            lambda image: image_queue.put(image)
        )

        print(
            f"[7/8] 相机预热："
            f"{args.sensor_warmup_frames} 帧"
        )

        latest_image: Optional[carla.Image] = None

        for _ in range(args.sensor_warmup_frames):
            world.tick()

            try:
                image = image_queue.get(timeout=2.0)
                latest_image = image
            except queue.Empty:
                pass

            latest_image = drain_latest_image(
                image_queue,
                latest_image,
            )

        if latest_image is None:
            # 再给 GPU 相机几帧机会。
            for _ in range(10):
                world.tick()

                try:
                    latest_image = image_queue.get(
                        timeout=2.0
                    )
                    break
                except queue.Empty:
                    continue

        if latest_image is None:
            raise RuntimeError(
                "RGB 相机没有返回图像。"
                "请检查 CARLA 是否使用 -nullrhi "
                "或 no_rendering_mode。"
            )

        save_carla_image_as_jpeg(
            latest_image,
            output_path,
        )

        print("[8/8] 采集成功")
        print(f"输出路径：{output_path}")
        print(
            f"CARLA frame："
            f"{latest_image.frame}"
        )
        print(
            f"图像尺寸："
            f"{latest_image.width}x"
            f"{latest_image.height}"
        )

    finally:
        if camera is not None:
            try:
                camera.stop()
            except Exception:
                pass

        for actor in reversed(actors):
            try:
                if actor.is_alive:
                    actor.destroy()
            except Exception:
                pass

        try:
            world.set_weather(original_weather)
        except Exception:
            pass

        try:
            world.apply_settings(original_settings)
        except Exception:
            pass

        print("已清理本脚本生成的车辆和相机")


if __name__ == "__main__":
    main()
