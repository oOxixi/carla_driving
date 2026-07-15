"""Strict, serialisable configuration for C's local command safety policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


CONFIG_SCHEMA_VERSION = "1.0"


def _finite(name: str, value: object, *, minimum: float | None = None,
            maximum: float | None = None, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be an int or float, not {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if positive and number <= 0.0:
        raise ValueError(f"{name} must be positive")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return number


@dataclass(frozen=True, slots=True)
class FuzzyCommandPolicyConfig:
    """SI-only policy parameters; D remains the final safety authority."""

    confidence_threshold: float = 0.80
    comfort_decel_mps2: float = 3.0
    max_decel_mps2: float = 5.0
    hold_brake: float = 0.55
    emergency_brake: float = 0.85
    standstill_speed_mps: float = 0.20

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence_threshold", _finite(
            "confidence_threshold", self.confidence_threshold, minimum=0.0, maximum=1.0))
        object.__setattr__(self, "comfort_decel_mps2", _finite(
            "comfort_decel_mps2", self.comfort_decel_mps2, positive=True))
        object.__setattr__(self, "max_decel_mps2", _finite(
            "max_decel_mps2", self.max_decel_mps2, positive=True))
        if self.comfort_decel_mps2 > self.max_decel_mps2:
            raise ValueError("comfort_decel_mps2 must not exceed max_decel_mps2")
        object.__setattr__(self, "hold_brake", _finite(
            "hold_brake", self.hold_brake, positive=True, maximum=1.0))
        object.__setattr__(self, "emergency_brake", _finite(
            "emergency_brake", self.emergency_brake, positive=True, maximum=1.0))
        object.__setattr__(self, "standstill_speed_mps", _finite(
            "standstill_speed_mps", self.standstill_speed_mps, minimum=0.0))

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONFIG_SCHEMA_VERSION, **asdict(self)}

    @classmethod
    def from_dict(cls, payload: object) -> "FuzzyCommandPolicyConfig":
        if type(payload) is not dict:
            raise TypeError("payload must be a plain dict")
        fields = {"schema_version", "confidence_threshold", "comfort_decel_mps2",
                  "max_decel_mps2", "hold_brake", "emergency_brake", "standstill_speed_mps"}
        if set(payload) != fields:
            missing, unknown = fields - set(payload), set(payload) - fields
            raise ValueError(f"payload fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
        if payload["schema_version"] != CONFIG_SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        return cls(**{name: payload[name] for name in fields - {"schema_version"}})
