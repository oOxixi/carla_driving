"""Versioned, CARLA-independent contracts shared by A and C.

Every dictionary boundary is strict: it carries ``schema_version`` and accepts no
unknown, missing, coercible, non-finite, or mismatched fields.  Longitudinal
quantities use SI units; speed fields express speed magnitudes unless explicitly
named ``closing_speed_mps`` or ``target_accel_mps2``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from compat import StrEnum


CONTRACT_VERSION = "1.0"
LOW_CONFIDENCE_THRESHOLD = 0.80


def _number(name: str, value: object, *, minimum: float | None = None) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be an int or float, not {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def _integer(name: str, value: object, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _text(name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _boolean(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def _payload(payload: object, fields: set[str]) -> dict[str, Any]:
    if type(payload) is not dict:
        raise TypeError("payload must be a plain dict")
    expected = fields | {"schema_version"}
    actual = set(payload)
    if actual != expected:
        missing, unknown = expected - actual, actual - expected
        raise ValueError(f"payload fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
    if type(payload["schema_version"]) is not str or payload["schema_version"] != CONTRACT_VERSION:
        raise ValueError(f"unsupported schema_version: {payload['schema_version']!r}")
    return payload


class SignalState(StrEnum):
    """UNKNOWN deliberately denotes an uncertain perception result."""

    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RuntimeVehicleState:
    frame: int
    sim_time_s: float
    speed_mps: float
    x_m: float
    y_m: float
    z_m: float
    yaw_deg: float
    lane_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame", _integer("frame", self.frame, minimum=0))
        object.__setattr__(self, "sim_time_s", _number("sim_time_s", self.sim_time_s, minimum=0.0))
        object.__setattr__(self, "speed_mps", _number("speed_mps", self.speed_mps, minimum=0.0))
        for name in ("x_m", "y_m", "z_m", "yaw_deg"):
            object.__setattr__(self, name, _number(name, getattr(self, name)))
        _text("lane_id", self.lane_id)

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "frame": self.frame, "sim_time_s": self.sim_time_s,
                "speed_mps": self.speed_mps, "x_m": self.x_m, "y_m": self.y_m, "z_m": self.z_m,
                "yaw_deg": self.yaw_deg, "lane_id": self.lane_id}

    @classmethod
    def from_dict(cls, payload: object) -> RuntimeVehicleState:
        data = _payload(payload, {"frame", "sim_time_s", "speed_mps", "x_m", "y_m", "z_m", "yaw_deg", "lane_id"})
        return cls(**{key: data[key] for key in data if key != "schema_version"})


@dataclass(frozen=True, slots=True)
class DrivingCommand:
    command_id: str
    received_at_s: float
    expires_at_s: float
    confidence: float
    action: str
    target_speed_mps: float | None = None
    is_ambiguous: bool = False
    confirmation_requested: bool = False

    def __post_init__(self) -> None:
        _text("command_id", self.command_id)
        _text("action", self.action)
        received = _number("received_at_s", self.received_at_s, minimum=0.0)
        expires = _number("expires_at_s", self.expires_at_s, minimum=0.0)
        confidence = _number("confidence", self.confidence, minimum=0.0)
        if expires < received:
            raise ValueError("expires_at_s must not precede received_at_s")
        if confidence > 1.0:
            raise ValueError("confidence must be <= 1.0")
        if self.target_speed_mps is not None:
            object.__setattr__(self, "target_speed_mps", _number("target_speed_mps", self.target_speed_mps, minimum=0.0))
        _boolean("is_ambiguous", self.is_ambiguous)
        _boolean("confirmation_requested", self.confirmation_requested)
        object.__setattr__(self, "received_at_s", received)
        object.__setattr__(self, "expires_at_s", expires)
        object.__setattr__(self, "confidence", confidence)

    def is_expired_at(self, sim_time_s: float) -> bool:
        # Expiry is an inclusive safety boundary: at the stated deadline the
        # command is no longer authorised to influence the vehicle.
        return _number("sim_time_s", sim_time_s, minimum=0.0) >= self.expires_at_s

    @property
    def requires_confirmation(self) -> bool:
        return self.confirmation_requested or self.is_ambiguous or self.confidence < LOW_CONFIDENCE_THRESHOLD

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "command_id": self.command_id, "received_at_s": self.received_at_s,
                "expires_at_s": self.expires_at_s, "confidence": self.confidence, "action": self.action,
                "target_speed_mps": self.target_speed_mps, "is_ambiguous": self.is_ambiguous,
                "confirmation_requested": self.confirmation_requested}

    @classmethod
    def from_dict(cls, payload: object) -> DrivingCommand:
        data = _payload(payload, {"command_id", "received_at_s", "expires_at_s", "confidence", "action", "target_speed_mps", "is_ambiguous", "confirmation_requested"})
        return cls(**{key: data[key] for key in data if key != "schema_version"})


@dataclass(frozen=True, slots=True)
class TrafficConstraint:
    signal_state: SignalState
    distance_to_stop_line_m: float | None
    speed_limit_mps: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.signal_state, SignalState):
            raise TypeError("signal_state must be SignalState")
        if self.distance_to_stop_line_m is not None:
            object.__setattr__(self, "distance_to_stop_line_m", _number("distance_to_stop_line_m", self.distance_to_stop_line_m, minimum=0.0))
        if self.speed_limit_mps is not None:
            object.__setattr__(self, "speed_limit_mps", _number("speed_limit_mps", self.speed_limit_mps, minimum=0.0))

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "signal_state": self.signal_state.value,
                "distance_to_stop_line_m": self.distance_to_stop_line_m, "speed_limit_mps": self.speed_limit_mps}

    @classmethod
    def from_dict(cls, payload: object) -> TrafficConstraint:
        data = _payload(payload, {"signal_state", "distance_to_stop_line_m", "speed_limit_mps"})
        if type(data["signal_state"]) is not str:
            raise TypeError("signal_state must be a string enum value")
        try:
            signal_state = SignalState(data["signal_state"])
        except ValueError as error:
            raise ValueError("signal_state is invalid") from error
        return cls(signal_state, data["distance_to_stop_line_m"], data["speed_limit_mps"])


@dataclass(frozen=True, slots=True)
class LongitudinalRequest:
    """Frame-aligned input for C's longitudinal controller.

    ``closing_speed_mps = ego_speed_mps - lead_speed_mps``.  A positive value
    means the ego vehicle is approaching the lead vehicle; zero or a negative
    value must not trigger time-to-collision (TTC) braking calculations.
    """

    vehicle: RuntimeVehicleState
    requested_speed_mps: float
    path_curvature_per_m: float
    traffic: TrafficConstraint | None = None
    lead_distance_m: float | None = None
    closing_speed_mps: float | None = None  # ego_speed_mps - lead_speed_mps; positive means closing.

    def __post_init__(self) -> None:
        if not isinstance(self.vehicle, RuntimeVehicleState):
            raise TypeError("vehicle must be RuntimeVehicleState")
        object.__setattr__(self, "requested_speed_mps", _number("requested_speed_mps", self.requested_speed_mps, minimum=0.0))
        object.__setattr__(self, "path_curvature_per_m", _number("path_curvature_per_m", self.path_curvature_per_m))
        if self.traffic is not None and not isinstance(self.traffic, TrafficConstraint):
            raise TypeError("traffic must be TrafficConstraint or None")
        if (self.lead_distance_m is None) != (self.closing_speed_mps is None):
            raise ValueError("lead_distance_m and closing_speed_mps must be provided together")
        if self.lead_distance_m is not None:
            object.__setattr__(self, "lead_distance_m", _number("lead_distance_m", self.lead_distance_m, minimum=0.0))
            object.__setattr__(self, "closing_speed_mps", _number("closing_speed_mps", self.closing_speed_mps))

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "vehicle": self.vehicle.to_dict(),
                "requested_speed_mps": self.requested_speed_mps, "path_curvature_per_m": self.path_curvature_per_m,
                "traffic": None if self.traffic is None else self.traffic.to_dict(), "lead_distance_m": self.lead_distance_m,
                "closing_speed_mps": self.closing_speed_mps}

    @classmethod
    def from_dict(cls, payload: object) -> LongitudinalRequest:
        data = _payload(payload, {"vehicle", "requested_speed_mps", "path_curvature_per_m", "traffic", "lead_distance_m", "closing_speed_mps"})
        if type(data["vehicle"]) is not dict:
            raise TypeError("vehicle must be an object")
        if data["traffic"] is not None and type(data["traffic"]) is not dict:
            raise TypeError("traffic must be an object or null")
        return cls(RuntimeVehicleState.from_dict(data["vehicle"]), data["requested_speed_mps"], data["path_curvature_per_m"],
                   None if data["traffic"] is None else TrafficConstraint.from_dict(data["traffic"]),
                   data["lead_distance_m"], data["closing_speed_mps"])


@dataclass(frozen=True, slots=True)
class ControlOutput:
    throttle: float
    brake: float
    steer: float = 0.0

    def __post_init__(self) -> None:
        throttle = _number("throttle", self.throttle, minimum=0.0)
        brake = _number("brake", self.brake, minimum=0.0)
        steer = _number("steer", self.steer)
        if throttle > 1.0 or brake > 1.0:
            raise ValueError("throttle and brake must be <= 1.0")
        if not -1.0 <= steer <= 1.0:
            raise ValueError("steer must be in [-1.0, 1.0]")
        if throttle > 0.0 and brake > 0.0:
            raise ValueError("throttle and brake are mutually exclusive")
        object.__setattr__(self, "throttle", throttle)
        object.__setattr__(self, "brake", brake)
        object.__setattr__(self, "steer", steer)

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "throttle": self.throttle, "brake": self.brake, "steer": self.steer}

    @classmethod
    def from_dict(cls, payload: object) -> ControlOutput:
        data = _payload(payload, {"throttle", "brake", "steer"})
        return cls(data["throttle"], data["brake"], data["steer"])


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    ttc_s: float | None
    desired_gap_m: float
    emergency_brake_requested: bool

    def __post_init__(self) -> None:
        if self.ttc_s is not None:
            object.__setattr__(self, "ttc_s", _number("ttc_s", self.ttc_s, minimum=0.0))
        object.__setattr__(self, "desired_gap_m", _number("desired_gap_m", self.desired_gap_m, minimum=0.0))
        _boolean("emergency_brake_requested", self.emergency_brake_requested)

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "ttc_s": self.ttc_s, "desired_gap_m": self.desired_gap_m,
                "emergency_brake_requested": self.emergency_brake_requested}

    @classmethod
    def from_dict(cls, payload: object) -> RiskMetrics:
        data = _payload(payload, {"ttc_s", "desired_gap_m", "emergency_brake_requested"})
        return cls(data["ttc_s"], data["desired_gap_m"], data["emergency_brake_requested"])


@dataclass(frozen=True, slots=True)
class LongitudinalOutput:
    control: ControlOutput
    target_accel_mps2: float
    target_speed_mps: float
    state: str
    reason: str
    risk: RiskMetrics

    def __post_init__(self) -> None:
        if not isinstance(self.control, ControlOutput) or not isinstance(self.risk, RiskMetrics):
            raise TypeError("control and risk must use their declared contracts")
        object.__setattr__(self, "target_accel_mps2", _number("target_accel_mps2", self.target_accel_mps2))
        object.__setattr__(self, "target_speed_mps", _number("target_speed_mps", self.target_speed_mps, minimum=0.0))
        _text("state", self.state)
        _text("reason", self.reason)

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "control": self.control.to_dict(), "target_accel_mps2": self.target_accel_mps2,
                "target_speed_mps": self.target_speed_mps, "state": self.state, "reason": self.reason,
                "risk": self.risk.to_dict()}

    @classmethod
    def from_dict(cls, payload: object) -> LongitudinalOutput:
        data = _payload(payload, {"control", "target_accel_mps2", "target_speed_mps", "state", "reason", "risk"})
        if type(data["control"]) is not dict or type(data["risk"]) is not dict:
            raise TypeError("control and risk must be objects")
        return cls(ControlOutput.from_dict(data["control"]), data["target_accel_mps2"], data["target_speed_mps"],
                   data["state"], data["reason"], RiskMetrics.from_dict(data["risk"]))


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True, slots=True)
class ExecutionFeedback:
    command_id: str
    status: ExecutionStatus
    completed_at_s: float
    detail: str

    def __post_init__(self) -> None:
        _text("command_id", self.command_id)
        if not isinstance(self.status, ExecutionStatus):
            raise TypeError("status must be an ExecutionStatus")
        object.__setattr__(self, "completed_at_s", _number("completed_at_s", self.completed_at_s, minimum=0.0))
        _text("detail", self.detail)

    @property
    def is_terminal(self) -> bool:
        return True

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CONTRACT_VERSION, "command_id": self.command_id, "status": self.status.value,
                "completed_at_s": self.completed_at_s, "detail": self.detail}

    @classmethod
    def from_dict(cls, payload: object) -> ExecutionFeedback:
        data = _payload(payload, {"command_id", "status", "completed_at_s", "detail"})
        if type(data["status"]) is not str:
            raise TypeError("status must be a string enum value")
        try:
            status = ExecutionStatus(data["status"])
        except ValueError as error:
            raise ValueError("status is invalid") from error
        return cls(data["command_id"], status, data["completed_at_s"], data["detail"])


__all__ = [
    "CONTRACT_VERSION", "LOW_CONFIDENCE_THRESHOLD", "SignalState", "RuntimeVehicleState", "DrivingCommand",
    "TrafficConstraint", "LongitudinalRequest", "ControlOutput", "RiskMetrics", "LongitudinalOutput",
    "ExecutionStatus", "ExecutionFeedback",
]
