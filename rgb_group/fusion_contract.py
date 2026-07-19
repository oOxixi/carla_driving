from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LidarRiskView:
    schema_version: str
    frame: int
    sim_time_s: float
    status: str

    front_distance_m: Optional[float] = None
    relative_speed_mps: Optional[float] = None
    ttc_s: Optional[float] = None

    left_lane_clear: Optional[bool] = None
    right_lane_clear: Optional[bool] = None

    obstacle_direction: str = "UNKNOWN"
    risk_level: str = "UNKNOWN"


def validate_frame_alignment(
    vision_frame: int,
    lidar_frame: int,
    max_frame_gap: int = 1,
) -> bool:
    return (
        abs(int(vision_frame) - int(lidar_frame))
        <= int(max_frame_gap)
    )
