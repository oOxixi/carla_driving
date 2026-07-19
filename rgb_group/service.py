from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from .schemas import TrafficLightObservation, VisionObservation


@dataclass(frozen=True)
class RGBPerceptionConfig:
    sensor_id: str = "front_rgb"
    stale_after_frames: int = 2


class RGBPerceptionService:
    def __init__(self, backend: Any, config: RGBPerceptionConfig | None = None) -> None:
        self.backend = backend
        self.config = config or RGBPerceptionConfig()
        self._last_frame = -1

    def process(self, rgb_frame) -> VisionObservation:
        started = time.monotonic_ns()
        warnings = []
        status = "OK"
        try:
            detections, traffic_light, backend_warnings = self.backend.infer(
                rgb_frame.image_bgr,
                rgb_frame.sensor_transform,
            )
            warnings.extend(backend_warnings)
            if rgb_frame.frame <= self._last_frame:
                status = "STALE"
                warnings.append("NON_INCREASING_FRAME")
            self._last_frame = max(self._last_frame, rgb_frame.frame)
        except Exception as exc:
            detections = []
            traffic_light = TrafficLightObservation()
            status = "ERROR"
            warnings.append(f"{type(exc).__name__}: {exc}")
        latency_ms = (time.monotonic_ns() - started) / 1e6
        h, w = rgb_frame.image_bgr.shape[:2]
        return VisionObservation(
            frame=rgb_frame.frame,
            sim_time_s=rgb_frame.sim_time_s,
            sensor_id=self.config.sensor_id,
            image_width=w,
            image_height=h,
            objects=detections,
            traffic_light=traffic_light,
            perception_status=status,
            latency_ms=round(latency_ms, 2),
            warnings=warnings,
        )
