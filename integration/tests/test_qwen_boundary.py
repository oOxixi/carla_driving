from __future__ import annotations

import json

import pytest

from integration.qwen_boundary import (
    QwenInputContext,
    fail_closed,
    validate_qwen_response,
)
from integration.day22.command_adapter import build_high_level_command


def test_input_context_is_json_safe_and_immutable_at_boundary() -> None:
    source = {"traffic_light": "RED"}
    context = QwenInputContext(
        request_id="request-1",
        frame=7,
        sim_time_s=0.35,
        voice_command="慢一点",
        rgb_ref="rgb/000007.npy",
        scene_state=source,
        perception={"lead_distance_m": 8.0},
        safety_state={"collision": False},
    )
    source["traffic_light"] = "GREEN"

    payload = context.to_payload()
    assert payload["schema_version"] == "1.0"
    assert payload["scene_state"]["traffic_light"] == "RED"
    assert json.loads(json.dumps(payload, ensure_ascii=False))["frame"] == 7


def test_valid_response_is_normalized() -> None:
    decision = validate_qwen_response(json.dumps({
        "action": "set_speed",
        "target_speed_mps": 4,
        "confidence": 0.9,
        "requires_confirmation": False,
        "reason_zh": "道路安全",
        "decision_source": "QWEN_VL",
        "visual_valid": True,
    }))

    assert decision["action"] == "SET_SPEED"
    assert decision["target_speed_mps"] == 4.0
    assert decision["requires_confirmation"] is False
    command = build_high_level_command(decision, "慢一点", command_id="qwen-1")
    assert command["visual_valid"] is True


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"action": "STOP", "confidence": 1.0}, "missing"),
        ({
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": "false",
        }, "must be bool"),
        ({
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": False,
            "steer": 0.2,
        }, "forbidden low-level"),
        ({
            "action": "SET_SPEED",
            "confidence": 1.0,
            "requires_confirmation": False,
        }, "requires target_speed_mps"),
        ({
            "action": "KEEP_LANE",
            "confidence": 1.0,
            "requires_confirmation": False,
            "unexpected": True,
        }, "unknown"),
    ],
)
def test_rejects_malformed_or_unsafe_responses(payload: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        validate_qwen_response(payload)


def test_fail_closed_maps_model_states_to_watchdog_alerts() -> None:
    assert fail_closed("PENDING", "waiting").watchdog_alerts == ("QWEN_PENDING",)
    assert fail_closed("TIMEOUT", "slow").watchdog_alerts == ("QWEN_TIMEOUT",)
    assert fail_closed("ERROR", "bad json").watchdog_alerts == ("QWEN_ERROR",)
