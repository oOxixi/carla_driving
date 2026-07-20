import math
from types import SimpleNamespace

import pytest

from integration.route_planner import (
    build_lane_change_route_reference,
    build_route_reference,
    command_turn_direction,
    select_topology_route_anchor,
)


class Waypoint:
    def __init__(self, x, y, yaw):
        self.transform = SimpleNamespace(
            location=SimpleNamespace(x=x, y=y), rotation=SimpleNamespace(yaw=yaw)
        )
        self.children = []
        self.lane_type = "Driving"
        self.is_junction = False
        self.left = None
        self.right = None

    def next(self, _step):
        return list(self.children)

    def get_left_lane(self):
        return self.left

    def get_right_lane(self):
        return self.right


class Map:
    def __init__(self, root):
        self.root = root

    def get_waypoint(self, _location, project_to_road=True):
        assert project_to_road
        return self.root


def _fork():
    root = Waypoint(0, 0, 0)
    left = Waypoint(2, -2, -45)
    straight = Waypoint(2, 0, 0)
    right = Waypoint(2, 2, 45)
    left.children = [Waypoint(3, -4, -70)]
    straight.children = [Waypoint(4, 0, 0)]
    right.children = [Waypoint(3, 4, 70)]
    root.children = [right, straight, left]
    return root


@pytest.mark.parametrize(("direction", "expected_y"), [("LEFT", -2.0), ("STRAIGHT", 0.0), ("RIGHT", 2.0)])
def test_route_selects_requested_first_branch(direction, expected_y):
    location = SimpleNamespace(x=0, y=0)
    route = build_route_reference(Map(_fork()), location, 5.0, turn_direction=direction, distance_m=6.0)
    assert route.points_xy_m[1][1] == expected_y
    assert route.curvature_per_m >= 0.0


def test_route_command_direction_is_conservative():
    assert command_turn_direction({"intent": "TURN", "parameters": {"direction": "LEFT"}}) == "LEFT"
    assert command_turn_direction({"intent": "SET_SPEED", "parameters": {"direction": "RIGHT"}}) == "STRAIGHT"
    assert command_turn_direction(None) == "STRAIGHT"


def test_route_rejects_invalid_parameters():
    location = SimpleNamespace(x=0, y=0)
    with pytest.raises(ValueError):
        build_route_reference(Map(_fork()), location, 5.0, turn_direction="UTURN")


def _parallel_lanes(length=100):
    center = [Waypoint(float(x), 0.0, 0.0) for x in range(length)]
    left = [Waypoint(float(x), -3.5, 0.0) for x in range(length)]
    right = [Waypoint(float(x), 3.5, 0.0) for x in range(length)]
    for lane in (center, left, right):
        for first, second in zip(lane, lane[1:]):
            first.children = [second]
    for current, left_item, right_item in zip(center, left, right):
        current.left = left_item
        current.right = right_item
    return center, left, right


@pytest.mark.parametrize(("direction", "expected_y"), [("LEFT", -3.5), ("RIGHT", 3.5)])
def test_lane_change_uses_same_direction_adjacent_driving_lane(direction, expected_y):
    center, _, _ = _parallel_lanes()
    route = build_lane_change_route_reference(
        Map(center[0]),
        SimpleNamespace(x=0.0, y=0.0),
        4.0,
        direction=direction,
        distance_m=60.0,
    )
    assert route.points_xy_m[0][1] == pytest.approx(0.0)
    assert route.points_xy_m[-1][1] == pytest.approx(expected_y)
    assert max(math.dist(a, b) for a, b in zip(route.points_xy_m, route.points_xy_m[1:])) < 2.0


def test_lane_change_rejects_opposite_direction_adjacent_lane():
    center, left, _ = _parallel_lanes()
    for current, opposite in zip(center, left):
        opposite.transform.rotation.yaw = 180.0
        current.left = opposite
    with pytest.raises(ValueError, match="same-direction"):
        build_lane_change_route_reference(
            Map(center[0]), SimpleNamespace(x=0.0, y=0.0), 4.0,
            direction="LEFT", distance_m=60.0,
        )


def test_topology_anchor_selection_avoids_signal_stop_points():
    first, _, _ = _parallel_lanes()
    second, _, _ = _parallel_lanes()
    for waypoint in second:
        waypoint.transform.location.y += 20.0

    class MultiMap:
        def get_waypoint(self, location, project_to_road=True):
            return first[0] if location.y < 10.0 else second[0]

    spawns = (
        SimpleNamespace(location=SimpleNamespace(x=0.0, y=0.0)),
        SimpleNamespace(location=SimpleNamespace(x=0.0, y=20.0)),
    )
    index, route, score = select_topology_route_anchor(
        MultiMap(), spawns, maneuver="FOLLOW", target_speed_mps=4.0,
        distance_m=60.0, forbidden_points_xy=((20.0, 0.0),),
    )
    assert index == 1
    assert route.points_xy_m[0][1] == pytest.approx(20.0)
    assert score < 500.0
