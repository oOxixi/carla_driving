"""Frozen high-level command boundary for Qwen/decision-module output.

The model side may only express an auditable action intent.  This adapter
normalizes that JSON into the existing voice-style envelope consumed by
``integration.ControlRuntime``; it never accepts low-level throttle/brake/steer.
"""

from __future__ import annotations

from collections.abc import Mapping
import math


HIGH_LEVEL_SCHEMA_VERSION = "1.0"
EXECUTABLE_ACTIONS = frozenset({
    "SET_SPEED",
    "SLOW_DOWN",
    "STOP",
    "EMERGENCY_STOP",
    "EMERGENCY_BRAKE",
    "KEEP_LANE",
    "START",
})
CONFIRMATION_ACTIONS = frozenset({
    "SPEED_UP",
    "FOLLOW_ROUTE",
    "PULL_OVER",
    "TURN",
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "AVOID",
    "AVOID_OBSTACLE",
})
FORBIDDEN_LOW_LEVEL_FIELDS = frozenset({
    "throttle",
    "brake",
    "steer",
    "steering_angle",
    "wheel_angle",
})


def is_high_level_command(payload: object) -> bool:
    """Return True for Qwen-style command JSON, not legacy voice envelopes."""
    return isinstance(payload, Mapping) and "action" in payload and "intent" not in payload


class HighLevelCommandAdapter:
    """Convert Qwen high-level JSON into A's command envelope contract."""

    def __init__(self, *, default_ttl_s: float = 3.0, default_slow_speed_mps: float = 2.0) -> None:
        self.default_ttl_s = _positive_number("default_ttl_s", default_ttl_s)
        self.default_slow_speed_mps = _nonnegative_number(
            "default_slow_speed_mps", default_slow_speed_mps,
        )

    def adapt(self, payload: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(payload, Mapping):
            raise TypeError("high-level command payload must be a mapping")
        forbidden = FORBIDDEN_LOW_LEVEL_FIELDS.intersection(payload.keys())
        if forbidden:
            return self._invalid_envelope(
                payload,
                "UNKNOWN",
                "LOW_LEVEL_FIELDS_FORBIDDEN",
                "Qwen/high-level commands must not include " + ",".join(sorted(forbidden)),
            )

        version = _required_text(payload, "schema_version")
        if version != HIGH_LEVEL_SCHEMA_VERSION:
            return self._invalid_envelope(
                payload,
                "UNKNOWN",
                "UNSUPPORTED_SCHEMA_VERSION",
                f"unsupported high-level schema_version: {version!r}",
            )

        action = _required_text(payload, "action").upper()
        confidence = _confidence(payload)
        valid_duration_s = _positive_number(
            "valid_duration_s",
            payload.get("valid_duration_s", self.default_ttl_s),
        )
        warnings: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []

        intent, parameters, confirm_required = self._runtime_fields(action, payload, warnings)
        if intent == "UNKNOWN":
            errors.append({"code": "UNKNOWN_ACTION", "message": f"unsupported action: {action}"})

        if payload.get("visual_valid") is False:
            warnings.append({
                "code": "VISUAL_INVALID",
                "message": "visual input was marked invalid; downstream safety must rely on other sources",
            })

        source_text = _source_text(payload, action)
        return {
            "schema_version": "1.0",
            "command_id": _required_text(payload, "command_id"),
            "source_text": source_text,
            "intent": intent,
            "parameters": parameters,
            "confidence": confidence,
            "intent_confidence": confidence,
            "status": "invalid" if errors else "valid",
            "ambiguity_type": "UNSUPPORTED_ACTION" if confirm_required else "NONE",
            "confirm_required": confirm_required,
            "errors": errors,
            "warnings": warnings,
            "valid_duration_s": valid_duration_s,
            "t_audio_start_ns": None,
            "t_asr_end_ns": None,
            "t_intent_end_ns": _optional_timestamp(payload, "timestamp_ns"),
            "high_level_action": action,
            "reason": _optional_text(payload, "reason") or _optional_text(payload, "reason_zh"),
            "visual_valid": payload.get("visual_valid"),
        }

    def _runtime_fields(
        self,
        action: str,
        payload: Mapping[str, object],
        warnings: list[dict[str, str]],
    ) -> tuple[str, dict[str, object], bool]:
        if action == "START":
            warnings.append({
                "code": "START_MAPPED_TO_KEEP_LANE",
                "message": "START is normalized to KEEP_LANE for the frozen A runtime contract",
            })
            action = "KEEP_LANE"
        if action == "EMERGENCY_BRAKE":
            action = "EMERGENCY_STOP"

        if action == "SET_SPEED":
            return "SET_SPEED", _speed_parameters(payload, required=True), False
        if action == "SLOW_DOWN":
            if payload.get("target_speed_mps") is None:
                warnings.append({
                    "code": "SLOW_DOWN_DEFAULT_SPEED",
                    "message": "SLOW_DOWN omitted target_speed_mps; using conservative default",
                })
                return "SLOW_DOWN", {"speed": self.default_slow_speed_mps, "unit": "m/s"}, False
            return "SLOW_DOWN", _speed_parameters(payload, required=True), False
        if action in {"STOP", "EMERGENCY_STOP", "KEEP_LANE"}:
            return action, {}, False

        if action in CONFIRMATION_ACTIONS:
            if action.startswith("TURN"):
                parameters = _direction_parameters(action, "TURN")
                return "TURN", parameters, True
            if action.startswith("CHANGE_LANE"):
                parameters = _direction_parameters(action, "CHANGE_LANE")
                return "CHANGE_LANE", parameters, True
            if action == "AVOID":
                return "AVOID_OBSTACLE", {}, True
            return action, {}, True

        return "UNKNOWN", {}, False

    def _invalid_envelope(
        self,
        payload: Mapping[str, object],
        intent: str,
        code: str,
        message: str,
    ) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "command_id": _safe_text(payload.get("command_id"), "rejected-high-level-command"),
            "source_text": _source_text(payload, _safe_text(payload.get("action"), "UNKNOWN")),
            "intent": intent,
            "parameters": {},
            "confidence": 0.0,
            "intent_confidence": 0.0,
            "status": "invalid",
            "ambiguity_type": "INVALID_HIGH_LEVEL_COMMAND",
            "confirm_required": False,
            "errors": [{"code": code, "message": message}],
            "warnings": [],
            "valid_duration_s": self.default_ttl_s,
            "t_audio_start_ns": None,
            "t_asr_end_ns": None,
            "t_intent_end_ns": _optional_timestamp_lenient(payload, "timestamp_ns"),
        }


