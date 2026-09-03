"""Generic CARLA scenario placement built on route-relative geometry."""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .route_geometry import actor_route_coordinates, offset_route_pose, route_pose_at_s
from .route_planner import select_heading_compatible_waypoint


_LANE_RELATIONS = frozenset({
    "CURRENT", "ORIGINAL", "LEFT_ADJACENT", "RIGHT_ADJACENT",
})


def _lane_relation(actor_spec: Mapping[str, object]) -> str:
    position = actor_spec.get("route_position")
    if not isinstance(position, Mapping):
        return "CURRENT"
    relation = str(position.get("lane_relation", "CURRENT")).strip().upper()
    if relation not in _LANE_RELATIONS:
        raise ValueError(f"unsupported route_position.lane_relation: {relation!r}")
    return relation


def _target_lane_waypoint(world_map: Any, base: Any, relation: str) -> Any:
    if relation in {"CURRENT", "ORIGINAL"}:
        return base
    getter_name = "get_left_lane" if relation == "LEFT_ADJACENT" else "get_right_lane"
    getter = getattr(base, getter_name, None)
    target = getter() if callable(getter) else None
    if target is None:
        raise RuntimeError(f"scenario actor requires unavailable {relation.lower()} lane")
    lane_type = str(getattr(target, "lane_type", "Driving")).rsplit(".", 1)[-1].upper()
    if lane_type != "DRIVING":
        raise RuntimeError(f"scenario actor target lane is not driving: {lane_type}")
    return target


def route_relative_carla_transform(
    carla_api: Any,
    world_map: Any,
    route_points_xy_m: Sequence[tuple[float, float]],
    actor_spec: Mapping[str, object],
    *,
    forward_offset_m: float = 0.0,
) -> Any:
    """Build a CARLA transform tied to route arc length and lane topology."""
    s_m, lateral_m, z_m, yaw_offset_deg = actor_route_coordinates(actor_spec)
    pose = route_pose_at_s(route_points_xy_m, s_m + float(forward_offset_m))
    base_location = carla_api.Location(x=pose.x_m, y=pose.y_m, z=0.0)
    route_transform = carla_api.Transform(
        base_location, carla_api.Rotation(yaw=pose.yaw_deg),
    )
    waypoint = select_heading_compatible_waypoint(world_map, route_transform)
    relation = _lane_relation(actor_spec)
    if waypoint is not None:
        target = _target_lane_waypoint(world_map, waypoint, relation)
        road_location = target.transform.location
        road_yaw = float(target.transform.rotation.yaw)
        road_pose = offset_route_pose(
            type(pose)(float(road_location.x), float(road_location.y), road_yaw, pose.s_m),
            lateral_m,
            yaw_offset_deg,
        )
        pitch = float(getattr(target.transform.rotation, "pitch", 0.0))
        roll = float(getattr(target.transform.rotation, "roll", 0.0))
        road_z = float(road_location.z)
    else:
        if relation not in {"CURRENT", "ORIGINAL"}:
            raise RuntimeError("cannot resolve adjacent lane without a CARLA waypoint")
        road_pose = offset_route_pose(pose, lateral_m, yaw_offset_deg)
        pitch = roll = road_z = 0.0
    return carla_api.Transform(
        carla_api.Location(
            x=road_pose.x_m,
            y=road_pose.y_m,
            z=road_z + max(0.0, z_m),
        ),
        carla_api.Rotation(pitch=pitch, yaw=road_pose.yaw_deg, roll=roll),
    )


def route_relative_target_location(
    carla_api: Any,
    world_map: Any,
    route_points_xy_m: Sequence[tuple[float, float]],
    actor_spec: Mapping[str, object],
) -> Any:
    """Resolve a walker's target with the same route frame as its spawn."""
    behavior = actor_spec.get("behavior", {})
    spawn = actor_spec.get("spawn", {})
    if not isinstance(behavior, Mapping) or not isinstance(spawn, Mapping):
        raise TypeError("scenario walker requires spawn and behavior objects")
    target = behavior.get("target_route_position")
    if target is None:
        target_xy = behavior.get("target_xy_m", [spawn.get("x", 0.0), spawn.get("y", 0.0)])
        if not isinstance(target_xy, (list, tuple)) or len(target_xy) != 2:
            raise TypeError("scenario walker target_xy_m must be [x, y]")
        target = {"s_m": target_xy[0], "lateral_offset_m": target_xy[1]}
    if not isinstance(target, Mapping):
        raise TypeError("target_route_position must be an object")
    synthetic = {
        "spawn": {
            "x": target.get("s_m", 0.0),
            "y": target.get("lateral_offset_m", 0.0),
            "z": spawn.get("z", 0.5),
            "yaw_deg": 0.0,
        },
        "route_position": dict(target),
    }
    return route_relative_carla_transform(
        carla_api, world_map, route_points_xy_m, synthetic,
    ).location


def validate_actor_route_coverage(
    actor_specs: Sequence[Mapping[str, object]],
    route_length_m: float,
) -> None:
    """Fail before CARLA mutation if an actor lies outside the route contract."""
    if not math.isfinite(float(route_length_m)) or route_length_m <= 0.0:
        raise ValueError("route_length_m must be finite and positive")
    for actor in actor_specs:
        s_m, _lateral, _z, _yaw = actor_route_coordinates(actor)
        if s_m > route_length_m + 1e-6:
            actor_id = actor.get("actor_id", "<unknown>")
            raise ValueError(
                f"scenario actor {actor_id!r} at s={s_m:.2f} m exceeds "
                f"route length {route_length_m:.2f} m"
            )


__all__ = [
    "route_relative_carla_transform",
    "route_relative_target_location",
    "validate_actor_route_coverage",
]
