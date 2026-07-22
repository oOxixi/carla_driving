from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


REQUIRED_RESULTS = {
    "empty": "outputs/day19_gt_projection_fix/vision_observations.jsonl",
    "front_vehicle": "outputs/day19_front_vehicle/vision_observations.jsonl",
    "pedestrian": "outputs/day19_pedestrian_fixed/vision_observations.jsonl",
    "unavailable": "outputs/day19_sensor_unavailable_fixed/vision_observations.jsonl",
}


def read_first_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                return json.loads(line)
    raise RuntimeError(f"No JSON record in {path}")


def validate_cases(repo: Path) -> dict:
    rows = {
        name: read_first_json(repo / relative)
        for name, relative in REQUIRED_RESULTS.items()
    }

    assert rows["empty"]["perception_status"] == "OK"
    assert rows["front_vehicle"]["scene_summary"]["front_vehicle"] is True
    assert rows["front_vehicle"]["scene_summary"]["front_obstacle"] is True
    assert rows["pedestrian"]["scene_summary"]["front_pedestrian"] is True
    assert rows["pedestrian"]["scene_summary"]["front_obstacle"] is True
    assert rows["unavailable"]["perception_status"] == "UNAVAILABLE"

    red_candidates = [
        rows["front_vehicle"],
        rows["pedestrian"],
    ]
    red = next(
        (
            row
            for row in red_candidates
            if row["traffic_light"]["state"] == "RED"
        ),
        None,
    )
    if red is None:
        raise RuntimeError("No valid RED traffic-light sample found")

    rows["red_light"] = red
    return rows


