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
    parser.add_argument(
        "--output",
        default="outputs/onnx_image_test.jpg",
    )
    args = parser.parse_args()

    image_path = Path(args.image)

    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(
            f"Failed to read image: {image_path}"
        )

    backend = YoloV8OnnxBackend(args.model)

    start = time.perf_counter()

    detections, traffic_light, warnings = backend.infer(
        image_bgr=image,
        sensor_transform=None,
    )

    latency_ms = (
        time.perf_counter() - start
    ) * 1000.0

    print(
        json.dumps(
            {
                "image": str(image_path),
                "latency_ms": round(latency_ms, 2),
                "traffic_light": (
                    traffic_light.to_dict()
                    if hasattr(traffic_light, "to_dict")
                    else str(traffic_light)
                ),
                "warnings": warnings,
                "detections": [
                    (
                        item.to_dict()
                        if hasattr(item, "to_dict")
                        else vars(item)
                    )
                    for item in detections
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    annotated = image.copy()

    for item in detections:
        x1, y1, x2, y2 = item.bbox_xyxy

        cv2.rectangle(
            annotated,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            (0, 255, 0),
            2,
        )

        label = (
            f"{item.category} "
            f"{item.confidence:.2f}"
        )

        cv2.putText(
            annotated,
            label,
            (int(x1), max(20, int(y1) - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not cv2.imwrite(
        str(output_path),
        annotated,
    ):
        raise RuntimeError(
            f"Failed to write {output_path}"
        )

    print("saved:", output_path)


if __name__ == "__main__":
    main()
