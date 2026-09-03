"""Map-independent route geometry and route-relative scenario placement.

Scenario actors and event progress must share the same arc-length reference as
the lateral controller.  Keeping these helpers free of CARLA types makes the
geometry deterministic, replayable, and suitable for property-based tests.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


Point2D = tuple[float, float]


def _finite(value: object, name: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def polyline_length_m(points: Sequence[Point2D]) -> float:
    if len(points) < 2:
        raise ValueError("route needs at least two points")
    return sum(math.dist(first, second) for first, second in zip(points, points[1:]))


def cumulative_distances_m(points: Sequence[Point2D]) -> tuple[float, ...]:
    if len(points) < 2:
        raise ValueError("route needs at least two points")
    values = [0.0]
    for first, second in zip(points, points[1:]):
        values.append(values[-1] + math.dist(first, second))
    if values[-1] <= 1e-9:
        raise ValueError("route length must be positive")
    return tuple(values)


@dataclass(frozen=True, slots=True)
class RoutePose:
    x_m: float
    y_m: float
    yaw_deg: float
    s_m: float


@dataclass(frozen=True, slots=True)
class RouteQuality:
    requested_distance_m: float
    actual_distance_m: float
    point_count: int
    maximum_step_m: float
    unique_cell_ratio: float
    reached_contract: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_distance_m": self.requested_distance_m,
            "actual_distance_m": self.actual_distance_m,
            "point_count": self.point_count,
            "maximum_step_m": self.maximum_step_m,
            "unique_cell_ratio": self.unique_cell_ratio,
            "reached_contract": self.reached_contract,
        }


def route_pose_at_s(points: Sequence[Point2D], s_m: float) -> RoutePose:
    """Interpolate a pose at route arc length ``s_m``.

    Values beyond the route are clamped to its endpoints.  Zero-length
    duplicate segments are ignored, which is important around CARLA junctions.
    """
    distances = cumulative_distances_m(points)
    target = min(max(0.0, _finite(s_m, "s_m")), distances[-1])
    for index, (start_s, end_s) in enumerate(zip(distances, distances[1:])):
        if end_s <= start_s + 1e-9:
            continue
        if target <= end_s + 1e-9:
            first, second = points[index], points[index + 1]
            ratio = min(1.0, max(0.0, (target - start_s) / (end_s - start_s)))
            dx, dy = second[0] - first[0], second[1] - first[1]
            return RoutePose(
                float(first[0] + dx * ratio),
                float(first[1] + dy * ratio),
                math.degrees(math.atan2(dy, dx)),
                target,
            )
    first, second = points[-2], points[-1]
    return RoutePose(
        float(second[0]),
        float(second[1]),
        math.degrees(math.atan2(second[1] - first[1], second[0] - first[0])),
        distances[-1],
    )


def offset_route_pose(pose: RoutePose, lateral_m: float, yaw_offset_deg: float = 0.0) -> RoutePose:
    """Offset a route pose toward CARLA's local positive-Y/right direction."""
    lateral = _finite(lateral_m, "lateral_m")
    yaw = math.radians(pose.yaw_deg)
    return RoutePose(
        pose.x_m - math.sin(yaw) * lateral,
        pose.y_m + math.cos(yaw) * lateral,
        pose.yaw_deg + _finite(yaw_offset_deg, "yaw_offset_deg"),
        pose.s_m,
    )


def actor_route_coordinates(actor_spec: Mapping[str, object]) -> tuple[float, float, float, float]:
    """Return ``(s, lateral, z, yaw_offset)`` for new and legacy actors.

    New scenarios may declare ``route_position``.  Existing scenarios remain
    compatible: their local ``spawn.x/y`` values are interpreted as route arc
    length and lateral offset instead of a tangent at only the initial ego pose.
    """
    spawn = actor_spec.get("spawn", {})
    if not isinstance(spawn, Mapping):
        raise TypeError("scenario actor spawn must be an object")
    position = actor_spec.get("route_position")
    if position is not None and not isinstance(position, Mapping):
        raise TypeError("scenario actor route_position must be an object")
    values = position if isinstance(position, Mapping) else spawn
    s_value = values.get("s_m", spawn.get("x", 0.0))
    lateral_value = values.get("lateral_offset_m", spawn.get("y", 0.0))
    return (
        max(0.0, _finite(s_value, "actor route s_m")),
        _finite(lateral_value, "actor route lateral_offset_m"),
        _finite(spawn.get("z", 0.5), "actor spawn z"),
        _finite(values.get("yaw_offset_deg", spawn.get("yaw_deg", 0.0)), "actor yaw offset"),
    )


