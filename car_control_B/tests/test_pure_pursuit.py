import math

import pytest

from car_control_A.routing import RouteReference as RuntimeRouteReference
from car_control_B.pure_pursuit import PurePursuitController, PurePursuitParams
from car_control_B.schemas import RouteReference, VehiclePose


def _controller():
    return PurePursuitController(PurePursuitParams(max_steer_delta_per_step=1.0))


def _ref():
    return RouteReference(points_xy_m=[(float(i), 0.0) for i in range(50)], target_speed_mps=5.0)


def test_center_on_straight_near_zero():
    out = _controller().step(VehiclePose(0.0, 0.0, 0.0, 5.0), _ref())
    assert abs(out.steer) < 1e-6


@pytest.mark.parametrize("angular_step", [0.025, 0.10, 0.20])
def test_circular_feedforward_is_invariant_to_waypoint_spacing(angular_step):
    radius = 20.0
    params = PurePursuitParams(
        base_lookahead_m=5.0, min_lookahead_m=5.0, max_lookahead_m=5.0,
        speed_gain_s=0.0, curvature_lookahead_gain=0.0, error_lookahead_gain=0.0,
        cross_track_gain=0.0, max_steer_delta_per_step=1.0,
    )
    points = [(radius * math.sin(i * angular_step), radius * (1.0 - math.cos(i * angular_step)))
              for i in range(15)]
    output = PurePursuitController(params).step(
        VehiclePose(0.0, 0.0, 0.0, 5.0), RouteReference(points_xy_m=points),
    )
    expected = math.atan(params.wheel_base_m / radius) / params.max_steer_angle_rad
    assert output.steer == pytest.approx(expected)


def test_short_route_end_uses_actual_chord_instead_of_requested_lookahead():
    params = PurePursuitParams(
        base_lookahead_m=10.0, min_lookahead_m=10.0, max_lookahead_m=10.0,
        cross_track_gain=0.0, max_steer_delta_per_step=1.0,
    )
    radius = 20.0
    points = [(radius * math.sin(a), radius * (1.0 - math.cos(a))) for a in (0.0, .05, .10)]
    output = PurePursuitController(params).step(
        VehiclePose(0., 0., 0., 3.), RouteReference(points_xy_m=points),
    )
    assert output.steer == pytest.approx(math.atan(params.wheel_base_m / radius) / params.max_steer_angle_rad)


def test_right_of_path_turns_left_negative_carla_sign():
    out = _controller().step(VehiclePose(0.0, 1.0, 0.0, 5.0), _ref())
    assert out.steer < 0
    assert out.cross_track_error_m > 0


def test_left_of_path_turns_right_positive_carla_sign():
    out = _controller().step(VehiclePose(0.0, -1.0, 0.0, 5.0), _ref())
    assert out.steer > 0
    assert out.cross_track_error_m < 0


def test_output_limited_to_range():
    out = _controller().step(VehiclePose(0.0, 20.0, 0.0, 5.0), _ref())
    assert -1.0 <= out.steer <= 1.0


def test_route_progress_reset_can_preserve_steering_rate_continuity() -> None:
    controller = PurePursuitController(PurePursuitParams(
        max_steer_delta_per_step=0.038,
        min_steer_delta_per_step=0.038,
        adaptive_max_steer_delta_per_step=0.038,
    ))
    first = controller.step(VehiclePose(0.0, -1.0, 0.0, 5.0), _ref())
    assert first.steer == pytest.approx(0.038)

    controller.reset(preserve_steer=True)
    second = controller.step(VehiclePose(0.0, 1.0, 0.0, 5.0), _ref())

    assert abs(second.steer - first.steer) <= 0.038


