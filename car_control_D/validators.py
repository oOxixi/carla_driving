"""Validation rules for commands, controls and final feedback."""
from __future__ import annotations

import math
from typing import Any, List

from .adapters import adapt_command, adapt_control
from .schemas import ALLOWED_INTENTS, SCHEMA_VERSION, TERMINAL_STATUSES, ValidationResult


def _finite_number(name: str, value: float, errors: List[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        errors.append(f"{name} must be a finite number")


def validate_control(control: Any) -> ValidationResult:
    errors: List[str] = []
    try:
        c = adapt_control(control)
    except Exception as exc:
        return ValidationResult(False, [f"control adapt failed: {exc}"])

    _finite_number("steer", c.steer, errors)
    _finite_number("throttle", c.throttle, errors)
    _finite_number("brake", c.brake, errors)
    if not -1.0 <= c.steer <= 1.0:
        errors.append("steer out of range [-1,1]")
    if not 0.0 <= c.throttle <= 1.0:
        errors.append("throttle out of range [0,1]")
    if not 0.0 <= c.brake <= 1.0:
        errors.append("brake out of range [0,1]")
    if c.throttle > 0.03 and c.brake > 0.03:
        errors.append("throttle and brake conflict")
    return ValidationResult(len(errors) == 0, errors)


def validate_command(command: Any) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        cmd = adapt_command(command)
    except Exception as exc:
        return ValidationResult(False, [f"command adapt failed: {exc}"])

    if cmd.schema_version != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    if not cmd.command_id:
        errors.append("command_id is required")
    if cmd.intent not in ALLOWED_INTENTS:
        errors.append(f"unsupported intent: {cmd.intent}")
    if not 0.0 <= cmd.confidence <= 1.0:
        errors.append("confidence out of range [0,1]")
    if not 0.0 <= cmd.intent_confidence <= 1.0:
        errors.append("intent_confidence out of range [0,1]")

    if cmd.intent == "CHANGE_LANE":
        direction = str(cmd.parameters.get("direction", "")).upper()
        if direction not in {"LEFT", "RIGHT"}:
            errors.append("CHANGE_LANE requires parameters.direction LEFT or RIGHT")
    if cmd.intent == "SET_SPEED":
        if "speed" not in cmd.parameters and "target_speed" not in cmd.parameters and "speed_kmh" not in cmd.parameters:
            errors.append("SET_SPEED requires speed/target_speed/speed_kmh")
    if cmd.intent == "UNKNOWN":
        warnings.append("UNKNOWN command should be rejected or held by safety layer")
    if cmd.confirm_required or cmd.ambiguity_type not in {"NONE", ""}:
        warnings.append("command requires confirmation or is ambiguous")
    return ValidationResult(len(errors) == 0, errors, warnings)


def validate_execution_feedback(feedback: Any) -> ValidationResult:
    errors: List[str] = []
    status = None
    if isinstance(feedback, dict):
        status = feedback.get("status")
        command_id = feedback.get("command_id")
    else:
        status = getattr(feedback, "status", None)
        command_id = getattr(feedback, "command_id", None)
    if not command_id:
        errors.append("feedback.command_id is required")
    if status not in TERMINAL_STATUSES:
        errors.append("feedback.status is not terminal")
    return ValidationResult(len(errors) == 0, errors)
