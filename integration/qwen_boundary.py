"""Strict CARLA-independent request/response boundary for Qwen decisions."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import re
from types import MappingProxyType
from typing import Any

from car_control_A.high_level_command import FORBIDDEN_LOW_LEVEL_FIELDS
from .day22.command_adapter import SUPPORTED_INTENTS


QWEN_BOUNDARY_SCHEMA_VERSION = "1.0"
_REQUIRED_RESPONSE_FIELDS = frozenset({
    "action", "confidence", "requires_confirmation",
})
_OPTIONAL_RESPONSE_FIELDS = frozenset({
    "target_speed_mps", "reason_zh", "decision_source", "visual_valid",
})
_ALLOWED_RESPONSE_FIELDS = _REQUIRED_RESPONSE_FIELDS | _OPTIONAL_RESPONSE_FIELDS


@dataclass(frozen=True, slots=True)
class QwenInputContext:
    """JSON-safe multimodal context passed to a Qwen adapter.

    ``rgb_ref`` identifies an image owned by the caller.  Keeping binary image
    data outside this contract makes logging/replay deterministic while a real
    model adapter may resolve the reference to pixels.
    """

    request_id: str
    frame: int
    sim_time_s: float
    voice_command: str
    rgb_ref: str | None
    scene_state: Mapping[str, Any]
    perception: Mapping[str, Any]
    safety_state: Mapping[str, Any]

    def __post_init__(self) -> None:
        if type(self.request_id) is not str or not self.request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if type(self.frame) is not int or self.frame < 0:
            raise ValueError("frame must be a non-negative integer")
        if (
            type(self.sim_time_s) not in (int, float)
            or isinstance(self.sim_time_s, bool)
            or not math.isfinite(float(self.sim_time_s))
            or self.sim_time_s < 0.0
        ):
            raise ValueError("sim_time_s must be finite and non-negative")
        if type(self.voice_command) is not str:
            raise TypeError("voice_command must be a string")
        if self.rgb_ref is not None and (
            type(self.rgb_ref) is not str or not self.rgb_ref.strip()
        ):
            raise ValueError("rgb_ref must be a non-empty string or None")
        for name in ("scene_state", "perception", "safety_state"):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise TypeError(f"{name} must be a mapping")
            copied = _json_mapping(name, value)
            object.__setattr__(self, name, MappingProxyType(copied))
        object.__setattr__(self, "request_id", self.request_id.strip())
        object.__setattr__(self, "sim_time_s", float(self.sim_time_s))
        if self.rgb_ref is not None:
            object.__setattr__(self, "rgb_ref", self.rgb_ref.strip())

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": QWEN_BOUNDARY_SCHEMA_VERSION,
            "request_id": self.request_id,
            "frame": self.frame,
            "sim_time_s": self.sim_time_s,
            "voice_command": self.voice_command,
            "rgb_ref": self.rgb_ref,
            "scene_state": dict(self.scene_state),
            "perception": dict(self.perception),
            "safety_state": dict(self.safety_state),
        }


@dataclass(frozen=True, slots=True)
class QwenBoundaryFailure:
    """Fail-closed signal consumed by the deterministic control/watchdog path."""

    status: str
    error: str
    watchdog_alerts: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"PENDING", "TIMEOUT", "STALE", "ERROR"}:
            raise ValueError("unsupported Qwen failure status")
        if type(self.error) is not str or not self.error:
            raise ValueError("error must be non-empty")
        if not self.watchdog_alerts:
            raise ValueError("fail-closed result requires a watchdog alert")


def validate_qwen_response(payload: object) -> dict[str, Any]:
    """Parse and strictly normalize one high-level Qwen decision.

    A single JSON-only Markdown fence is normalized because Qwen2.5-VL may
    add that wrapper even when explicitly asked for raw JSON.  Extra prose,
    multiple fences, unknown fields and low-level controls remain rejected.
    The returned plain dict is safe to pass to the Day22 command adapter.
    """
    if type(payload) is str:
        payload = _unwrap_single_json_fence(payload)
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ValueError("Qwen response must be one JSON object without prose") from error
    if not isinstance(payload, Mapping):
        raise TypeError("Qwen response must be a mapping or JSON object string")
    keys = set(payload)
    forbidden = FORBIDDEN_LOW_LEVEL_FIELDS.intersection(keys)
    if forbidden:
        raise ValueError(
            "Qwen response contains forbidden low-level fields: "
            + ",".join(sorted(forbidden))
        )
    missing = _REQUIRED_RESPONSE_FIELDS - keys
    unknown = keys - _ALLOWED_RESPONSE_FIELDS
    if missing or unknown:
        raise ValueError(
            f"Qwen response fields mismatch; missing={sorted(missing)}, "
            f"unknown={sorted(unknown)}"
        )

    action = _nonempty_text(payload["action"], "action").upper()
    if action not in SUPPORTED_INTENTS:
        raise ValueError(f"unsupported Qwen action: {action}")
    confidence = _bounded_number(payload["confidence"], "confidence", 0.0, 1.0)
    confirmation = payload["requires_confirmation"]
    if type(confirmation) is not bool:
        raise TypeError("requires_confirmation must be bool")

    normalized: dict[str, Any] = {
        "action": action,
        "confidence": confidence,
        "requires_confirmation": confirmation,
    }
    target = payload.get("target_speed_mps")
    if action == "SET_SPEED" and target is None:
        raise ValueError("SET_SPEED requires target_speed_mps")
    if target is not None:
        if action not in {"SET_SPEED", "SLOW_DOWN"}:
            raise ValueError(f"{action} must not include target_speed_mps")
        normalized["target_speed_mps"] = _bounded_number(
            target, "target_speed_mps", 0.0, 50.0,
        )
    for name in ("reason_zh", "decision_source"):
        if name in payload:
            normalized[name] = _nonempty_text(payload[name], name)
    if "visual_valid" in payload:
        if type(payload["visual_valid"]) is not bool:
            raise TypeError("visual_valid must be bool")
        normalized["visual_valid"] = payload["visual_valid"]
    return normalized


def _unwrap_single_json_fence(payload: str) -> str:
    stripped = payload.strip()
    if not stripped.startswith("```"):
        return stripped
    match = re.fullmatch(
        r"```(?:json)?[ \t]*\r?\n(?P<body>[\s\S]*?)\r?\n```",
        stripped,
        flags=re.IGNORECASE,
    )
    if match is None or "```" in match.group("body"):
        raise ValueError("Qwen response must be one JSON object without prose")
    return match.group("body").strip()


def fail_closed(status: str, error: str) -> QwenBoundaryFailure:
    """Convert a non-ready Qwen state into a deterministic watchdog signal."""
    normalized = str(status).strip().upper()
    alerts = {
        "PENDING": ("QWEN_PENDING",),
        "TIMEOUT": ("QWEN_TIMEOUT",),
        "STALE": ("QWEN_STALE",),
        "ERROR": ("QWEN_ERROR",),
    }
    try:
        watchdog = alerts[normalized]
    except KeyError as exception:
        raise ValueError(f"unsupported Qwen failure status: {status!r}") from exception
    return QwenBoundaryFailure(normalized, str(error) or normalized, watchdog)


def _json_mapping(name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if any(type(key) is not str for key in copied):
        raise TypeError(f"{name} keys must be strings")
    try:
        json.dumps(copied, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must contain JSON-safe finite values") from error
    return copied


def _nonempty_text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _bounded_number(value: object, name: str, minimum: float, maximum: float) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{name} must be finite and in [{minimum}, {maximum}]")
    return result


__all__ = [
    "QWEN_BOUNDARY_SCHEMA_VERSION",
    "QwenBoundaryFailure",
    "QwenInputContext",
    "fail_closed",
    "validate_qwen_response",
]
