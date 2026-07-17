from car_control_D.validators import validate_command, validate_control


def test_voice_group_slow_down_command_is_valid():
    cmd = {
        "schema_version": "1.0",
        "command_id": "cmd_4679fc8e",
        "source_text": "进入隧道了，减速哈。",
        "intent": "SLOW_DOWN",
        "parameters": {"mode": "RELATIVE", "action": "DECELERATE"},
        "asr_confidence": None,
        "intent_confidence": 0.95,
        "status": "valid",
        "ambiguity_type": "NONE",
        "confirm_required": False,
        "errors": [],
        "warnings": [],
        "confidence": 0.95,
    }
    result = validate_command(cmd)
    assert result.valid, result.to_dict()


def test_change_lane_requires_direction():
    cmd = {"schema_version": "1.0", "command_id": "c1", "source_text": "变道", "intent": "CHANGE_LANE", "parameters": {}, "confidence": 0.9}
    result = validate_command(cmd)
    assert not result.valid
    assert any("direction" in err for err in result.errors)


def test_control_conflict_invalid():
    result = validate_control({"steer": 0.0, "throttle": 0.5, "brake": 0.5})
    assert not result.valid
