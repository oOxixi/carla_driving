from __future__ import annotations

from car_control_A.high_level_command import HighLevelCommandAdapter, is_high_level_command
from integration.voice_adapter import VoiceCommandAdapter


def qwen_command(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": "1.0",
        "command_id": "qwen-1",
        "action": "SET_SPEED",
        "target_speed_mps": 5.0,
        "confidence": 0.95,
        "reason": "clear lane",
        "visual_valid": True,
        "timestamp_ns": 123,
        "valid_duration_s": 3.0,
    }
    result.update(overrides)
    return result


def test_qwen_set_speed_becomes_existing_voice_envelope() -> None:
    envelope = HighLevelCommandAdapter().adapt(qwen_command())

    assert is_high_level_command(qwen_command())
    assert envelope["intent"] == "SET_SPEED"
    assert envelope["parameters"] == {"speed": 5.0, "unit": "m/s"}
    assert envelope["t_intent_end_ns"] == 123

    adapted = VoiceCommandAdapter().adapt(envelope, now_s=10.0)
    assert adapted.control_authorized
    assert adapted.command.action == "SET_SPEED"
    assert adapted.command.target_speed_mps == 5.0


def test_slow_down_uses_explicit_or_conservative_default_speed() -> None:
    adapter = HighLevelCommandAdapter(default_slow_speed_mps=2.0)

    explicit = adapter.adapt(qwen_command(action="SLOW_DOWN", target_speed_mps=3.0))
    defaulted = adapter.adapt(qwen_command(action="SLOW_DOWN", target_speed_mps=None))

    assert explicit["intent"] == "SLOW_DOWN"
    assert explicit["parameters"] == {"speed": 3.0, "unit": "m/s"}
    assert defaulted["parameters"] == {"speed": 2.0, "unit": "m/s"}
    assert defaulted["warnings"][0]["code"] == "SLOW_DOWN_DEFAULT_SPEED"


def test_start_is_normalized_to_keep_lane_and_has_terminal_runtime_action() -> None:
    envelope = HighLevelCommandAdapter().adapt(qwen_command(action="START", target_speed_mps=None))

    assert envelope["intent"] == "KEEP_LANE"
    assert envelope["warnings"][0]["code"] == "START_MAPPED_TO_KEEP_LANE"
    adapted = VoiceCommandAdapter().adapt(envelope, now_s=1.0)
    assert adapted.control_authorized
    assert adapted.command.action == "KEEP_LANE"
    assert not adapted.command.requires_confirmation


def test_unsupported_manoeuvre_is_confirmation_gated_not_executed() -> None:
    envelope = HighLevelCommandAdapter().adapt(qwen_command(action="CHANGE_LANE_LEFT", target_speed_mps=None))

    assert envelope["intent"] == "CHANGE_LANE"
    assert envelope["parameters"] == {"direction": "LEFT"}
    assert envelope["confirm_required"] is True

    adapted = VoiceCommandAdapter().adapt(envelope, now_s=1.0)
    assert adapted.control_authorized
    assert adapted.command.action == "MULTIMODAL_DECISION"
    assert adapted.command.requires_confirmation


def test_low_level_fields_are_rejected_before_runtime_authority() -> None:
    envelope = HighLevelCommandAdapter().adapt(qwen_command(throttle=0.5))

    assert envelope["status"] == "invalid"
    assert envelope["intent"] == "UNKNOWN"
    adapted = VoiceCommandAdapter().adapt(envelope, now_s=1.0)
    assert not adapted.control_authorized
    assert adapted.command.action == "NO_OP"

