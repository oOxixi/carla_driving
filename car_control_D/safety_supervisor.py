"""Final safety arbitration for D.

D is called after B/C produce raw controls and before A applies CARLA VehicleControl.
D does not call CARLA APIs directly.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Optional

from .adapters import adapt_command, adapt_control, adapt_risk, adapt_vehicle_state
from .schemas import CommandView, ControlOutput, RiskView, SafetyDecision, VehicleStateView
from .validators import validate_command, validate_control


@dataclass(frozen=True)
class SafetyConfig:
    min_front_distance_m: float = 5.0
    low_ttc_s: float = 1.5
    caution_ttc_s: float = 2.5
    stop_line_guard_m: float = 8.0
    max_lane_offset_m: float = 1.8
    severe_route_deviation_m: float = 3.0
    route_recovery_max_speed_mps: float = 1.5
    route_recovery_throttle: float = 0.15
    route_recovery_steer_limit: float = 0.35
    low_confidence_threshold: float = 0.80
    hold_brake: float = 0.55
    emergency_brake: float = 1.0
    caution_brake: float = 0.35
    standstill_speed_mps: float = 0.15

    def __post_init__(self) -> None:
        values = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }
        if any(
            type(value) not in (int, float) or not math.isfinite(float(value))
            for value in values.values()
        ):
            raise ValueError("all safety configuration values must be finite numbers")
        if any(float(values[name]) < 0.0 for name in (
            "min_front_distance_m", "low_ttc_s", "caution_ttc_s",
            "stop_line_guard_m", "max_lane_offset_m",
            "severe_route_deviation_m", "route_recovery_max_speed_mps",
            "standstill_speed_mps",
        )):
            raise ValueError("safety distances, times and speeds must be non-negative")
        if self.low_ttc_s > self.caution_ttc_s:
            raise ValueError("low_ttc_s must not exceed caution_ttc_s")
        if self.max_lane_offset_m > self.severe_route_deviation_m:
            raise ValueError("max_lane_offset_m must not exceed severe_route_deviation_m")
        if any(not 0.0 <= float(values[name]) <= 1.0 for name in (
            "route_recovery_throttle", "route_recovery_steer_limit",
            "low_confidence_threshold", "hold_brake", "emergency_brake",
            "caution_brake",
        )):
            raise ValueError("control and confidence configuration values must be in [0, 1]")


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
        state_error = False
        risk_error = False
        command_error = False
        try:
            vs = adapt_vehicle_state(vehicle_state or {})
        except Exception:
            vs = VehicleStateView()
            state_error = True
        try:
            rv = adapt_risk(risk or {})
        except Exception:
            rv = RiskView()
            risk_error = True
        command_provided = command is not None
        try:
            cmd = adapt_command(command or {
                "schema_version": "1.0",
                "command_id": "",
                "source_text": "",
                "intent": "UNKNOWN",
            })
        except Exception:
            cmd = CommandView("1.0", "", "", "UNKNOWN")
            command_error = True
        cmd_result = validate_command(command or cmd.to_dict()) if command is not None else None
        try:
            alerts = tuple(watchdog_alerts or ())
        except Exception:
            alerts = ("INVALID_WATCHDOG_ALERTS",)
        if any(type(alert) is not str or not alert.strip() for alert in alerts):
            alerts = ("INVALID_WATCHDOG_ALERTS",)

        metrics = {
            "front_distance_m": vs.front_distance_m,
            "ttc_s": rv.ttc_s,
            "lane_offset_m": vs.lane_offset_m,
            "route_deviation_m": vs.route_deviation_m,
            "traffic_light": vs.traffic_light,
            "watchdog_alerts": list(alerts),
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

        def recover_route() -> SafetyDecision:
            steer = max(min(raw.steer, cfg.route_recovery_steer_limit), -cfg.route_recovery_steer_limit)
            if vs.speed_mps >= cfg.route_recovery_max_speed_mps:
                control = ControlOutput(
                    throttle=0.0,
                    brake=max(raw.brake, cfg.caution_brake),
                    steer=steer,
                )
            elif raw.brake > 0.0:
                control = ControlOutput(throttle=0.0, brake=raw.brake, steer=steer)
            else:
                control = ControlOutput(
                    throttle=min(raw.throttle, cfg.route_recovery_throttle),
                    brake=0.0,
                    steer=steer,
                )
            return SafetyDecision(
                final_control=control,
                safety_override=True,
                reason="ROUTE_DEVIATION_RECOVERY",
                risk_metrics=metrics,
                raw_control=raw,
            )

        if not control_result.valid:
            detail = "_".join(control_result.errors).upper().replace(" ", "_")
            if "THROTTLE_AND_BRAKE_CONFLICT" in detail:
                return stop("INVALID_CONTROL_OUTPUT_THROTTLE_BRAKE_CONFLICT")
            return stop("INVALID_CONTROL_OUTPUT")
        if state_error:
            return stop("INVALID_VEHICLE_STATE")
        if risk_error:
            return stop("INVALID_RISK_STATE")
        if alerts:
            return stop("WATCHDOG_ALERT")
        if vs.collision:
            return stop("COLLISION_DETECTED")
        if vs.red_light_violation:
            return stop("RED_LIGHT_VIOLATION_DETECTED")
        if command_provided and cmd.intent in {"EMERGENCY_STOP", "STOP"}:
            return stop(f"COMMAND_{cmd.intent}")
        if command_provided and (
            command_error or cmd.intent == "UNKNOWN" or (cmd_result and not cmd_result.valid)
        ):
            return stop("COMMAND_REJECTED", brake=cfg.hold_brake)
        if command_provided and (cmd.confirm_required or cmd.ambiguity_type not in {"NONE", ""} or
                                 cmd.confidence < cfg.low_confidence_threshold):
            return stop("COMMAND_NEEDS_CONFIRMATION", brake=cfg.hold_brake)
        if rv.emergency_brake_requested:
            return stop("RISK_EMERGENCY_BRAKE_REQUESTED")
        if rv.ttc_s is not None and rv.ttc_s <= cfg.low_ttc_s:
            return stop("LOW_TTC")
        if vs.front_distance_m is not None and vs.front_distance_m <= cfg.min_front_distance_m:
            return stop("EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE")
        if vs.distance_to_stop_line_m is not None and vs.distance_to_stop_line_m <= cfg.stop_line_guard_m:
            unsafe_light = vs.traffic_light in {"RED", "YELLOW", "UNKNOWN"}
            brake_hold_missing = raw.brake < cfg.hold_brake
            still_moving = vs.speed_mps > cfg.standstill_speed_mps
            if unsafe_light and (raw.throttle > 0.05 or still_moving or brake_hold_missing):
                return stop("RED_LIGHT_STOP_LINE_GUARD")
        if vs.route_deviation_m is not None and abs(vs.route_deviation_m) >= cfg.severe_route_deviation_m:
            return recover_route()
        # CARLA's nearest-lane waypoint can jump to a neighbouring branch in a
        # junction.  When an explicit route reference independently confirms
        # that ego remains inside the allowed corridor, it is the stronger
        # signal.  A missing or excessive route deviation still fails closed.
        route_confirms_lane_safe = (
            vs.route_deviation_m is not None
            and abs(vs.route_deviation_m) < cfg.max_lane_offset_m
        )
        if (vs.lane_offset_m is not None
                and abs(vs.lane_offset_m) >= cfg.max_lane_offset_m
                and not route_confirms_lane_safe):
            return caution("LANE_OFFSET_TOO_LARGE")
        if vs.lane_invasion and not route_confirms_lane_safe:
            return caution("LANE_INVASION_DETECTED")
        if rv.ttc_s is not None and rv.ttc_s <= cfg.caution_ttc_s:
            return caution("CAUTION_TTC")

        return SafetyDecision(
            final_control=raw,
            safety_override=False,
            reason="NONE",
            risk_metrics=metrics,
            raw_control=raw,
        )
