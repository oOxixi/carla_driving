"""Path utilities for member B lateral control."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

Point2D = Tuple[float, float]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def wrap_angle_rad(angle: float) -> float:
    """Wrap angle to [-pi, pi]."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def distance(p1: Point2D, p2: Point2D) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def cumulative_lengths(points: Sequence[Point2D]) -> List[float]:
    if len(points) < 2:
        raise ValueError("path must contain at least two points")
    out = [0.0]
    for i in range(1, len(points)):
        out.append(out[-1] + distance(points[i - 1], points[i]))
    return out


def resample_path(points: Sequence[Point2D], spacing_m: float = 0.5) -> List[Point2D]:
    """Resample a polyline by approximate arc length.

    This prevents waypoint spacing jumps at intersections from destabilizing the
    controller. The first and last points are always preserved.
    """
    if len(points) < 2:
        raise ValueError("path must contain at least two points")
    if spacing_m <= 0 or not math.isfinite(spacing_m):
        raise ValueError("spacing_m must be positive and finite")

    lengths = cumulative_lengths(points)
    total = lengths[-1]
    if total == 0:
        raise ValueError("path length is zero")

    samples: List[Point2D] = []
    s = 0.0
    seg = 0
    while s < total:
        while seg < len(lengths) - 2 and lengths[seg + 1] < s:
            seg += 1
        seg_s0 = lengths[seg]
        seg_s1 = lengths[seg + 1]
        ratio = 0.0 if seg_s1 == seg_s0 else (s - seg_s0) / (seg_s1 - seg_s0)
        x0, y0 = points[seg]
        x1, y1 = points[seg + 1]
        samples.append((x0 + ratio * (x1 - x0), y0 + ratio * (y1 - y0)))
        s += spacing_m
    if distance(samples[-1], points[-1]) > 1e-6:
        samples.append(points[-1])
    return samples


def find_nearest_index(points: Sequence[Point2D], x: float, y: float, start_index: int = 0, search_window: int | None = None) -> int:
    """Return index of nearest path point.

    search_window limits computation around the previous nearest index when A
    provides one; the default searches the whole path.
    """
    if not points:
        raise ValueError("points is empty")
    n = len(points)
    if search_window is None:
        lo, hi = 0, n
    else:
        lo = max(0, start_index - search_window)
        hi = min(n, start_index + search_window + 1)
    best_i = lo
    best_d = float("inf")
    for i in range(lo, hi):
        d = math.hypot(points[i][0] - x, points[i][1] - y)
        if d < best_d:
            best_i = i
            best_d = d
    return best_i


def find_lookahead_index(points: Sequence[Point2D], start_index: int, current_xy: Point2D, lookahead_distance_m: float) -> int:
    if lookahead_distance_m <= 0:
        raise ValueError("lookahead_distance_m must be positive")
    for i in range(max(0, start_index), len(points)):
        if distance(current_xy, points[i]) >= lookahead_distance_m:
            return i
    return len(points) - 1


def compute_path_heading(points: Sequence[Point2D], index: int) -> float:
    if len(points) < 2:
        raise ValueError("path must contain at least two points")
    index = max(0, min(index, len(points) - 1))
    if index == len(points) - 1:
        p0, p1 = points[index - 1], points[index]
    else:
        p0, p1 = points[index], points[index + 1]
    return math.atan2(p1[1] - p0[1], p1[0] - p0[0])


def signed_cross_track_error(points: Sequence[Point2D], nearest_index: int, x: float, y: float) -> float:
    """Signed lateral error; in CARLA coordinates positive is path-right."""
    heading = compute_path_heading(points, nearest_index)
    px, py = points[nearest_index]
    dx = x - px
    dy = y - py
    return -math.sin(heading) * dx + math.cos(heading) * dy


def estimate_curvature(points: Sequence[Point2D], index: int, stride: int = 3) -> float:
    """Estimate signed curvature from three path points."""
    if len(points) < 3:
        return 0.0
    i0 = max(0, index - stride)
    i1 = max(0, min(index, len(points) - 1))
    i2 = min(len(points) - 1, index + stride)
    if i0 == i1 or i1 == i2:
        return 0.0
    x1, y1 = points[i0]
    x2, y2 = points[i1]
    x3, y3 = points[i2]
    a = distance((x1, y1), (x2, y2))
    b = distance((x2, y2), (x3, y3))
    c = distance((x3, y3), (x1, y1))
    if a * b * c == 0:
        return 0.0
    signed_area2 = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
    curvature = 2.0 * signed_area2 / (a * b * c)
    return curvature
