from __future__ import annotations

import math

from car_control_A import LongitudinalRequest, RuntimeVehicleState, SignalState, TrafficConstraint
from car_control_C import (
    FollowingController,
    LongitudinalController,
    LongitudinalParameters,
    SpeedPID,
    SpeedPlanner,
    SpeedPlannerParameters,
    TrafficRulePlanner,
)
from car_control_C.stop_controller import StopParameters


def vehicle(speed: float = 0.0) -> RuntimeVehicleState:
    return RuntimeVehicleState(1, 1.0, speed, 0.0, 0.0, 0.0, 0.0, "lane-1")


def request(*, speed: float = 0.0, requested: float = 10.0, curvature: float = 0.0,
            traffic: TrafficConstraint | None = None, lead: float | None = None,
            closing: float | None = None) -> LongitudinalRequest:
    return LongitudinalRequest(vehicle(speed), requested, curvature, traffic, lead, closing)


def test_pid_anti_windup_and_reset_on_target_step() -> None:
    pid = SpeedPID(kp=1.0, ki=4.0, kd=0.0, integral_limit=0.2, accel_min_mps2=-3.0, accel_max_mps2=2.0)
    for _ in range(20):
        assert pid.step(20.0, 0.0, 0.1) <= 2.0
    assert abs(pid.integral) <= 0.2
    pid.step(0.0, 20.0, 0.1)
    assert abs(pid.integral) <= 0.2


def test_control_is_mutually_exclusive_and_rate_limited() -> None:
    controller = LongitudinalController(LongitudinalParameters(max_control_delta_per_s=0.2))
    first = controller.step(request(speed=0.0, requested=20.0), 0.1)
    assert first.control.throttle > 0.0 and first.control.brake == 0.0
    assert first.control.throttle <= 0.02 + 1e-9
    second = controller.step(request(speed=20.0, requested=0.0), 0.1)
    assert not (second.control.throttle > 0.0 and second.control.brake > 0.0)
    assert second.control.brake <= 0.02 + 1e-9


def test_curvature_speed_constraint_limits_target() -> None:
    controller = LongitudinalController(LongitudinalParameters(max_lateral_accel_mps2=2.0))
    output = controller.step(request(requested=30.0, curvature=0.5), 0.1)
    assert output.target_speed_mps <= math.sqrt(2.0 / 0.5) + 1e-9


def test_hard_curve_cap_is_not_relaxed_by_command_ramp() -> None:
    controller = LongitudinalController(LongitudinalParameters(max_lateral_accel_mps2=2.0))
    output = controller.step(request(speed=20.0, requested=30.0, curvature=0.5), 0.1)
    assert output.target_speed_mps <= 2.0


def test_unreachable_red_stop_uses_visible_maximum_brake_fallback() -> None:
    controller = LongitudinalController()
    output = controller.step(request(speed=10.0, traffic=TrafficConstraint(SignalState.RED, 2.0)), 0.1)
    assert output.control.throttle == 0.0
    assert output.control.brake == 1.0
    assert output.reason == "stop_unreachable_fallback"


def test_stop_controller_reaches_and_holds_brake() -> None:
    controller = LongitudinalController(LongitudinalParameters(hold_brake=0.6))
    traffic = TrafficConstraint(SignalState.RED, 0.1, 15.0)
    output = controller.step(request(speed=0.0, traffic=traffic), 0.1)
    assert output.state == "HOLD"
    assert output.control.throttle == 0.0
    assert output.control.brake >= 0.6


def test_stop_controller_has_all_four_phases_and_creep_cap() -> None:
    controller = LongitudinalController()
    assert controller.stop_controller.state_for(8.0, None).value == "CRUISE"
    assert controller.stop_controller.state_for(8.0, 20.0).value == "DECELERATE"
    assert controller.stop_controller.state_for(1.0, 1.0).value == "CREEP"
    assert controller.stop_controller.state_for(0.1, 0.1).value == "HOLD"
    output = controller.step(request(speed=1.0, traffic=TrafficConstraint(SignalState.RED, 1.0)), 0.1)
    assert output.state == "CREEP"
    assert output.target_speed_mps <= controller.stop_controller.parameters.creep_speed_mps


