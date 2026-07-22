"""Day20 high-level targets routed through D before CARLA control is applied."""
from __future__ import annotations

import math
from typing import Any, Callable, Mapping

from car_control_D import SafetySupervisor


class CarlaControlAdapter:
    """Convert a Day20 target to raw control, then let D make the final decision."""

    def __init__(
        self,
        supervisor: SafetySupervisor | None = None,
        *,
        control_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.supervisor = supervisor or SafetySupervisor()
        self._control_factory = control_factory

    def _make_vehicle_control(self, *, throttle: float, brake: float, steer: float) -> Any:
        if self._control_factory is None:
            import carla

            factory = carla.VehicleControl
        else:
            factory = self._control_factory
        return factory(throttle=throttle, brake=brake, steer=steer)

    @staticmethod
    def get_speed_mps(vehicle: Any) -> float:
        velocity = vehicle.get_velocity()
        return math.hypot(float(velocity.x), float(velocity.y))

    @classmethod
    def get_speed_kmh(cls, vehicle: Any) -> float:
        return cls.get_speed_mps(vehicle) * 3.6

    @staticmethod
    def _front_distance_m(scene_state: Mapping[str, Any] | None) -> float | None:
        if not scene_state:
            return None
        distances = []
        for item in scene_state.get("objects", ()):
            if not isinstance(item, Mapping) or item.get("direction") != "front":
                continue
            value = item.get("distance_m")
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                distances.append(float(value))
        return min(distances, default=None)

    def _vehicle_state(
        self,
        vehicle: Any,
        scene_state: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        transform = vehicle.get_transform()
        location = transform.location
        ego_scene = scene_state.get("ego", {}) if scene_state else {}
        return {
            "frame": int(scene_state.get("frame_id", 0)) if scene_state else 0,
            "sim_time_s": float(scene_state.get("sim_time_s", 0.0)) if scene_state else 0.0,
            "speed_mps": self.get_speed_mps(vehicle),
            "x_m": float(location.x),
            "y_m": float(location.y),
            "z_m": float(location.z),
            "yaw_deg": float(transform.rotation.yaw),
            "lane_id": int(ego_scene.get("lane_id", 0)),
            "front_distance_m": self._front_distance_m(scene_state),
            "distance_to_stop_line_m": scene_state.get("distance_to_stop_line_m") if scene_state else None,
            "traffic_light": str(scene_state.get("traffic_light", "UNKNOWN")).upper() if scene_state else "UNKNOWN",
            "lane_offset_m": scene_state.get("lane_offset_m") if scene_state else None,
            "route_deviation_m": scene_state.get("route_deviation_m") if scene_state else None,
            "collision": bool(scene_state.get("collision", False)) if scene_state else False,
            "red_light_violation": bool(scene_state.get("red_light_violation", False)) if scene_state else False,
            "lane_invasion": bool(scene_state.get("lane_invasion", False)) if scene_state else False,
        }

    @staticmethod
    def _raw_control(current_speed_kmh: float, control_target: Any) -> tuple[dict[str, float], str]:
        target_speed = control_target.target_speed_kmh
        if control_target.emergency_stop:
            return {"throttle": 0.0, "brake": 1.0, "steer": 0.0}, "emergency_stop"
        if control_target.stop:
            return {"throttle": 0.0, "brake": 0.8, "steer": 0.0}, "stop"
        if target_speed is None:
            return {"throttle": 0.0, "brake": 0.0, "steer": 0.0}, "no_action"
        if current_speed_kmh < target_speed - 1.0:
            control = {"throttle": 0.35, "brake": 0.0, "steer": 0.0}
        elif current_speed_kmh > target_speed + 2.0:
            control = {"throttle": 0.0, "brake": 0.35, "steer": 0.0}
        else:
            control = {"throttle": 0.15, "brake": 0.0, "steer": 0.0}
        return control, f"target_speed={target_speed}"

    @staticmethod
    def _command(
        control_target: Any,
        *,
        command_id: str,
        confidence: float,
    ) -> dict[str, Any]:
        if control_target.emergency_stop:
            intent = "EMERGENCY_STOP"
        elif control_target.stop:
            intent = "STOP"
        elif control_target.target_speed_kmh is not None:
            intent = "SET_SPEED"
        else:
            intent = "UNKNOWN"
        return {
            "schema_version": "1.0",
            "command_id": command_id,
            "source_text": "Day20 Qwen high-level target",
            "intent": intent,
            "parameters": (
                {"speed_kmh": float(control_target.target_speed_kmh)}
                if intent == "SET_SPEED"
                else {}
            ),
            "intent_confidence": float(confidence),
            "confidence": float(confidence),
            "status": "valid",
            "ambiguity_type": "NONE",
            "confirm_required": False,
            "errors": [],
            "warnings": [],
            "valid_duration_s": 5.0,
        }

    def apply(
        self,
        vehicle: Any,
        control_target: Any,
        *,
        scene_state: Mapping[str, Any] | None = None,
        command_id: str = "day20_command",
        confidence: float = 1.0,
        risk: Mapping[str, Any] | None = None,
        watchdog_alerts: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Apply only D's final control; raw Day20 control never reaches CARLA."""
        current_speed = self.get_speed_kmh(vehicle)
        raw_control, raw_reason = self._raw_control(current_speed, control_target)
        decision = self.supervisor.arbitrate(
            raw_control=raw_control,
            vehicle_state=self._vehicle_state(vehicle, scene_state),
            command=self._command(
                control_target, command_id=command_id, confidence=confidence,
            ),
            risk=risk or {},
            watchdog_alerts=watchdog_alerts,
        )
        final = decision.final_control
        control = self._make_vehicle_control(
            throttle=float(final.throttle),
            brake=float(final.brake),
            steer=float(final.steer),
        )
        vehicle.apply_control(control)
        return {
            "current_speed_kmh": round(current_speed, 2),
            "target_speed_kmh": control_target.target_speed_kmh,
            "raw_control": raw_control,
            "control": {
                "throttle": control.throttle,
                "brake": control.brake,
                "steer": control.steer,
            },
            "raw_reason": raw_reason,
            "safety_override": decision.safety_override,
            "safety_reason": decision.reason,
        }
