from integration.day20.parser import parse_intent
from integration.day20.schemas import (
    ALLOWED_ACTIONS,
    validate_driving_intent,
)


EXPECTED_ACTIONS = {
    "START",
    "STOP",
    "SET_SPEED",
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "AVOID_OBJECT",
    "EMERGENCY_BRAKE",
    "RETURN_TO_LANE",
}


def test_allowed_action_set_is_frozen():
    assert ALLOWED_ACTIONS == EXPECTED_ACTIONS


def test_strict_qwen_json_can_be_parsed():
    raw_output = {
        "actions": [
            {
                "action": "SET_SPEED",
                "target_id": "vehicle_12",
                "target_speed_kmh": 20,
            }
        ],
        "confidence": 0.92,
        "reason": "前方车辆减速，需要降低目标速度",
    }

    intent = parse_intent(raw_output)

    assert len(intent.actions) == 1
    assert intent.actions[0].action == "SET_SPEED"
    assert intent.actions[0].target_id == "vehicle_12"
    assert intent.actions[0].target_speed_kmh == 20
    assert intent.confidence == 0.92
    assert validate_driving_intent(intent)["valid"] is True


def test_low_level_control_action_is_rejected():
    raw_output = {
        "actions": [
            {
                "action": "STEER",
                "target_id": "",
                "target_speed_kmh": 0,
            }
        ],
        "confidence": 0.8,
        "reason": "尝试直接控制方向盘",
    }

    intent = parse_intent(raw_output)

    assert intent.actions == []


def test_empty_action_list_is_invalid():
    raw_output = {
        "actions": [],
        "confidence": 0.8,
        "reason": "没有生成有效动作",
    }

    intent = parse_intent(raw_output)
    validation = validate_driving_intent(intent)

    assert validation["valid"] is False
    assert "actions must not be empty" in validation["errors"]
