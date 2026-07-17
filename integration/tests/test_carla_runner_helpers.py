from argparse import Namespace
import math

import pytest

from car_control_B.schemas import RouteReference, VehiclePose

from integration.carla_perception import PerceptionTimeoutError
from integration.carla_runner import (
    _acceptance_lateral_controller,
    _load_command,
    _rejected_load_envelope,
    _scenario_completed,
    _speed_mps,
    _warm_up_sensor_bridge,
)
from integration.contracts import PerceptionFrame
from integration.voice_adapter import VoiceCommandAdapter


def _args(scenario):
    return Namespace(scenario=scenario, frames=100)


def test_voice_load_failure_becomes_rejected_no_op() -> None:
    envelope = _rejected_load_envelope(FileNotFoundError("missing.wav"))
    adapted = VoiceCommandAdapter().adapt(envelope, now_s=1.0)
    assert not adapted.control_authorized
    assert adapted.command.action == "NO_OP"
    assert adapted.feedback is not None


def test_load_command_rejects_non_object_json_before_runtime_logging(tmp_path) -> None:
    path = tmp_path / "command.json"
    path.write_text("[]", encoding="utf-8")
    args = Namespace(command_json=str(path), audio=None, test_command_ttl_s=None)
    with pytest.raises(TypeError, match="JSON root must be an object"):
        _load_command(args)


def test_sensor_warmup_retries_until_an_aligned_frame_arrives() -> None:
    class Session:
        def __init__(self):
            self.frame = 10

        def tick(self, timeout):
            self.frame += 1
            return self.frame

    class World:
        def __init__(self, session):
            self.session = session

        def get_snapshot(self):
            return Namespace(timestamp=Namespace(elapsed_seconds=self.session.frame * 0.05))

    class Bridge:
        def __init__(self):
            self.calls = 0

        def acquire(self, frame, sim_time_s, timeout_s):
            self.calls += 1
            if self.calls == 1:
                raise PerceptionTimeoutError("not ready")
            return object()

    session = Session()
    bridge = Bridge()
    _warm_up_sensor_bridge(session, World(session), bridge, attempts=3,
                           tick_timeout_s=60.0, sensor_timeout_s=0.5)
    assert bridge.calls == 2


def test_vehicle_speed_ignores_vertical_spawn_settling() -> None:
    velocity = Namespace(x=3.0, y=4.0, z=-9.8)
    assert _speed_mps(velocity) == pytest.approx(5.0)


def test_acceptance_lateral_tuning_limits_steer_and_rate() -> None:
    controller = _acceptance_lateral_controller()
    assert controller.params.steer_sign == 1.0
    assert controller.params.max_steer == pytest.approx(0.60)
    assert controller.params.max_steer_delta_per_step == pytest.approx(0.04)
    assert controller.params.min_lookahead_m >= 3.5


def test_carla_left_handed_closed_loop_converges_to_straight_route() -> None:
    controller = _acceptance_lateral_controller()
    reference = RouteReference([(float(x), 0.0) for x in range(100)])
    x, y, yaw, speed, dt = 0.0, 1.0, 0.0, 4.0, 0.05
    for frame in range(80):
        output = controller.step(VehiclePose(x, y, yaw, speed, frame=frame), reference)
        steer_angle = output.steer * controller.params.max_steer_angle_rad
        yaw += speed / controller.params.wheel_base_m * math.tan(steer_angle) * dt
        x += speed * math.cos(yaw) * dt
        y += speed * math.sin(yaw) * dt
    assert abs(y) < 0.25
    assert abs(y) < 1.0


def test_scenario_completion_uses_safety_acceptance_conditions() -> None:
    red = PerceptionFrame(100, 5.0, traffic_light="RED", distance_to_stop_line_m=0.8)
    assert _scenario_completed(_args("red_stop"), frames=100, final_speed_mps=0.1,
                               final_scene=red, min_gap_m=None, collision_seen=False)
    assert not _scenario_completed(_args("red_stop"), frames=100, final_speed_mps=0.1,
                                   final_scene=PerceptionFrame(100, 5.0, traffic_light="RED",
                                                               distance_to_stop_line_m=2.0),
                                   min_gap_m=None, collision_seen=False)
    assert _scenario_completed(_args("follow"), frames=100, final_speed_mps=2.0,
                               final_scene=None, min_gap_m=3.1, collision_seen=False)
    assert not _scenario_completed(_args("emergency"), frames=100, final_speed_mps=0.5,
                                   final_scene=None, min_gap_m=4.0, collision_seen=False)
