from __future__ import annotations

import pytest

from car_control_A import ExecutionStatus
from integration.voice_adapter import VoiceCommandAdapter


def envelope(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": "1.0", "command_id": "cmd-1", "source_text": "设置速度36公里每小时",
        "intent": "SET_SPEED", "parameters": {"speed": 36, "unit": "km/h"},
        "intent_confidence": 0.95, "status": "valid", "ambiguity_type": "NONE",
        "confirm_required": False, "errors": [], "warnings": [], "valid_duration_s": 3.0,
        "t_audio_start_ns": 1, "t_asr_end_ns": 2, "t_intent_end_ns": 3,
    }
    result.update(overrides)
    return result


def test_set_speed_converts_kmh_and_uses_carla_time() -> None:
    adapted = VoiceCommandAdapter().adapt(envelope(), now_s=12.5)
    assert adapted.command.action == "SET_SPEED"
    assert adapted.command.target_speed_mps == pytest.approx(10.0)
    assert adapted.command.received_at_s == 12.5
    assert adapted.command.expires_at_s == 15.5
    assert adapted.metadata.t_intent_end_ns == 3


def test_set_speed_accepts_documented_chinese_units() -> None:
    adapter = VoiceCommandAdapter()
    for unit in ("公里/小时", "千米/小时"):
        adapted = adapter.adapt(envelope(parameters={"speed": 36, "unit": unit}), now_s=1.0)
        assert adapted.control_authorized
        assert adapted.command.target_speed_mps == pytest.approx(10.0)

    adapted = adapter.adapt(envelope(parameters={"speed": 10, "unit": "米/秒"}), now_s=1.0)
    assert adapted.control_authorized
    assert adapted.command.target_speed_mps == pytest.approx(10.0)


@pytest.mark.parametrize(("intent", "action"), [("STOP", "STOP"), ("EMERGENCY_STOP", "EMERGENCY_BRAKE")])
def test_safe_simple_intents(intent: str, action: str) -> None:
    adapted = VoiceCommandAdapter().adapt(envelope(intent=intent, parameters={}), now_s=1.0)
    assert adapted.command.action == action
    assert not adapted.command.requires_confirmation


@pytest.mark.parametrize("intent", ["SPEED_UP", "SLOW_DOWN", "PULL_OVER", "AVOID_OBSTACLE", "CHANGE_LANE", "KEEP_LANE", "FOLLOW_ROUTE", "TURN"])
def test_complex_intents_are_confirmation_gated(intent: str) -> None:
    adapted = VoiceCommandAdapter().adapt(envelope(intent=intent, parameters={}), now_s=1.0)
    assert adapted.command.action == "MULTIMODAL_DECISION"
    assert adapted.command.requires_confirmation
    assert adapted.metadata.intent == intent


def test_invalid_or_unknown_command_is_a_rejected_no_op() -> None:
    adapted = VoiceCommandAdapter().adapt(envelope(intent="UNKNOWN", status="invalid", errors=["unknown_intent"]), now_s=1.0)
    assert adapted.command.action == "NO_OP"
    assert not adapted.control_authorized
    assert adapted.feedback is not None
    assert adapted.feedback.status is ExecutionStatus.REJECTED
    assert adapted.metadata.errors[0].code == "unknown_intent"


def test_object_diagnostics_are_normalized_without_losing_code_or_message() -> None:
    adapted = VoiceCommandAdapter().adapt(envelope(
        intent="UNKNOWN", status="invalid",
        errors=[{"code": "B1_UNKNOWN", "message": "no intent"}],
        warnings=[{"code": "LOW_SNR", "message": "audio noisy"}],
    ), now_s=1.0)
    assert adapted.metadata.errors[0].code == "B1_UNKNOWN"
    assert adapted.metadata.errors[0].message == "no intent"
    assert adapted.metadata.warnings[0].code == "LOW_SNR"


@pytest.mark.parametrize("parameters", [{}, {"speed": 20, "unit": "mph"}, {"speed": -1, "unit": "km/h"}])
def test_invalid_set_speed_is_rejected(parameters: dict[str, object]) -> None:
    adapted = VoiceCommandAdapter().adapt(envelope(parameters=parameters), now_s=1.0)
    assert not adapted.control_authorized
    assert adapted.command.action == "NO_OP"
    assert adapted.feedback is not None and adapted.feedback.status is ExecutionStatus.REJECTED


def test_rejects_bad_envelope_types() -> None:
    bad_bool = VoiceCommandAdapter().adapt(envelope(confirm_required="false"), now_s=1.0)
    bad_version = VoiceCommandAdapter().adapt(envelope(schema_version="2.0"), now_s=1.0)
    assert not bad_bool.control_authorized
    assert not bad_version.control_authorized
