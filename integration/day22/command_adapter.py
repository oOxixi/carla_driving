from __future__ import annotations

import time
import uuid
from typing import Any, Mapping


SUPPORTED_INTENTS = {
    "START",
    "STOP",
    "SLOW_DOWN",
    "SET_SPEED",
    "EMERGENCY_STOP",
}


def build_command(
    decision: Mapping[str, Any],
    source_text: str,
) -> dict[str, Any]:
    action = str(decision.get("action", "")).strip().upper()

    if action not in SUPPORTED_INTENTS:
        raise ValueError(f"unsupported Day22 action: {action}")

    parameters: dict[str, Any] = {}

    if action in {"SET_SPEED", "SLOW_DOWN"}:
        target_speed = decision.get("target_speed_mps")

        if target_speed is not None:
            parameters = {
                "speed": max(0.0, float(target_speed)),
                "unit": "m/s",
            }

    return {
        "schema_version": "1.0",
        "command_id": "qwen_day22_" + uuid.uuid4().hex[:8],
        "source_text": str(source_text),
        "intent": action,
        "parameters": parameters,
        "confidence": float(decision.get("confidence", 0.0)),
        "intent_confidence": float(
            decision.get("confidence", 0.0)
        ),
        "status": "valid",
        "ambiguity_type": "NONE",
        "confirm_required": bool(
            decision.get("requires_confirmation", False)
        ),
        "errors": [],
        "warnings": [],
        "valid_duration_s": 3.0,
        "t_audio_start_ns": None,
        "t_asr_end_ns": None,
        "t_intent_end_ns": time.monotonic_ns(),
        "reason_zh": str(decision.get("reason_zh", "")),
    }
