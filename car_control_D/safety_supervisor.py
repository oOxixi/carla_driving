"""Final safety arbitration for D.

D is called after B/C produce raw controls and before A applies CARLA VehicleControl.
D does not call CARLA APIs directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .adapters import adapt_command, adapt_control, adapt_risk, adapt_vehicle_state
from .schemas import ControlOutput, SafetyDecision
from .validators import validate_command, validate_control


@dataclass(frozen=True)
class SafetyConfig:
    min_front_distance_m: float = 5.0
    low_ttc_s: float = 1.5
    caution_ttc_s: float = 2.5
    stop_line_guard_m: float = 8.0
    max_lane_offset_m: float = 1.8
    severe_route_deviation_m: float = 3.0
    low_confidence_threshold: float = 0.80
    hold_brake: float = 0.55
    emergency_brake: float = 1.0
    caution_brake: float = 0.35


class SafetySupervisor:
    def __init__(self, config: Optional[SafetyConfig] = None) -> None:
        self.config = config or SafetyConfig()

    def arbitrate(
        self,
        raw_control: Any,
        vehicle_state: Any = None,
        command: Any = None,
        risk: Any = None,
        watchdog_alerts: Optional[Iterable[str]] = None,
    ) -> SafetyDecision:
        cfg = self.config
        control_result = validate_control(raw_control)
        try:
            raw = adapt_control(raw_control)
        except Exception:
            raw = ControlOutput(throttle=0.0, brake=0.0, steer=0.0)
        vs = adapt_vehicle_state(vehicle_state or {})
        rv = adapt_risk(risk or {})
        command_provided = command is not None
        cmd = adapt_command(command or {"schema_version":"1.0", "command_id":"", "source_text":"", "intent":"UNKNOWN"})
        cmd_result = validate_command(command or cmd.to_dict()) if command is not None else None

        metrics = {
            "front_distance_m": vs.front_distance_m,
            "ttc_s": rv.ttc_s,
            "lane_offset_m": vs.lane_offset_m,
            "route_deviation_m": vs.route_deviation_m,
            "traffic_light": vs.traffic_light,
        }

        def stop(reason: str, brake: Optional[float] = None, steer: float = 0.0) -> SafetyDecision:
            return SafetyDecision(
                final_control=ControlOutput(throttle=0.0, brake=brake if brake is not None else cfg.emergency_brake, steer=steer),
                safety_override=True,
                reason=reason,
                risk_metrics=metrics,
                raw_control=raw,
            )

        def caution(reason: str) -> SafetyDecision:
            return SafetyDecision(
                final_control=ControlOutput(throttle=0.0, brake=max(raw.brake, cfg.caution_brake), steer=max(min(raw.steer, 0.35), -0.35)),
                safety_override=True,
                reason=reason,
                risk_metrics=metrics,
                raw_control=raw,
            )

        if not control_result.valid:
            return stop("INVALID_CONTROL_OUTPUT")
        if watchdog_alerts:
            return stop("WATCHDOG_ALERT")
        if command_provided and cmd.intent in {"EMERGENCY_STOP", "STOP"}:
            return stop(f"COMMAND_{cmd.intent}")
        if command_provided and (cmd.intent == "UNKNOWN" or (cmd_result and not cmd_result.valid)):
            return stop("COMMAND_REJECTED", brake=cfg.hold_brake)
        if command_provided and (cmd.confirm_required or cmd.ambiguity_type not in {"NONE", ""} or
                                 cmd.confidence < cfg.low_confidence_threshold):
            return stop("COMMAND_NEEDS_CONFIRMATION", brake=cfg.hold_brake)
        if rv.emergency_brake_requested:
            return stop("RISK_EMERGENCY_BRAKE_REQUESTED")
        if rv.ttc_s is not None and rv.ttc_s <= cfg.low_ttc_s:
            return stop("LOW_TTC")
        if vs.front_distance_m is not None and vs.front_distance_m <= cfg.min_front_distance_m:
            return stop("FRONT_OBSTACLE_TOO_CLOSE")
        if vs.distance_to_stop_line_m is not None and vs.distance_to_stop_line_m <= cfg.stop_line_guard_m:
            if vs.traffic_light in {"RED", "YELLOW", "UNKNOWN"} and raw.throttle > 0.05:
                return stop("STOP_LINE_OR_LIGHT_GUARD")
        if vs.route_deviation_m is not None and abs(vs.route_deviation_m) >= cfg.severe_route_deviation_m:
            return stop("SEVERE_ROUTE_DEVIATION")
        if vs.lane_offset_m is not None and abs(vs.lane_offset_m) >= cfg.max_lane_offset_m:
            return caution("LANE_OFFSET_TOO_LARGE")
        if rv.ttc_s is not None and rv.ttc_s <= cfg.caution_ttc_s:
            return caution("CAUTION_TTC")

        return SafetyDecision(
            final_control=raw,
            safety_override=False,
            reason="NONE",
            risk_metrics=metrics,
            raw_control=raw,
        )