def test_following_gap_and_ttc_emergency_request() -> None:
    following = FollowingController()
    risk = following.risk(ego_speed_mps=15.0, lead_distance_m=5.0, closing_speed_mps=10.0)
    assert risk.desired_gap_m > 5.0
    assert risk.ttc_s == 0.5
    assert risk.emergency_brake_requested


def test_non_closing_lead_has_no_ttc_and_multi_constraint_minimum() -> None:
    controller = LongitudinalController()
    output = controller.step(request(speed=10.0, requested=30.0, curvature=0.2,
        traffic=TrafficConstraint(SignalState.GREEN, None, 4.0), lead=100.0, closing=-2.0), 0.1)
    assert output.risk.ttc_s is None
    assert output.target_speed_mps <= 4.0


def test_traffic_lights_red_yellow_green_and_unknown() -> None:
    planner = TrafficRulePlanner()
    assert planner.stop_required(TrafficConstraint(SignalState.RED, 20.0))
    assert planner.stop_required(TrafficConstraint(SignalState.YELLOW, 20.0))
    assert not planner.stop_required(TrafficConstraint(SignalState.GREEN, 20.0))
    assert planner.stop_required(TrafficConstraint(SignalState.UNKNOWN, 20.0))


def test_red_yellow_and_unknown_constrain_running_controller() -> None:
    for signal in (SignalState.RED, SignalState.YELLOW, SignalState.UNKNOWN):
        output = LongitudinalController().step(request(speed=5.0, traffic=TrafficConstraint(signal, 5.0)), 0.1)
        assert output.state in {"DECELERATE", "CREEP", "HOLD"}
        assert output.target_speed_mps < 5.0


def test_control_output_serializes_and_actuator_transition_stays_exclusive() -> None:
    controller = LongitudinalController(LongitudinalParameters(max_control_delta_per_s=1.0))
    accelerating = controller.step(request(speed=0.0, requested=10.0), 0.1)
    braking = controller.step(request(speed=10.0, requested=0.0), 0.1)
    assert accelerating.control.to_dict()["throttle"] > 0.0
    assert braking.control.throttle == 0.0
    assert braking.control.brake <= 0.1 + 1e-9
    assert braking.to_dict()["risk"]["schema_version"] == "1.0"


def test_invalid_parameters_are_rejected() -> None:
    import pytest
    with pytest.raises(ValueError):
        LongitudinalController(LongitudinalParameters(max_control_delta_per_s=0.0))
    with pytest.raises(ValueError):
        LongitudinalParameters(hold_brake=0.0)
    with pytest.raises(ValueError):
        StopParameters(hold_brake=0.0)


def test_public_parameters_and_step_reject_bool_nan_and_infinity() -> None:
    import pytest
    with pytest.raises(TypeError):
        LongitudinalParameters(max_accel_mps2=True)
    with pytest.raises(ValueError):
        LongitudinalParameters(max_decel_mps2=0.0)
    with pytest.raises(ValueError):
        SpeedPlannerParameters(max_lateral_accel_mps2=float("nan"))
    with pytest.raises(ValueError):
        SpeedPID(accel_max_mps2=float("inf"))
    with pytest.raises(TypeError):
        SpeedPID().step(1.0, 0.0, True)
    with pytest.raises(ValueError):
        SpeedPlanner().plan(request(), float("inf"))


def test_controller_reset_removes_previous_braking_and_target_history() -> None:
    controller = LongitudinalController(LongitudinalParameters(max_control_delta_per_s=1.0))
    controller.step(request(speed=10.0, traffic=TrafficConstraint(SignalState.RED, 2.0)), 0.1)
    assert controller._last_brake == 1.0
    controller.reset()
    assert controller._last_brake == 0.0
    assert controller.speed_planner._previous_target is None
    fresh = controller.step(request(speed=0.0, requested=10.0), 0.1)
    assert fresh.control.throttle <= 0.1 + 1e-9
    assert fresh.control.brake == 0.0
