from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2

from rgb_group.onnx_backend import YoloV8OnnxBackend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--frame", type=int, default=0)
    parser.add_argument("--sim-time-s", type=float, default=0.0)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    image = cv2.imread(args.image)

    if image is None:
        raise RuntimeError(
            f"Cannot read image: {args.image}"
        )

    height, width = image.shape[:2]

    backend = YoloV8OnnxBackend(
        model_path=args.model,
        confidence_threshold=args.confidence,
    )

    start = time.perf_counter()

    detections, traffic_light, warnings = backend.infer(
        image_bgr=image,
        sensor_transform=None,
    )

    latency_ms = (
        time.perf_counter() - start
    ) * 1000.0

    front_vehicle = any(
        detection.category == "VEHICLE"
        and detection.in_danger_zone
        for detection in detections
    )

    front_pedestrian = any(
        detection.category == "PEDESTRIAN"
        and detection.in_danger_zone
        for detection in detections
    )

    front_obstacle = any(
        detection.in_danger_zone
        and detection.category
        in {
            "VEHICLE",
            "PEDESTRIAN",
            "BICYCLE",
            "MOTORCYCLE",
            "TRAFFIC_CONE",
            "ROADBLOCK",
        }
        for detection in detections
    )

    row = {
        "schema_version": "1.0",
        "frame": args.frame,
        "sim_time_s": args.sim_time_s,
        "sensor_id": "front_rgb",
        "image_width": width,
        "image_height": height,
        "objects": [
            detection.to_dict()
            for detection in detections
        ],
        "traffic_light": traffic_light.to_dict(),
        "perception_status": "OK",
        "latency_ms": round(latency_ms, 3),
        "warnings": warnings,
        "scene_summary": {
            "front_vehicle": front_vehicle,
            "front_pedestrian": front_pedestrian,
            "front_obstacle": front_obstacle,
            "red_light": (
                traffic_light.state == "RED"
            ),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            row,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(row, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
