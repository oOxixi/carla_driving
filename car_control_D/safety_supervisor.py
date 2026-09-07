"""Final safety arbitration for D.

D is called after B/C produce raw controls and before A applies CARLA VehicleControl.
D does not call CARLA APIs directly.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Optional
from strategy_config import DEFAULT_STRATEGY, dynamic_safety_distance

from .adapters import adapt_command, adapt_control, adapt_risk, adapt_vehicle_state
from .schemas import CommandView, ControlOutput, RiskView, SafetyDecision, VehicleStateView
from .validators import validate_command, validate_control


@dataclass(frozen=True)
class SafetyConfig:
    # ``min_front_distance_m`` is a compatibility floor. The operational
    # threshold is computed dynamically for every frame.
    min_front_distance_m: float = DEFAULT_STRATEGY.safety_distance.minimum_emergency_distance_m
    low_ttc_s: float = DEFAULT_STRATEGY.common.emergency_ttc_s
    caution_ttc_s: float = DEFAULT_STRATEGY.common.caution_ttc_s
    stop_line_guard_m: float = DEFAULT_STRATEGY.supervisor.stop_line_guard_m
    max_lane_offset_m: float = DEFAULT_STRATEGY.supervisor.max_lane_offset_m
    minimum_lane_offset_m: float = DEFAULT_STRATEGY.supervisor.minimum_lane_offset_m
    severe_route_deviation_m: float = DEFAULT_STRATEGY.supervisor.severe_route_deviation_m
    minimum_severe_route_deviation_m: float = DEFAULT_STRATEGY.supervisor.minimum_severe_route_deviation_m
    route_speed_sensitivity: float = DEFAULT_STRATEGY.supervisor.route_speed_sensitivity
    route_curvature_sensitivity: float = DEFAULT_STRATEGY.supervisor.route_curvature_sensitivity
    route_recovery_max_speed_mps: float = DEFAULT_STRATEGY.supervisor.route_recovery_max_speed_mps
    # Severe route deviation is not a condition in which D may authorize
    # propulsion. Recovery requires a newly validated route/steering reference.
    route_recovery_throttle: float = DEFAULT_STRATEGY.supervisor.route_recovery_throttle
    route_recovery_steer_limit: float = DEFAULT_STRATEGY.supervisor.route_recovery_steer_limit
    route_deviation_brake: float = DEFAULT_STRATEGY.supervisor.route_deviation_brake
    low_confidence_threshold: float = DEFAULT_STRATEGY.common.command_confidence_threshold
    hold_brake: float = DEFAULT_STRATEGY.common.hold_brake
    emergency_brake: float = DEFAULT_STRATEGY.common.emergency_brake
    caution_brake: float = DEFAULT_STRATEGY.supervisor.caution_brake
    standstill_speed_mps: float = DEFAULT_STRATEGY.common.standstill_speed_mps

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
            "minimum_lane_offset_m", "severe_route_deviation_m",
            "minimum_severe_route_deviation_m", "route_speed_sensitivity",
            "route_curvature_sensitivity", "route_recovery_max_speed_mps",
            "standstill_speed_mps",
        )):
            raise ValueError("safety distances, times and speeds must be non-negative")
        if self.low_ttc_s > self.caution_ttc_s:
            raise ValueError("low_ttc_s must not exceed caution_ttc_s")
        if self.max_lane_offset_m > self.severe_route_deviation_m:
            raise ValueError("max_lane_offset_m must not exceed severe_route_deviation_m")
        if self.minimum_lane_offset_m > self.max_lane_offset_m:
            raise ValueError("minimum_lane_offset_m must not exceed max_lane_offset_m")
        if self.minimum_severe_route_deviation_m > self.severe_route_deviation_m:
            raise ValueError("minimum severe deviation must not exceed severe route deviation")
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
            "road_curvature_per_m": vs.road_curvature_per_m,
            "watchdog_alerts": list(alerts),
        }

        closing_speed = None
        if rv.ttc_s is not None and rv.ttc_s > 0.0 and vs.front_distance_m is not None:
            closing_speed = vs.front_distance_m / rv.ttc_s
        distance_envelope = dynamic_safety_distance(
            ego_speed_mps=vs.speed_mps,
            closing_speed_mps=closing_speed,
            curvature_per_m=vs.road_curvature_per_m,
            actor_type=vs.front_actor_type,
            sensor_margin_scale=vs.sensor_margin_scale,
        )
        metrics["dynamic_safety_distance"] = distance_envelope.to_dict()
        route_scale = 1.0 + cfg.route_speed_sensitivity * vs.speed_mps + (
            cfg.route_curvature_sensitivity * abs(vs.road_curvature_per_m)
        )
        lane_offset_threshold = max(
            cfg.minimum_lane_offset_m, cfg.max_lane_offset_m / route_scale,
        )
        severe_route_threshold = max(
            cfg.minimum_severe_route_deviation_m,
            cfg.severe_route_deviation_m / route_scale,
        )
        severe_route_threshold = max(severe_route_threshold, lane_offset_threshold)
        metrics["dynamic_lane_offset_threshold_m"] = lane_offset_threshold
        metrics["dynamic_severe_route_deviation_m"] = severe_route_threshold

        def category(reason: str) -> str:
            if reason.startswith("COMMAND_"):
                return "QWEN_OR_COMMAND"
            if reason.startswith("INVALID_CONTROL"):
                return "CONTROL"
            if reason in {"INVALID_VEHICLE_STATE", "INVALID_RISK_STATE"}:
                return "PERCEPTION"
            if reason == "WATCHDOG_ALERT":
                return (
                    "PERCEPTION"
                    if any("SENSOR" in item or "PERCEPTION" in item for item in alerts)
                    else "WATCHDOG"
                )
            if "ROUTE" in reason or "LANE" in reason:
                return "ROUTE_OR_LATERAL_CONTROL"
            if reason == "NONE":
                return "NONE"
            return "SAFETY_POLICY"

        def stop(reason: str, brake: Optional[float] = None, steer: float = 0.0) -> SafetyDecision:
            return SafetyDecision(
                final_control=ControlOutput(throttle=0.0, brake=brake if brake is not None else cfg.emergency_brake, steer=steer),
                safety_override=True,
                reason=reason,
                risk_metrics=metrics,
                raw_control=raw,
                reason_category=category(reason),
            )

        def caution(reason: str) -> SafetyDecision:
            return SafetyDecision(
                final_control=ControlOutput(throttle=0.0, brake=max(raw.brake, cfg.caution_brake), steer=max(min(raw.steer, cfg.route_recovery_steer_limit), -cfg.route_recovery_steer_limit)),
                safety_override=True,
                reason=reason,
                risk_metrics=metrics,
                raw_control=raw,
                reason_category=category(reason),
            )

        def recover_route() -> SafetyDecision:
            steer = max(min(raw.steer, cfg.route_recovery_steer_limit), -cfg.route_recovery_steer_limit)
            control = ControlOutput(
                throttle=0.0,
                brake=max(raw.brake, cfg.route_deviation_brake),
                steer=steer,
            )
            return SafetyDecision(
                final_control=control,
                safety_override=True,
                reason="ROUTE_DEVIATION_RECOVERY_STOP",
                risk_metrics=metrics,
                raw_control=raw,
                reason_category="ROUTE_OR_LATERAL_CONTROL",
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
        emergency_front_distance = max(
            cfg.min_front_distance_m, distance_envelope.emergency_distance_m,
        )
        if vs.front_distance_m is not None and vs.front_distance_m <= emergency_front_distance:
            return stop("EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE")
        dynamic_stop_guard_m = max(
            cfg.stop_line_guard_m,
            DEFAULT_STRATEGY.longitudinal.stop_hold_distance_m
            + vs.speed_mps * DEFAULT_STRATEGY.safety_distance.reaction_time_s
            + vs.speed_mps * vs.speed_mps
            / (2.0 * DEFAULT_STRATEGY.common.comfortable_decel_mps2),
        )
        metrics["dynamic_stop_line_guard_m"] = dynamic_stop_guard_m
        if vs.distance_to_stop_line_m is not None and vs.distance_to_stop_line_m <= dynamic_stop_guard_m:
            unsafe_light = vs.traffic_light in {"RED", "YELLOW", "UNKNOWN"}
            brake_hold_missing = raw.brake < cfg.hold_brake
            still_moving = vs.speed_mps > cfg.standstill_speed_mps
            if unsafe_light and (raw.throttle > 0.05 or still_moving or brake_hold_missing):
                return stop("RED_LIGHT_STOP_LINE_GUARD")
        if vs.route_deviation_m is not None and abs(vs.route_deviation_m) >= severe_route_threshold:
            return recover_route()
        # CARLA's nearest-lane waypoint can jump to a neighbouring branch in a
        # junction.  When an explicit route reference independently confirms
        # that ego remains inside the allowed corridor, it is the stronger
        # signal.  A missing or excessive route deviation still fails closed.
        route_confirms_lane_safe = (
            vs.route_deviation_m is not None
            and abs(vs.route_deviation_m) < lane_offset_threshold
        )
        if (vs.lane_offset_m is not None
                and abs(vs.lane_offset_m) >= lane_offset_threshold
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
            reason_category="NONE",
        )
