from car_control_D.safety_supervisor import SafetySupervisor


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
