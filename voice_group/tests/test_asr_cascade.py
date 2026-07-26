from __future__ import annotations

import json

import pytest

from voice_group.asr_cascade import (
    ConfidenceCalibrator,
    apply_verification,
    mark_verifier_unavailable,
    needs_verification,
    semantic_signature,
)


def command(
    *,
    intent: str = "SET_SPEED",
    source_text: str = "速度设为30公里",
    parameters: dict | None = None,
    status: str = "valid",
) -> dict:
    return {
        "intent": intent,
        "source_text": source_text,
        "parameters": parameters or {"speed": 30, "unit": "km/h"},
        "status": status,
        "confirm_required": False,
        "ambiguity_type": "NONE",
        "warnings": [],
    }


def verification(
    *,
    text: str = "速度设为30公里",
    confidence: float | None = 0.90,
) -> dict:
    return {
        "text": text,
        "raw_word_probability": 0.8,
        "calibrated_confidence": confidence,
        "calibration_available": confidence is not None,
        "latency_ms": 20.0,
    }


def test_policy_verifies_only_commands_that_can_change_control() -> None:
    assert needs_verification(command())
    assert needs_verification(
        command(
            intent="KEEP_LANE",
            source_text="继续保持30公里",
            parameters={"mode": "KEEP_CURRENT_LANE"},
        )
    )
    assert not needs_verification(
        command(
            intent="UNKNOWN",
            source_text="天气如何",
            parameters={},
            status="unknown",
        )
    )
    assert not needs_verification(
        command(
            intent="EMERGENCY_STOP",
            source_text="紧急停车",
            parameters={"brake": "FULL"},
        )
    )
    assert not needs_verification(
        command(
            intent="KEEP_LANE",
            source_text="保持当前车道",
            parameters={"mode": "KEEP_CURRENT_LANE"},
        )
    )


def test_semantic_agreement_authorizes_high_confidence_result() -> None:
    primary = command()
    secondary = command()
    result = apply_verification(
        primary,
        verification(),
        secondary,
        minimum_confidence=0.60,
    )

    assert semantic_signature(primary) == semantic_signature(secondary)
    assert "asr_confidence" not in result
    assert result["verification_confidence"] == 0.90
    assert result["confirm_required"] is False
    assert result["asr_verification"]["semantic_agreement"] is True


def test_semantic_disagreement_requires_confirmation() -> None:
    result = apply_verification(
        command(),
        verification(text="速度设为80公里"),
        command(parameters={"speed": 80, "unit": "km/h"}),
        minimum_confidence=0.60,
    )

    assert result["confirm_required"] is True
    assert result["ambiguity_type"] == "ASR_MODEL_DISAGREEMENT"
    assert result["warnings"][-1]["code"] == "ASR_MODEL_DISAGREEMENT"


def test_low_confidence_disagreement_does_not_override_primary_model() -> None:
    result = apply_verification(
        command(),
        verification(text="速度设为80公里", confidence=0.20),
        command(parameters={"speed": 80, "unit": "km/h"}),
        minimum_confidence=0.60,
    )

    assert result["confirm_required"] is False
    assert result["warnings"][-1]["code"] == "ASR_UNCERTAIN_DISAGREEMENT"


def test_secondary_model_never_blocks_a_primary_stop() -> None:
    primary = command(
        intent="EMERGENCY_STOP",
        source_text="紧急停车",
        parameters={"brake": "FULL"},
    )
    secondary = command(
        intent="UNKNOWN",
        source_text="天气",
        parameters={},
        status="unknown",
    )
    result = apply_verification(
        primary,
        verification(text="天气", confidence=0.99),
        secondary,
        minimum_confidence=0.60,
    )

    assert result["confirm_required"] is False
    assert result["warnings"][-1]["code"] == "ASR_UNCERTAIN_DISAGREEMENT"


def test_obstacle_homophone_does_not_block_same_manoeuvre() -> None:
    primary = command(
        intent="AVOID_OBSTACLE",
        source_text="从左边绕开障碍物",
        parameters={"direction": "LEFT", "target": "OBSTACLE"},
    )
    secondary = command(
        intent="AVOID_OBSTACLE",
        source_text="从左边绕开帐碍物",
        parameters={"direction": "LEFT"},
    )
    result = apply_verification(
        primary,
        verification(text="从左边绕开帐碍物", confidence=0.99),
        secondary,
        minimum_confidence=0.90,
    )

    assert result["confirm_required"] is False
    assert result["asr_verification"]["semantic_agreement"] is True


def test_uncalibrated_agreement_is_audited_without_fake_score() -> None:
    result = apply_verification(
        command(),
        verification(confidence=None),
        command(),
        minimum_confidence=0.60,
    )

    assert "verification_confidence" not in result
    assert result["confirm_required"] is False
    assert result["warnings"][-1]["code"] == "UNCALIBRATED_VERIFIER"


def test_missing_verifier_fails_into_confirmation_gate() -> None:
    result = mark_verifier_unavailable(command(), RuntimeError("missing"))

    assert result["confirm_required"] is True
    assert result["ambiguity_type"] == "ASR_VERIFIER_UNAVAILABLE"
    assert result["asr_verification"]["available"] is False


def test_calibrator_only_returns_score_when_file_exists(tmp_path) -> None:
    missing = ConfidenceCalibrator(tmp_path / "missing.json")
    assert missing.transform(0.9) is None

    path = tmp_path / "calibration.json"
    path.write_text(
        json.dumps(
            {
                "method": "platt_logit",
                "intercept": 0.0,
                "slope": 1.0,
            }
        ),
        encoding="utf-8",
    )
    calibrated = ConfidenceCalibrator(path)
    assert calibrated.transform(0.8) == pytest.approx(0.8)
