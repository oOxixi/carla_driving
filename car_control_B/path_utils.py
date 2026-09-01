"""Path utilities for member B lateral control."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

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
    """Signed distance to the nearest adjacent path segment.

    Using the tangent of a single nearest waypoint makes the reported error
    jump at a polyline corner: the waypoint may be nearest while the vehicle
    is still closest to the segment entering that waypoint. Projecting onto
    both adjacent segments keeps the metric geometrically meaningful and
    gives Stanley-style feedback the correct sign through intersections.
    Positive remains path-right in CARLA coordinates.
    """
    if len(points) < 2:
        raise ValueError("path must contain at least two points")
    index = max(0, min(nearest_index, len(points) - 1))
    segment_starts = range(max(0, index - 1), min(index + 1, len(points) - 1))
    best_distance_sq = math.inf
    best_error = 0.0
    for start in segment_starts:
        x0, y0 = points[start]
        x1, y1 = points[start + 1]
        sx, sy = x1 - x0, y1 - y0
        length_sq = sx * sx + sy * sy
        if length_sq <= 1e-12:
            continue
        projection = clamp(((x - x0) * sx + (y - y0) * sy) / length_sq, 0.0, 1.0)
        px, py = x0 + projection * sx, y0 + projection * sy
        dx, dy = x - px, y - py
        distance_sq = dx * dx + dy * dy
        if distance_sq < best_distance_sq:
            length = math.sqrt(length_sq)
            best_distance_sq = distance_sq
            best_error = -(sy / length) * dx + (sx / length) * dy
    if not math.isfinite(best_distance_sq):
        raise ValueError("path contains no non-zero segment adjacent to nearest_index")
    return best_error


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


def max_abs_curvature_ahead(
    points: Sequence[Point2D],
    start_index: int,
    *,
    horizon_m: float = 30.0,
    stride: int = 3,
) -> float:
    """Return smoothed peak curvature only over the upcoming local path.

    A route-wide maximum makes one distant junction limit every straight in a
    long mission.  The local horizon preserves advance slowing for a nearby
    curve without carrying that constraint across kilometres of road.
    """
    if len(points) < 3:
        return 0.0
    if not math.isfinite(horizon_m) or horizon_m <= 0.0:
        raise ValueError("horizon_m must be positive and finite")
    if type(stride) is not int or stride <= 0:
        raise ValueError("stride must be a positive integer")
    start = max(0, min(int(start_index), len(points) - 1))
    end = start
    travelled = 0.0
    while end < len(points) - 1 and travelled < horizon_m:
        travelled += distance(points[end], points[end + 1])
        end += 1
    return max(
        (
            abs(estimate_curvature(points, index, stride=stride))
            for index in range(start, end + 1)
        ),
        default=0.0,
    )
