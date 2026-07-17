from car_control_A import RuntimeVehicleState
from car_control_A.routing import RouteReference
from car_control_B.pure_pursuit import PurePursuitController

from integration import ControlRuntime, PerceptionFrame


def _vehicle(frame=1, time=0.05, speed=0.0):
    return RuntimeVehicleState(frame=frame, sim_time_s=time, speed_mps=speed, x_m=0.0, y_m=0.0, z_m=0.0,
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
    assert result.raw_control is not None


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


def test_rejected_voice_is_no_op_and_does_not_replace_active_command():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    previous_speed = runtime.requested_speed_mps
    rejected = runtime.submit_voice(_voice("UNKNOWN", {}), now_s=0.10)
    assert not rejected.control_authorized
    assert runtime.requested_speed_mps == previous_speed
    result = runtime.step(_vehicle(frame=2, time=0.10),
                          PerceptionFrame(frame=2, sim_time_s=0.10), _route(), dt_s=0.05)
    assert result.final_control.throttle > 0.0
    assert any(item.status.value == "REJECTED" for item in result.feedback)


def test_confirmation_gated_complex_command_uses_fuzzy_safe_deceleration():
    runtime = ControlRuntime(PurePursuitController())
    adapted = runtime.submit_voice(_voice("CHANGE_LANE", {"direction": "LEFT"}), now_s=0.05)
    assert adapted.control_authorized and adapted.command.requires_confirmation
    result = runtime.step(_vehicle(speed=4.0), PerceptionFrame(frame=1, sim_time_s=0.05),
                          _route(), dt_s=0.05)
    assert result.longitudinal is not None
    assert result.longitudinal.state == "CONFIRMING"
    assert result.final_control.throttle == 0.0
    assert result.final_control.brake > 0.0


def test_normal_stop_uses_c_comfort_braking_but_emergency_stop_uses_d_full_brake():
    normal = ControlRuntime(PurePursuitController())
    normal.submit_voice(_voice("STOP", {}), now_s=0.05)
    normal_result = normal.step(_vehicle(speed=4.0), PerceptionFrame(frame=1, sim_time_s=0.05),
                                _route(), dt_s=0.05)
    assert normal_result.safety_reason == "NONE"
    assert 0.0 < normal_result.final_control.brake < 1.0

    emergency = ControlRuntime(PurePursuitController())
    emergency.submit_voice(_voice("EMERGENCY_STOP", {}), now_s=0.05)
    emergency_result = emergency.step(_vehicle(speed=4.0), PerceptionFrame(frame=1, sim_time_s=0.05),
                                      _route(), dt_s=0.05)
    assert emergency_result.safety_reason == "COMMAND_EMERGENCY_STOP"
    assert emergency_result.final_control.brake == 1.0


def test_stop_completion_is_reported_and_brake_hold_persists():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice("STOP", {}), now_s=0.05)
    first = runtime.step(_vehicle(), PerceptionFrame(frame=1, sim_time_s=0.05), _route(), dt_s=0.05)
    assert any(item.status.value == "SUCCEEDED" for item in first.feedback)
    second = runtime.step(_vehicle(frame=2, time=0.10), PerceptionFrame(frame=2, sim_time_s=0.10),
                          _route(), dt_s=0.05)
    assert second.final_control.throttle == 0.0
    assert second.final_control.brake >= 0.55


def test_watchdog_stop_is_latched_until_explicit_reset():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    alerted = runtime.step(_vehicle(), PerceptionFrame(frame=1, sim_time_s=0.05), _route(), dt_s=0.05,
                           watchdog_alerts=("SENSOR_TIMEOUT",))
    assert alerted.final_control.brake == 1.0 and runtime.safety_latched
    still_stopped = runtime.step(_vehicle(frame=2, time=0.10), PerceptionFrame(frame=2, sim_time_s=0.10),
                                 _route(), dt_s=0.05)
    assert still_stopped.final_control.brake == 1.0
    runtime.reset_safety_latch()
    assert not runtime.safety_latched


