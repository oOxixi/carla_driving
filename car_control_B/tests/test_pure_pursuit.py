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
