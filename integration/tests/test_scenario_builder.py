from types import SimpleNamespace

import pytest

from integration.scenario_builder import (
    ActorPlacementError,
    actor_resample_offsets,
    offset_actor_route_position,
    route_relative_carla_transform,
    route_relative_target_location,
    validate_actor_transform,
    validate_actor_route_coverage,
)


class _Location(SimpleNamespace):
    def __init__(self, x=0.0, y=0.0, z=0.0):
        super().__init__(x=x, y=y, z=z)


class _Rotation(SimpleNamespace):
    def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
        super().__init__(pitch=pitch, yaw=yaw, roll=roll)


class _Transform(SimpleNamespace):
    def __init__(self, location, rotation):
        super().__init__(location=location, rotation=rotation)


CARLA = SimpleNamespace(Location=_Location, Rotation=_Rotation, Transform=_Transform)


class _Waypoint:
    lane_type = "Driving"
    lane_width = 3.5

    def __init__(self, x: float, y: float, yaw: float, *, left=None, right=None):
        self.transform = _Transform(_Location(x, y, 1.0), _Rotation(yaw=yaw))
        self._left = left
        self._right = right

    def get_left_lane(self):
        return self._left

    def get_right_lane(self):
        return self._right


class _Map:
    def __init__(self, waypoint):
        self.waypoint = waypoint

    def get_waypoint(self, _location, project_to_road=True):
        assert project_to_road
        return self.waypoint


def test_actor_uses_route_tangent_and_lane_center() -> None:
    waypoint = _Waypoint(10.0, 5.0, 90.0)
    transform = route_relative_carla_transform(
        CARLA,
        _Map(waypoint),
        ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0)),
        {"spawn": {"x": 15.0, "y": 0.0, "z": 0.5, "yaw_deg": 0.0}},
    )
    assert (transform.location.x, transform.location.y, transform.location.z) == pytest.approx((10.0, 5.0, 1.5))
    assert transform.rotation.yaw == pytest.approx(90.0)


def test_explicit_adjacent_lane_uses_map_lane_relationship() -> None:
    left = _Waypoint(10.0, 1.5, 0.0)
    current = _Waypoint(10.0, 5.0, 0.0, left=left)
    transform = route_relative_carla_transform(
        CARLA,
        _Map(current),
        ((0.0, 0.0), (20.0, 0.0)),
        {
            "spawn": {"z": 0.5},
            "route_position": {"s_m": 10.0, "lane_relation": "LEFT_ADJACENT"},
        },
    )
    assert (transform.location.x, transform.location.y) == pytest.approx((10.0, 1.5))


def test_walker_target_uses_route_arc_length_on_a_curve() -> None:
    waypoint = _Waypoint(10.0, 8.0, 90.0)
    target = route_relative_target_location(
        CARLA,
        _Map(waypoint),
        ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0)),
        {
            "spawn": {"x": 10.0, "y": 2.0, "z": 0.5},
            "behavior": {"target_xy_m": [18.0, -2.0]},
        },
    )
    assert (target.x, target.y) == pytest.approx((12.0, 8.0))


def test_actor_outside_route_is_rejected_before_spawning() -> None:
    with pytest.raises(ValueError, match="exceeds route length"):
        validate_actor_route_coverage(
            ({"actor_id": "late", "spawn": {"x": 101.0, "y": 0.0}},),
            100.0,
        )


def test_legacy_lane_width_offset_uses_real_adjacent_lane_center() -> None:
    left = _Waypoint(10.0, 3.5, 0.0)
    current = _Waypoint(10.0, 0.0, 0.0, left=left)
    transform = route_relative_carla_transform(
        CARLA,
        _Map(current),
        ((0.0, 0.0), (20.0, 0.0)),
        {"type": "vehicle", "spawn": {"x": 10.0, "y": 3.5, "z": 0.5}},
    )
    assert (transform.location.x, transform.location.y) == pytest.approx((10.0, 3.5))


def test_resampling_moves_walker_spawn_and_target_together() -> None:
    actor = {
        "actor_id": "pedestrian",
        "type": "walker.pedestrian",
        "spawn": {"z": 0.5},
        "route_position": {"s_m": 20.0, "lateral_offset_m": 4.0},
        "behavior": {
            "target_route_position": {"s_m": 20.0, "lateral_offset_m": -4.0},
        },
    }
    moved = offset_actor_route_position(actor, longitudinal_m=3.0, lateral_m=0.5)
    assert moved["route_position"]["s_m"] == pytest.approx(23.0)
    assert moved["behavior"]["target_route_position"] == {
        "s_m": pytest.approx(23.0),
        "lateral_offset_m": pytest.approx(-3.5),
    }


def test_actor_resampling_is_seeded_and_reproducible() -> None:
    actor = {"actor_id": "lead"}
    first = actor_resample_offsets(actor, seed=123)
    assert first == actor_resample_offsets(actor, seed=123)
    assert first[0] == (0.0, 0.0)
    assert first != actor_resample_offsets(actor, seed=124)


def test_vehicle_legality_rejects_lane_marking_and_overlap() -> None:
    waypoint = _Waypoint(10.0, 0.0, 0.0)
    world_map = _Map(waypoint)
    on_marking = _Transform(_Location(10.0, 1.7, 1.5), _Rotation(yaw=0.0))
    with pytest.raises(ActorPlacementError, match="lane marking"):
        validate_actor_transform(
            world_map, on_marking, {"type": "vehicle"},
        )

    legal = _Transform(_Location(10.0, 0.0, 1.5), _Rotation(yaw=0.0))
    with pytest.raises(ActorPlacementError, match="overlaps"):
        validate_actor_transform(
            world_map,
            legal,
            {"type": "vehicle"},
            occupied_locations=(_Location(11.0, 0.0, 1.5),),
        )

