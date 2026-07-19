from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple
import numpy as np
import onnxruntime as ort

from .geometry import image_region, is_in_danger_zone
from .schemas import Detection, TrafficLightObservation

COCO_TO_CATEGORY: Dict[int, str] = {
    0: "PEDESTRIAN",
    1: "BICYCLE",
    2: "VEHICLE",
    3: "MOTORCYCLE",
    5: "VEHICLE",
    7: "VEHICLE",
    9: "TRAFFIC_LIGHT",
}


def _letterbox(image: np.ndarray, size: int) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    import cv2

    h, w = image.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    left = (size - nw) // 2
    top = (size - nh) // 2
    canvas[top:top + nh, left:left + nw] = resized
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    tensor = rgb.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    return tensor, scale, (left, top)


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> List[int]:
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes.T
    areas = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        union = areas[i] + areas[order[1:]] - inter + 1e-9
        iou = inter / union
        order = order[1:][iou <= iou_threshold]
    return keep


class YoloV8OnnxBackend:
    """Generic YOLOv8/YOLO11 detection ONNX backend for COCO-style models."""

    name = "ONNX_YOLO"

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.50,
        input_size: int = 640,
        providers: Sequence[str] | None = None,
    ) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {path}")
        available = ort.get_available_providers()
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if "CUDAExecutionProvider" in available else ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(path), providers=list(providers))
        self.input_name = self.session.get_inputs()[0].name
        self.confidence_threshold = float(confidence_threshold)
        self.iou_threshold = float(iou_threshold)
        self.input_size = int(input_size)

    def infer(self, image_bgr, sensor_transform=None):
        h, w = image_bgr.shape[:2]
        tensor, scale, (pad_x, pad_y) = _letterbox(image_bgr, self.input_size)
        output = self.session.run(None, {self.input_name: tensor})[0]
        pred = np.squeeze(output)
        if pred.ndim != 2:
            raise RuntimeError(f"Unexpected ONNX output shape: {output.shape}")
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T
        if pred.shape[1] < 6:
            raise RuntimeError(f"Unexpected YOLO output shape: {pred.shape}")

        boxes_xywh = pred[:, :4]
        class_scores = pred[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(len(class_scores)), class_ids]
        mask = scores >= self.confidence_threshold
        boxes_xywh, class_ids, scores = boxes_xywh[mask], class_ids[mask], scores[mask]

        boxes = np.empty_like(boxes_xywh)
        boxes[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2
        boxes[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2
        boxes[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2
        boxes[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2
        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad_x) / scale
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad_y) / scale
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, w - 1)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, h - 1)

        keep_all: List[int] = []
        for class_id in np.unique(class_ids):
            idx = np.where(class_ids == class_id)[0]
            keep_local = _nms(boxes[idx], scores[idx], self.iou_threshold)
            keep_all.extend(idx[k] for k in keep_local)

        detections: List[Detection] = []
        light_candidates = []
        for sequence_id, idx in enumerate(sorted(keep_all, key=lambda i: -scores[i])):
            category = COCO_TO_CATEGORY.get(int(class_ids[idx]), "UNKNOWN")
            if category == "UNKNOWN":
                continue
            x1, y1, x2, y2 = [int(round(v)) for v in boxes[idx]]
            if x2 <= x1 or y2 <= y1:
                continue
            bbox = (x1, y1, x2, y2)

            if category == "PEDESTRIAN":
                center_x = (x1 + x2) / 2.0
                bottom_y = y2
                box_height = y2 - y1

                danger = (
                    w * 0.30
                    <= center_x
                    <= w * 0.70
                    and bottom_y >= h * 0.58
                    and box_height >= h * 0.08
                )

            elif category in {
                "VEHICLE",
                "BICYCLE",
                "MOTORCYCLE",
                "TRAFFIC_CONE",
                "ROADBLOCK",
            }:
                danger = is_in_danger_zone(
                    bbox,
                    w,
                    h,
                )

            else:
                danger = False

            det = Detection(
                track_id=f"onnx_{sequence_id}",
                category=category,
                confidence=float(scores[idx]),
                bbox_xyxy=bbox,
                image_region=image_region(bbox, w),
                in_danger_zone=danger,
                source=self.name,
                metadata={"coco_class_id": int(class_ids[idx])},
            )
            detections.append(det)
            if category == "TRAFFIC_LIGHT":
                light_candidates.append(det)

        # COCO detector finds the traffic-light object but not its color.
        # The state stays UNKNOWN until a dedicated color classifier is integrated.
        if light_candidates:
            det = max(light_candidates, key=lambda d: d.confidence)
            light = TrafficLightObservation(
                state="UNKNOWN",
                confidence=det.confidence,
                visible=True,
                bbox_xyxy=det.bbox_xyxy,
                source=self.name,
            )
            warnings = ["TRAFFIC_LIGHT_COLOR_CLASSIFIER_NOT_CONFIGURED"]
        else:
            light = TrafficLightObservation()
            warnings = []
        return detections, light, warnings
