"""Simple lane-change/local-offset path helpers for B.

High-level decisions such as when to change lane still belong to A/model layer.
This module only provides a smooth path generator when A provides start/end
centerlines or an offset instruction.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .path_utils import compute_path_heading, resample_path

Point2D = Tuple[float, float]


def smoothstep5(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 10 * t**3 - 15 * t**4 + 6 * t**5


def offset_path(points: Sequence[Point2D], lateral_offset_m: float) -> List[Point2D]:
    """Offset path to its left by positive lateral_offset_m."""
    if len(points) < 2:
        raise ValueError("path must contain at least two points")
    out: List[Point2D] = []
    for i, p in enumerate(points):
        heading = compute_path_heading(points, i)
        nx = -math.sin(heading)
        ny = math.cos(heading)
        out.append((p[0] + lateral_offset_m * nx, p[1] + lateral_offset_m * ny))
    return out


def generate_lane_change_path(base_points: Sequence[Point2D], lateral_offset_m: float, start_s_ratio: float = 0.15, end_s_ratio: float = 0.85, spacing_m: float = 0.5) -> List[Point2D]:
    """Generate a smooth lateral offset transition along a base path.

    start_s_ratio/end_s_ratio define where the lateral transition begins/ends
    over the path index progression. Positive offset means target path is left of
    the base path. For CARLA right lane change, use negative offset depending on
    map coordinate convention.
    """
    points = resample_path(base_points, spacing_m=spacing_m)
    n = len(points)
    if n < 2:
        raise ValueError("path must contain at least two points")
    start_i = int(max(0, min(n - 1, start_s_ratio * (n - 1))))
    end_i = int(max(start_i + 1, min(n - 1, end_s_ratio * (n - 1))))
    out: List[Point2D] = []
    for i, p in enumerate(points):
        if i <= start_i:
            ratio = 0.0
        elif i >= end_i:
            ratio = 1.0
        else:
            ratio = smoothstep5((i - start_i) / max(1, end_i - start_i))
        heading = compute_path_heading(points, i)
        nx = -math.sin(heading)
        ny = math.cos(heading)
        off = lateral_offset_m * ratio
        out.append((p[0] + off * nx, p[1] + off * ny))
    return out
