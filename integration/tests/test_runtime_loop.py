from car_control_A import RuntimeVehicleState
from car_control_A.routing import RouteReference
from car_control_B.pure_pursuit import PurePursuitController

from integration import ControlRuntime, PerceptionFrame


def _vehicle(frame=1, time=0.05):
    return RuntimeVehicleState(frame=frame, sim_time_s=time, speed_mps=0.0, x_m=0.0, y_m=0.0, z_m=0.0,
                               yaw_deg=0.0, lane_id="lane_1")


def _route():
    return RouteReference(((0.0, 0.0), (10.0, 0.0), (20.0, 0.0)), 0.0, 5.0)


def _voice(intent="SET_SPEED", parameters=None):
    return {"schema_version": "1.0", "command_id": "voice-1", "source_text": "速度设为18公里每小时",
            "intent": intent, "parameters": parameters or {"speed": 18, "unit": "km/h"},
            "asr_confidence": 0.99, "intent_confidence": 0.99, "confidence": 0.99, "status": "valid",
            "ambiguity_type": "NONE", "confirm_required": False, "errors": [], "warnings": []}


def test_runtime_composes_voice_b_c_d_and_keeps_lane_id_safe_for_d():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    result = runtime.step(_vehicle(), PerceptionFrame(frame=1, sim_time_s=0.05), _route(), dt_s=0.05)
    assert result.safety_override is False
    assert result.final_control.brake == 0.0
    assert result.final_control.throttle > 0.0
    assert -1.0 <= result.final_control.steer <= 1.0


def test_runtime_preserves_d_emergency_stop_authority():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice("EMERGENCY_STOP", {}), now_s=0.05)
    result = runtime.step(_vehicle(), PerceptionFrame(frame=1, sim_time_s=0.05), _route(), dt_s=0.05)
    assert result.safety_override is True
    assert result.safety_reason == "COMMAND_EMERGENCY_STOP"
    assert result.final_control.throttle == 0.0
    assert result.final_control.brake == 1.0


def test_runtime_fails_closed_on_misaligned_perception():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    result = runtime.step(_vehicle(), PerceptionFrame(frame=2, sim_time_s=0.10), _route(), dt_s=0.05)
    assert result.safety_override is True
    assert result.safety_reason == "INTEGRATION_FAILURE"
    assert result.final_control.brake == 1.0


def test_expired_voice_command_cannot_retain_propulsion_authority():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    expired_vehicle = _vehicle(frame=2, time=3.05)
    result = runtime.step(expired_vehicle, PerceptionFrame(frame=2, sim_time_s=3.05), _route(), dt_s=0.05)
    assert result.safety_override is True
    assert result.safety_reason == "WATCHDOG_ALERT"
    assert result.final_control.throttle == 0.0
    assert result.final_control.brake == 1.0
