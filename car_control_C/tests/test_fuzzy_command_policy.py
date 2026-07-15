from __future__ import annotations

import pytest

from car_control_A import DrivingCommand, LongitudinalRequest, RuntimeVehicleState
from car_control_C import FuzzyCommandPolicy, FuzzyCommandPolicyConfig


def _request(*, sim_time: float = 5.0, speed: float = 8.0, requested: float = 12.0) -> LongitudinalRequest:
    vehicle = RuntimeVehicleState(1, sim_time, speed, 0.0, 0.0, 0.0, 0.0, "lane-1")
    return LongitudinalRequest(vehicle, requested, 0.0)


def _command(**changes: object) -> DrivingCommand:
    data: dict[str, object] = {"command_id": "voice-1", "received_at_s": 1.0,
        "expires_at_s": 10.0, "confidence": 0.95, "action": "SET_SPEED",
        "target_speed_mps": 12.0, "is_ambiguous": False, "confirmation_requested": False}
    data.update(changes)
    return DrivingCommand(**data)  # type: ignore[arg-type]


def test_clear_command_passes_through_without_policy_override() -> None:
    request = _request()
    result = FuzzyCommandPolicy().evaluate(_command(), request)
    assert not result.intervened
    assert not result.requires_confirmation
    assert result.request is request
    assert result.output is None


@pytest.mark.parametrize("changes", [
    {"confidence": 0.79}, {"is_ambiguous": True}, {"confirmation_requested": True},
])
def test_untrusted_command_requires_confirmation_and_never_keeps_cruise_target(changes: dict[str, object]) -> None:
    result = FuzzyCommandPolicy().evaluate(_command(**changes), _request())
    assert result.intervened and result.requires_confirmation
    assert result.request.requested_speed_mps == 0.0
    assert result.output is not None
    assert result.output.state == "CONFIRMING"
    assert result.output.target_speed_mps == 0.0
    assert result.output.control.throttle == 0.0
    assert result.output.control.brake > 0.0
    assert result.output.risk.ttc_s is None
    assert result.output.risk.emergency_brake_requested is False


def test_standstill_confirmation_holds_brake() -> None:
    result = FuzzyCommandPolicy().evaluate(_command(is_ambiguous=True), _request(speed=0.1))
    assert result.output is not None
    assert result.output.state == "HOLD"
    assert result.output.control.brake == FuzzyCommandPolicyConfig().hold_brake


def test_low_confidence_preserves_low_ttc_risk_and_escalates_local_brake() -> None:
    request = LongitudinalRequest(_request().vehicle, 12.0, 0.0, None, 2.0, 4.0)
    config = FuzzyCommandPolicyConfig(emergency_brake=0.9)
    result = FuzzyCommandPolicy(config).evaluate(_command(confidence=0.1), request)
    assert result.request.requested_speed_mps == 0.0
    assert result.output is not None
    assert result.output.state == "EMERGENCY_BRAKE"
    assert result.output.risk.ttc_s == 0.5
    assert result.output.risk.emergency_brake_requested is True
    assert result.output.control.brake >= 0.9


def test_expired_command_is_explicitly_rejected_and_stops() -> None:
    result = FuzzyCommandPolicy().evaluate(_command(expires_at_s=5.0), _request(sim_time=5.0))
    assert result.intervened and not result.requires_confirmation
    assert result.request.requested_speed_mps == 0.0
    assert result.output is not None and result.output.state == "REJECTED"
    assert result.feedback is not None and result.feedback.status.value == "EXPIRED"


def test_config_is_strict_and_round_trips() -> None:
    config = FuzzyCommandPolicyConfig(confidence_threshold=0.7, comfort_decel_mps2=2.0)
    assert FuzzyCommandPolicyConfig.from_dict(config.to_dict()) == config
    with pytest.raises(TypeError):
        FuzzyCommandPolicyConfig(hold_brake=True)
    with pytest.raises(ValueError):
        FuzzyCommandPolicyConfig(hold_brake=0.0)
    with pytest.raises(ValueError):
        FuzzyCommandPolicyConfig(comfort_decel_mps2=6.0, max_decel_mps2=5.0)
    with pytest.raises(ValueError):
        FuzzyCommandPolicyConfig.from_dict({"schema_version": "1.0"})
