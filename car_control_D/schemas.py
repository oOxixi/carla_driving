"""Shared data structures for D: safety arbitration, scoring and evidence.

This file must not import other car_control_D modules. Other modules may import it.
That avoids circular imports during pytest collection.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"

ALLOWED_INTENTS = {
    "FORWARD",
    "STOP",
    "EMERGENCY_STOP",
    "PULL_OVER",
    "SET_SPEED",
    "AVOID_OBSTACLE",
    "CHANGE_LANE",
    "KEEP_LANE",
    "SPEED_UP",
    "SLOW_DOWN",
    "UNKNOWN",
}

TERMINAL_STATUSES = {
    "SUCCEEDED",
    "FAILED",
    "REJECTED",
    "EXPIRED",
    "TIMED_OUT",
    "SAFETY_OVERRIDE",
}


@dataclass(frozen=True)
class ControlOutput:
    throttle: float
    brake: float
    steer: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommandView:
    schema_version: str
    command_id: str
    source_text: str
    intent: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    asr_confidence: Optional[float] = None
    intent_confidence: float = 1.0
    status: str = "valid"
    ambiguity_type: str = "NONE"
    confirm_required: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0
    t_audio_start_ns: Optional[int] = None
    t_asr_end_ns: Optional[int] = None
    t_intent_end_ns: Optional[int] = None
    valid_duration_s: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VehicleStateView:
    frame: int = 0
    sim_time_s: float = 0.0
    speed_mps: float = 0.0
    x_m: float = 0.0
    y_m: float = 0.0
    z_m: float = 0.0
    yaw_deg: float = 0.0
    lane_id: int = 0
    front_distance_m: Optional[float] = None
    distance_to_stop_line_m: Optional[float] = None
    traffic_light: str = "UNKNOWN"
    lane_offset_m: Optional[float] = None
    route_deviation_m: Optional[float] = None
    collision: bool = False
    red_light_violation: bool = False
    lane_invasion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskView:
    ttc_s: Optional[float] = None
    desired_gap_m: Optional[float] = None
    emergency_brake_requested: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SafetyDecision:
    final_control: ControlOutput
    safety_override: bool
    reason: str = "NONE"
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    raw_control: Optional[ControlOutput] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioResult:
    scenario_id: str
    difficulty: str
    status: str
    collision_count: int = 0
    red_light_violation_count: int = 0
    route_deviation_count: int = 0
    unfinished_task_count: int = 0
    safety_override_count: int = 0
    command_count: int = 0
    e2e_latency_ms: Optional[float] = None
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
