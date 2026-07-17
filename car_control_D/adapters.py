"""Adapters that accept dicts or A/C dataclasses and convert them to D views."""
from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from .schemas import CommandView, ControlOutput, RiskView, VehicleStateView, SCHEMA_VERSION


def _as_mapping(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "to_dict"):
        return dict(obj.to_dict())
    return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_") and not callable(getattr(obj, k))}


def optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("bool is not a float")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError("non-finite float")
    return f


def _get(d: Dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in d:
            return d[name]
    return default


def adapt_control(obj: Any) -> ControlOutput:
    d = _as_mapping(obj)
    return ControlOutput(
        throttle=optional_float(_get(d, "throttle", default=0.0)) or 0.0,
        brake=optional_float(_get(d, "brake", default=0.0)) or 0.0,
        steer=optional_float(_get(d, "steer", default=0.0)) or 0.0,
    )


def adapt_command(obj: Any) -> CommandView:
    d = _as_mapping(obj)
    intent_confidence = optional_float(d.get("intent_confidence", d.get("confidence", 1.0)))
    confidence = optional_float(d.get("confidence", d.get("intent_confidence", 1.0)))
    return CommandView(
        schema_version=str(d.get("schema_version", SCHEMA_VERSION)),
        command_id=str(d.get("command_id", "")),
        source_text=str(d.get("source_text", "")),
        intent=str(d.get("intent", "UNKNOWN")).upper(),
        parameters=dict(d.get("parameters", {}) or {}),
        asr_confidence=optional_float(d.get("asr_confidence")) if d.get("asr_confidence") is not None else None,
        intent_confidence=1.0 if intent_confidence is None else intent_confidence,
        status=str(d.get("status", "valid")),
        ambiguity_type=str(d.get("ambiguity_type", "NONE")).upper(),
        confirm_required=bool(d.get("confirm_required", False)),
        errors=list(d.get("errors", []) or []),
        warnings=list(d.get("warnings", []) or []),
        confidence=1.0 if confidence is None else confidence,
        t_audio_start_ns=d.get("t_audio_start_ns"),
        t_asr_end_ns=d.get("t_asr_end_ns"),
        t_intent_end_ns=d.get("t_intent_end_ns"),
        valid_duration_s=optional_float(d.get("valid_duration_s", 5.0)) or 5.0,
    )


def adapt_vehicle_state(obj: Any) -> VehicleStateView:
    d = _as_mapping(obj)
    return VehicleStateView(
        frame=int(_get(d, "frame", "frame_id", default=0) or 0),
        sim_time_s=optional_float(_get(d, "sim_time_s", "sim_time", default=0.0)) or 0.0,
        speed_mps=optional_float(_get(d, "speed_mps", default=0.0)) or 0.0,
        x_m=optional_float(_get(d, "x_m", "x", default=0.0)) or 0.0,
        y_m=optional_float(_get(d, "y_m", "y", default=0.0)) or 0.0,
        z_m=optional_float(_get(d, "z_m", "z", default=0.0)) or 0.0,
        yaw_deg=optional_float(_get(d, "yaw_deg", default=0.0)) or 0.0,
        lane_id=int(_get(d, "lane_id", default=0) or 0),
        front_distance_m=optional_float(_get(d, "front_distance_m", "front_distance", default=None)),
        distance_to_stop_line_m=optional_float(_get(d, "distance_to_stop_line_m", "stop_line_distance", default=None)),
        traffic_light=str(_get(d, "traffic_light", "signal_state", default="UNKNOWN")).upper(),
        lane_offset_m=optional_float(_get(d, "lane_offset_m", "lane_offset", default=None)),
        route_deviation_m=optional_float(_get(d, "route_deviation_m", "route_deviation", default=None)),
        collision=bool(_get(d, "collision", default=False)),
        red_light_violation=bool(_get(d, "red_light_violation", default=False)),
        lane_invasion=bool(_get(d, "lane_invasion", default=False)),
    )


def adapt_risk(obj: Any) -> RiskView:
    d = _as_mapping(obj)
    return RiskView(
        ttc_s=optional_float(_get(d, "ttc_s", "ttc", default=None)),
        desired_gap_m=optional_float(_get(d, "desired_gap_m", default=None)),
        emergency_brake_requested=bool(_get(d, "emergency_brake_requested", default=False)),
    )
