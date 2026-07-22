from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
import time

import cv2

from rgb_group.onnx_backend import YoloV8OnnxBackend


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--expected-category")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    image_paths = sorted(
        Path(args.input_dir).glob("frame_*.jpg")
    )

    if not image_paths:
        raise RuntimeError(
            f"No images found in {args.input_dir}"
        )

    backend = YoloV8OnnxBackend(
        model_path=args.model,
        confidence_threshold=args.confidence,
        iou_threshold=0.50,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    category_frame_counts = Counter()
    latencies = []
    records = []

    for image_path in image_paths:
        image = cv2.imread(str(image_path))

        if image is None:
            print("skip unreadable:", image_path)
            continue

        start = time.perf_counter()

        detections, traffic_light, warnings = backend.infer(
            image_bgr=image,
            sensor_transform=None,
        )

        latency_ms = (
            time.perf_counter() - start
        ) * 1000.0

        latencies.append(latency_ms)

        categories = sorted({
            detection.category
            for detection in detections
        })

        for category in categories:
            category_frame_counts[category] += 1

        record = {
            "image": str(image_path),
            "latency_ms": round(latency_ms, 3),
            "categories": categories,
            "traffic_light_visible": traffic_light.visible,
            "traffic_light_state": traffic_light.state,
            "detections": [
                detection.to_dict()
                for detection in detections
            ],
            "warnings": warnings,
        }

        records.append(record)

        print(
            image_path.name,
            "categories=",
            categories,
            "latency_ms=",
            round(latency_ms, 2),
        )

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(record, ensure_ascii=False)
                + "\n"
            )

    print("\n=== Sequence summary ===")
    print("frames:", len(records))
    print("category frame counts:", dict(category_frame_counts))

    if latencies:
        print("mean latency_ms:", round(mean(latencies), 2))
        print("median latency_ms:", round(median(latencies), 2))
        print("max latency_ms:", round(max(latencies), 2))

    if args.expected_category:
        detected_frames = category_frame_counts[
            args.expected_category
        ]
        total_frames = len(records)

        print(
            f"{args.expected_category}: "
            f"{detected_frames}/{total_frames}"
        )

        if detected_frames == 0:
            raise AssertionError(
                f"{args.expected_category} was never detected"
            )


if __name__ == "__main__":
    main()
