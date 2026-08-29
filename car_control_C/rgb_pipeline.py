"""C-role RGB pipeline summary helpers.

The runtime detector lives in ``integration.rgb_detector``.  This module keeps
the C deliverable name from the handoff and provides JSON-ready summaries for
ROI, Top-K, and latency evidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class RgbDetection:
    class_name: str
    confidence: float
    bbox_xyxy_norm: tuple[float, float, float, float]
    source: str
    track_id: str | None = None

    def __post_init__(self) -> None:
        if not self.class_name.strip():
            raise ValueError("class_name must be non-empty")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if len(self.bbox_xyxy_norm) != 4:
            raise ValueError("bbox_xyxy_norm must contain four values")
        for value in self.bbox_xyxy_norm:
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("bbox coordinates must be normalized to [0, 1]")
        if not self.source.strip():
            raise ValueError("source must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "class_name": self.class_name,
            "confidence": float(self.confidence),
            "bbox_xyxy_norm": [float(value) for value in self.bbox_xyxy_norm],
            "source": self.source,
            "track_id": self.track_id,
        }


@dataclass(frozen=True, slots=True)
class RgbPipelineSummary:
    frame_id: int
    top_k: tuple[RgbDetection, ...]
    p95_latency_ms: float | None
    p95_within_30ms: bool | None
    roi_policy: str
    jump_guard: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "frame_id": self.frame_id,
            "top_k": [item.to_dict() for item in self.top_k],
            "p95_latency_ms": self.p95_latency_ms,
            "p95_within_30ms": self.p95_within_30ms,
            "roi_policy": self.roi_policy,
            "jump_guard": self.jump_guard,
        }


def _nearest_rank_p95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def summarize_rgb_pipeline(
    *,
    frame_id: int,
    detections: Iterable[RgbDetection],
    top_k: int = 5,
    latency_ms_samples: Sequence[float] = (),
) -> RgbPipelineSummary:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    ranked = tuple(
        sorted(detections, key=lambda item: item.confidence, reverse=True)[:top_k]
    )
    p95 = _nearest_rank_p95(latency_ms_samples)
    return RgbPipelineSummary(
        frame_id=frame_id,
        top_k=ranked,
        p95_latency_ms=p95,
        p95_within_30ms=None if p95 is None else p95 <= 30.0,
        roi_policy="front_driving_corridor",
        jump_guard="low_frequency_detection_high_frequency_tracking",
    )
