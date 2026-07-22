"""Dependency-light ONNX object detection for frame-aligned CARLA RGB images.

The runtime dependency is imported lazily so controller-only tests do not need
ONNX Runtime.  The decoder accepts raw Ultralytics YOLO detection exports with
the common ``[1, 84, N]``/``[1, N, 84]`` output and end-to-end ``[N, 6]``
outputs.  Only road-user classes required by C/D are retained.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from .contracts import DetectedObject


COCO_ROAD_USERS = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class OnnxDetectionError(RuntimeError):
    """Model, preprocessing or inference failure that must fail closed."""


@dataclass(frozen=True, slots=True)
class _Letterbox:
    scale: float
    pad_x: float
    pad_y: float
    original_width: int
    original_height: int


def carla_rgb_array(measurement: Any) -> np.ndarray:
    """Convert a CARLA BGRA payload (or a test RGB array) to uint8 RGB."""
    if hasattr(measurement, "rgb_array"):
        image = np.asarray(measurement.rgb_array)
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("rgb_array must have shape (H, W, 3)")
        return image.astype(np.uint8, copy=False)
    raw = getattr(measurement, "raw_data", None)
    width = getattr(measurement, "width", None)
    height = getattr(measurement, "height", None)
    if raw is None or type(width) is not int or type(height) is not int or width < 1 or height < 1:
        raise ValueError("CARLA RGB payload requires raw_data, width and height")
    bgra = np.frombuffer(raw, dtype=np.uint8)
    if bgra.size != width * height * 4:
        raise ValueError("CARLA RGB raw_data size does not match width/height BGRA layout")
    return bgra.reshape((height, width, 4))[:, :, [2, 1, 0]]


def _resize_rgb(image: np.ndarray, width: int, height: int) -> np.ndarray:
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - exercised in deployment packaging
        raise OnnxDetectionError("Pillow is required for ONNX detector preprocessing") from error
    return np.asarray(Image.fromarray(image, mode="RGB").resize((width, height), Image.Resampling.BILINEAR))


def _letterbox(image: np.ndarray, input_width: int, input_height: int) -> tuple[np.ndarray, _Letterbox]:
    height, width = image.shape[:2]
    scale = min(input_width / width, input_height / height)
    resized_width = max(1, int(round(width * scale)))
    resized_height = max(1, int(round(height * scale)))
    resized = _resize_rgb(image, resized_width, resized_height)
    pad_x = (input_width - resized_width) // 2
    pad_y = (input_height - resized_height) // 2
    canvas = np.full((input_height, input_width, 3), 114, dtype=np.uint8)
    canvas[pad_y:pad_y + resized_height, pad_x:pad_x + resized_width] = resized
    tensor = np.transpose(canvas.astype(np.float32) / 255.0, (2, 0, 1))[None, ...]
    return np.ascontiguousarray(tensor), _Letterbox(
        scale, float(pad_x), float(pad_y), width, height,
    )


def _box_iou(box: Sequence[float], boxes: np.ndarray) -> np.ndarray:
    left = np.maximum(float(box[0]), boxes[:, 0])
    top = np.maximum(float(box[1]), boxes[:, 1])
    right = np.minimum(float(box[2]), boxes[:, 2])
    bottom = np.minimum(float(box[3]), boxes[:, 3])
    intersection = np.maximum(0.0, right - left) * np.maximum(0.0, bottom - top)
    area = max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))
    other_area = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0.0, boxes[:, 3] - boxes[:, 1])
    return intersection / np.maximum(area + other_area - intersection, 1e-9)


def _class_aware_nms(
    boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray, iou_threshold: float,
) -> list[int]:
    keep: list[int] = []
    for class_id in np.unique(class_ids):
        indices = np.flatnonzero(class_ids == class_id)
        indices = indices[np.argsort(scores[indices])[::-1]]
        while indices.size:
            current = int(indices[0])
            keep.append(current)
            if indices.size == 1:
                break
            remaining = indices[1:]
            indices = remaining[_box_iou(boxes[current], boxes[remaining]) <= iou_threshold]
    return sorted(keep, key=lambda index: float(scores[index]), reverse=True)


class OnnxYoloDetector:
    """Ultralytics-style ONNX road-user detector with auditable postprocessing."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: int = 640,
        providers: Sequence[str] = ("CPUExecutionProvider",),
        session: Any | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        if session is None and not self.model_path.is_file():
            raise FileNotFoundError(f"ONNX detector model not found: {self.model_path}")
        if not 0.0 < confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in (0, 1]")
        if not 0.0 < iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be in (0, 1]")
        if type(input_size) is not int or input_size < 32:
            raise ValueError("input_size must be an integer >= 32")
        if session is None:
            try:
                import onnxruntime as ort
            except ImportError as error:
                raise OnnxDetectionError(
                    "onnxruntime is required when --rgb-detector-model is configured"
                ) from error
            try:
                session = ort.InferenceSession(str(self.model_path), providers=list(providers))
            except Exception as error:
                raise OnnxDetectionError(f"failed to load ONNX model: {error}") from error
        self._session = session
        inputs = tuple(session.get_inputs())
        if len(inputs) != 1:
            raise OnnxDetectionError("detector ONNX model must expose exactly one image input")
        self._input_name = str(inputs[0].name)
        shape = tuple(inputs[0].shape)
        self._input_height = int(shape[2]) if len(shape) == 4 and type(shape[2]) is int else input_size
        self._input_width = int(shape[3]) if len(shape) == 4 and type(shape[3]) is int else input_size
        self.confidence_threshold = float(confidence_threshold)
        self.iou_threshold = float(iou_threshold)

    def detect_measurement(self, measurement: Any) -> tuple[DetectedObject, ...]:
        return self.detect_rgb(carla_rgb_array(measurement))

    def detect_rgb(self, image_rgb: np.ndarray) -> tuple[DetectedObject, ...]:
        image = np.asarray(image_rgb)
        if image.ndim != 3 or image.shape[2] != 3 or image.shape[0] < 1 or image.shape[1] < 1:
            raise ValueError("image_rgb must have shape (H, W, 3)")
        tensor, transform = _letterbox(image.astype(np.uint8, copy=False), self._input_width, self._input_height)
        try:
            outputs = self._session.run(None, {self._input_name: tensor})
        except Exception as error:
            raise OnnxDetectionError(f"ONNX inference failed: {error}") from error
        if not outputs:
            raise OnnxDetectionError("ONNX detector returned no outputs")
        return self._decode(np.asarray(outputs[0]), transform)

    def _decode(self, output: np.ndarray, transform: _Letterbox) -> tuple[DetectedObject, ...]:
        rows = np.squeeze(output)
        if rows.ndim != 2:
            raise OnnxDetectionError(f"unsupported detector output shape: {output.shape}")
        if rows.shape[0] in {84, 85} and rows.shape[1] not in {84, 85}:
            rows = rows.T

        if rows.shape[1] == 6:
            boxes = rows[:, :4].astype(np.float32)
            scores = rows[:, 4].astype(np.float32)
            class_ids = rows[:, 5].astype(np.int64)
        elif rows.shape[1] in {84, 85}:
            xywh = rows[:, :4].astype(np.float32)
            class_scores = rows[:, -80:].astype(np.float32)
            class_ids = np.argmax(class_scores, axis=1).astype(np.int64)
            scores = class_scores[np.arange(len(rows)), class_ids]
            if rows.shape[1] == 85:
                scores = scores * rows[:, 4].astype(np.float32)
            boxes = np.empty_like(xywh)
            boxes[:, 0] = xywh[:, 0] - xywh[:, 2] / 2.0
            boxes[:, 1] = xywh[:, 1] - xywh[:, 3] / 2.0
            boxes[:, 2] = xywh[:, 0] + xywh[:, 2] / 2.0
            boxes[:, 3] = xywh[:, 1] + xywh[:, 3] / 2.0
        else:
            raise OnnxDetectionError(f"unsupported detector output columns: {rows.shape[1]}")

        allowed = np.array([class_id in COCO_ROAD_USERS for class_id in class_ids], dtype=bool)
        selected = allowed & np.isfinite(scores) & (scores >= self.confidence_threshold)
        boxes, scores, class_ids = boxes[selected], scores[selected], class_ids[selected]
        if not len(boxes):
            return ()

        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - transform.pad_x) / transform.scale
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - transform.pad_y) / transform.scale
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0.0, float(transform.original_width))
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0.0, float(transform.original_height))
        valid = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
        boxes, scores, class_ids = boxes[valid], scores[valid], class_ids[valid]
        keep = _class_aware_nms(boxes, scores, class_ids, self.iou_threshold)
        detections: list[DetectedObject] = []
        for index in keep:
            x1, y1, x2, y2 = boxes[index]
            detections.append(DetectedObject(
                class_id=int(class_ids[index]),
                class_name=COCO_ROAD_USERS[int(class_ids[index])],
                confidence=float(scores[index]),
                bbox_xyxy_norm=(
                    float(x1 / transform.original_width),
                    float(y1 / transform.original_height),
                    float(x2 / transform.original_width),
                    float(y2 / transform.original_height),
                ),
            ))
        return tuple(detections)


def driving_corridor_detections(
    detections: Iterable[DetectedObject],
    *,
    center_min: float = 0.20,
    center_max: float = 0.80,
    minimum_bottom: float = 0.30,
) -> tuple[DetectedObject, ...]:
    """Select plausible ego-lane road users without pretending to segment lanes."""
    selected: list[DetectedObject] = []
    for detection in detections:
        x1, _y1, x2, y2 = detection.bbox_xyxy_norm
        center = (x1 + x2) / 2.0
        if center_min <= center <= center_max and y2 >= minimum_bottom:
            selected.append(detection)
    return tuple(selected)


__all__ = [
    "COCO_ROAD_USERS",
    "OnnxDetectionError",
    "OnnxYoloDetector",
    "carla_rgb_array",
    "driving_corridor_detections",
]
