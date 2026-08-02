"""C-role sensor timestamp and extrinsics audit helpers.

This module is a thin deliverable layer for the team handoff.  The live CARLA
sensor acquisition remains in ``integration.carla_perception``; these helpers
turn frame stamps, timing, and extrinsics into a small record that can be logged
or checked without importing CARLA.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SensorFrameStamp:
    frame_id: int
    timestamp_s: float
    source: str = "CARLA_SENSOR"

    def __post_init__(self) -> None:
        if type(self.frame_id) is not int or self.frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        if type(self.timestamp_s) not in (int, float):
            raise TypeError("timestamp_s must be numeric")
        if not str(self.source).strip():
            raise ValueError("source must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "timestamp_s": float(self.timestamp_s),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class SensorAudit:
    frame_id: int
    sim_time_s: float
    stamps: Mapping[str, SensorFrameStamp]
    extrinsics: Mapping[str, Mapping[str, float]]
    max_frame_delta: int
    max_time_delta_s: float
    alignment_ok: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "frame_id": self.frame_id,
            "sim_time_s": float(self.sim_time_s),
            "stamps": {name: stamp.to_dict() for name, stamp in self.stamps.items()},
            "extrinsics": {
                name: {key: float(value) for key, value in values.items()}
                for name, values in self.extrinsics.items()
            },
            "max_frame_delta": self.max_frame_delta,
            "max_time_delta_s": round(self.max_time_delta_s, 6),
            "alignment_ok": self.alignment_ok,
        }


def build_sensor_audit(
    *,
    frame_id: int,
    sim_time_s: float,
    stamps: Mapping[str, SensorFrameStamp],
    extrinsics: Mapping[str, Mapping[str, float]] | None = None,
    max_allowed_frame_delta: int = 0,
    max_allowed_time_delta_s: float = 0.05,
) -> SensorAudit:
    if type(frame_id) is not int or frame_id < 0:
        raise ValueError("frame_id must be a non-negative integer")
    if not stamps:
        raise ValueError("at least one sensor stamp is required")
    frame_deltas = [abs(stamp.frame_id - frame_id) for stamp in stamps.values()]
    time_deltas = [abs(float(stamp.timestamp_s) - float(sim_time_s)) for stamp in stamps.values()]
    max_frame_delta = max(frame_deltas)
    max_time_delta_s = max(time_deltas)
    alignment_ok = (
        max_frame_delta <= max_allowed_frame_delta
        and max_time_delta_s <= max_allowed_time_delta_s
    )
    return SensorAudit(
        frame_id=frame_id,
        sim_time_s=float(sim_time_s),
        stamps=dict(stamps),
        extrinsics=dict(extrinsics or {}),
        max_frame_delta=max_frame_delta,
        max_time_delta_s=max_time_delta_s,
        alignment_ok=alignment_ok,
    )