def test_low_confidence_command_can_be_confirmed_then_execute():
    runtime = ControlRuntime(PurePursuitController(), default_speed_mps=0.0)
    command = _voice()
    command["command_id"] = "confirm-speed"
    command["confidence"] = command["intent_confidence"] = 0.7
    runtime.submit_voice(command, now_s=0.05)
    before = runtime.step(_vehicle(speed=2.0), PerceptionFrame(frame=1, sim_time_s=0.05),
                          _route(), dt_s=0.05)
    assert before.longitudinal is not None and before.longitudinal.state == "CONFIRMING"

    assert runtime.confirm_voice("confirm-speed", approved=True, now_s=0.10) is None
    after = runtime.step(_vehicle(frame=2, time=0.15, speed=2.0),
                         PerceptionFrame(frame=2, sim_time_s=0.15), _route(), dt_s=0.05)
    assert after.longitudinal is not None and after.longitudinal.state != "CONFIRMING"
    assert runtime.requested_speed_mps == 5.0


def test_declined_confirmation_is_terminal_and_holds_vehicle():
    runtime = ControlRuntime(PurePursuitController())
    command = _voice()
    command["command_id"] = "decline-speed"
    command["confidence"] = command["intent_confidence"] = 0.7
    runtime.submit_voice(command, now_s=0.05)
    feedback = runtime.confirm_voice("decline-speed", approved=False, now_s=0.10)
    assert feedback is not None and feedback.status.value == "REJECTED"
    result = runtime.step(_vehicle(frame=2, time=0.15),
                          PerceptionFrame(frame=2, sim_time_s=0.15), _route(), dt_s=0.05)
    assert result.final_control.throttle == 0.0
    assert result.final_control.brake > 0.0


def test_confirmed_complex_command_fails_without_concrete_decision():
    runtime = ControlRuntime(PurePursuitController())
    command = _voice("TURN", {"direction": "LEFT"})
    command["command_id"] = "complex"
    runtime.submit_voice(command, now_s=0.05)
    feedback = runtime.confirm_voice("complex", approved=True, now_s=0.10)
    assert feedback is not None and feedback.status.value == "FAILED"
    result = runtime.step(_vehicle(frame=2, time=0.15),
                          PerceptionFrame(frame=2, sim_time_s=0.15), _route(), dt_s=0.05)
    assert result.final_control.throttle == 0.0
    assert result.final_control.brake > 0.0


def test_completed_set_speed_keeps_cruise_authority_without_stale_d_command():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    for frame in range(1, 4):
        result = runtime.step(
            _vehicle(frame=frame, time=frame * 0.05, speed=5.0),
            PerceptionFrame(frame=frame, sim_time_s=frame * 0.05), _route(), dt_s=0.05,
        )
    assert any(item.status.value == "SUCCEEDED" for item in result.feedback)
    cruising = runtime.step(_vehicle(frame=4, time=0.20, speed=4.5),
                            PerceptionFrame(frame=4, sim_time_s=0.20), _route(), dt_s=0.05)
    assert cruising.safety_reason == "NONE"
    assert cruising.final_control.brake == 0.0


def test_superseded_command_emits_terminal_feedback_for_audit():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    replacement = _voice("STOP", {})
    replacement["command_id"] = "voice-2"
    runtime.submit_voice(replacement, now_s=0.10)
    result = runtime.step(_vehicle(frame=2, time=0.10),
                          PerceptionFrame(frame=2, sim_time_s=0.10), _route(), dt_s=0.05)
    old = [item for item in result.feedback if item.command_id == "voice-1"]
    assert len(old) == 1
    assert old[0].status.value == "FAILED"


def test_outer_runtime_can_fail_active_command_explicitly():
    runtime = ControlRuntime(PurePursuitController())
    runtime.submit_voice(_voice(), now_s=0.05)
    feedback = runtime.fail_active(now_s=0.10, detail="CARLA disconnected")
    assert feedback is not None and feedback.status.value == "FAILED"
    assert runtime.active_command_id is None
    assert runtime.requested_speed_mps == 0.0