def test_steering_slew_rate_is_normalized_by_simulation_time() -> None:
    params = PurePursuitParams(
        max_steer_delta_per_step=0.038,
        min_steer_delta_per_step=0.038,
        adaptive_max_steer_delta_per_step=0.038,
    )
    at_20_hz = PurePursuitController(params)
    first_20_hz = at_20_hz.step(
        VehiclePose(0.0, -1.0, 0.0, 5.0, sim_time_s=1.0), _ref(),
    )
    second_20_hz = at_20_hz.step(
        VehiclePose(0.0, 1.0, 0.0, 5.0, sim_time_s=1.05), _ref(),
    )

    at_10_hz = PurePursuitController(params)
    first_10_hz = at_10_hz.step(
        VehiclePose(0.0, -1.0, 0.0, 5.0, sim_time_s=1.0), _ref(),
    )
    second_10_hz = at_10_hz.step(
        VehiclePose(0.0, 1.0, 0.0, 5.0, sim_time_s=1.1), _ref(),
    )

    assert first_20_hz.steer == pytest.approx(first_10_hz.steer)
    assert abs(second_20_hz.steer - first_20_hz.steer) == pytest.approx(0.038)
    assert abs(second_10_hz.steer - first_10_hz.steer) == pytest.approx(0.076)


def test_steering_rate_reference_period_must_be_positive() -> None:
    with pytest.raises(ValueError, match="steer_rate_reference_dt_s"):
        PurePursuitParams(steer_rate_reference_dt_s=0.0)


