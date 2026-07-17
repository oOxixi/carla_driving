from car_control_B.schemas import RouteReference, VehiclePose
from car_control_B.stanley import StanleyController, StanleyParams


def _controller():
    return StanleyController(StanleyParams(max_steer_delta_per_step=1.0))


def _ref():
    return RouteReference(points_xy_m=[(float(i), 0.0) for i in range(50)], target_speed_mps=5.0)


def test_stanley_right_of_path_turns_left():
    out = _controller().step(VehiclePose(0.0, 1.0, 0.0, 5.0), _ref())
    assert out.steer < 0


def test_stanley_left_of_path_turns_right():
    out = _controller().step(VehiclePose(0.0, -1.0, 0.0, 5.0), _ref())
    assert out.steer > 0