def _speed_parameters(payload: Mapping[str, object], *, required: bool) -> dict[str, object]:
    value = payload.get("target_speed_mps")
    if value is None and not required:
        return {}
    speed = _nonnegative_number("target_speed_mps", value)
    return {"speed": speed, "unit": "m/s"}


def _direction_parameters(action: str, prefix: str) -> dict[str, object]:
    suffix = action.removeprefix(prefix).strip("_")
    return {} if not suffix else {"direction": suffix}


def _source_text(payload: Mapping[str, object], action: str) -> str:
    explicit = _optional_text(payload, "source_text")
    if explicit is not None:
        return explicit
    reason = _optional_text(payload, "reason") or _optional_text(payload, "reason_zh")
    return f"Qwen high-level action {action}" if reason is None else f"{action}: {reason}"


def _required_text(data: Mapping[str, object], name: str) -> str:
    value = data.get(name)
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(data: Mapping[str, object], name: str) -> str | None:
    value = data.get(name)
    return value.strip() if type(value) is str and value.strip() else None


def _safe_text(value: object, default: str) -> str:
    return value.strip() if type(value) is str and value.strip() else default


def _confidence(data: Mapping[str, object]) -> float:
    return _bounded_confidence(data.get("confidence", data.get("intent_confidence", 0.0)))


def _bounded_confidence(value: object) -> float:
    result = _nonnegative_number("confidence", value)
    if result > 1.0:
        raise ValueError("confidence must be <= 1.0")
    return result


def _nonnegative_number(name: str, value: object) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int or float")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _positive_number(name: str, value: object) -> float:
    result = _nonnegative_number(name, value)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _optional_timestamp(data: Mapping[str, object], name: str) -> int | None:
    value = data.get(name)
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int or null")
    return value


def _optional_timestamp_lenient(data: Mapping[str, object], name: str) -> int | None:
    try:
        return _optional_timestamp(data, name)
    except (TypeError, ValueError):
        return None


__all__ = [
    "HIGH_LEVEL_SCHEMA_VERSION",
    "EXECUTABLE_ACTIONS",
    "CONFIRMATION_ACTIONS",
    "FORBIDDEN_LOW_LEVEL_FIELDS",
    "HighLevelCommandAdapter",
    "is_high_level_command",
]
