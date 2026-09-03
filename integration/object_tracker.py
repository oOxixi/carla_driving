"""Sensor-only temporal IDs for detected road users."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from .contracts import DetectedObject


def _center(detection: DetectedObject) -> tuple[float, float]:
    x1, y1, x2, y2 = detection.bbox_xyxy_norm
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


@dataclass(slots=True)
class _Track:
    detection: DetectedObject
    last_frame: int


class SensorObjectTracker:
    """Greedy class/range/image association with opaque stable IDs."""

    def __init__(
        self,
        *,
        maximum_frame_gap: int = 5,
        maximum_center_shift: float = 0.25,
        minimum_range_gate_m: float = 3.0,
    ) -> None:
        if maximum_frame_gap < 1:
            raise ValueError("maximum_frame_gap must be positive")
        self.maximum_frame_gap = int(maximum_frame_gap)
        self.maximum_center_shift = float(maximum_center_shift)
        self.minimum_range_gate_m = float(minimum_range_gate_m)
        self._tracks: dict[str, _Track] = {}
        self._next_id = 1

    def update(
        self, frame: int, detections: Sequence[DetectedObject],
    ) -> tuple[DetectedObject, ...]:
        self._tracks = {
            track_id: track
            for track_id, track in self._tracks.items()
            if frame - track.last_frame <= self.maximum_frame_gap
        }
        available = set(self._tracks)
        output: list[DetectedObject] = []
        for detection in detections:
            track_id = detection.track_id or self._best_match(detection, available)
            if track_id is None:
                track_id = f"C-{self._next_id:04d}"
                self._next_id += 1
            available.discard(track_id)
            tracked = replace(detection, track_id=track_id)
            self._tracks[track_id] = _Track(tracked, int(frame))
            output.append(tracked)
        return tuple(output)

    def _best_match(
        self, detection: DetectedObject, available: set[str],
    ) -> str | None:
        center_x, center_y = _center(detection)
        candidates: list[tuple[float, str]] = []
        for track_id in available:
            previous = self._tracks[track_id].detection
            if previous.class_name.lower() != detection.class_name.lower():
                continue
            previous_x, previous_y = _center(previous)
            center_shift = abs(center_x - previous_x) + abs(center_y - previous_y)
            if center_shift > self.maximum_center_shift:
                continue
            range_cost = 0.0
            if previous.distance_m is not None and detection.distance_m is not None:
                range_delta = abs(previous.distance_m - detection.distance_m)
                range_gate = max(self.minimum_range_gate_m, previous.distance_m * 0.25)
                if range_delta > range_gate:
                    continue
                range_cost = range_delta / range_gate
            candidates.append((center_shift + range_cost, track_id))
        return min(candidates, default=(0.0, None), key=lambda item: item[0])[1]


__all__ = ["SensorObjectTracker"]
