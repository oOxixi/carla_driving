"""Generic CARLA scenario placement built on route-relative geometry."""
from __future__ import annotations

from copy import deepcopy
import math
import random
from typing import Any, Mapping, Sequence

from .route_geometry import actor_route_coordinates, offset_route_pose, route_pose_at_s
from .route_planner import select_heading_compatible_waypoint


_LANE_RELATIONS = frozenset({
    "CURRENT", "ORIGINAL", "LEFT_ADJACENT", "RIGHT_ADJACENT",
})


class ActorPlacementError(RuntimeError):
    """A route-relative actor candidate is not legal on the current map."""


def _wrap_degrees(value: float) -> float:
    return (float(value) + 180.0) % 360.0 - 180.0


def _is_vehicle(actor_spec: Mapping[str, object]) -> bool:
    return str(actor_spec.get("type", "vehicle")).strip().lower() == "vehicle"


def _lane_width_m(waypoint: Any) -> float:
    value = float(getattr(waypoint, "lane_width", 3.5))
    return value if math.isfinite(value) and value > 0.5 else 3.5


def _same_direction(base: Any, target: Any, *, tolerance_deg: float = 45.0) -> bool:
    base_yaw = float(base.transform.rotation.yaw)
    target_yaw = float(target.transform.rotation.yaw)
    return abs(_wrap_degrees(target_yaw - base_yaw)) <= tolerance_deg


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
    if not _same_direction(base, target):
        raise RuntimeError(
            f"scenario actor target {relation.lower()} lane runs in the opposite direction"
        )
    return target


def _legacy_vehicle_lane(
    world_map: Any,
    base: Any,
    lateral_m: float,
) -> tuple[Any, float]:
    """Convert legacy lane-width offsets into topology lane relations.

    Older JSON files used ``spawn.y = +/-3.5`` to mean an adjacent lane.  On
    curves that places the vehicle on a marking because the offset is applied
    after projecting the route point.  Walk the real CARLA lane graph and keep
    only the residual in-lane offset instead.
    """
    target = base
    residual = float(lateral_m)
    for _ in range(3):
        width = _lane_width_m(target)
        if abs(residual) < width * 0.75:
            break
        relation = "LEFT_ADJACENT" if residual > 0.0 else "RIGHT_ADJACENT"
        next_lane = _target_lane_waypoint(world_map, target, relation)
        residual -= math.copysign(width, residual)
        target = next_lane
    return target, residual


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
        if actor_spec.get("route_position") is None and _is_vehicle(actor_spec):
            target, lateral_m = _legacy_vehicle_lane(
                world_map, target, lateral_m,
            )
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


def offset_actor_route_position(
    actor_spec: Mapping[str, object],
    *,
    longitudinal_m: float = 0.0,
    lateral_m: float = 0.0,
) -> dict[str, object]:
    """Return a copy with route offsets applied to either schema generation."""
    result = dict(actor_spec)
    position = actor_spec.get("route_position")
    if isinstance(position, Mapping):
        updated = dict(position)
        updated["s_m"] = max(
            0.0,
            float(updated.get("s_m", 0.0)) + float(longitudinal_m),
        )
        updated["lateral_offset_m"] = (
            float(updated.get("lateral_offset_m", 0.0)) + float(lateral_m)
        )
        result["route_position"] = updated
    else:
        spawn = actor_spec.get("spawn", {})
        if not isinstance(spawn, Mapping):
            raise TypeError("scenario actor spawn must be an object")
        updated = dict(spawn)
        updated["x"] = max(
            0.0,
            float(updated.get("x", 0.0)) + float(longitudinal_m),
        )
        updated["y"] = float(updated.get("y", 0.0)) + float(lateral_m)
        result["spawn"] = updated
    def shift_progress_triggers(value: object) -> object:
        copied = deepcopy(value)

        def visit(node: object) -> None:
            if isinstance(node, dict):
                if str(node.get("type", "")).lower() == "route_progress_greater_than_m":
                    node["value"] = max(
                        0.0,
                        float(node.get("value", 0.0)) + float(longitudinal_m),
                    )
                for child in node.values():
                    visit(child)
            elif isinstance(node, (list, tuple)):
                for child in node:
                    visit(child)

        visit(copied)
        return copied

    spawn_trigger = actor_spec.get("spawn_trigger")
    if isinstance(spawn_trigger, Mapping):
        result["spawn_trigger"] = shift_progress_triggers(spawn_trigger)

    behavior = actor_spec.get("behavior")
    if isinstance(behavior, Mapping):
        updated_behavior = shift_progress_triggers(behavior)
        assert isinstance(updated_behavior, dict)
        target = behavior.get("target_route_position")
        if isinstance(target, Mapping):
            updated_target = dict(target)
            updated_target["s_m"] = max(
                0.0,
                float(updated_target.get("s_m", 0.0)) + float(longitudinal_m),
            )
            updated_target["lateral_offset_m"] = (
                float(updated_target.get("lateral_offset_m", 0.0))
                + float(lateral_m)
            )
            updated_behavior["target_route_position"] = updated_target
        else:
            target_xy = behavior.get("target_xy_m")
            if isinstance(target_xy, (list, tuple)) and len(target_xy) == 2:
                updated_behavior["target_xy_m"] = [
                    max(0.0, float(target_xy[0]) + float(longitudinal_m)),
                    float(target_xy[1]) + float(lateral_m),
                ]
        result["behavior"] = updated_behavior
    return result


