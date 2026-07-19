from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    weight = index - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "jsonl",
        nargs="?",
        default="outputs/rgb_gt_smoke_v2/vision_observations.jsonl",
    )
    args = parser.parse_args()

    path = Path(args.jsonl)
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSON at line {line_no}: {exc}"
                ) from exc

    if not rows:
        raise RuntimeError("No observations found")

    statuses = Counter()
    traffic_lights = Counter()
    categories = Counter()
    sources = Counter()
    regions = Counter()
    danger_categories = Counter()
    object_frames = defaultdict(set)
    latencies = []
    frames = []

    front_vehicle_frames = 0
    front_pedestrian_frames = 0
    front_obstacle_frames = 0
    red_light_frames = 0

    for row in rows:
        statuses[row.get("perception_status", "MISSING")] += 1

        frame = int(row.get("frame", -1))
        frames.append(frame)

        latency = row.get("latency_ms")
        if isinstance(latency, (int, float)):
            latencies.append(float(latency))

        light = row.get("traffic_light") or {}
        traffic_lights[light.get("state", "MISSING")] += 1

        summary = row.get("scene_summary") or {}
        front_vehicle_frames += bool(summary.get("front_vehicle"))
        front_pedestrian_frames += bool(summary.get("front_pedestrian"))
        front_obstacle_frames += bool(summary.get("front_obstacle"))
        red_light_frames += bool(summary.get("red_light"))

        for obj in row.get("objects", []):
            category = obj.get("category", "UNKNOWN")
            source = obj.get("source", "UNKNOWN")
            region = obj.get("image_region", "UNKNOWN")

            categories[category] += 1
            sources[source] += 1
            regions[region] += 1
            object_frames[category].add(frame)

            if obj.get("in_danger_zone"):
                danger_categories[category] += 1

    consecutive = all(
        frames[i] == frames[i - 1] + 1
        for i in range(1, len(frames))
    )

    print("=== RGB感知结果汇总 ===")
    print(f"文件: {path}")
    print(f"总帧数: {len(rows)}")
    print(f"帧范围: {min(frames)} ~ {max(frames)}")
    print(f"帧号连续: {consecutive}")
    print(f"状态: {dict(statuses)}")
    print(f"交通灯: {dict(traffic_lights)}")
    print(f"目标类别累计: {dict(categories)}")
    print(f"目标来源: {dict(sources)}")
    print(f"图像区域累计: {dict(regions)}")
    print(f"危险区目标累计: {dict(danger_categories)}")

    print("\n=== 按类别出现帧数 ===")
    for category, category_frames in sorted(object_frames.items()):
        print(
            f"{category:16s}: "
            f"{len(category_frames)}/{len(rows)} 帧"
        )

    print("\n=== 场景摘要 ===")
    print(f"front_vehicle:    {front_vehicle_frames}/{len(rows)}")
    print(f"front_pedestrian: {front_pedestrian_frames}/{len(rows)}")
    print(f"front_obstacle:   {front_obstacle_frames}/{len(rows)}")
    print(f"red_light:        {red_light_frames}/{len(rows)}")

    if latencies:
        print("\n=== 感知处理延时，不含CARLA world.tick等待 ===")
        print(f"平均: {mean(latencies):.2f} ms")
        print(f"中位数: {median(latencies):.2f} ms")
        print(f"P95: {percentile(latencies, 0.95):.2f} ms")
        print(f"最大: {max(latencies):.2f} ms")

    print("\n=== 每帧目标详情 ===")
    for row in rows:
        print(
            f"\nframe={row['frame']} "
            f"light={row['traffic_light']['state']} "
            f"objects={len(row.get('objects', []))}"
        )
        for obj in row.get("objects", []):
            print(
                "  "
                f"{obj.get('category'):16s} "
                f"confidence={obj.get('confidence')} "
                f"region={obj.get('image_region')} "
                f"danger={obj.get('in_danger_zone')} "
                f"bbox={obj.get('bbox_xyxy')}"
            )


if __name__ == "__main__":
    main()