def test_target_behind_ego_is_invalid_instead_of_silent_zero_steer():
    controller = _controller()
    vehicle = VehiclePose(10.0, 0.0, 0.0, 5.0)
    reference = RouteReference(points_xy_m=[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    out = controller.step(vehicle, reference)
    assert out.status == "INVALID"
    assert out.reason == "TARGET_BEHIND_EGO"
    assert out.steer == 0.0


@pytest.mark.parametrize("side", [-1.0, 1.0])
def test_off_center_nearest_point_behind_ego_uses_local_forward_target(side):
    pose = VehiclePose(10.2, side * 4.0, side * 0.3, 5.0)
    out = _controller().step(pose, _ref())
    dx, dy = out.target_point_xy_m[0] - pose.x_m, out.target_point_xy_m[1] - pose.y_m
    assert math.cos(pose.yaw_rad) * dx + math.sin(pose.yaw_rad) * dy > 0.05
    assert out.status == "OK"
    assert out.target_index - out.nearest_index < 10
    assert out.steer * side < 0.0


def test_forward_target_search_does_not_skip_to_remote_overlapping_lap():
    points = [(float(i), 0.) for i in range(11)] + [(10., float(i)) for i in range(1, 31)]
    points += [(float(i), 30.) for i in range(11, 41)] + [(40., 0.), (50., 0.)]
    out = _controller().step(VehiclePose(12., 0., 0., 5.), RouteReference(points_xy_m=points))
    assert out.status == "INVALID"
    assert out.target_index < 20


def test_tight_local_curve_shortens_lookahead_without_affecting_straight() -> None:
    controller = _controller()
    straight = controller.step(VehiclePose(0.0, 0.0, 0.0, 5.0), _ref())
    curved_points = [
        (5.0 * math.sin(index * 0.1), 5.0 * (1.0 - math.cos(index * 0.1)))
        for index in range(20)
    ]
    curved = _controller().step(
        VehiclePose(0.0, 0.0, 0.0, 5.0),
        RouteReference(points_xy_m=curved_points, target_speed_mps=5.0),
    )

    assert curved.lookahead_distance_m < straight.lookahead_distance_m
    assert curved.lookahead_distance_m >= _controller().params.min_lookahead_m


def test_cross_track_feedback_reduces_inside_corner_steer() -> None:
    curved_points = [
        (5.0 * math.sin(index * 0.1), 5.0 * (1.0 - math.cos(index * 0.1)))
        for index in range(20)
    ]
    reference = RouteReference(points_xy_m=curved_points, target_speed_mps=5.0)
    vehicle = VehiclePose(0.0, 0.8, 0.0, 3.0)
    feed_forward_only = PurePursuitController(PurePursuitParams(
        cross_track_gain=0.0, max_steer_delta_per_step=1.0,
    )).step(vehicle, reference)
    with_feedback = PurePursuitController(PurePursuitParams(
        cross_track_gain=0.8, max_steer_delta_per_step=1.0,
    )).step(vehicle, reference)

    assert with_feedback.cross_track_error_m > 0.0
    assert with_feedback.steer < feed_forward_only.steer


def test_local_progress_does_not_jump_to_a_later_overlapping_lap() -> None:
    controller = PurePursuitController(PurePursuitParams(
        nearest_search_window=10,
        max_steer_delta_per_step=1.0,
    ))
    first_lap = [(float(index), 0.0) for index in range(21)]
    overlap = [(float(index), 0.0) for index in range(20, -1, -1)]
    reference = RouteReference(
        points_xy_m=[*first_lap, *overlap],
        target_speed_mps=5.0,
    )

    controller.step(VehiclePose(0.0, 0.0, 0.0, 5.0), reference)
    output = controller.step(VehiclePose(5.0, 0.0, 0.0, 5.0), reference)

    assert output.nearest_index == 5


def test_route_progress_is_restored_after_temporary_manoeuvre_route() -> None:
    controller = PurePursuitController(PurePursuitParams(
        nearest_search_window=2,
        route_reacquire_search_window=50,
        max_steer_delta_per_step=1.0,
    ))
    mission = RouteReference(
        points_xy_m=[(float(index), 0.0) for index in range(100)],
        target_speed_mps=5.0,
    )
    manoeuvre = RouteReference(
        points_xy_m=[(20.0 + float(index), 3.5) for index in range(20)],
        target_speed_mps=4.0,
    )

    assert controller.step(VehiclePose(20.0, 0.0, 0.0, 5.0), mission).nearest_index == 20
    controller.step(VehiclePose(20.0, 3.5, 0.0, 4.0), manoeuvre)
    restored = controller.step(VehiclePose(60.0, 0.0, 0.0, 5.0), mission)

    assert restored.nearest_index == 60


def test_external_mission_progress_restores_beyond_reacquire_window() -> None:
    controller = PurePursuitController(PurePursuitParams(
        nearest_search_window=2,
        route_reacquire_search_window=20,
        max_steer_delta_per_step=1.0,
    ))
    mission = RouteReference(
        points_xy_m=[(float(index), 0.0) for index in range(200)],
        target_speed_mps=5.0,
    )
    manoeuvre = RouteReference(
        points_xy_m=[(20.0 + float(index), 3.5) for index in range(120)],
        target_speed_mps=4.0,
    )

    controller.step(VehiclePose(20.0, 0.0, 0.0, 5.0), mission)
    controller.step(VehiclePose(130.0, 3.5, 0.0, 4.0), manoeuvre)
    assert controller.synchronize_route_progress(mission, 130.0) == 130

    restored = controller.step(VehiclePose(130.0, 0.0, 0.0, 5.0), mission)

    assert restored.nearest_index == 130
    assert restored.status == "OK"


def test_small_frame_window_prevents_gradual_progress_jump_on_overlap() -> None:
    controller = PurePursuitController(PurePursuitParams(
        nearest_search_window=2,
        route_reacquire_search_window=50,
        max_steer_delta_per_step=1.0,
    ))
    reference = RouteReference(
        points_xy_m=[
            *((float(index), 0.0) for index in range(21)),
            *((float(index), 0.0) for index in range(20, -1, -1)),
        ],
        target_speed_mps=5.0,
    )

    output = None
    for frame in range(26):
        output = controller.step(
            VehiclePose(frame * 0.4, 0.0, 0.0, 5.0), reference,
        )

    assert output is not None
    assert output.nearest_index == 10


def test_step_any_reuses_adapted_geometry_for_runtime_route() -> None:
    controller = PurePursuitController(PurePursuitParams(
        nearest_search_window=2,
        max_steer_delta_per_step=1.0,
    ))
    first_pass = [(float(index), 0.10) for index in range(21)]
    closer_overlap = [(float(index), 0.0) for index in range(21)]
    reference = RuntimeRouteReference(
        points_xy_m=tuple([*first_pass, *closer_overlap]),
        curvature_per_m=0.0,
        target_speed_mps=5.0,
    )

    controller.step_any(VehiclePose(0.0, 0.10, 0.0, 5.0), reference)
    output = controller.step_any(VehiclePose(1.0, 0.04, 0.0, 5.0), reference)

    assert output.nearest_index == 1