def actor_resample_offsets(
    actor_spec: Mapping[str, object],
    *,
    seed: int,
    max_attempts: int = 17,
) -> tuple[tuple[float, float], ...]:
    """Return deterministic, reproducible nearby samples for failed spawns."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    actor_id = str(actor_spec.get("actor_id", "actor"))
    stable_actor_key = sum((index + 1) * ord(char) for index, char in enumerate(actor_id))
    rng = random.Random(int(seed) ^ stable_actor_key)
    candidates = [(0.0, 0.0)]
    for distance_m in (2.0, 4.0, 6.0, 8.0, 12.0, 20.0, 40.0, 60.0):
        signs = [1.0, -1.0]
        rng.shuffle(signs)
        candidates.extend((sign * distance_m, 0.0) for sign in signs)
    return tuple(candidates[:max_attempts])


def validate_actor_transform(
    world_map: Any,
    transform: Any,
    actor_spec: Mapping[str, object],
    *,
    occupied_locations: Sequence[Any] = (),
) -> None:
    """Reject off-lane, misaligned, buried, or overlapping actor candidates."""
    location = transform.location
    rotation = transform.rotation
    values = (
        float(location.x), float(location.y), float(location.z),
        float(rotation.yaw),
    )
    if any(not math.isfinite(value) for value in values):
        raise ActorPlacementError("candidate transform contains a non-finite value")

    projected = world_map.get_waypoint(location, project_to_road=True)
    if projected is None:
        raise ActorPlacementError("candidate cannot be projected to a CARLA waypoint")
    actor_type = str(actor_spec.get("type", "vehicle")).strip().lower()
    if actor_type == "vehicle":
        lane_type = str(getattr(projected, "lane_type", "Driving")).rsplit(".", 1)[-1].upper()
        if lane_type != "DRIVING":
            raise ActorPlacementError(f"vehicle candidate is on {lane_type}, not DRIVING")
        road_location = projected.transform.location
        centre_error_m = math.hypot(
            float(location.x) - float(road_location.x),
            float(location.y) - float(road_location.y),
        )
        if centre_error_m > max(0.35, _lane_width_m(projected) * 0.45):
            raise ActorPlacementError(
                f"vehicle candidate is too close to a lane marking: centre_error={centre_error_m:.2f}m"
            )
        heading_error = abs(_wrap_degrees(
            float(rotation.yaw) - float(projected.transform.rotation.yaw)
        ))
        if heading_error > 30.0:
            raise ActorPlacementError(
                f"vehicle yaw is not aligned with its lane: error={heading_error:.1f}deg"
            )

    road_z = float(projected.transform.location.z)
    if float(location.z) < road_z - 0.1 or float(location.z) > road_z + 3.0:
        raise ActorPlacementError(
            f"candidate height is invalid: z={float(location.z):.2f}, road_z={road_z:.2f}"
        )
    minimum_separation_m = 2.5 if actor_type == "vehicle" else 0.65
    for occupied in occupied_locations:
        separation_m = math.sqrt(
            (float(location.x) - float(occupied.x)) ** 2
            + (float(location.y) - float(occupied.y)) ** 2
            + (float(location.z) - float(occupied.z)) ** 2
        )
        if separation_m < minimum_separation_m:
            raise ActorPlacementError(
                f"candidate overlaps another actor: separation={separation_m:.2f}m"
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
    "ActorPlacementError",
    "actor_resample_offsets",
    "offset_actor_route_position",
    "route_relative_carla_transform",
    "route_relative_target_location",
    "validate_actor_transform",
    "validate_actor_route_coverage",
]
