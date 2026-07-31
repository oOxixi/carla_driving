"""Road ROI, low-rate detection, high-rate stable tracking and Top-K output."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
import math
import time
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class RGBPipelineConfig:
    roi_top_ratio: float = 0.20
    roi_bottom_ratio: float = 1.0
    input_width: int = 640
    input_height: int = 384
    detection_interval_frames: int = 3
    top_k: int = 12
    iou_match_threshold: float = 0.25
    max_track_age_frames: int = 6

    def __post_init__(self) -> None:
        if not 0.0 <= self.roi_top_ratio < self.roi_bottom_ratio <= 1.0:
            raise ValueError("ROI ratios must satisfy 0 <= top < bottom <= 1")
        for name in ("input_width", "input_height", "detection_interval_frames", "top_k", "max_track_age_frames"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not 0.0 <= self.iou_match_threshold <= 1.0:
            raise ValueError("iou_match_threshold must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class RGBDetection:
    class_name: str
    confidence: float
    bbox_xyxy_norm: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if type(self.class_name) is not str or not self.class_name:
            raise ValueError("class_name must be non-empty")
        if type(self.confidence) not in (int, float) or isinstance(self.confidence, bool) or not math.isfinite(float(self.confidence)) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and in [0, 1]")
        if type(self.bbox_xyxy_norm) is not tuple or len(self.bbox_xyxy_norm) != 4:
            raise TypeError("bbox_xyxy_norm must be a tuple of four values")
        box = tuple(float(value) for value in self.bbox_xyxy_norm)
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in box):
            raise ValueError("bbox coordinates must be finite and in [0, 1]")
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("bbox must have positive area")
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "bbox_xyxy_norm", box)


@dataclass(frozen=True, slots=True)
class RGBTrack:
    track_id: str
    class_name: str
    confidence: float
    bbox_xyxy_norm: tuple[float, float, float, float]
    first_frame_id: int
    last_frame_id: int
    age_frames: int
    detected_this_frame: bool


def _iou(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    left, top = max(first[0], second[0]), max(first[1], second[1])
    right, bottom = min(first[2], second[2]), min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    area_first = (first[2] - first[0]) * (first[3] - first[1])
    area_second = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / max(area_first + area_second - intersection, 1e-12)


class RGBPipeline:
    """Detector callback receives the resized ROI and returns normalized ROI boxes."""

    def __init__(
        self,
        detector: Callable[[np.ndarray], Iterable[RGBDetection | Mapping[str, Any]]],
        *,
        config: RGBPipelineConfig | None = None,
        gpu_preprocess: Callable[[np.ndarray, int, int], np.ndarray] | None = None,
    ) -> None:
        if not callable(detector):
            raise TypeError("detector must be callable")
        self.detector = detector
        self.config = config or RGBPipelineConfig()
        self.gpu_preprocess = gpu_preprocess
        self._tracks: dict[str, RGBTrack] = {}
        self._next_track = 1
        self._last_detection_frame: int | None = None
        self._latencies_ms: list[float] = []

    def process(self, image_rgb: np.ndarray, *, frame_id: int) -> tuple[RGBTrack, ...]:
        started = time.perf_counter_ns()
        image = np.asarray(image_rgb)
        if image.ndim != 3 or image.shape[2] != 3 or image.shape[0] < 2 or image.shape[1] < 2:
            raise ValueError("image_rgb must have shape (H, W, 3)")
        if type(frame_id) is not int or frame_id < 0:
            raise ValueError("frame_id must be non-negative")
        detect = self._last_detection_frame is None or frame_id - self._last_detection_frame >= self.config.detection_interval_frames
        if detect:
            roi, top_ratio, height_ratio = self._preprocess(image)
            raw = tuple(self.detector(roi))
            detections = tuple(self._normalize(item, top_ratio, height_ratio) for item in raw)
            self._associate(detections, frame_id)
            self._last_detection_frame = frame_id
        else:
            self._propagate(frame_id)
        active = [track for track in self._tracks.values() if frame_id - track.last_frame_id <= self.config.max_track_age_frames]
        # Near/large/lower boxes are safety-relevant; confidence is the stable tie-break.
        active.sort(key=lambda item: (
            -item.bbox_xyxy_norm[3],
            -(item.bbox_xyxy_norm[2] - item.bbox_xyxy_norm[0]) * (item.bbox_xyxy_norm[3] - item.bbox_xyxy_norm[1]),
            -item.confidence,
            item.track_id,
        ))
        self._latencies_ms.append((time.perf_counter_ns() - started) / 1e6)
        return tuple(active[: self.config.top_k])

    def metrics(self) -> dict[str, Any]:
        values = sorted(self._latencies_ms)
        return {
            "frames": len(values),
            "mean_ms": sum(values) / len(values) if values else None,
            "p95_ms": values[min(len(values) - 1, math.ceil(0.95 * len(values)) - 1)] if values else None,
            "max_ms": max(values) if values else None,
            "active_tracks": len(self._tracks),
            "detection_interval_frames": self.config.detection_interval_frames,
        }

    def _preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float, float]:
        height = image.shape[0]
        top = int(round(height * self.config.roi_top_ratio))
        bottom = max(top + 1, int(round(height * self.config.roi_bottom_ratio)))
        roi = image[top:bottom]
        if self.gpu_preprocess is not None:
            resized = self.gpu_preprocess(roi, self.config.input_width, self.config.input_height)
        else:
            try:
                from PIL import Image
            except ImportError as error:  # pragma: no cover
                raise RuntimeError("Pillow is required for RGB preprocessing") from error
            resized = np.asarray(Image.fromarray(roi.astype(np.uint8)).resize(
                (self.config.input_width, self.config.input_height), Image.Resampling.BILINEAR,
            ))
        return resized, top / height, (bottom - top) / height

    @staticmethod
    def _normalize(item: RGBDetection | Mapping[str, Any], top_ratio: float, height_ratio: float) -> RGBDetection:
        if not isinstance(item, RGBDetection):
            item = RGBDetection(
                str(item["class_name"]),
                float(item["confidence"]),
                tuple(item["bbox_xyxy_norm"]),
            )
        x1, y1, x2, y2 = item.bbox_xyxy_norm
        return RGBDetection(
            item.class_name,
            item.confidence,
            (x1, top_ratio + y1 * height_ratio, x2, top_ratio + y2 * height_ratio),
        )

    def _associate(self, detections: tuple[RGBDetection, ...], frame_id: int) -> None:
        unmatched = set(self._tracks)
        updated: dict[str, RGBTrack] = {}
        for detection in sorted(detections, key=lambda item: (-item.confidence, item.class_name, item.bbox_xyxy_norm)):
            candidates = [
                (track_id, _iou(self._tracks[track_id].bbox_xyxy_norm, detection.bbox_xyxy_norm))
                for track_id in unmatched
                if self._tracks[track_id].class_name == detection.class_name
            ]
            track_id: str | None = None
            if candidates:
                candidate_id, score = max(candidates, key=lambda item: (item[1], item[0]))
                if score >= self.config.iou_match_threshold:
                    track_id = candidate_id
                    unmatched.remove(candidate_id)
            if track_id is None:
                track_id = f"rgb-{self._next_track:06d}"
                self._next_track += 1
                first = frame_id
                age = 1
            else:
                previous = self._tracks[track_id]
                first = previous.first_frame_id
                age = previous.age_frames + max(1, frame_id - previous.last_frame_id)
            updated[track_id] = RGBTrack(
                track_id, detection.class_name, detection.confidence, detection.bbox_xyxy_norm,
                first, frame_id, age, True,
            )
        for track_id in unmatched:
            previous = self._tracks[track_id]
            if frame_id - previous.last_frame_id <= self.config.max_track_age_frames:
                updated[track_id] = replace(previous, age_frames=previous.age_frames + 1, detected_this_frame=False)
        self._tracks = updated

    def _propagate(self, frame_id: int) -> None:
        self._tracks = {
            track_id: replace(track, age_frames=track.age_frames + 1, detected_this_frame=False)
            for track_id, track in self._tracks.items()
            if frame_id - track.last_frame_id <= self.config.max_track_age_frames
        }


__all__ = ["RGBDetection", "RGBPipeline", "RGBPipelineConfig", "RGBTrack"]
