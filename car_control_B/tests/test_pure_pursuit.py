import math

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


def test_target_behind_ego_is_invalid_instead_of_silent_zero_steer():
    controller = _controller()
    vehicle = VehiclePose(10.0, 0.0, 0.0, 5.0)
    reference = RouteReference(points_xy_m=[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    out = controller.step(vehicle, reference)
    assert out.status == "INVALID"
    assert out.reason == "TARGET_BEHIND_EGO"
    assert out.steer == 0.0


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
