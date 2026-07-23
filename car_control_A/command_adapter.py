"""Conservative conversion of recognised speech text into driving commands.

Only unambiguous, bounded basic actions take the fast path.  Everything else is
represented as a request for the asynchronous multimodal decision provider;
this module intentionally never invents a manoeuvre for a complex utterance.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Protocol, runtime_checkable

from compat import StrEnum
from .contracts import DrivingCommand


class CommandDisposition(StrEnum):
    FAST_PATH = "FAST_PATH"
    NEEDS_DECISION = "NEEDS_DECISION"


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    command_id: str
    text: str
    received_at_s: float
    expires_at_s: float
    confidence: float


@dataclass(frozen=True, slots=True)
class AdaptedCommand:
    disposition: CommandDisposition
    command: DrivingCommand | None = None
    decision_request: DecisionRequest | None = None

    def __post_init__(self) -> None:
        if (self.command is None) == (self.decision_request is None):
            raise ValueError("exactly one of command or decision_request is required")


@runtime_checkable
class DecisionProvider(Protocol):
    """Future VLM/decision module boundary; it may execute asynchronously."""

    def submit(self, request: DecisionRequest) -> None: ...


_SPEED_RE = re.compile(r"(?:请)?(?:设置(?:到|为)?|速度(?:设置)?(?:到|为)?|以)?\s*(\d+(?:\.\d+)?)\s*(?:公里每小时|千米每小时|km/?h|kph)", re.IGNORECASE)


class CommandAdapter:
    def __init__(self, *, default_ttl_s: float = 5.0) -> None:
        if type(default_ttl_s) not in (int, float):
            raise TypeError("default_ttl_s must be an int or float")
        ttl = float(default_ttl_s)
        if not math.isfinite(ttl) or ttl <= 0.0:
            raise ValueError("default_ttl_s must be finite and positive")
        self._default_ttl_s = ttl

    def adapt(self, text: str, *, command_id: str, now_s: float, confidence: float,
              expires_at_s: float | None = None) -> AdaptedCommand:
        if type(text) is not str or not text.strip():
            raise ValueError("text must be a non-empty string")
        if type(command_id) is not str or not command_id.strip():
            raise ValueError("command_id must be a non-empty string")
        received_at = self._finite_nonnegative("now_s", now_s)
        confidence_value = self._finite_nonnegative("confidence", confidence)
        if confidence_value > 1.0:
            raise ValueError("confidence must be <= 1.0")
        expiry = received_at + self._default_ttl_s if expires_at_s is None else self._finite_nonnegative("expires_at_s", expires_at_s)
        if expiry < received_at:
            raise ValueError("expires_at_s must not precede now_s")
        normalized = re.sub(r"\s+", "", text).lower()
        action: str | None = None
        target_speed_mps: float | None = None
        if any(word in normalized for word in ("紧急刹车", "紧急制动", "立刻刹车")):
            action = "EMERGENCY_BRAKE"
        elif normalized in {"停车", "停止", "停下", "请停车", "请停止"}:
            action = "STOP"
        else:
            match = _SPEED_RE.fullmatch(normalized)
            if match:
                target_speed_mps = float(match.group(1)) / 3.6
                action = "SET_SPEED"
        if action is not None:
            return AdaptedCommand(CommandDisposition.FAST_PATH, command=DrivingCommand(
                command_id, received_at, expiry, confidence_value, action, target_speed_mps,
            ))
        return AdaptedCommand(CommandDisposition.NEEDS_DECISION, decision_request=DecisionRequest(
            command_id, text, received_at, expiry, confidence_value,
        ))

    @staticmethod
    def _finite_nonnegative(name: str, value: object) -> float:
        if type(value) not in (int, float):
            raise TypeError(f"{name} must be an int or float")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"{name} must be finite")
        if result < 0.0:
            raise ValueError(f"{name} must be non-negative")
        return result
