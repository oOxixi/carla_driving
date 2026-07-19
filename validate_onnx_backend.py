from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import cv2

from rgb_group.onnx_backend import YoloV8OnnxBackend


def first_image(directory: str) -> Path:
    images = sorted(Path(directory).glob("frame_*.jpg"))

    if not images:
        raise RuntimeError(
            f"No frame images found in {directory}"
        )

    return images[0]


def validate_detection_bounds(
    detections,
    width: int,
    height: int,
) -> None:
    for detection in detections:
        x1, y1, x2, y2 = detection.bbox_xyxy

        if not (0 <= x1 < x2 < width):
            raise AssertionError(
                f"Invalid x coordinates: "
                f"{detection.bbox_xyxy}"
            )

        if not (0 <= y1 < y2 < height):
            raise AssertionError(
                f"Invalid y coordinates: "
                f"{detection.bbox_xyxy}"
            )

        if not (
            0.0
            <= float(detection.confidence)
            <= 1.0
        ):
            raise AssertionError(
                f"Invalid confidence: "
                f"{detection.confidence}"
            )


def run_case(
    backend: YoloV8OnnxBackend,
    image_path: Path,
    expected_categories: Iterable[str],
) -> None:
    image = cv2.imread(str(image_path))

    if image is None:
        raise RuntimeError(
            f"Cannot read image: {image_path}"
        )

    height, width = image.shape[:2]

    detections, traffic_light, warnings = backend.infer(
        image_bgr=image,
        sensor_transform=None,
    )

    categories = [
        detection.category
        for detection in detections
    ]

    print(f"\nImage: {image_path}")
    print("Categories:", categories)
    print("Warnings:", warnings)

    for detection in detections:
        print(
            " ",
            detection.category,
            round(detection.confidence, 4),
            detection.bbox_xyxy,
            detection.image_region,
            detection.in_danger_zone,
        )

    validate_detection_bounds(
        detections=detections,
        width=width,
        height=height,
    )

    for expected in expected_categories:
        if expected not in categories:
            raise AssertionError(
                f"{expected} not detected in "
                f"{image_path}; got {categories}"
            )

    if traffic_light.visible:
        if traffic_light.state != "UNKNOWN":
            raise AssertionError(
                "ONNX traffic-light detector must not "
                "invent a color state"
            )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        default="models/yolov8n.onnx",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.25,
    )
    parser.add_argument(
        "--vehicle-dir",
        default="outputs/day19_front_vehicle",
    )
    parser.add_argument(
        "--pedestrian-dir",
        default="outputs/day20_pedestrian_7m",
    )

    args = parser.parse_args()

    backend = YoloV8OnnxBackend(
        model_path=args.model,
        confidence_threshold=args.confidence,
        iou_threshold=0.50,
    )

    run_case(
        backend=backend,
        image_path=first_image(args.vehicle_dir),
        expected_categories=["VEHICLE"],
    )

    run_case(
        backend=backend,
        image_path=first_image(args.pedestrian_dir),
        expected_categories=["PEDESTRIAN"],
    )

    print("\nONNX backend validation passed")


if __name__ == "__main__":
    main()
