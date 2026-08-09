"""CARLA waypoint route generation shared by the acceptance runner.

The planner is intentionally local: it follows CARLA topology for a bounded
distance and can select the first junction branch requested by a voice/decision
command.  It does not pretend to be a global navigation service.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from car_control_A.routing import RouteReference
from car_control_B.path_utils import estimate_curvature


_DIRECTIONS = {"LEFT", "RIGHT", "STRAIGHT"}
_MANEUVERS = {
    "FOLLOW", "FOLLOW_LEFT", "FOLLOW_RIGHT",
    "TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT",
}
_HEADING_GRID_CELL_M = 5.0


@dataclass(frozen=True, slots=True)
class _WaypointSpatialIndex:
    world_map: Any
    step_m: float
    buckets: dict[tuple[int, int], tuple[Any, ...]]


_WAYPOINT_INDEX_BY_MAP_ID: dict[int, _WaypointSpatialIndex] = {}


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


def _route_length(points: Sequence[tuple[float, float]]) -> float:
    return sum(math.dist(first, second) for first, second in zip(points, points[1:]))


def _heading(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.degrees(math.atan2(second[1] - first[1], second[0] - first[0]))


def _route_yaw_change(points: Sequence[tuple[float, float]]) -> float:
    if len(points) < 4:
        return 0.0
    stride = min(3, len(points) // 2)
    return _wrap_degrees(_heading(points[-stride - 1], points[-1]) - _heading(points[0], points[stride]))


def _is_driving_lane(waypoint: Any | None) -> bool:
    if waypoint is None:
        return False
    lane_type = str(getattr(waypoint, "lane_type", "Driving")).split(".")[-1].upper()
    return lane_type == "DRIVING"


def _same_direction(first: Any, second: Any, tolerance_deg: float = 45.0) -> bool:
    return abs(_wrap_degrees(_yaw(second) - _yaw(first))) <= tolerance_deg


def _ego_yaw_deg(ego_or_location: Any) -> float | None:
    """Return actor/transform yaw without guessing it from a bare Location."""
    if callable(getattr(ego_or_location, "get_transform", None)):
        transform = ego_or_location.get_transform()
        return float(transform.rotation.yaw)
    rotation = getattr(ego_or_location, "rotation", None)
    if rotation is not None and hasattr(rotation, "yaw"):
        return float(rotation.yaw)
    return None


def _waypoint_distance_m(waypoint: Any, location: Any) -> float:
    candidate = waypoint.transform.location
    return math.hypot(float(candidate.x) - float(location.x), float(candidate.y) - float(location.y))


def warm_heading_waypoint_cache(world_map: Any, *, search_step_m: float = 1.0) -> int:
    """Build a process-local spatial index outside the active control loop."""
    if not math.isfinite(float(search_step_m)) or search_step_m <= 0.0:
        raise ValueError("search_step_m must be finite and positive")
    key = id(world_map)
    cached = _WAYPOINT_INDEX_BY_MAP_ID.get(key)
    if cached is not None and cached.world_map is world_map and cached.step_m == float(search_step_m):
        return sum(len(values) for values in cached.buckets.values())
    generate = getattr(world_map, "generate_waypoints", None)
    if not callable(generate):
        raise RuntimeError("map cannot enumerate waypoints")
    mutable: dict[tuple[int, int], list[Any]] = {}
    count = 0
    for candidate in generate(float(search_step_m)):
        if not _is_driving_lane(candidate):
            continue
        location = candidate.transform.location
        cell = (
            math.floor(float(location.x) / _HEADING_GRID_CELL_M),
            math.floor(float(location.y) / _HEADING_GRID_CELL_M),
        )
        mutable.setdefault(cell, []).append(candidate)
        count += 1
    buckets = {cell: tuple(values) for cell, values in mutable.items()}
    _WAYPOINT_INDEX_BY_MAP_ID[key] = _WaypointSpatialIndex(
        world_map, float(search_step_m), buckets,
    )
    return count


def _nearby_indexed_waypoints(
    world_map: Any,
    location: Any,
    *,
    search_radius_m: float,
    search_step_m: float,
) -> tuple[Any, ...]:
    warm_heading_waypoint_cache(world_map, search_step_m=search_step_m)
    index = _WAYPOINT_INDEX_BY_MAP_ID[id(world_map)]
    center_x = math.floor(float(location.x) / _HEADING_GRID_CELL_M)
    center_y = math.floor(float(location.y) / _HEADING_GRID_CELL_M)
    extent = int(math.ceil(search_radius_m / _HEADING_GRID_CELL_M))
    return tuple(
        waypoint
        for dx in range(-extent, extent + 1)
        for dy in range(-extent, extent + 1)
        for waypoint in index.buckets.get((center_x + dx, center_y + dy), ())
    )


def select_heading_compatible_waypoint(
    world_map: Any,
    ego_or_location: Any,
    *,
    max_heading_error_deg: float = 45.0,
    search_radius_m: float = 5.0,
    search_step_m: float = 1.0,
) -> Any:
    """Project to a nearby driving lane that agrees with the ego heading.

    CARLA's ``get_waypoint(project_to_road=True)`` minimizes geometric
    distance only. At stacked/crossing road geometry that can select a road
    whose tangent points behind the vehicle. A bare ``Location`` has no
    heading, so scenario builders retain the legacy nearest projection; live
    actor routes always apply this direction gate.
    """
    if max_heading_error_deg <= 0.0 or max_heading_error_deg > 90.0:
        raise ValueError("max_heading_error_deg must be in (0, 90]")
    if search_radius_m <= 0.0 or search_step_m <= 0.0:
        raise ValueError("search radius and step must be positive")
    location = ego_or_location.get_location() if hasattr(ego_or_location, "get_location") else ego_or_location
    nearest = world_map.get_waypoint(location, project_to_road=True)
    if not _is_driving_lane(nearest):
        raise RuntimeError("route anchor is not on a driving lane")
    ego_yaw = _ego_yaw_deg(ego_or_location)
    if ego_yaw is None:
        return nearest
    nearest_error = abs(_wrap_degrees(_yaw(nearest) - ego_yaw))
    if nearest_error <= max_heading_error_deg:
        return nearest

    candidates: list[tuple[float, float, float, Any]] = []
    for candidate in _nearby_indexed_waypoints(
        world_map,
        location,
        search_radius_m=search_radius_m,
        search_step_m=search_step_m,
    ):
        if not _is_driving_lane(candidate):
            continue
        distance = _waypoint_distance_m(candidate, location)
        if distance > search_radius_m:
            continue
        heading_error = abs(_wrap_degrees(_yaw(candidate) - ego_yaw))
        if heading_error > max_heading_error_deg:
            continue
        # Distance remains primary inside the direction gate; the small yaw
        # term provides deterministic preference between overlapping lanes.
        score = distance + heading_error / max_heading_error_deg
        candidates.append((score, heading_error, distance, candidate))
    if not candidates:
        raise RuntimeError(
            "no nearby driving waypoint agrees with ego heading; route refresh rejected"
        )
    candidates.sort(key=lambda item: (item[0], item[1], item[2], _yaw(item[3])))
    return candidates[0][3]


def _next_straight(waypoint: Any, step_m: float) -> Any | None:
    return _choose_branch(waypoint, tuple(waypoint.next(step_m)), "STRAIGHT")


def _advance_waypoint(waypoint: Any, distance_m: float, step_m: float) -> Any | None:
    current = waypoint
    for _ in range(max(1, int(math.ceil(distance_m / step_m)))):
        current = _next_straight(current, step_m)
        if current is None:
            return None
    return current


def _adjacent_driving_lane(waypoint: Any, direction: str) -> Any | None:
    getter_name = "get_left_lane" if direction == "LEFT" else "get_right_lane"
    getter = getattr(waypoint, getter_name, None)
    candidate = getter() if callable(getter) else None
    if not _is_driving_lane(candidate) or not _same_direction(waypoint, candidate):
        return None
    return candidate


def _enum_token(value: Any) -> str:
    """Return a stable token for CARLA enums and lightweight test doubles."""
    return str(value).rsplit(".", 1)[-1].replace("_", "").upper()


def _lane_change_permission_allows(waypoint: Any, direction: str) -> bool:
    permission = getattr(waypoint, "lane_change", None)
    if permission is None:
        # Old map/test doubles do not expose the CARLA 0.9.x field.  Real
        # CARLA waypoints always do, and are checked below.
        return True
    token = _enum_token(permission)
    if token in {"BOTH", direction}:
        return True
    if token in {"NONE", "LEFT", "RIGHT"}:
        return False
    try:
        bits = int(permission)
    except (TypeError, ValueError):
        return False
    required_bit = 2 if direction == "LEFT" else 1
    return bool(bits & required_bit)


def lane_change_rejection_reason(waypoint: Any, direction: str) -> str | None:
    """Explain why crossing the requested boundary is illegal at a waypoint.

    Lane-invasion sensors are necessarily retrospective.  Route generation
    must reject a prohibited boundary before lateral control receives it.
    """
    side = str(direction).strip().upper()
    if side not in {"LEFT", "RIGHT"}:
        raise ValueError("lane-change direction must be LEFT or RIGHT")
    if bool(getattr(waypoint, "is_junction", False)):
        return "JUNCTION_FORBIDS_LANE_CHANGE"
    marking = getattr(
        waypoint,
        "left_lane_marking" if side == "LEFT" else "right_lane_marking",
        None,
    )
    marking_type = getattr(marking, "type", None)
    if marking_type is not None:
        token = _enum_token(marking_type)
        if "SOLID" in token:
            return "SOLID_LANE_MARKING_FORBIDS_CHANGE"
        if token in {"CURB", "GRASS", "NONE", "OTHER"}:
            return "NON_CROSSABLE_LANE_BOUNDARY"
    if not _lane_change_permission_allows(waypoint, side):
        return "LANE_CHANGE_PERMISSION_FORBIDS_CHANGE"
    return None


def _validate_lane_change_corridor(
    start: Any,
    *,
    direction: str,
    distance_m: float,
    step_m: float,
) -> None:
    """Validate the origin-lane boundary for the whole crossover corridor."""
    current = start
    for _ in range(max(1, int(math.ceil(distance_m / step_m))) + 1):
        reason = lane_change_rejection_reason(current, direction)
        if reason is not None:
            raise ValueError(reason)
        next_waypoint = _next_straight(current, step_m)
        if next_waypoint is None:
            raise ValueError("LANE_CHANGE_CORRIDOR_DEAD_END")
        current = next_waypoint


def _hermite_lane_change(
    start: Any,
    end: Any,
    *,
    samples: int,
    tangent_scale_m: float,
) -> tuple[tuple[float, float], ...]:
    """Smoothly join two parallel lane-centre waypoints."""
    start_location, end_location = start.transform.location, end.transform.location
    start_yaw, end_yaw = math.radians(_yaw(start)), math.radians(_yaw(end))
    p0 = (float(start_location.x), float(start_location.y))
    p1 = (float(end_location.x), float(end_location.y))
    m0 = (math.cos(start_yaw) * tangent_scale_m, math.sin(start_yaw) * tangent_scale_m)
    m1 = (math.cos(end_yaw) * tangent_scale_m, math.sin(end_yaw) * tangent_scale_m)
    points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        t = index / samples
        h00 = 2.0 * t ** 3 - 3.0 * t ** 2 + 1.0
        h10 = t ** 3 - 2.0 * t ** 2 + t
        h01 = -2.0 * t ** 3 + 3.0 * t ** 2
        h11 = t ** 3 - t ** 2
        points.append((
            h00 * p0[0] + h10 * m0[0] + h01 * p1[0] + h11 * m1[0],
            h00 * p0[1] + h10 * m0[1] + h01 * p1[1] + h11 * m1[1],
        ))
    return tuple(points)


def build_lane_change_route_reference(
    world_map: Any,
    anchor_or_location: Any,
    target_speed_mps: float,
    *,
    direction: str,
    distance_m: float = 60.0,
    step_m: float = 1.0,
    transition_start_m: float = 12.0,
    transition_length_m: float = 28.0,
) -> RouteReference:
    """Build a legal same-direction adjacent-lane transition."""
    side = str(direction).strip().upper()
    if side not in {"LEFT", "RIGHT"}:
        raise ValueError("lane-change direction must be LEFT or RIGHT")
    location = (anchor_or_location.get_location()
                if hasattr(anchor_or_location, "get_location") else anchor_or_location)
    current = world_map.get_waypoint(location, project_to_road=True)
    if not _is_driving_lane(current):
        raise ValueError("lane-change anchor is not on a driving lane")

    prefix: list[tuple[float, float]] = []
    for _ in range(max(1, int(math.ceil(transition_start_m / step_m))) + 1):
        loc = current.transform.location
        prefix.append((float(loc.x), float(loc.y)))
        next_waypoint = _next_straight(current, step_m)
        if next_waypoint is None or bool(getattr(current, "is_junction", False)):
            raise ValueError("lane-change prefix reaches a junction or dead end")
        current = next_waypoint

    adjacent = _adjacent_driving_lane(current, side)
    if adjacent is None or bool(getattr(adjacent, "is_junction", False)):
        raise ValueError(f"no same-direction driving lane on the {side.lower()}")
    _validate_lane_change_corridor(
        current,
        direction=side,
        distance_m=transition_length_m,
        step_m=step_m,
    )
    target_end = _advance_waypoint(adjacent, transition_length_m, step_m)
    if target_end is None or bool(getattr(target_end, "is_junction", False)):
        raise ValueError("adjacent lane cannot support the full transition")

    transition = _hermite_lane_change(
        current,
        target_end,
        samples=max(8, int(math.ceil(transition_length_m / step_m))),
        tangent_scale_m=transition_length_m,
    )
    points = prefix + list(transition)
    target = target_end
    while _route_length(points) < distance_m:
        target = _next_straight(target, step_m)
        if target is None:
            break
        loc = target.transform.location
        points.append((float(loc.x), float(loc.y)))
    if _route_length(points) < distance_m * 0.8:
        raise ValueError("adjacent lane route is too short")
    route_points = tuple(points)
    return RouteReference(route_points, _route_curvature(route_points), float(target_speed_mps))


def build_scenario_route_reference(
    world_map: Any,
    anchor_or_location: Any,
    target_speed_mps: float,
    *,
    maneuver: str,
    distance_m: float,
    step_m: float = 1.0,
) -> RouteReference:
    """Convert a scenario manoeuvre into a CARLA-topology route."""
    action = str(maneuver).strip().upper()
    if action not in _MANEUVERS:
        raise ValueError(f"unsupported scenario maneuver: {maneuver!r}")
    if action.startswith("CHANGE_LANE_"):
        return build_lane_change_route_reference(
            world_map,
            anchor_or_location,
            target_speed_mps,
            direction=action.rsplit("_", 1)[-1],
            distance_m=distance_m,
            step_m=step_m,
        )
    direction = action.removeprefix("TURN_") if action.startswith("TURN_") else "STRAIGHT"
    return build_route_reference(
        world_map,
        anchor_or_location,
        target_speed_mps,
        turn_direction=direction,
        distance_m=distance_m,
        step_m=step_m,
    )


def select_topology_route_anchor(
    world_map: Any,
    spawn_points: Sequence[Any],
    *,
    maneuver: str,
    target_speed_mps: float,
    distance_m: float,
    forbidden_points_xy: Sequence[tuple[float, float]] = (),
    candidate_index: int = 0,
) -> tuple[int, RouteReference, float]:
    """Pick a spawn whose generated route is legal, long enough and avoids lights."""
    if not spawn_points:
        raise ValueError("at least one spawn point is required")
    action = str(maneuver).strip().upper()
    candidates: list[tuple[float, int, RouteReference]] = []
    for index, transform in enumerate(spawn_points):
        try:
            route = build_scenario_route_reference(
                world_map,
                transform.location,
                target_speed_mps,
                maneuver=action,
                distance_m=distance_m,
            )
        except (AttributeError, TypeError, ValueError):
            continue
        points = route.points_xy_m
        length_penalty = max(0.0, distance_m - _route_length(points)) * 10.0
        yaw_change = _route_yaw_change(points)
        if action == "TURN_LEFT":
            direction_penalty = abs(yaw_change + 90.0) if yaw_change <= -25.0 else 1_000.0
        elif action == "TURN_RIGHT":
            direction_penalty = abs(yaw_change - 90.0) if yaw_change >= 25.0 else 1_000.0
        elif action == "FOLLOW":
            direction_penalty = abs(yaw_change)
        elif action == "FOLLOW_LEFT":
            direction_penalty = abs(yaw_change + 20.0) if yaw_change <= -5.0 else 1_000.0
        elif action == "FOLLOW_RIGHT":
            direction_penalty = abs(yaw_change - 20.0) if yaw_change >= 5.0 else 1_000.0
        elif action.startswith("CHANGE_LANE_"):
            # Lane-change contracts measure signed displacement in the
            # initial ego frame, so the acceptance segment must remain a
            # straight same-direction multi-lane road rather than turn at the
            # next junction after completing the lateral transition.
            direction_penalty = abs(yaw_change) * 10.0
            if abs(yaw_change) > 20.0:
                direction_penalty += 1_000.0
        else:
            direction_penalty = 0.0
        curvature_penalty = route.curvature_per_m * (50.0 if action.startswith("TURN_") else 5.0)
        light_penalty = 0.0
        if forbidden_points_xy:
            nearest = min(
                math.dist(route_point, blocked)
                for route_point in points for blocked in forbidden_points_xy
            )
            if nearest < 6.0:
                light_penalty = 500.0 + (6.0 - nearest) * 20.0
        score = length_penalty + direction_penalty + curvature_penalty + light_penalty
        candidates.append((score, index, route))
    if not candidates:
        raise RuntimeError(f"no Town route supports maneuver {action}")
    candidates.sort(key=lambda item: (item[0], item[1]))
    score, index, route = candidates[candidate_index % len(candidates)]
    if score >= 1_000.0:
        raise RuntimeError(f"no Town route has the required topology for {action}")
    return index, route, score


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
    waypoint = select_heading_compatible_waypoint(world_map, ego_or_location)
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


__all__ = [
    "build_lane_change_route_reference",
    "build_route_reference",
    "build_scenario_route_reference",
    "lane_change_rejection_reason",
    "command_turn_direction",
    "select_heading_compatible_waypoint",
    "select_topology_route_anchor",
    "warm_heading_waypoint_cache",
]