def write_readme(delivery: Path) -> None:
    readme = """# RGB视觉感知模块：7月19日基线交付

## 用途

本包向第一组Qwen/联调成员和第二组雷达/控制成员提供统一的
`VisionObservation` 接口、可调用代码、受控场景脚本和五类样例。

当前 `CARLA_GT` 后端用于仿真接口验证，不代表真实RGB模型准确率。

## 已验证场景

- 空道路：`perception_status=OK` 且无可见目标
- 前车：`front_vehicle=true`
- 行人：`front_pedestrian=true`
- 红灯：`traffic_light.state=RED`
- 传感器不可用：`perception_status=UNAVAILABLE`

## 最小调用

```python
from rgb_group.camera_sensor import FrontRGBCamera
from rgb_group.carla_gt_backend import CarlaGroundTruthBackend
from rgb_group.service import RGBPerceptionService

camera = FrontRGBCamera(
    world=world,
    vehicle=ego_vehicle,
    width=640,
    height=360,
    fov_deg=90.0,
)

backend = CarlaGroundTruthBackend(
    world=world,
    ego_vehicle=ego_vehicle,
    width=640,
    height=360,
    fov_deg=90.0,
)

service = RGBPerceptionService(backend)

expected_frame = world.tick()
rgb_frame = camera.get_for_frame(
    expected_frame=expected_frame,
    timeout_s=10.0,
)
vision = service.process(rgb_frame).to_dict()
```

## 主要输出字段

- `frame`: CARLA世界帧号
- `sim_time_s`: CARLA仿真时间
- `objects`: 目标列表
- `traffic_light`: 交通灯状态
- `perception_status`: `OK/UNAVAILABLE/...`
- `scene_summary`: 给Qwen和控制组使用的简化摘要
- `latency_ms`: 感知结构化耗时，不含`world.tick()`

## 给Qwen组

优先读取：

- `scene_summary.front_vehicle`
- `scene_summary.front_pedestrian`
- `scene_summary.front_obstacle`
- `scene_summary.red_light`
- `perception_status`
- `objects[].category`
- `objects[].image_region`
- `objects[].in_danger_zone`

## 给第二组

RGB负责类别、图像位置、可见性和视觉语义。

RGB不提供精确距离、相对速度、TTC、停止线距离、油门、刹车和方向盘。
这些由LiDAR、车辆状态、控制和D安全仲裁提供。

## 关键语义

- `objects=[]` + `perception_status=OK`：成功观察，当前没有可见目标。
- `objects=[]` + `perception_status=UNAVAILABLE`：传感器不可用，不能认为道路安全。

## 测试

```bash
python -m compileall -q rgb_group
python -m pytest -q rgb_group/tests
```

## 当前边界

1. `CARLA_GT`仅用于仿真联调。
2. ONNX真实目标检测属于7月20日后续任务。
3. 交通灯视觉颜色分类仍需继续实现。
4. 当前服务器CARLA渲染较慢；这不是`latency_ms`。
"""
    (delivery / "README.md").write_text(readme, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--name", default="rgb_day19_delivery_v1")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    delivery = repo / args.name

    rows = validate_cases(repo)

    if delivery.exists():
        shutil.rmtree(delivery)

    (delivery / "rgb_group" / "tests").mkdir(parents=True)
    (delivery / "examples").mkdir()
    (delivery / "docs").mkdir()

    module_files = [
        "__init__.py",
        "camera_sensor.py",
        "carla_gt_backend.py",
        "geometry.py",
        "onnx_backend.py",
        "schemas.py",
        "service.py",
        "visualize.py",
    ]
    for name in module_files:
        shutil.copy2(repo / "rgb_group" / name, delivery / "rgb_group" / name)

    for test_path in (repo / "rgb_group" / "tests").glob("*.py"):
        shutil.copy2(test_path, delivery / "rgb_group" / "tests" / test_path.name)

    helper_files = [
        "demo_rgb_carla.py",
        "demo_rgb_controlled.py",
        "analyze_rgb_results.py",
        "check_rgb_environment.py",
        "requirements_rgb.txt",
    ]
    for name in helper_files:
        path = repo / name
        if path.exists():
            shutil.copy2(path, delivery / name)

    sample_names = {
        "empty": "vision_empty_road.json",
        "front_vehicle": "vision_front_vehicle.json",
        "pedestrian": "vision_pedestrian.json",
        "red_light": "vision_red_light.json",
        "unavailable": "vision_unavailable.json",
    }
    for key, filename in sample_names.items():
        (delivery / "examples" / filename).write_text(
            json.dumps(rows[key], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    for relative in REQUIRED_RESULTS.values():
        src = repo / relative
        analysis = src.parent / "analysis.txt"
        if analysis.exists():
            shutil.copy2(
                analysis,
                delivery / "docs" / f"{src.parent.name}_analysis.txt",
            )

    write_readme(delivery)

    handoff = """# HANDOFF：RGB视觉感知 7月19日

## 对外接口
输出`VisionObservation dict`，Schema版本`1.0`。

## 已完成
- CARLA RGB同步取帧
- 目标类别、二维框、区域、危险区
- 交通灯状态
- 空道路、前车、行人、红灯、传感器不可用样例
- 安全销毁传感器Actor
- 单元测试

## 给第一组
Qwen与联调模块直接消费`examples/*.json`或调用`RGBPerceptionService`。

## 给第二组
使用视觉类别与摘要；距离、TTC和最终动作仍由第二组提供。

## 安全边界
`UNAVAILABLE`绝不能等同于无障碍。
`CARLA_GT`不能作为真实视觉模型准确率。
"""
    (delivery / "HANDOFF_RGB_DAY19.md").write_text(handoff, encoding="utf-8")

    subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(delivery / "rgb_group")],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(delivery / "rgb_group" / "tests")],
        check=True,
    )

    zip_path = repo / f"{args.name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in delivery.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, path.relative_to(repo))

    tar_path = shutil.make_archive(
        str(repo / args.name),
        "gztar",
        root_dir=repo,
        base_dir=args.name,
    )

    print("Delivery directory:", delivery)
    print("ZIP:", zip_path)
    print("TAR.GZ:", tar_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
