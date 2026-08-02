import math

import pytest

from car_control_D.safety_supervisor import SafetyConfig, SafetySupervisor


def test_low_ttc_forces_stop():
    s = SafetySupervisor()
    decision = s.arbitrate(
        raw_control={"steer": 0.1, "throttle": 0.4, "brake": 0.0},
        vehicle_state={"speed_mps": 8.0},
        command={"schema_version": "1.0", "command_id": "c", "source_text": "前进", "intent": "FORWARD", "confidence": 0.95},
        risk={"ttc_s": 1.0},
    )
    assert decision.safety_override
    assert decision.final_control.brake == 1.0
    assert decision.reason == "LOW_TTC"


def test_slow_down_clear_command_passes():
    s = SafetySupervisor()
    decision = s.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.2, "brake": 0.0},
        vehicle_state={"speed_mps": 6.0, "front_distance_m": 30.0},
        command={"schema_version": "1.0", "command_id": "c", "source_text": "减速", "intent": "SLOW_DOWN", "confidence": 0.95},
        risk={"ttc_s": 10.0},
    )
    assert not decision.safety_override
    assert decision.final_control.throttle == 0.2


def test_unknown_command_held():
    s = SafetySupervisor()
    decision = s.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.4, "brake": 0.0},
        vehicle_state={},
        command={"schema_version": "1.0", "command_id": "c", "source_text": "随便开", "intent": "UNKNOWN", "confidence": 0.3},
        risk={},
    )
    assert decision.safety_override
    assert decision.reason == "COMMAND_REJECTED"


def test_close_front_obstacle_reason_is_auditable_as_emergency() -> None:
    decision = SafetySupervisor().arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.4, "brake": 0.0},
        vehicle_state={"speed_mps": 5.0, "front_distance_m": 2.0},
        command=None,
        risk={},
    )
    assert decision.reason == "EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE"


def test_red_light_guard_reason_identifies_red_light() -> None:
    decision = SafetySupervisor().arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.2, "brake": 0.0},
        vehicle_state={"speed_mps": 2.0, "traffic_light": "RED", "distance_to_stop_line_m": 0.5},
        command=None,
        risk={},
    )
    assert decision.reason == "RED_LIGHT_STOP_LINE_GUARD"


def test_red_light_guard_blocks_unbraked_coasting_and_holds_standstill() -> None:
    supervisor = SafetySupervisor()
    coasting = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.0, "brake": 0.0},
        vehicle_state={"speed_mps": 3.0, "traffic_light": "RED", "distance_to_stop_line_m": 5.0},
    )
    assert coasting.reason == "RED_LIGHT_STOP_LINE_GUARD"
    assert coasting.final_control.brake == 1.0

    stopped_without_hold = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.0, "brake": 0.0},
        vehicle_state={"speed_mps": 0.0, "traffic_light": "RED", "distance_to_stop_line_m": 2.0},
    )
    assert stopped_without_hold.reason == "RED_LIGHT_STOP_LINE_GUARD"

    held = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.0, "brake": 0.55},
        vehicle_state={"speed_mps": 0.0, "traffic_light": "RED", "distance_to_stop_line_m": 2.0},
    )
    assert not held.safety_override


@pytest.mark.parametrize(
    "kwargs",
    [
        {"low_ttc_s": math.nan},
        {"low_ttc_s": 3.0, "caution_ttc_s": 2.0},
        {"hold_brake": 1.1},
        {"max_lane_offset_m": 4.0, "severe_route_deviation_m": 3.0},
    ],
)
def test_safety_config_rejects_unsafe_values(kwargs) -> None:
    with pytest.raises(ValueError):
        SafetyConfig(**kwargs)


def test_malformed_sensor_and_watchdog_inputs_fail_closed() -> None:
    supervisor = SafetySupervisor()
    invalid_state = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.2, "brake": 0.0},
        vehicle_state={"speed_mps": float("nan")},
    )
    assert invalid_state.reason == "INVALID_VEHICLE_STATE"
    assert invalid_state.final_control.brake == 1.0

    invalid_watchdog = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.2, "brake": 0.0},
        vehicle_state={},
        watchdog_alerts=(123,),
    )
    assert invalid_watchdog.reason == "WATCHDOG_ALERT"
    assert invalid_watchdog.risk_metrics["watchdog_alerts"] == ["INVALID_WATCHDOG_ALERTS"]

    invalid_signal = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.2, "brake": 0.0},
        vehicle_state={"traffic_light": "BROKEN"},
    )
    assert invalid_signal.reason == "INVALID_VEHICLE_STATE"


def test_collision_and_red_light_violation_are_hard_stops() -> None:
    supervisor = SafetySupervisor()
    collision = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.2, "brake": 0.0},
        vehicle_state={"collision": True},
    )
    assert collision.reason == "COLLISION_DETECTED"
    assert collision.final_control.brake == 1.0

    violation = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.2, "brake": 0.0},
        vehicle_state={"red_light_violation": True},
    )
    assert violation.reason == "RED_LIGHT_VIOLATION_DETECTED"
    assert violation.final_control.brake == 1.0


def test_route_deviation_never_applies_low_speed_recovery_throttle() -> None:
    supervisor = SafetySupervisor()
    decision = supervisor.arbitrate(
        raw_control={"steer": -0.8, "throttle": 0.4, "brake": 0.0},
        vehicle_state={"speed_mps": 0.5, "route_deviation_m": 3.2},
        command=None,
        risk={},
    )
    assert decision.safety_override
    assert decision.reason == "ROUTE_DEVIATION_RECOVERY_STOP"
    assert decision.final_control.throttle == 0.0
    assert decision.final_control.brake >= supervisor.config.route_deviation_brake
    assert decision.final_control.steer == -supervisor.config.route_recovery_steer_limit


def test_route_recovery_brakes_above_recovery_speed() -> None:
    supervisor = SafetySupervisor()
    decision = supervisor.arbitrate(
        raw_control={"steer": 0.2, "throttle": 0.4, "brake": 0.0},
        vehicle_state={"speed_mps": 2.0, "route_deviation_m": 3.2},
        command=None,
        risk={},
    )
    assert decision.reason == "ROUTE_DEVIATION_RECOVERY_STOP"
    assert decision.final_control.throttle == 0.0
    assert decision.final_control.brake >= supervisor.config.caution_brake
    assert decision.final_control.steer == 0.2


def test_route_reference_prevents_false_lane_offset_stop_inside_junction() -> None:
    decision = SafetySupervisor().arbitrate(
        raw_control={"steer": 0.2, "throttle": 0.3, "brake": 0.0},
        vehicle_state={
            "speed_mps": 2.5,
            "lane_offset_m": 2.3,
            "route_deviation_m": 0.9,
        },
        command=None,
        risk={},
    )
    assert not decision.safety_override
    assert decision.reason == "NONE"
    assert decision.final_control.throttle == 0.3
    assert decision.final_control.steer == 0.2


def test_lane_offset_still_cautions_without_safe_route_confirmation() -> None:
    decision = SafetySupervisor().arbitrate(
        raw_control={"steer": 0.2, "throttle": 0.3, "brake": 0.0},
        vehicle_state={
            "speed_mps": 2.5,
            "lane_offset_m": 2.3,
            "route_deviation_m": 2.0,
        },
        command=None,
        risk={},
    )
    assert decision.safety_override
    assert decision.reason == "LANE_OFFSET_TOO_LARGE"
    assert decision.final_control.throttle == 0.0
