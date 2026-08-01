from __future__ import annotations

import time
import uuid
from typing import Any, Mapping

from car_control_A.high_level_command import HighLevelCommandAdapter


SUPPORTED_INTENTS = {
    "START",
    "STOP",
    "SLOW_DOWN",
    "SET_SPEED",
    "EMERGENCY_STOP",
}


def build_high_level_command(
    decision: Mapping[str, Any],
    source_text: str,
    *,
    command_id: str | None = None,
) -> dict[str, Any]:
    action = str(decision.get("action", "")).strip().upper()

    if action not in SUPPORTED_INTENTS:
        raise ValueError(f"unsupported Day22 action: {action}")

    high_level: dict[str, Any] = {
        "schema_version": "1.0",
        "command_id": command_id or "qwen_day22_" + uuid.uuid4().hex[:8],
        "source_text": str(source_text),
        "action": action,
        "confidence": float(decision.get("confidence", 0.0)),
        "requires_confirmation": bool(
            decision.get("requires_confirmation", False)
        ),
        "valid_duration_s": 3.0,
        "timestamp_ns": time.monotonic_ns(),
        "reason_zh": str(decision.get("reason_zh", "")),
        "decision_source": str(decision.get("decision_source", "UNKNOWN")),
    }

    target_speed = decision.get("target_speed_mps")
    if action in {"SET_SPEED", "SLOW_DOWN"} and target_speed is not None:
        high_level["target_speed_mps"] = max(0.0, float(target_speed))
    if "visual_valid" in decision:
        visual_valid = decision["visual_valid"]
        if type(visual_valid) is not bool:
            raise TypeError("visual_valid must be bool")
        high_level["visual_valid"] = visual_valid
    if "target_track_id" in decision:
        target_track_id = decision["target_track_id"]
        if type(target_track_id) is not str or not target_track_id.strip():
            raise TypeError("target_track_id must be a non-empty string")
        high_level["target_track_id"] = target_track_id.strip()

    return high_level


def build_command(
    decision: Mapping[str, Any],
    source_text: str,
) -> dict[str, Any]:
    """Build the frozen A runtime envelope from a Day22 decision."""
    return HighLevelCommandAdapter().adapt(
        build_high_level_command(decision, source_text)
    )


__all__ = ["SUPPORTED_INTENTS", "build_command", "build_high_level_command"]