def project_route_progress_m(
    points: Sequence[Point2D],
    x_m: float,
    y_m: float,
    *,
    previous_s_m: float | None = None,
    backward_tolerance_m: float = 2.0,
    forward_window_m: float = 80.0,
) -> float:
    """Project a position onto a possibly self-overlapping route.

    A prior progress value disambiguates loops and crossing roads.  Candidates
    far behind or implausibly far ahead are excluded before choosing the
    geometrically nearest segment.
    """
    x = _finite(x_m, "x_m")
    y = _finite(y_m, "y_m")
    distances = cumulative_distances_m(points)
    previous = None if previous_s_m is None else max(0.0, _finite(previous_s_m, "previous_s_m"))
    candidates: list[tuple[float, float]] = []
    fallback: list[tuple[float, float]] = []
    for index, (first, second) in enumerate(zip(points, points[1:])):
        dx, dy = second[0] - first[0], second[1] - first[1]
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-12:
            continue
        ratio = min(1.0, max(0.0, ((x - first[0]) * dx + (y - first[1]) * dy) / length_sq))
        projected_x = first[0] + ratio * dx
        projected_y = first[1] + ratio * dy
        error_sq = (x - projected_x) ** 2 + (y - projected_y) ** 2
        s_value = distances[index] + ratio * math.sqrt(length_sq)
        fallback.append((error_sq, s_value))
        if previous is None or (
            s_value >= previous - max(0.0, backward_tolerance_m)
            and s_value <= previous + max(0.0, forward_window_m)
        ):
            candidates.append((error_sq, s_value))
    if not fallback:
        raise ValueError("route has no non-zero segments")
    selected = min(
        candidates or fallback,
        key=lambda item: (
            item[0],
            abs(item[1] - previous) if previous is not None else 0.0,
            -item[1],
        ),
    )[1]
    return selected if previous is None else max(previous, selected)


def evaluate_route_quality(
    points: Sequence[Point2D],
    requested_distance_m: float,
    *,
    contract_tolerance_m: float | None = None,
    uniqueness_cell_m: float = 2.0,
) -> RouteQuality:
    requested = _finite(requested_distance_m, "requested_distance_m")
    if requested <= 0.0:
        raise ValueError("requested_distance_m must be positive")
    actual = polyline_length_m(points)
    steps = tuple(math.dist(first, second) for first, second in zip(points, points[1:]))
    cell = _finite(uniqueness_cell_m, "uniqueness_cell_m")
    if cell <= 0.0:
        raise ValueError("uniqueness_cell_m must be positive")
    occupied = {
        (round(float(x) / cell), round(float(y) / cell))
        for x, y in points
    }
    tolerance = (
        max(2.0, requested * 0.01)
        if contract_tolerance_m is None
        else max(0.0, _finite(contract_tolerance_m, "contract_tolerance_m"))
    )
    return RouteQuality(
        requested_distance_m=requested,
        actual_distance_m=actual,
        point_count=len(points),
        maximum_step_m=max(steps, default=0.0),
        unique_cell_ratio=len(occupied) / max(1, len(points)),
        reached_contract=actual + tolerance >= requested,
    )


__all__ = [
    "RoutePose",
    "RouteQuality",
    "actor_route_coordinates",
    "cumulative_distances_m",
    "evaluate_route_quality",
    "offset_route_pose",
    "polyline_length_m",
    "project_route_progress_m",
    "route_pose_at_s",
]
