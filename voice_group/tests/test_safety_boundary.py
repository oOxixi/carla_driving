from __future__ import annotations

import pytest

from voice_group.nlu_b2.parser import parse_command
from voice_group.vehicle_nlu.src.b1_service import process_asr_text


def test_low_asr_confidence_blocks_otherwise_executable_speed_command() -> None:
    result = parse_command(
        process_asr_text(
            request_id="low-asr-speed",
            text="速度设为30公里",
            asr_confidence=0.20,
        )
    )

    assert result["intent"] == "SET_SPEED"
    assert result["status"] == "low_confidence"
    assert result["slots"] == {}
    assert result["errors"][0]["code"] == "LOW_ASR_CONFIDENCE"


def test_missing_asr_confidence_remains_backward_compatible() -> None:
    result = parse_command(
        process_asr_text(
            request_id="legacy-speed",
            text="速度设为30公里",
            asr_confidence=None,
        )
    )

    assert result["status"] == "valid"
    assert result["slots"]["speed"] == 30


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("在这儿停。", "STOP"),
        ("停到右边吗。", "PULL_OVER"),
        ("别充那么快吧。", "SLOW_DOWN"),
        ("撒一脚吧。", "STOP"),
        ("刹刹车！", "EMERGENCY_STOP"),
        ("踩死车！", "EMERGENCY_STOP"),
    ],
)
def test_observed_asr_variants_remain_safe_and_executable(
    text: str,
    intent: str,
) -> None:
    result = parse_command(
        process_asr_text(
            request_id="observed-asr-variant",
            text=text,
            asr_confidence=1.0,
        )
    )

    assert result["intent"] == intent
    assert result["status"] == "valid"


@pytest.mark.parametrize(
    ("text", "intent", "expected_slots"),
    [
        ("在这庭，", "STOP", {}),
        ("麻烦换左遍车道，", "CHANGE_LANE", {"direction": "LEFT"}),
        ("马上杀，", "EMERGENCY_STOP", {}),
        ("降降素", "SLOW_DOWN", {}),
        ("麻烦停车停车，", "EMERGENCY_STOP", {}),
    ],
)
def test_current_sensevoice_errors_keep_the_expected_control_semantics(
    text: str,
    intent: str,
    expected_slots: dict[str, object],
) -> None:
    result = parse_command(
        process_asr_text(
            request_id="sensevoice-error-tolerance",
            text=text,
            asr_confidence=1.0,
        )
    )

    assert result["intent"] == intent
    assert result["status"] == "valid"
    assert all(result["slots"].get(key) == value for key, value in expected_slots.items())


def test_missing_action_is_not_inferred_from_urgency_word_alone() -> None:
    result = parse_command(
        process_asr_text(
            request_id="missing-emergency-action",
            text="马上！",
            asr_confidence=1.0,
        )
    )

    assert result["intent"] == "UNKNOWN"
    assert result["status"] == "unknown"
