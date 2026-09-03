import math

import pytest

from integration.route_geometry import (
    actor_route_coordinates,
    evaluate_route_quality,
    offset_route_pose,
    project_route_progress_m,
    route_pose_at_s,
)


def test_route_pose_follows_curve_instead_of_initial_ego_tangent() -> None:
    points = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0))
    pose = route_pose_at_s(points, 15.0)
    assert (pose.x_m, pose.y_m, pose.yaw_deg) == pytest.approx((10.0, 5.0, 90.0))


def test_positive_lateral_offset_uses_route_local_right_axis() -> None:
    pose = offset_route_pose(route_pose_at_s(((0.0, 0.0), (0.0, 10.0)), 5.0), 2.0)
    assert (pose.x_m, pose.y_m) == pytest.approx((-2.0, 5.0))


def test_legacy_actor_xy_is_interpreted_as_route_s_and_lateral_offset() -> None:
    values = actor_route_coordinates({
        "spawn": {"x": 42.0, "y": 3.5, "z": 0.6, "yaw_deg": 5.0},
    })
    assert values == pytest.approx((42.0, 3.5, 0.6, 5.0))


def test_explicit_route_position_supports_lane_semantics_without_breaking_spawn_height() -> None:
    values = actor_route_coordinates({
        "spawn": {"z": 0.75},
        "route_position": {"s_m": 80.0, "lateral_offset_m": -0.2, "lane_relation": "LEFT_ADJACENT"},
    })
    assert values == pytest.approx((80.0, -0.2, 0.75, 0.0))


def test_progress_projection_disambiguates_overlapping_return_segment() -> None:
    route = ((0.0, 0.0), (10.0, 0.0), (0.0, 0.0))
    assert project_route_progress_m(route, 5.0, 0.0, previous_s_m=2.0) == pytest.approx(5.0)
    assert project_route_progress_m(route, 5.0, 0.0, previous_s_m=12.0) == pytest.approx(15.0)


@pytest.mark.parametrize("offset", [-0.3, -0.1, 0.0, 0.1, 0.3])
def test_small_position_perturbations_preserve_monotonic_progress(offset: float) -> None:
    route = tuple((float(index), math.sin(index / 10.0)) for index in range(101))
    previous = 0.0
    for index in range(0, 101, 5):
        current = project_route_progress_m(
            route, float(index), math.sin(index / 10.0) + offset,
            previous_s_m=previous,
        )
        assert current >= previous
        previous = current


def test_route_quality_rejects_a_silent_short_route() -> None:
    quality = evaluate_route_quality(((0.0, 0.0), (50.0, 0.0)), 100.0)
    assert quality.reached_contract is False
    assert quality.actual_distance_m == pytest.approx(50.0)

