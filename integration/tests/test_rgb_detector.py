from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from integration.contracts import DetectedObject
from integration.rgb_detector import (
    OnnxDetectionError,
    OnnxYoloDetector,
    carla_rgb_array,
    driving_corridor_detections,
)


@dataclass
class Input:
    name: str = "images"
    shape: tuple[int, int, int, int] = (1, 3, 640, 640)


class Session:
    def __init__(self, output: np.ndarray, *, fail: bool = False):
        self.output = output
        self.fail = fail
        self.feed = None

    def get_inputs(self):
        return [Input()]

    def run(self, _output_names, feed):
        self.feed = feed
        if self.fail:
            raise RuntimeError("backend failed")
        return [self.output]


def _raw_yolo_output(*rows: tuple[float, float, float, float, int, float]) -> np.ndarray:
    output = np.zeros((1, 84, len(rows)), dtype=np.float32)
    for index, (cx, cy, width, height, class_id, score) in enumerate(rows):
        output[0, :4, index] = (cx, cy, width, height)
        output[0, 4 + class_id, index] = score
    return output


def test_carla_bgra_is_converted_to_rgb() -> None:
    measurement = type("Image", (), {
        "width": 2,
        "height": 1,
        "raw_data": bytes([10, 20, 30, 255, 40, 50, 60, 255]),
    })()
    assert carla_rgb_array(measurement).tolist() == [[[30, 20, 10], [60, 50, 40]]]


def test_yolo_decoder_keeps_only_person_and_vehicle_classes() -> None:
    output = _raw_yolo_output(
        (320.0, 320.0, 160.0, 160.0, 2, 0.90),
        (120.0, 300.0, 60.0, 180.0, 0, 0.80),
        (500.0, 300.0, 80.0, 80.0, 9, 0.99),
    )
    session = Session(output)
    detector = OnnxYoloDetector("unused.onnx", session=session)
    detections = detector.detect_rgb(np.zeros((450, 800, 3), dtype=np.uint8))

    assert [item.class_name for item in detections] == ["car", "person"]
    assert detections[0].confidence == pytest.approx(0.9)
    assert detections[0].bbox_xyxy_norm == pytest.approx((0.375, 0.2777778, 0.625, 0.7222222))
    assert session.feed["images"].shape == (1, 3, 640, 640)
    assert session.feed["images"].dtype == np.float32


def test_class_aware_nms_removes_overlapping_duplicate() -> None:
    output = _raw_yolo_output(
        (320.0, 320.0, 160.0, 160.0, 2, 0.90),
        (324.0, 324.0, 160.0, 160.0, 2, 0.70),
    )
    detections = OnnxYoloDetector("unused.onnx", session=Session(output)).detect_rgb(
        np.zeros((640, 640, 3), dtype=np.uint8)
    )
    assert len(detections) == 1
    assert detections[0].confidence == pytest.approx(0.9)


def test_corridor_filter_uses_normalized_box_location() -> None:
    center = DetectedObject(2, "car", 0.9, (0.4, 0.3, 0.6, 0.8))
    side = DetectedObject(0, "person", 0.8, (0.0, 0.3, 0.1, 0.8))
    assert driving_corridor_detections((side, center)) == (center,)


def test_backend_failure_is_explicit() -> None:
    detector = OnnxYoloDetector(
        "unused.onnx", session=Session(_raw_yolo_output(), fail=True),
    )
    with pytest.raises(OnnxDetectionError, match="backend failed"):
        detector.detect_rgb(np.zeros((64, 64, 3), dtype=np.uint8))
