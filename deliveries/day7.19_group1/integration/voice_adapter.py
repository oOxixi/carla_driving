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

from car_control_A import DrivingCommand, ExecutionFeedback, ExecutionStatus


VOICE_SCHEMA_VERSION = "1.0"
_ALLOWED_INTENTS = frozenset({
    "EMERGENCY_STOP", "STOP", "SET_SPEED", "SPEED_UP", "SLOW_DOWN",
    "PULL_OVER", "AVOID_OBSTACLE", "CHANGE_LANE", "KEEP_LANE", "FOLLOW_ROUTE", "TURN", "UNKNOWN",
})
_COMPLEX_INTENTS = frozenset({
    "SPEED_UP", "SLOW_DOWN", "PULL_OVER", "AVOID_OBSTACLE", "CHANGE_LANE", "KEEP_LANE", "FOLLOW_ROUTE", "TURN",
})


@dataclass(frozen=True, slots=True)
class VoiceDiagnostic:
    """Normalized diagnostic emitted by either voice pipeline revision."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class VoiceCommandMetadata:
    """Auditable voice fields which do not belong in A's minimal contract."""

    source_text: str
    intent: str
    parameters: dict[str, object]
    status: str
    ambiguity_type: str
    errors: tuple[VoiceDiagnostic, ...]
    warnings: tuple[VoiceDiagnostic, ...]
    t_audio_start_ns: int | None
    t_asr_end_ns: int | None
    t_intent_end_ns: int | None


@dataclass(frozen=True, slots=True)
class AdaptedVoiceCommand:
    """A command ready for A/C plus its immutable audit metadata."""

    command: DrivingCommand
    metadata: VoiceCommandMetadata
    control_authorized: bool = True
    feedback: ExecutionFeedback | None = None


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
        now = _nonnegative_number("now_s", now_s)
        if not isinstance(envelope, Mapping):
            return self._rejected({}, now, "envelope must be a mapping")
        try:
            return self._adapt_validated(envelope, now)
        except (TypeError, ValueError) as error:
            return self._rejected(envelope, now, str(error))

    def _adapt_validated(self, envelope: Mapping[str, object], now: float) -> AdaptedVoiceCommand:
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
        errors = _diagnostic_tuple(envelope.get("errors", []), "errors")
        warnings = _diagnostic_tuple(envelope.get("warnings", []), "warnings")
        confidence = _confidence(envelope)
        confirm_required = _optional_bool(envelope, "confirm_required", default=False)
        ttl = envelope.get("valid_duration_s", self._default_ttl_s)
        expiry = now + _positive_number("valid_duration_s", ttl)

        invalid = status != "valid" or intent == "UNKNOWN" or bool(errors)
        if invalid:
            reason = "voice command is not valid"
            if errors:
                reason = "; ".join(item.code for item in errors)
            return self._rejected(envelope, now, reason, errors=errors, warnings=warnings)

        action, target_speed_mps, force_confirmation = self._runtime_fields(intent, parameters)

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

    def _rejected(self, envelope: Mapping[str, object], now: float, reason: str, *,
                  errors: tuple[VoiceDiagnostic, ...] | None = None,
                  warnings: tuple[VoiceDiagnostic, ...] | None = None) -> AdaptedVoiceCommand:
        """Return an auditable NO_OP without granting longitudinal authority."""
        command_id = _safe_text(envelope.get("command_id"), "rejected-voice-command")
        source_text = _safe_text(envelope.get("source_text"), "<unavailable>")
        intent = _safe_text(envelope.get("intent"), "UNKNOWN").upper()
        parameters = envelope.get("parameters")
        safe_parameters = dict(parameters) if type(parameters) is dict else {}
        status = _safe_text(envelope.get("status"), "invalid").lower()
        ambiguity = _safe_text(envelope.get("ambiguity_type"), "UNKNOWN")
        normalized_errors = errors if errors is not None else _diagnostic_tuple_lenient(envelope.get("errors"))
        normalized_errors = normalized_errors + (VoiceDiagnostic("VEHICLE_ADAPTER_REJECTED", reason),)
        normalized_warnings = warnings if warnings is not None else _diagnostic_tuple_lenient(envelope.get("warnings"))
        ttl_value = envelope.get("valid_duration_s", self._default_ttl_s)
        try:
            ttl = _positive_number("valid_duration_s", ttl_value)
        except (TypeError, ValueError):
            ttl = self._default_ttl_s
        command = DrivingCommand(
            command_id=command_id,
            received_at_s=now,
            expires_at_s=now + ttl,
            confidence=0.0,
            action="NO_OP",
            is_ambiguous=True,
            confirmation_requested=False,
        )
        metadata = VoiceCommandMetadata(
            source_text=source_text, intent=intent, parameters=safe_parameters, status=status,
            ambiguity_type=ambiguity, errors=normalized_errors, warnings=normalized_warnings,
            t_audio_start_ns=_optional_timestamp_lenient(envelope, "t_audio_start_ns"),
            t_asr_end_ns=_optional_timestamp_lenient(envelope, "t_asr_end_ns"),
            t_intent_end_ns=_optional_timestamp_lenient(envelope, "t_intent_end_ns"),
        )
        feedback = ExecutionFeedback(command_id, ExecutionStatus.REJECTED, now, reason)
        return AdaptedVoiceCommand(command, metadata, control_authorized=False, feedback=feedback)

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


def _diagnostic_tuple(value: object, name: str) -> tuple[VoiceDiagnostic, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} must be a list")
    result: list[VoiceDiagnostic] = []
    for item in value:
        if type(item) is str and item.strip():
            result.append(VoiceDiagnostic(item, item))
        elif isinstance(item, Mapping):
            code = item.get("code")
            message = item.get("message")
            if type(code) is not str or not code.strip() or type(message) is not str:
                raise TypeError(f"{name} objects require non-empty code and string message")
            result.append(VoiceDiagnostic(code, message))
        else:
            raise TypeError(f"{name} entries must be strings or {{code, message}} objects")
    return tuple(result)


def _diagnostic_tuple_lenient(value: object) -> tuple[VoiceDiagnostic, ...]:
    try:
        return _diagnostic_tuple(value if value is not None else [], "diagnostics")
    except (TypeError, ValueError):
        return ()


def _safe_text(value: object, default: str) -> str:
    return value.strip() if type(value) is str and value.strip() else default


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


__all__ = ["VOICE_SCHEMA_VERSION", "VoiceDiagnostic", "VoiceCommandMetadata", "AdaptedVoiceCommand", "VoiceCommandAdapter"]
