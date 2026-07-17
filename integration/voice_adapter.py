"""Translate the voice-group envelope into the A/C runtime command contract.

The voice pipeline deliberately uses wall-clock independent, monotonic-nanosecond
timestamps for latency measurement.  CARLA commands instead expire on simulation
time.  ``VoiceCommandAdapter`` is the single boundary that records the former as
metadata and creates the latter when the envelope reaches the CARLA frame loop.

Complex manoeuvres are never silently converted into a steering or speed command.
They are emitted as a confirmation-gated ``MULTIMODAL_DECISION`` command, which C
will bring to a safe stop until the future decision provider returns a concrete
command.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from car_control_A import DrivingCommand


VOICE_SCHEMA_VERSION = "1.0"
_ALLOWED_INTENTS = frozenset({
    "EMERGENCY_STOP", "STOP", "SET_SPEED", "SPEED_UP", "SLOW_DOWN",
    "PULL_OVER", "AVOID_OBSTACLE", "CHANGE_LANE", "KEEP_LANE", "FOLLOW_ROUTE", "TURN", "UNKNOWN",
})
_COMPLEX_INTENTS = frozenset({
    "SPEED_UP", "SLOW_DOWN", "PULL_OVER", "AVOID_OBSTACLE", "CHANGE_LANE", "KEEP_LANE", "FOLLOW_ROUTE", "TURN",
})


@dataclass(frozen=True, slots=True)
class VoiceCommandMetadata:
    """Auditable voice fields which do not belong in A's minimal contract."""

    source_text: str
    intent: str
    parameters: dict[str, object]
    status: str
    ambiguity_type: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    t_audio_start_ns: int | None
    t_asr_end_ns: int | None
    t_intent_end_ns: int | None


@dataclass(frozen=True, slots=True)
class AdaptedVoiceCommand:
    """A command ready for A/C plus its immutable audit metadata."""

    command: DrivingCommand
    metadata: VoiceCommandMetadata


class VoiceCommandAdapter:
    """Validate and safely adapt the JSON returned by ``voice_group.pipeline``."""

    def __init__(self, *, default_ttl_s: float = 3.0) -> None:
        self._default_ttl_s = _positive_number("default_ttl_s", default_ttl_s)

    def adapt(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand:
        """Create a CARLA-time command from a voice envelope.

        ``now_s`` must be the simulation timestamp of the frame receiving the
        envelope.  It intentionally is not inferred from voice timestamps, since
        monotonic host time and CARLA simulation time have distinct origins.
        """
        if not isinstance(envelope, Mapping):
            raise TypeError("envelope must be a mapping")
        now = _nonnegative_number("now_s", now_s)
        version = _required_text(envelope, "schema_version")
        if version != VOICE_SCHEMA_VERSION:
            raise ValueError(f"unsupported voice schema_version: {version!r}")
        command_id = _required_text(envelope, "command_id")
        source_text = _required_text(envelope, "source_text")
        intent = _required_text(envelope, "intent").upper()
        if intent not in _ALLOWED_INTENTS:
            raise ValueError(f"unsupported voice intent: {intent!r}")
        parameters = envelope.get("parameters", {})
        if type(parameters) is not dict:
            raise TypeError("parameters must be a plain dict")
        status = _required_text(envelope, "status").lower()
        ambiguity_type = _required_text(envelope, "ambiguity_type")
        errors = _string_tuple(envelope.get("errors", []), "errors")
        warnings = _string_tuple(envelope.get("warnings", []), "warnings")
        confidence = _confidence(envelope)
        confirm_required = _optional_bool(envelope, "confirm_required", default=False)
        ttl = envelope.get("valid_duration_s", self._default_ttl_s)
        expiry = now + _positive_number("valid_duration_s", ttl)

        action, target_speed_mps, force_confirmation = self._runtime_fields(intent, parameters)
        invalid = status != "valid" or intent == "UNKNOWN" or bool(errors)
        # Invalid or complex requests retain their original intent in metadata,
        # but can only affect longitudinal control through the C safe fallback.
        if invalid:
            action = "STOP"
            target_speed_mps = None
            force_confirmation = True

        command = DrivingCommand(
            command_id=command_id,
            received_at_s=now,
            expires_at_s=expiry,
            confidence=confidence,
            action=action,
            target_speed_mps=target_speed_mps,
            is_ambiguous=(ambiguity_type.upper() != "NONE" or invalid),
            confirmation_requested=(confirm_required or force_confirmation),
        )
        metadata = VoiceCommandMetadata(
            source_text=source_text, intent=intent, parameters=dict(parameters), status=status,
            ambiguity_type=ambiguity_type, errors=errors, warnings=warnings,
            t_audio_start_ns=_optional_timestamp(envelope, "t_audio_start_ns"),
            t_asr_end_ns=_optional_timestamp(envelope, "t_asr_end_ns"),
            t_intent_end_ns=_optional_timestamp(envelope, "t_intent_end_ns"),
        )
        return AdaptedVoiceCommand(command, metadata)

    @staticmethod
    def _runtime_fields(intent: str, parameters: Mapping[str, object]) -> tuple[str, float | None, bool]:
        if intent == "EMERGENCY_STOP":
            return "EMERGENCY_BRAKE", None, False
        if intent == "STOP":
            return "STOP", None, False
        if intent == "SET_SPEED":
            speed = parameters.get("speed")
            if type(speed) not in (int, float) or isinstance(speed, bool):
                raise ValueError("SET_SPEED requires numeric parameters.speed")
            unit = parameters.get("unit", "km/h")
            if type(unit) is not str:
                raise TypeError("SET_SPEED parameters.unit must be a string")
            normalized_unit = unit.strip().lower().replace(" ", "")
            if normalized_unit in {"km/h", "kph", "kmh", "公里/小时", "千米/小时"}:
                target = float(speed) / 3.6
            elif normalized_unit in {"m/s", "mps", "米/秒"}:
                target = float(speed)
            else:
                raise ValueError(f"unsupported SET_SPEED unit: {unit!r}")
            if not math.isfinite(target) or target < 0.0:
                raise ValueError("SET_SPEED target speed must be finite and non-negative")
            return "SET_SPEED", target, False
        if intent in _COMPLEX_INTENTS:
            return "MULTIMODAL_DECISION", None, True
        # UNKNOWN is handled by the invalid envelope path in adapt().
        return "STOP", None, True


def _required_text(data: Mapping[str, object], name: str) -> str:
    value = data.get(name)
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


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


def _confidence(data: Mapping[str, object]) -> float:
    value = data.get("confidence", data.get("intent_confidence"))
    result = _nonnegative_number("confidence", value)
    if result > 1.0:
        raise ValueError("confidence must be <= 1.0")
    return result


def _optional_bool(data: Mapping[str, object], name: str, *, default: bool) -> bool:
    value = data.get(name, default)
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise TypeError(f"{name} must be a list of strings")
    return tuple(value)


def _optional_timestamp(data: Mapping[str, object], name: str) -> int | None:
    value = data.get(name)
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int or null")
    return value


__all__ = ["VOICE_SCHEMA_VERSION", "VoiceCommandMetadata", "AdaptedVoiceCommand", "VoiceCommandAdapter"]
