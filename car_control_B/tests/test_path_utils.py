import math

from car_control_B.path_utils import (
    compute_path_heading,
    find_lookahead_index,
    find_nearest_index,
    max_abs_curvature_ahead,
    resample_path,
    signed_cross_track_error,
    wrap_angle_rad,
)


def test_wrap_angle():
    assert -math.pi <= wrap_angle_rad(4 * math.pi + 0.2) <= math.pi
    assert abs(wrap_angle_rad(2 * math.pi + 0.1) - 0.1) < 1e-9


def test_nearest_and_lookahead():
    points = [(float(i), 0.0) for i in range(10)]
    idx = find_nearest_index(points, 2.2, 0.1)
    assert idx == 2
    target = find_lookahead_index(points, idx, (2.2, 0.0), 3.0)
    assert target >= 6


def test_cross_track_sign():
    points = [(0.0, 0.0), (10.0, 0.0)]
    assert signed_cross_track_error(points, 0, 1.0, 1.0) > 0
    assert signed_cross_track_error(points, 0, 1.0, -1.0) < 0


def test_cross_track_projects_onto_incoming_segment_at_corner() -> None:
    points = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]

    error = signed_cross_track_error(points, 1, 1.5, -0.2)

    assert error == -0.2


def test_resample_path_preserves_ends():
    points = [(0.0, 0.0), (10.0, 0.0)]
    sampled = resample_path(points, spacing_m=2.0)
    assert sampled[0] == (0.0, 0.0)
    assert sampled[-1] == (10.0, 0.0)
    assert len(sampled) >= 6


def test_heading():
    assert abs(compute_path_heading([(0.0, 0.0), (1.0, 0.0)], 0)) < 1e-9


def test_local_curvature_ignores_a_distant_turn_until_it_enters_horizon():
    points = [(float(x), 0.0) for x in range(101)]
    points += [(100.0, float(y)) for y in range(1, 31)]

    assert max_abs_curvature_ahead(points, 0, horizon_m=30.0) == 0.0
    assert max_abs_curvature_ahead(points, 90, horizon_m=30.0) > 0.0


def test_local_curvature_rejects_invalid_contract_values():
    points = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
    try:
        max_abs_curvature_ahead(points, 0, horizon_m=0.0)
    except ValueError as error:
        assert "horizon_m" in str(error)
    else:
        raise AssertionError("zero curvature horizon must be rejected")
