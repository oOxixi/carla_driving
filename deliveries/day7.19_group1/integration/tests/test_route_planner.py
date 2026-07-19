from types import SimpleNamespace

import pytest

from integration.route_planner import build_route_reference, command_turn_direction


class Waypoint:
    def __init__(self, x, y, yaw):
        self.transform = SimpleNamespace(
            location=SimpleNamespace(x=x, y=y), rotation=SimpleNamespace(yaw=yaw)
        )
        self.children = []

    def next(self, _step):
        return list(self.children)


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
