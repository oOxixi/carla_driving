"""CARLA waypoint route generation shared by the acceptance runner.

The planner is intentionally local: it follows CARLA topology for a bounded
distance and can select the first junction branch requested by a voice/decision
command.  It does not pretend to be a global navigation service.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from car_control_A.routing import RouteReference
from car_control_B.path_utils import estimate_curvature


_DIRECTIONS = {"LEFT", "RIGHT", "STRAIGHT"}


def _wrap_degrees(angle: float) -> float:
    return (float(angle) + 180.0) % 360.0 - 180.0


def _yaw(waypoint: Any) -> float:
    return float(waypoint.transform.rotation.yaw)


def _branch_delta(current: Any, candidate: Any) -> float:
    """CARLA uses a left-handed frame: positive yaw turns to the right."""
    return _wrap_degrees(_yaw(candidate) - _yaw(current))


def _choose_branch(current: Any, candidates: Iterable[Any], direction: str) -> Any | None:
    options = tuple(candidates)
    if not options:
        return None
    if len(options) == 1:
        return options[0]
    deltas = tuple((candidate, _branch_delta(current, candidate)) for candidate in options)
    if direction == "LEFT":
        matching = tuple(item for item in deltas if item[1] < -5.0)
        if matching:
            return min(matching, key=lambda item: abs(item[1] + 90.0))[0]
    elif direction == "RIGHT":
        matching = tuple(item for item in deltas if item[1] > 5.0)
        if matching:
            return min(matching, key=lambda item: abs(item[1] - 90.0))[0]
    return min(deltas, key=lambda item: abs(item[1]))[0]


def _route_curvature(points: tuple[tuple[float, float], ...]) -> float:
    if len(points) < 3:
        return 0.0
    values = (abs(estimate_curvature(points, index, stride=1)) for index in range(1, len(points) - 1))
    return max(values, default=0.0)


def build_route_reference(
    world_map: Any,
    ego_or_location: Any,
    target_speed_mps: float,
    *,
    turn_direction: str = "STRAIGHT",
    distance_m: float = 500.0,
    step_m: float = 2.0,
) -> RouteReference:
    """Build a bounded forward route and a conservative curvature estimate."""
    direction = str(turn_direction).strip().upper()
    if direction not in _DIRECTIONS:
        raise ValueError(f"turn_direction must be one of {sorted(_DIRECTIONS)}")
    if not math.isfinite(float(target_speed_mps)) or target_speed_mps < 0.0:
        raise ValueError("target_speed_mps must be finite and non-negative")
    if not math.isfinite(float(distance_m)) or distance_m <= 0.0:
        raise ValueError("distance_m must be finite and positive")
    if not math.isfinite(float(step_m)) or step_m <= 0.0:
        raise ValueError("step_m must be finite and positive")

    location = ego_or_location.get_location() if hasattr(ego_or_location, "get_location") else ego_or_location
    waypoint = world_map.get_waypoint(location, project_to_road=True)
    points: list[tuple[float, float]] = []
    branch_consumed = False
    max_steps = max(2, int(math.ceil(distance_m / step_m)) + 1)
    for _ in range(max_steps):
        if waypoint is None:
            break
        loc = waypoint.transform.location
        point = (float(loc.x), float(loc.y))
        if not points or math.hypot(point[0] - points[-1][0], point[1] - points[-1][1]) > 1e-6:
            points.append(point)
        candidates = tuple(waypoint.next(step_m))
        requested = direction if not branch_consumed else "STRAIGHT"
        if len(candidates) > 1:
            branch_consumed = True
        waypoint = _choose_branch(waypoint, candidates, requested)

    if len(points) < 2:
        x, y = float(location.x), float(location.y)
        points = [(x, y), (x + step_m, y)]
    route_points = tuple(points)
    return RouteReference(route_points, _route_curvature(route_points), float(target_speed_mps))


def command_turn_direction(command: dict[str, object] | None) -> str:
    """Extract only an explicit route direction; all other commands go straight."""
    if not command:
        return "STRAIGHT"
    intent = str(command.get("intent", "")).upper()
    if intent not in {"TURN", "CHANGE_LANE"}:
        return "STRAIGHT"
    parameters = command.get("parameters", {})
    if not isinstance(parameters, dict):
        return "STRAIGHT"
    value = str(parameters.get("direction", "STRAIGHT")).upper()
    return value if value in _DIRECTIONS else "STRAIGHT"


__all__ = ["build_route_reference", "command_turn_direction"]
