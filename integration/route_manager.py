"""Destination-driven global route planning over CARLA map topology.

The manager owns the route coordinate frame shared by scenario placement,
control and scoring.  It deliberately contains no scenario-specific spawn
indices or branch choices: callers provide a start and destination and receive
one validated, deterministic route plus continuous route-state queries.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field, replace
import hashlib
import heapq
import itertools
import math
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from car_control_A.routing import RouteReference

from .route_geometry import (
    cumulative_distances_m,
    project_route_progress_m,
    route_pose_at_s,
)


Point2D = tuple[float, float]


class RoutePlanningError(RuntimeError):
    """A route failure with a stable machine-readable reason code."""

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.code = str(code)
        self.detail = str(detail)
        self.context = dict(context or {})
        super().__init__(f"{self.code}: {self.detail}")


@dataclass(frozen=True, slots=True)
class RouteSample:
    x_m: float
    y_m: float
    z_m: float
    yaw_deg: float
    s_m: float
    road_id: int | None
    section_id: int | None
    lane_id: int | None
    is_junction: bool
    left_lane_id: int | None
    right_lane_id: int | None

    @property
    def point_xy_m(self) -> Point2D:
        return (self.x_m, self.y_m)


@dataclass(frozen=True, slots=True)
class RouteValidation:
    total_length_m: float
    point_count: int
    maximum_gap_m: float
    destination_error_m: float
    repeated_sample_count: int
    junction_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "total_length_m": self.total_length_m,
            "point_count": self.point_count,
            "maximum_gap_m": self.maximum_gap_m,
            "destination_error_m": self.destination_error_m,
            "repeated_sample_count": self.repeated_sample_count,
            "junction_count": self.junction_count,
        }


@dataclass(frozen=True, slots=True)
class GlobalRoute:
    reference: RouteReference
    samples: tuple[RouteSample, ...]
    validation: RouteValidation
    start_xy_m: Point2D
    destination_xy_m: Point2D
    waypoints: tuple[Any, ...] = field(repr=False, compare=False)

    @property
    def total_length_m(self) -> float:
        return self.validation.total_length_m


@dataclass(frozen=True, slots=True)
class RouteState:
    route_s: float
    route_progress: float
    route_remaining_m: float
    nearest_route_point: Point2D
    cross_track_error_m: float
    road_curvature: float
    road_id: int | None
    lane_id: int | None
    lane_relation: str
    left_lane_id: int | None
    right_lane_id: int | None
    nearest_index: int
    reached_destination: bool
    status: str
    reason: str | None
    requires_replan: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "route_s": self.route_s,
            "route_progress": self.route_progress,
            "route_remaining_m": self.route_remaining_m,
            "nearest_route_point": list(self.nearest_route_point),
            "cross_track_error_m": self.cross_track_error_m,
            "road_curvature": self.road_curvature,
            "road_id": self.road_id,
            "lane_id": self.lane_id,
            "lane_relation": self.lane_relation,
            "left_lane_id": self.left_lane_id,
            "right_lane_id": self.right_lane_id,
            "nearest_index": self.nearest_index,
            "reached_destination": self.reached_destination,
            "status": self.status,
            "reason": self.reason,
            "requires_replan": self.requires_replan,
        }


@dataclass(frozen=True, slots=True)
class RoutePlacement:
    """A map-valid placement resolved from route distance and lane relation."""

    route_s: float
    lane_relation: str
    x_m: float
    y_m: float
    z_m: float
    yaw_deg: float
    road_id: int | None
    lane_id: int | None


@dataclass(frozen=True, slots=True)
class RouteRecoveryPolicy:
    """Map-independent hysteresis for automatic off-route recovery."""

    off_route_threshold_m: float = 6.0
    confirmation_s: float = 0.5
    cooldown_s: float = 5.0
    maximum_attempts: int = 3

    @classmethod
    def from_mapping(cls, value: Mapping[str, object] | None) -> "RouteRecoveryPolicy":
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise TypeError("route.recovery must be an object")
        unknown = set(value).difference({
            "off_route_threshold_m", "confirmation_s", "cooldown_s",
            "maximum_attempts",
        })
        if unknown:
            raise ValueError(
                "unsupported route.recovery field(s): " + ", ".join(sorted(unknown))
            )
        return cls(
            off_route_threshold_m=float(value.get("off_route_threshold_m", 6.0)),
            confirmation_s=float(value.get("confirmation_s", 0.5)),
            cooldown_s=float(value.get("cooldown_s", 5.0)),
            maximum_attempts=value.get("maximum_attempts", 3),  # type: ignore[arg-type]
        )

    def __post_init__(self) -> None:
        if (
            not math.isfinite(float(self.off_route_threshold_m))
            or self.off_route_threshold_m <= 0.0
        ):
            raise ValueError("off_route_threshold_m must be finite and positive")
        if not math.isfinite(float(self.confirmation_s)) or self.confirmation_s < 0.0:
            raise ValueError("confirmation_s must be finite and non-negative")
        if not math.isfinite(float(self.cooldown_s)) or self.cooldown_s < 0.0:
            raise ValueError("cooldown_s must be finite and non-negative")
        if type(self.maximum_attempts) is not int or self.maximum_attempts < 1:
            raise ValueError("maximum_attempts must be a positive integer")


@dataclass(frozen=True, slots=True)
class RouteRecoveryDecision:
    status: str
    reason: str | None
    should_replan: bool
    attempt: int


class RouteRecoveryTracker:
    """Turn noisy per-frame deviation into deterministic recovery decisions."""

    def __init__(self, policy: RouteRecoveryPolicy | None = None) -> None:
        self.policy = policy or RouteRecoveryPolicy()
        self._off_route_since_s: float | None = None
        self._last_attempt_s: float | None = None
        self._attempts = 0

    @property
    def attempts(self) -> int:
        return self._attempts

    def observe(
        self,
        route_state: RouteState,
        sim_time_s: float,
        *,
        recovery_suppressed: bool = False,
    ) -> RouteRecoveryDecision:
        now_s = float(sim_time_s)
        if not math.isfinite(now_s) or now_s < 0.0:
            raise ValueError("sim_time_s must be finite and non-negative")
        if route_state.reached_destination:
            self._off_route_since_s = None
            return RouteRecoveryDecision("DESTINATION_REACHED", None, False, self._attempts)
        if not route_state.requires_replan:
            self._off_route_since_s = None
            return RouteRecoveryDecision("ON_ROUTE", None, False, self._attempts)
        if recovery_suppressed:
            self._off_route_since_s = None
            return RouteRecoveryDecision(
                "RECOVERY_SUPPRESSED",
                "INTENTIONAL_MANEUVER_ACTIVE",
                False,
                self._attempts,
            )
        if self._off_route_since_s is None:
            self._off_route_since_s = now_s
        if now_s - self._off_route_since_s < self.policy.confirmation_s:
            return RouteRecoveryDecision(
                "OFF_ROUTE_CONFIRMING",
                "ROUTE_DEVIATION_CONFIRMING",
                False,
                self._attempts,
            )
        if self._attempts >= self.policy.maximum_attempts:
            return RouteRecoveryDecision(
                "RECOVERY_EXHAUSTED",
                "ROUTE_REPLAN_ATTEMPTS_EXHAUSTED",
                False,
                self._attempts,
            )
        if (
            self._last_attempt_s is not None
            and now_s - self._last_attempt_s < self.policy.cooldown_s
        ):
            return RouteRecoveryDecision(
                "REPLAN_COOLDOWN",
                "ROUTE_REPLAN_COOLDOWN",
                False,
                self._attempts,
            )
        self._attempts += 1
        self._last_attempt_s = now_s
        self._off_route_since_s = None
        return RouteRecoveryDecision(
            "REPLANNING",
            "ROUTE_DEVIATION_REPLAN_REQUIRED",
            True,
            self._attempts,
        )

    def note_replan_succeeded(self) -> None:
        self._off_route_since_s = None

    def reset_mission(self) -> None:
        self._off_route_since_s = None
        self._last_attempt_s = None
        self._attempts = 0


@dataclass(frozen=True, slots=True)
class _TopologyEdge:
    index: int
    entry: Any
    exit: Any
    waypoints: tuple[Any, ...]
    length_m: float


@dataclass(frozen=True, slots=True)
class _LaneChangeTransition:
    source_edge_index: int
    target_edge_index: int
    side: str
    candidates: tuple[tuple[Any, Any], ...] = field(repr=False, compare=False)


class _BlendedWaypoint:
    """Waypoint-shaped route sample used inside a smooth legal lane change."""

    def __init__(
        self,
        source: Any,
        target: Any,
        *,
        x_m: float,
        y_m: float,
        z_m: float,
        yaw_deg: float,
        target_weight: float,
    ) -> None:
        base = target if target_weight >= 0.5 else source
        source_location = source.transform.location
        location_type = type(source_location)
        try:
            location = location_type(x=float(x_m), y=float(y_m), z=float(z_m))
        except TypeError:
            location = location_type(float(x_m), float(y_m), float(z_m))
        self.transform = SimpleNamespace(
            location=location,
            rotation=SimpleNamespace(yaw=float(yaw_deg)),
        )
        for name in (
            "road_id", "section_id", "lane_id", "s", "lane_type", "is_junction",
        ):
            setattr(self, name, getattr(base, name, None))
        self._base = base

    def get_left_lane(self) -> Any | None:
        getter = getattr(self._base, "get_left_lane", None)
        return getter() if callable(getter) else None

    def get_right_lane(self) -> Any | None:
        getter = getattr(self._base, "get_right_lane", None)
        return getter() if callable(getter) else None


def _location(value: Any) -> Any:
    if callable(getattr(value, "get_location", None)):
        return value.get_location()
    transform = getattr(value, "transform", None)
    if transform is not None and hasattr(transform, "location"):
        return transform.location
    return getattr(value, "location", value)


def _transform(value: Any) -> Any | None:
    if callable(getattr(value, "get_transform", None)):
        return value.get_transform()
    if hasattr(value, "location") and hasattr(value, "rotation"):
        return value
    return None


def _xy(value: Any) -> Point2D:
    location = _location(value)
    return (float(location.x), float(location.y))


def _distance(first: Any, second: Any) -> float:
    return math.dist(_xy(first), _xy(second))


def _wrap_degrees(angle: float) -> float:
    return (float(angle) + 180.0) % 360.0 - 180.0


def _yaw(waypoint: Any) -> float:
    return float(waypoint.transform.rotation.yaw)


def _is_driving_lane(waypoint: Any | None) -> bool:
    if waypoint is None:
        return False
    lane_type = str(getattr(waypoint, "lane_type", "Driving")).split(".")[-1]
    return lane_type.upper() == "DRIVING"


def _lane_identity(waypoint: Any) -> tuple[int | None, int | None, int | None]:
    return (
        getattr(waypoint, "road_id", None),
        getattr(waypoint, "section_id", None),
        getattr(waypoint, "lane_id", None),
    )


def _visit_key(waypoint: Any) -> tuple[object, ...]:
    road_id, section_id, lane_id = _lane_identity(waypoint)
    lane_s = getattr(waypoint, "s", None)
    if road_id is not None and lane_id is not None and lane_s is not None:
        return (road_id, section_id, lane_id, round(float(lane_s), 2))
    x_m, y_m = _xy(waypoint)
    return (round(x_m, 2), round(y_m, 2), round(_yaw(waypoint), 1))


def _same_direction(first: Any, second: Any, tolerance_deg: float = 60.0) -> bool:
    return abs(_wrap_degrees(_yaw(first) - _yaw(second))) <= tolerance_deg


def _lane_change_allowed(waypoint: Any, side: str) -> bool:
    """Read CARLA lane-marking permissions without importing the CARLA module."""
    marking = getattr(
        waypoint,
        "left_lane_marking" if side == "LEFT" else "right_lane_marking",
        None,
    )
    value = getattr(marking, "lane_change", None)
    if value is None:
        value = getattr(waypoint, "lane_change", None)
    if value is None:
        return False
    try:
        mask = int(value)
    except (TypeError, ValueError):
        normalized = str(value).split(".")[-1].strip().upper()
        return normalized == "BOTH" or normalized == side
    # CARLA LaneChange uses Right=1, Left=2 and Both=3.
    return bool(mask & (2 if side == "LEFT" else 1))


def _curvature(points: Sequence[Point2D], index: int) -> float:
    if len(points) < 3:
        return 0.0
    center = min(max(1, int(index)), len(points) - 2)
    first, middle, last = points[center - 1], points[center], points[center + 1]
    a, b, c = math.dist(middle, last), math.dist(first, last), math.dist(first, middle)
    denominator = a * b * c
    if denominator <= 1e-9:
        return 0.0
    twice_area = abs(
        (middle[0] - first[0]) * (last[1] - first[1])
        - (middle[1] - first[1]) * (last[0] - first[0])
    )
    return 2.0 * twice_area / denominator


class RouteManager:
    """Plan and query one global destination route for a CARLA map."""

    def __init__(
        self,
        world_map: Any,
        *,
        sample_step_m: float = 2.0,
        finish_radius_m: float = 4.0,
        maximum_gap_m: float | None = None,
        maximum_expansions: int = 50_000,
        off_route_threshold_m: float = 6.0,
    ) -> None:
        if not math.isfinite(float(sample_step_m)) or sample_step_m <= 0.0:
            raise ValueError("sample_step_m must be finite and positive")
        if not math.isfinite(float(finish_radius_m)) or finish_radius_m <= 0.0:
            raise ValueError("finish_radius_m must be finite and positive")
        if type(maximum_expansions) is not int or maximum_expansions < 1:
            raise ValueError("maximum_expansions must be a positive integer")
        self.world_map = world_map
        self.sample_step_m = float(sample_step_m)
        self.finish_radius_m = float(finish_radius_m)
        self.maximum_gap_m = (
            max(5.0, self.sample_step_m * 3.0)
            if maximum_gap_m is None else float(maximum_gap_m)
        )
        self.maximum_expansions = maximum_expansions
        if not math.isfinite(float(off_route_threshold_m)) or off_route_threshold_m <= 0.0:
            raise ValueError("off_route_threshold_m must be finite and positive")
        self.off_route_threshold_m = float(off_route_threshold_m)
        self._edges: tuple[_TopologyEdge, ...] | None = None
        self._adjacency: dict[int, tuple[int, ...]] | None = None
        self._lane_change_transitions: dict[
            tuple[int, int], _LaneChangeTransition
        ] = {}

    def plan(
        self,
        start: Any,
        destination: Any,
        target_speed_mps: float,
    ) -> GlobalRoute:
        if not math.isfinite(float(target_speed_mps)) or target_speed_mps < 0.0:
            raise ValueError("target_speed_mps must be finite and non-negative")
        start_waypoint = self._project_endpoint(start, "ROUTE_START_UNMAPPABLE")
        destination_waypoint = self._project_endpoint(
            destination, "ROUTE_DESTINATION_UNMAPPABLE",
        )
        edges, adjacency = self._topology_graph()
        start_edge = self._locate_edge(start_waypoint, edges, "ROUTE_START_UNMAPPABLE")
        goal_edge = self._locate_edge(
            destination_waypoint, edges, "ROUTE_DESTINATION_UNMAPPABLE",
        )
        blocked_connections: set[tuple[int, int]] = set()
        while True:
            edge_path = self._search(
                start_edge.index,
                goal_edge.index,
                destination_waypoint,
                edges,
                adjacency,
                blocked_connections=blocked_connections,
            )
            try:
                waypoints = self._assemble_waypoints(
                    edge_path, start_waypoint, destination_waypoint, edges,
                )
                break
            except RoutePlanningError as error:
                if error.code not in {
                    "ROUTE_LANE_CHANGE_UNAVAILABLE",
                    "ROUTE_LANE_CHANGE_SEQUENCE_INVALID",
                }:
                    raise
                source_index = error.context.get("source_edge_index")
                target_index = error.context.get("target_edge_index")
                if type(source_index) is not int or type(target_index) is not int:
                    raise
                connection = (source_index, target_index)
                if connection in blocked_connections:
                    raise
                blocked_connections.add(connection)
        return self._build_global_route(
            waypoints, start_waypoint, destination_waypoint,
            float(target_speed_mps),
        )

    def plan_distance(
        self,
        start: Any,
        distance_m: float,
        target_speed_mps: float,
    ) -> GlobalRoute:
        """Generate a topology-following coverage route of a requested length.

        This mode is for distance-contract missions such as the 8 km competition
        scene, where a shortest path to one destination cannot express the task.
        Junction choices prefer unvisited legal topology and never introduce an
        implicit lane change.
        """
        if not math.isfinite(float(distance_m)) or distance_m <= 0.0:
            raise ValueError("distance_m must be finite and positive")
        if not math.isfinite(float(target_speed_mps)) or target_speed_mps < 0.0:
            raise ValueError("target_speed_mps must be finite and non-negative")
        start_waypoint = self._project_endpoint(start, "ROUTE_START_UNMAPPABLE")
        requested_distance_m = float(distance_m)
        waypoints = [start_waypoint]
        visits = {_visit_key(start_waypoint): 1}
        accumulated_m = 0.0
        maximum_steps = max(
            32,
            math.ceil(requested_distance_m / self.sample_step_m) * 4,
        )
        for _ in range(maximum_steps):
            if accumulated_m + 1e-9 >= requested_distance_m:
                break
            current = waypoints[-1]
            candidates = tuple(
                waypoint
                for waypoint in current.next(self.sample_step_m)
                if _is_driving_lane(waypoint) and _same_direction(current, waypoint, 120.0)
            )
            if not candidates:
                raise RoutePlanningError(
                    "ROUTE_ENDED_EARLY",
                    f"coverage route ended at {accumulated_m:.2f} m before "
                    f"the {requested_distance_m:.2f} m contract",
                )
            selected = min(
                candidates,
                key=lambda waypoint: (
                    visits.get(_visit_key(waypoint), 0),
                    -self._future_novel_capacity(waypoint, visits, depth=8),
                    abs(_wrap_degrees(_yaw(waypoint) - _yaw(current))),
                    _visit_key(waypoint),
                ),
            )
            step_length_m = _distance(current, selected)
            if step_length_m <= 1e-6 or step_length_m > self.maximum_gap_m:
                raise RoutePlanningError(
                    "ROUTE_DISCONTINUOUS",
                    f"coverage route step {step_length_m:.2f} m is invalid",
                )
            waypoints.append(selected)
            accumulated_m += step_length_m
            key = _visit_key(selected)
            visits[key] = visits.get(key, 0) + 1
        if accumulated_m + 1e-9 < requested_distance_m:
            raise RoutePlanningError(
                "ROUTE_ENDED_EARLY",
                f"coverage route reached only {accumulated_m:.2f} m of "
                f"{requested_distance_m:.2f} m",
            )
        route = self._build_global_route(
            waypoints,
            start_waypoint,
            waypoints[-1],
            float(target_speed_mps),
            allow_repeated_samples=True,
        )
        metadata = dict(route.reference.metadata)
        metadata.update({
            "planner": "CARLA_TOPOLOGY_COVERAGE",
            "planning_mode": "TOPOLOGY_DISTANCE_COVERAGE",
            "requested_distance_m": requested_distance_m,
        })
        return replace(route, reference=replace(route.reference, metadata=metadata))

    def state(
        self,
        route: GlobalRoute,
        x_m: float,
        y_m: float,
        *,
        previous_s_m: float | None = None,
        forward_window_m: float = 80.0,
    ) -> RouteState:
        points = route.reference.points_xy_m
        route_s = project_route_progress_m(
            points, x_m, y_m,
            previous_s_m=previous_s_m,
            forward_window_m=forward_window_m,
        )
        cumulative = cumulative_distances_m(points)
        index = min(
            len(points) - 1,
            bisect_left(cumulative, route_s),
        )
        pose = route_pose_at_s(points, route_s)
        route_sample = route.samples[index]
        vehicle_waypoint = self._project_xy_like(route.waypoints[index], x_m, y_m)
        vehicle_lane_id = getattr(vehicle_waypoint, "lane_id", route_sample.lane_id)
        lane_relation = "UNKNOWN"
        if vehicle_waypoint is None:
            lane_relation = "UNKNOWN"
        elif vehicle_lane_id == route_sample.lane_id:
            lane_relation = "CURRENT"
        elif vehicle_lane_id == route_sample.left_lane_id:
            lane_relation = "LEFT"
        elif vehicle_lane_id == route_sample.right_lane_id:
            lane_relation = "RIGHT"
        remaining = max(0.0, route.total_length_m - route_s)
        endpoint_error = math.dist((float(x_m), float(y_m)), route.destination_xy_m)
        cross_track_error = math.dist(
            (float(x_m), float(y_m)), (pose.x_m, pose.y_m),
        )
        reached_destination = (
            endpoint_error <= self.finish_radius_m
            and remaining <= self.finish_radius_m * 2.0
        )
        requires_replan = (
            not reached_destination
            and cross_track_error > self.off_route_threshold_m
        )
        status = (
            "DESTINATION_REACHED" if reached_destination
            else "OFF_ROUTE" if requires_replan
            else "ON_ROUTE"
        )
        return RouteState(
            route_s=route_s,
            route_progress=min(1.0, route_s / route.total_length_m),
            route_remaining_m=remaining,
            nearest_route_point=(pose.x_m, pose.y_m),
            cross_track_error_m=cross_track_error,
            road_curvature=_curvature(points, index),
            road_id=getattr(vehicle_waypoint, "road_id", route_sample.road_id),
            lane_id=vehicle_lane_id,
            lane_relation=lane_relation,
            left_lane_id=route_sample.left_lane_id,
            right_lane_id=route_sample.right_lane_id,
            nearest_index=index,
            reached_destination=reached_destination,
            status=status,
            reason="ROUTE_DEVIATION_REPLAN_REQUIRED" if requires_replan else None,
            requires_replan=requires_replan,
        )

    def placement(
        self,
        route: GlobalRoute,
        route_s: float,
        lane_relation: str = "CURRENT",
    ) -> RoutePlacement:
        """Resolve an actor/event pose using route distance plus lane relation."""
        if not math.isfinite(float(route_s)):
            raise ValueError("route_s must be finite")
        relation = str(lane_relation).strip().upper()
        if relation not in {"LEFT", "CURRENT", "RIGHT"}:
            raise ValueError("lane_relation must be LEFT, CURRENT or RIGHT")
        clamped_s = min(max(0.0, float(route_s)), route.total_length_m)
        cumulative = cumulative_distances_m(route.reference.points_xy_m)
        index = min(len(route.waypoints) - 1, bisect_left(cumulative, clamped_s))
        waypoint = route.waypoints[index]
        if relation != "CURRENT":
            waypoint = self._adjacent_lane(waypoint, relation)
            if waypoint is None:
                raise RoutePlanningError(
                    "ROUTE_LANE_UNAVAILABLE",
                    f"no legal {relation.lower()} driving lane at route_s={clamped_s:.2f}",
                )
        location = waypoint.transform.location
        return RoutePlacement(
            route_s=clamped_s,
            lane_relation=relation,
            x_m=float(location.x),
            y_m=float(location.y),
            z_m=float(getattr(location, "z", 0.0)),
            yaw_deg=_yaw(waypoint),
            road_id=getattr(waypoint, "road_id", None),
            lane_id=getattr(waypoint, "lane_id", None),
        )

    def local_reference(
        self,
        route: GlobalRoute,
        route_s: float,
        target_speed_mps: float,
        *,
        lookbehind_m: float = 8.0,
        lookahead_m: float = 80.0,
    ) -> RouteReference:
        """Return a bounded controller view while the global route stays authoritative."""
        values = (route_s, target_speed_mps, lookbehind_m, lookahead_m)
        if any(
            type(value) not in (int, float)
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError("local route reference values must be finite numbers")
        if target_speed_mps < 0.0:
            raise ValueError("target_speed_mps must be non-negative")
        if lookbehind_m < 0.0 or lookahead_m <= 0.0:
            raise ValueError("lookbehind_m must be non-negative and lookahead_m positive")

        center_s = min(max(0.0, float(route_s)), route.total_length_m)
        start_s = max(0.0, center_s - float(lookbehind_m))
        end_s = min(route.total_length_m, center_s + float(lookahead_m))
        if end_s - start_s < min(1.0, route.total_length_m):
            start_s = max(0.0, end_s - max(1.0, self.sample_step_m))
        cumulative = cumulative_distances_m(route.reference.points_xy_m)
        start_pose = route_pose_at_s(route.reference.points_xy_m, start_s)
        end_pose = route_pose_at_s(route.reference.points_xy_m, end_s)
        points: list[Point2D] = [(start_pose.x_m, start_pose.y_m)]
        points.extend(
            point
            for point, sample_s in zip(route.reference.points_xy_m, cumulative)
            if start_s < sample_s < end_s
        )
        points.append((end_pose.x_m, end_pose.y_m))
        deduplicated: list[Point2D] = []
        for point in points:
            if deduplicated and math.dist(deduplicated[-1], point) <= 1e-6:
                continue
            deduplicated.append(point)
        if len(deduplicated) < 2:
            raise RoutePlanningError(
                "ROUTE_LOCAL_REFERENCE_EMPTY",
                f"cannot build a control window at route_s={center_s:.2f}",
            )
        local_points = tuple(deduplicated)
        metadata = dict(route.reference.metadata)
        metadata.update({
            "reference_scope": "LOCAL_CONTROL",
            "global_route_id": route.reference.route_id,
            "global_s_start_m": start_s,
            "global_s_end_m": end_s,
            "global_route_s_m": center_s,
        })
        return RouteReference(
            local_points,
            max(
                (_curvature(local_points, index) for index in range(len(local_points))),
                default=0.0,
            ),
            float(target_speed_mps),
            route_id=(
                f"{route.reference.route_id or 'global'}:local:"
                f"{start_s:.1f}:{end_s:.1f}"
            ),
            metadata=metadata,
        )

    def mission_placement(
        self,
        route: GlobalRoute,
        mission_route_s: float,
        mission_progress_offset_m: float,
        lane_relation: str = "CURRENT",
    ) -> RoutePlacement:
        """Resolve an absolute mission ``route_s`` on the current replanned route."""
        if not math.isfinite(float(mission_route_s)) or not math.isfinite(
            float(mission_progress_offset_m)
        ):
            raise ValueError("mission route positions must be finite")
        local_s = float(mission_route_s) - float(mission_progress_offset_m)
        if local_s < -1e-6:
            raise RoutePlanningError(
                "ROUTE_EVENT_ALREADY_PASSED",
                f"event s={mission_route_s:.2f} precedes active route origin "
                f"s={mission_progress_offset_m:.2f}",
            )
        if local_s > route.total_length_m + 1e-6:
            raise RoutePlanningError(
                "ROUTE_EVENT_BEYOND_ACTIVE_ROUTE",
                f"event local s={local_s:.2f} exceeds active route length "
                f"{route.total_length_m:.2f}",
            )
        placement = self.placement(route, local_s, lane_relation)
        return replace(placement, route_s=float(mission_route_s))

    def replan(
        self,
        current: Any,
        destination: Any,
        target_speed_mps: float,
    ) -> GlobalRoute:
        """Rebuild a route from the current map pose after an off-route event."""
        route = self.plan(current, destination, target_speed_mps)
        current_xy = _xy(current)
        connector_length_m = math.dist(current_xy, route.start_xy_m)
        if connector_length_m > max(
            self.maximum_gap_m,
            self.off_route_threshold_m * 2.0,
        ):
            raise RoutePlanningError(
                "ROUTE_RECOVERY_CONNECTOR_UNSAFE",
                f"current pose is {connector_length_m:.2f} m from the replanned lane",
            )
        metadata = dict(route.reference.metadata)
        metadata["planning_reason"] = "OFF_ROUTE_REPLAN"
        metadata["recovery_connector_m"] = connector_length_m
        if connector_length_m <= 0.1:
            reference = replace(route.reference, metadata=metadata)
            return replace(route, reference=reference)

        base_points = route.reference.points_xy_m
        base_cumulative = cumulative_distances_m(base_points)
        merge_s_m = min(
            route.total_length_m,
            max(8.0, connector_length_m * 3.0),
        )
        merge_index = min(
            len(base_points) - 1,
            bisect_left(base_cumulative, merge_s_m),
        )
        merge_point = base_points[merge_index]
        merge_length_m = math.dist(current_xy, merge_point)
        connector_steps = max(
            2,
            math.ceil(merge_length_m / self.sample_step_m),
        )
        connector_points = tuple(
            (
                current_xy[0] + (merge_point[0] - current_xy[0]) * index / connector_steps,
                current_xy[1] + (merge_point[1] - current_xy[1]) * index / connector_steps,
            )
            for index in range(connector_steps)
        )
        points = (*connector_points, *base_points[merge_index:])
        cumulative = cumulative_distances_m(points)
        connector_samples = tuple(
            replace(
                route.samples[0],
                x_m=point[0],
                y_m=point[1],
                s_m=cumulative[index],
            )
            for index, point in enumerate(connector_points)
        )
        samples = (
            *connector_samples,
            *(
                replace(
                    sample,
                    s_m=cumulative[len(connector_points) + index],
                )
                for index, sample in enumerate(route.samples[merge_index:])
            ),
        )
        validation = replace(
            route.validation,
            total_length_m=cumulative[-1],
            point_count=len(points),
            maximum_gap_m=max(
                route.validation.maximum_gap_m,
                max(
                    math.dist(first, second)
                    for first, second in zip(points, points[1:])
                ),
            ),
        )
        route_fingerprint = "|".join(
            f"{x_m:.2f},{y_m:.2f}" for x_m, y_m in points
        ).encode("ascii")
        reference = RouteReference(
            points,
            max(
                (_curvature(points, index) for index in range(len(points))),
                default=0.0,
            ),
            route.reference.target_speed_mps,
            route_id=f"replan-{hashlib.sha256(route_fingerprint).hexdigest()[:16]}",
            metadata=metadata,
        )
        return GlobalRoute(
            reference=reference,
            samples=samples,
            validation=validation,
            start_xy_m=current_xy,
            destination_xy_m=route.destination_xy_m,
            waypoints=(
                *(route.waypoints[0] for _ in connector_points),
                *route.waypoints[merge_index:],
            ),
        )

    def _project_xy_like(self, sample_waypoint: Any, x_m: float, y_m: float) -> Any | None:
        location = sample_waypoint.transform.location
        try:
            query = type(location)(x=float(x_m), y=float(y_m), z=float(getattr(location, "z", 0.0)))
        except TypeError:
            try:
                query = type(location)(float(x_m), float(y_m), float(getattr(location, "z", 0.0)))
            except TypeError:
                return None
        return self.world_map.get_waypoint(query, project_to_road=True)

    def _future_novel_capacity(
        self,
        waypoint: Any,
        visits: Mapping[tuple[object, ...], int],
        *,
        depth: int,
        branch_seen: frozenset[tuple[object, ...]] = frozenset(),
    ) -> int:
        if depth <= 0:
            return 0
        key = _visit_key(waypoint)
        if key in branch_seen:
            return 0
        successors = tuple(
            candidate
            for candidate in waypoint.next(self.sample_step_m)
            if _is_driving_lane(candidate)
        )
        novelty = 1 if visits.get(key, 0) == 0 else 0
        if not successors:
            return novelty
        next_seen = branch_seen | {key}
        return novelty + max(
            self._future_novel_capacity(
                candidate,
                visits,
                depth=depth - 1,
                branch_seen=next_seen,
            )
            for candidate in successors
        )

    def _project_endpoint(self, value: Any, code: str) -> Any:
        waypoint = self.world_map.get_waypoint(
            _location(value), project_to_road=True,
        )
        if not _is_driving_lane(waypoint):
            raise RoutePlanningError(code, "endpoint is not on a driving lane")
        transform = _transform(value)
        if transform is not None:
            heading_error = abs(_wrap_degrees(
                _yaw(waypoint) - float(transform.rotation.yaw),
            ))
            if heading_error > 90.0:
                raise RoutePlanningError(code, "endpoint heading opposes the projected lane")
        return waypoint

    def _topology_graph(self) -> tuple[tuple[_TopologyEdge, ...], dict[int, tuple[int, ...]]]:
        if self._edges is not None and self._adjacency is not None:
            return self._edges, self._adjacency
        get_topology = getattr(self.world_map, "get_topology", None)
        if not callable(get_topology):
            raise RoutePlanningError("ROUTE_TOPOLOGY_UNAVAILABLE", "map has no get_topology()")
        raw = tuple(get_topology())
        if not raw:
            raise RoutePlanningError("ROUTE_TOPOLOGY_UNAVAILABLE", "map topology is empty")
        edges: list[_TopologyEdge] = []
        for pair in raw:
            if not isinstance(pair, Sequence) or len(pair) != 2:
                raise RoutePlanningError("ROUTE_TOPOLOGY_INVALID", "topology edge must be a pair")
            entry, exit_waypoint = pair
            if not _is_driving_lane(entry) or not _is_driving_lane(exit_waypoint):
                continue
            waypoints = self._sample_edge(entry, exit_waypoint)
            length = sum(
                _distance(first, second)
                for first, second in zip(waypoints, waypoints[1:])
            )
            if length <= 1e-6:
                continue
            edges.append(_TopologyEdge(len(edges), entry, exit_waypoint, waypoints, length))
        if not edges:
            raise RoutePlanningError("ROUTE_TOPOLOGY_INVALID", "topology has no driving edges")
        adjacency = self._connect_edges(tuple(edges))
        self._edges = tuple(edges)
        self._adjacency = adjacency
        return self._edges, self._adjacency

    def _sample_edge(self, entry: Any, exit_waypoint: Any) -> tuple[Any, ...]:
        if _distance(entry, exit_waypoint) <= self.sample_step_m * 1.5:
            return (entry, exit_waypoint)
        points = [entry]
        current = entry
        seen = {_visit_key(entry)}
        limit = max(16, int(_distance(entry, exit_waypoint) / self.sample_step_m) * 8 + 64)
        for _ in range(limit):
            if _distance(current, exit_waypoint) <= self.sample_step_m * 1.5:
                break
            candidates = tuple(
                item for item in current.next(self.sample_step_m)
                if _is_driving_lane(item)
            )
            if not candidates:
                break
            same_lane = tuple(
                item for item in candidates
                if _lane_identity(item) == _lane_identity(exit_waypoint)
            )
            candidate = min(
                same_lane or candidates,
                key=lambda item: (
                    _distance(item, exit_waypoint),
                    abs(_wrap_degrees(_yaw(item) - _yaw(exit_waypoint))),
                    _visit_key(item),
                ),
            )
            key = _visit_key(candidate)
            if key in seen:
                raise RoutePlanningError(
                    "ROUTE_LOOP_DETECTED", "topology edge repeats a waypoint",
                )
            seen.add(key)
            points.append(candidate)
            current = candidate
        if _visit_key(points[-1]) != _visit_key(exit_waypoint):
            points.append(exit_waypoint)
        return tuple(points)

    def _connect_edges(self, edges: tuple[_TopologyEdge, ...]) -> dict[int, tuple[int, ...]]:
        by_lane: dict[tuple[int | None, int | None, int | None], list[_TopologyEdge]] = {}
        for edge in edges:
            by_lane.setdefault(_lane_identity(edge.entry), []).append(edge)
        mutable: dict[int, set[int]] = {edge.index: set() for edge in edges}
        for edge in edges:
            successors = tuple(
                item for item in edge.exit.next(max(0.5, self.sample_step_m * 0.5))
                if _is_driving_lane(item)
            )
            for successor in successors:
                candidates = by_lane.get(_lane_identity(successor), ())
                ranked = sorted(
                    (
                        (_distance(successor, candidate.entry), candidate)
                        for candidate in candidates
                        if _same_direction(successor, candidate.entry)
                    ),
                    key=lambda item: (item[0], item[1].index),
                )
                if ranked and ranked[0][0] <= self.maximum_gap_m:
                    mutable[edge.index].add(ranked[0][1].index)
            if not mutable[edge.index]:
                for candidate in edges:
                    if candidate.index == edge.index:
                        continue
                    if (
                        _distance(edge.exit, candidate.entry) <= self.sample_step_m * 1.5
                        and _same_direction(edge.exit, candidate.entry)
                    ):
                        mutable[edge.index].add(candidate.index)

        transition_candidates: dict[
            tuple[int, int, str], list[tuple[Any, Any]]
        ] = {}
        for edge in edges:
            if bool(getattr(edge.entry, "is_junction", False)):
                continue
            for waypoint in edge.waypoints:
                if bool(getattr(waypoint, "is_junction", False)):
                    continue
                for side in ("LEFT", "RIGHT"):
                    if not _lane_change_allowed(waypoint, side):
                        continue
                    adjacent = self._adjacent_lane(waypoint, side)
                    if adjacent is None:
                        continue
                    if getattr(adjacent, "road_id", None) != getattr(
                        waypoint, "road_id", None,
                    ):
                        continue
                    target_edges = by_lane.get(_lane_identity(adjacent), ())
                    ranked = sorted(
                        (
                            min(
                                _distance(adjacent, sample)
                                for sample in candidate.waypoints
                            ),
                            candidate.index,
                            candidate,
                        )
                        for candidate in target_edges
                        if candidate.index != edge.index
                        and _same_direction(waypoint, candidate.entry)
                    )
                    if not ranked or ranked[0][0] > self.maximum_gap_m:
                        continue
                    target = ranked[0][2]
                    transition_candidates.setdefault(
                        (edge.index, target.index, side), [],
                    ).append((waypoint, adjacent))

        self._lane_change_transitions = {}
        for (source_index, target_index, side), candidates in sorted(
            transition_candidates.items(),
        ):
            key = (source_index, target_index)
            unique = []
            keys = set()
            for source, target in candidates:
                candidate_key = (_visit_key(source), _visit_key(target))
                if candidate_key in keys:
                    continue
                keys.add(candidate_key)
                trial = _LaneChangeTransition(
                    source_index,
                    target_index,
                    side,
                    ((source, target),),
                )
                try:
                    self._build_lane_change_connector(trial, source)
                except RoutePlanningError:
                    continue
                unique.append((source, target))
            if not unique:
                continue
            transition = _LaneChangeTransition(
                source_index,
                target_index,
                side,
                tuple(unique),
            )
            existing = self._lane_change_transitions.get(key)
            if existing is None or len(transition.candidates) > len(existing.candidates):
                self._lane_change_transitions[key] = transition
                mutable[source_index].add(target_index)
        return {
            index: tuple(sorted(successors))
            for index, successors in mutable.items()
        }

    def _locate_edge(
        self,
        waypoint: Any,
        edges: tuple[_TopologyEdge, ...],
        code: str,
    ) -> _TopologyEdge:
        identity = _lane_identity(waypoint)
        same_lane = tuple(
            edge for edge in edges
            if _lane_identity(edge.entry) == identity
            or _lane_identity(edge.exit) == identity
        )
        candidates = same_lane or edges
        ranked = sorted(
            (
                (
                    min(_distance(waypoint, sample) for sample in edge.waypoints),
                    abs(_wrap_degrees(_yaw(waypoint) - _yaw(edge.entry))),
                    edge.index,
                    edge,
                )
                for edge in candidates
            ),
            key=lambda item: item[:3],
        )
        if not ranked or ranked[0][0] > self.maximum_gap_m:
            raise RoutePlanningError(code, "no topology edge matches the endpoint")
        return ranked[0][3]

    def _search(
        self,
        start_index: int,
        goal_index: int,
        destination: Any,
        edges: tuple[_TopologyEdge, ...],
        adjacency: Mapping[int, tuple[int, ...]],
        *,
        blocked_connections: set[tuple[int, int]] | frozenset[tuple[int, int]] = frozenset(),
    ) -> tuple[int, ...]:
        counter = itertools.count()
        frontier: list[tuple[float, float, int, int]] = [
            (_distance(edges[start_index].exit, destination), 0.0, next(counter), start_index),
        ]
        costs = {start_index: 0.0}
        parents: dict[int, int | None] = {start_index: None}
        found = False
        for _ in range(self.maximum_expansions):
            if not frontier:
                break
            _priority, cost, _order, current = heapq.heappop(frontier)
            if cost > costs.get(current, math.inf) + 1e-9:
                continue
            if current == goal_index:
                found = True
                break
            for successor in adjacency.get(current, ()):
                if (current, successor) in blocked_connections:
                    continue
                lane_change_penalty_m = (
                    25.0
                    if (current, successor) in self._lane_change_transitions
                    else 0.0
                )
                next_cost = cost + edges[successor].length_m + lane_change_penalty_m
                if next_cost + 1e-9 >= costs.get(successor, math.inf):
                    continue
                costs[successor] = next_cost
                parents[successor] = current
                heuristic = _distance(edges[successor].exit, destination)
                heapq.heappush(
                    frontier,
                    (next_cost + heuristic, next_cost, next(counter), successor),
                )
        if not found:
            raise RoutePlanningError(
                "ROUTE_UNREACHABLE",
                f"no topology path from edge {start_index} to edge {goal_index}",
            )
        reversed_path: list[int] = []
        cursor: int | None = goal_index
        while cursor is not None:
            reversed_path.append(cursor)
            cursor = parents[cursor]
        return tuple(reversed(reversed_path))

    def _assemble_waypoints(
        self,
        edge_path: Sequence[int],
        start: Any,
        destination: Any,
        edges: tuple[_TopologyEdge, ...],
    ) -> tuple[Any, ...]:
        assembled: list[Any] = []
        incoming_waypoint: Any | None = None
        for path_index, edge_index in enumerate(edge_path):
            edge = edges[edge_index]
            edge_waypoints = edge.waypoints
            start_index = (
                min(
                    range(len(edge_waypoints)),
                    key=lambda index: _distance(
                        start if path_index == 0 else incoming_waypoint,
                        edge_waypoints[index],
                    ),
                )
                if path_index == 0 or incoming_waypoint is not None
                else 0
            )
            outgoing = None
            if path_index + 1 < len(edge_path):
                outgoing = self._lane_change_transitions.get(
                    (edge_index, edge_path[path_index + 1]),
                )
            end_index = len(edge_waypoints) - 1
            connector: tuple[Any, ...] = ()
            connector_target: Any | None = None
            if outgoing is not None:
                minimum_change_index = min(
                    len(edge_waypoints) - 1,
                    start_index + max(2, math.ceil(8.0 / self.sample_step_m)),
                )
                for source, _target in outgoing.candidates:
                    source_index = min(
                        range(len(edge_waypoints)),
                        key=lambda index: _distance(source, edge_waypoints[index]),
                    )
                    if source_index < minimum_change_index:
                        continue
                    try:
                        candidate_connector, candidate_target = (
                            self._build_lane_change_connector(outgoing, source)
                        )
                    except RoutePlanningError:
                        continue
                    end_index = source_index
                    connector = candidate_connector
                    connector_target = candidate_target
                    break
                if not connector:
                    raise RoutePlanningError(
                        "ROUTE_LANE_CHANGE_UNAVAILABLE",
                        f"no complete legal {outgoing.side.lower()} lane-change corridor "
                        f"from edge {edge_index} to {outgoing.target_edge_index}",
                        context={
                            "source_edge_index": edge_index,
                            "target_edge_index": outgoing.target_edge_index,
                        },
                    )
            if start_index > end_index:
                target_edge_index = (
                    outgoing.target_edge_index
                    if outgoing is not None else edge_index
                )
                raise RoutePlanningError(
                    "ROUTE_LANE_CHANGE_SEQUENCE_INVALID",
                    f"lane-change sequence reverses progress on edge {edge_index}",
                    context={
                        "source_edge_index": edge_index,
                        "target_edge_index": target_edge_index,
                    },
                )
            for waypoint in edge_waypoints[start_index:end_index + 1]:
                if assembled and _visit_key(waypoint) == _visit_key(assembled[-1]):
                    continue
                assembled.append(waypoint)
            for waypoint in connector[1:]:
                if assembled and _distance(waypoint, assembled[-1]) <= 1e-6:
                    assembled[-1] = waypoint
                else:
                    assembled.append(waypoint)
            incoming_waypoint = connector_target
        start_index = min(range(len(assembled)), key=lambda index: _distance(start, assembled[index]))
        destination_index = min(
            range(start_index, len(assembled)),
            key=lambda index: _distance(destination, assembled[index]),
        )
        selected = [start, *assembled[start_index + 1:destination_index], destination]
        deduplicated: list[Any] = []
        for waypoint in selected:
            if deduplicated and _distance(waypoint, deduplicated[-1]) <= 1e-6:
                deduplicated[-1] = waypoint
            else:
                deduplicated.append(waypoint)
        if len(deduplicated) < 2:
            raise RoutePlanningError("ROUTE_ENDED_EARLY", "route contains fewer than two points")
        return tuple(deduplicated)

    def _build_lane_change_connector(
        self,
        transition: _LaneChangeTransition,
        source: Any,
    ) -> tuple[tuple[Any, ...], Any]:
        """Build a smooth, permission-checked connector between parallel lanes."""
        transition_length_m = max(18.0, self.sample_step_m * 8.0)
        step_count = max(8, math.ceil(transition_length_m / self.sample_step_m))
        source_identity = _lane_identity(source)
        target_identity = _lane_identity(
            min(
                transition.candidates,
                key=lambda pair: _distance(pair[0], source),
            )[1]
        )
        current = source
        connector: list[Any] = []
        target = None
        for index in range(step_count + 1):
            if index:
                candidates = tuple(
                    waypoint
                    for waypoint in current.next(self.sample_step_m)
                    if _is_driving_lane(waypoint)
                    and _lane_identity(waypoint) == source_identity
                    and _same_direction(current, waypoint)
                )
                if not candidates:
                    raise RoutePlanningError(
                        "ROUTE_LANE_CHANGE_UNAVAILABLE",
                        "source lane ends before the lane change can complete",
                    )
                current = min(candidates, key=lambda item: _distance(current, item))
            if bool(getattr(current, "is_junction", False)):
                raise RoutePlanningError(
                    "ROUTE_LANE_CHANGE_UNAVAILABLE",
                    "lane change would enter a junction",
                )
            if not _lane_change_allowed(current, transition.side):
                raise RoutePlanningError(
                    "ROUTE_LANE_CHANGE_UNAVAILABLE",
                    "lane marking stops permitting the requested lane change",
                )
            target = self._adjacent_lane(current, transition.side)
            if target is None or _lane_identity(target) != target_identity:
                raise RoutePlanningError(
                    "ROUTE_LANE_CHANGE_UNAVAILABLE",
                    "adjacent driving lane is not continuous through the transition",
                )
            source_location = current.transform.location
            target_location = target.transform.location
            ratio = index / step_count
            blend = ratio * ratio * (3.0 - 2.0 * ratio)
            source_yaw = _yaw(current)
            yaw = source_yaw + _wrap_degrees(_yaw(target) - source_yaw) * blend
            connector.append(_BlendedWaypoint(
                current,
                target,
                x_m=(1.0 - blend) * float(source_location.x)
                + blend * float(target_location.x),
                y_m=(1.0 - blend) * float(source_location.y)
                + blend * float(target_location.y),
                z_m=(1.0 - blend) * float(getattr(source_location, "z", 0.0))
                + blend * float(getattr(target_location, "z", 0.0)),
                yaw_deg=yaw,
                target_weight=blend,
            ))
        assert target is not None
        return tuple(connector), target

    def _build_global_route(
        self,
        waypoints: Sequence[Any],
        start: Any,
        destination: Any,
        target_speed_mps: float,
        *,
        allow_repeated_samples: bool = False,
    ) -> GlobalRoute:
        points = tuple(_xy(item) for item in waypoints)
        cumulative = cumulative_distances_m(points)
        gaps = tuple(math.dist(first, second) for first, second in zip(points, points[1:]))
        maximum_gap = max(gaps, default=0.0)
        if maximum_gap > self.maximum_gap_m:
            raise RoutePlanningError(
                "ROUTE_DISCONTINUOUS",
                f"maximum waypoint gap {maximum_gap:.2f} m exceeds {self.maximum_gap_m:.2f} m",
            )
        keys = [_visit_key(item) for item in waypoints]
        repeated = len(keys) - len(set(keys))
        if repeated and not allow_repeated_samples:
            raise RoutePlanningError(
                "ROUTE_LOOP_DETECTED", f"route repeats {repeated} waypoint samples",
            )
        if any(not _is_driving_lane(item) for item in waypoints):
            raise RoutePlanningError(
                "ROUTE_WRONG_LANE_TYPE", "route contains a non-driving waypoint",
            )
        destination_error = _distance(waypoints[-1], destination)
        if destination_error > self.finish_radius_m:
            raise RoutePlanningError(
                "ROUTE_ENDED_EARLY",
                f"destination error {destination_error:.2f} m exceeds finish radius",
            )
        samples = tuple(
            self._route_sample(waypoint, cumulative[index])
            for index, waypoint in enumerate(waypoints)
        )
        validation = RouteValidation(
            total_length_m=cumulative[-1],
            point_count=len(points),
            maximum_gap_m=maximum_gap,
            destination_error_m=destination_error,
            repeated_sample_count=repeated,
            junction_count=sum(
                1 for previous, current in zip(samples, samples[1:])
                if current.is_junction and not previous.is_junction
            ),
        )
        maximum_curvature = max(
            (_curvature(points, index) for index in range(len(points))),
            default=0.0,
        )
        lane_change_count = sum(
            1
            for previous, current in zip(waypoints, waypoints[1:])
            if getattr(previous, "road_id", None) == getattr(current, "road_id", None)
            and getattr(previous, "lane_id", None) != getattr(current, "lane_id", None)
        )
        route_fingerprint = "|".join(
            f"{x_m:.2f},{y_m:.2f}" for x_m, y_m in points
        ).encode("ascii")
        reference = RouteReference(
            points,
            maximum_curvature,
            target_speed_mps,
            route_id=f"topology-{hashlib.sha256(route_fingerprint).hexdigest()[:16]}",
            metadata={
                "planner": "CARLA_TOPOLOGY_ASTAR",
                "validation": validation.to_dict(),
                "lane_change_count": lane_change_count,
            },
        )
        return GlobalRoute(
            reference=reference,
            samples=samples,
            validation=validation,
            start_xy_m=_xy(start),
            destination_xy_m=_xy(destination),
            waypoints=tuple(waypoints),
        )

    @staticmethod
    def _route_sample(waypoint: Any, s_m: float) -> RouteSample:
        location = waypoint.transform.location
        left = RouteManager._adjacent_lane(waypoint, "LEFT")
        right = RouteManager._adjacent_lane(waypoint, "RIGHT")
        return RouteSample(
            x_m=float(location.x),
            y_m=float(location.y),
            z_m=float(getattr(location, "z", 0.0)),
            yaw_deg=_yaw(waypoint),
            s_m=float(s_m),
            road_id=getattr(waypoint, "road_id", None),
            section_id=getattr(waypoint, "section_id", None),
            lane_id=getattr(waypoint, "lane_id", None),
            is_junction=bool(getattr(waypoint, "is_junction", False)),
            left_lane_id=getattr(left, "lane_id", None),
            right_lane_id=getattr(right, "lane_id", None),
        )

    @staticmethod
    def _adjacent_lane(waypoint: Any, side: str) -> Any | None:
        getter = getattr(
            waypoint,
            "get_left_lane" if side == "LEFT" else "get_right_lane",
            None,
        )
        adjacent = getter() if callable(getter) else None
        if not _is_driving_lane(adjacent) or not _same_direction(waypoint, adjacent):
            return None
        return adjacent


__all__ = [
    "GlobalRoute",
    "RouteManager",
    "RoutePlacement",
    "RoutePlanningError",
    "RouteRecoveryDecision",
    "RouteRecoveryPolicy",
    "RouteRecoveryTracker",
    "RouteSample",
    "RouteState",
    "RouteValidation",
]
