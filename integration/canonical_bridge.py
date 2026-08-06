"""Adapters between the legacy CARLA loop and frozen second-group V1 objects."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from runtime.interface_registry import InterfaceRegistry
from .contracts import PerceptionFrame


_CLASS_MAP = {
    "person": "pedestrian",
    "pedestrian": "pedestrian",
    "bicycle": "cyclist",
    "motorcycle": "cyclist",
    "cyclist": "cyclist",
    "car": "vehicle",
    "truck": "vehicle",
    "bus": "vehicle",
    "vehicle": "vehicle",
    "obstacle": "obstacle",
}


def voice_envelope_to_driving_command(
    envelope: Mapping[str, Any],
    *,
    received_at_ns: int,
    registry: InterfaceRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or InterfaceRegistry()
    intent = str(envelope.get("intent", "UNKNOWN")).upper()
    canonical_intent = {
        "FOLLOW_ROUTE": "FOLLOW",
        "EMERGENCY_STOP": "EMERGENCY_STOP",
        "STOP": "STOP",
        "SET_SPEED": "SET_SPEED",
        "SLOW_DOWN": "SLOW_DOWN",
        "KEEP_LANE": "KEEP_LANE",
        "CHANGE_LANE": "CHANGE_LANE",
        "TURN": "TURN",
        "PULL_OVER": "PULL_OVER",
        "AVOID_OBSTACLE": "AVOID_OBSTACLE",
    }.get(intent, "UNKNOWN")
    parameters = envelope.get("parameters", {})
    if not isinstance(parameters, Mapping):
        parameters = {}
    canonical_parameters: dict[str, Any] = {}
    speed = parameters.get("speed")
    if speed is not None and type(speed) in (int, float) and not isinstance(speed, bool):
        unit = str(parameters.get("unit", "km/h")).lower().replace(" ", "")
        target = float(speed) / 3.6 if unit in {"km/h", "kph", "kmh", "公里/小时", "千米/小时"} else float(speed)
        if math.isfinite(target) and target >= 0.0:
            canonical_parameters["target_speed_mps"] = target
    direction = str(parameters.get("direction", "")).upper()
    if direction in {"LEFT", "RIGHT", "STRAIGHT"}:
        canonical_parameters["direction"] = direction
    target_id = parameters.get("target_id")
    if type(target_id) is str and target_id:
        canonical_parameters["target_id"] = target_id
    ttl_s = envelope.get("valid_duration_s", 3.0)
    if type(ttl_s) not in (int, float) or isinstance(ttl_s, bool) or not math.isfinite(float(ttl_s)) or ttl_s <= 0:
        ttl_s = 3.0
    confidence = envelope.get("confidence", envelope.get("intent_confidence", 0.0))
    if type(confidence) not in (int, float) or isinstance(confidence, bool) or not math.isfinite(float(confidence)):
        confidence = 0.0
    payload = {
        "schema_version": "1.0",
        "command_id": str(envelope.get("command_id", "invalid-command")),
        "source_text": str(envelope.get("source_text", "<unavailable>")),
        "intent": canonical_intent,
        "parameters": canonical_parameters,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "received_at_ns": received_at_ns,
        "deadline_ns": received_at_ns + int(float(ttl_s) * 1e9),
        "source": "VOICE",
        "ambiguity": str(envelope.get("ambiguity_type", "NONE")),
        "requires_confirmation": bool(envelope.get("confirm_required", False)),
    }
    return registry.validate("driving_command", payload)


def perception_frame_to_state(
    scene: PerceptionFrame,
    vehicle: Any,
    *,
    captured_at_ns: int,
    perception_mode: str,
    registry: InterfaceRegistry | None = None,
) -> dict[str, Any]:
    if not isinstance(scene, PerceptionFrame):
        raise TypeError("scene must be PerceptionFrame")
    registry = registry or InterfaceRegistry()
    objects = []
    mode = str(perception_mode).lower()
    sensor_mode = mode in {"sensors", "sensors_radar"}
    radar_valid = mode == "sensors_radar"
    sensor_failed = mode in {"failed", "sensor_failure"}
    for index, item in enumerate(scene.detected_objects):
        class_name = _CLASS_MAP.get(str(item.class_name).lower(), "unknown")
        distance = float(item.distance_m) if item.distance_m is not None else 50.0
        x1, _y1, x2, _y2 = item.bbox_xyxy_norm
        image_center = (x1 + x2) / 2.0
        lateral = (0.5 - image_center) * 7.0
        velocity_x = float(scene.lead_speed_mps or 0.0) if index == 0 else 0.0
        closing = float(vehicle.speed_mps) - velocity_x
        ttc = distance / closing if closing > 0.05 else None
        sources = (
            ["LIDAR"]
            if class_name == "obstacle" and item.distance_m is not None
            else ["RGB"] + (["LIDAR"] if item.distance_m is not None else [])
        )
        if not sensor_mode:
            sources = ["WORLD"]
        objects.append({
            # The legacy bridge has no tracker-owned ID.  A class/index key is
            # at least stable across adjacent low-frequency detector frames;
            # never embed frame_id, which would guarantee Qwen target expiry.
            "track_id": item.track_id or f"legacy-{class_name}-{index:03d}",
            "class": class_name,
            "position_m": [distance, lateral, 0.0],
            "velocity_mps": [velocity_x, 0.0, 0.0],
            "distance_m": distance,
            "ttc_s": ttc,
            "confidence": float(item.confidence),
            "sources": sources,
            "bbox_xyxy_norm": list(item.bbox_xyxy_norm),
        })
    ttc_s = None
    if scene.lead_distance_m is not None and scene.lead_speed_mps is not None:
        closing = float(vehicle.speed_mps) - float(scene.lead_speed_mps)
        if closing > 0.05:
            ttc_s = float(scene.lead_distance_m) / closing
    min_gap = scene.lead_distance_m
    if scene.collision or (ttc_s is not None and ttc_s <= 1.5) or (min_gap is not None and min_gap <= 5.0):
        risk = "EMERGENCY"
    elif ttc_s is not None and ttc_s <= 2.5:
        risk = "HIGH"
    elif min_gap is not None and min_gap <= 10.0:
        risk = "CAUTION"
    else:
        risk = "LOW"
    missing = ([] if radar_valid else ["RADAR"]) if sensor_mode else ["RGB", "RADAR", "LIDAR"]
    degraded = (["RADAR_MISSING"] if sensor_mode and not radar_valid else [])
    if not sensor_mode:
        degraded = ["STRUCTURED_WORLD_STATE_NO_RAW_SENSORS"]
    if sensor_failed:
        degraded = ["SENSOR_ACQUISITION_FAILURE"]
    state = {
        "schema_version": "1.0",
        "frame_id": scene.frame,
        "sim_time_s": scene.sim_time_s,
        "captured_at_ns": captured_at_ns,
        "coordinate_frame": "ego_front_x_left_y_up_z_m",
        "objects": objects,
        "traffic_light": scene.traffic_light,
        "distance_to_stop_line_m": scene.distance_to_stop_line_m,
        "speed_limit_mps": scene.speed_limit_mps,
        "ttc_s": ttc_s,
        "min_gap_m": min_gap,
        "risk_level": risk,
        "modality_valid": {
            "rgb": sensor_mode,
            "radar": radar_valid,
            "lidar": sensor_mode,
            "vehicle_state": True,
        },
        "stale": sensor_failed,
        "sync": {
            "reference_frame_id": scene.frame,
            "max_skew_ms": 0.0,
            "within_tolerance": not sensor_failed,
            "missing_modalities": missing,
        },
        "degraded_reason_codes": degraded,
    }
    return registry.validate("perception_state", state)


def control_command_to_voice_envelope(
    control: Mapping[str, Any],
    *,
    source_text: str,
) -> dict[str, Any]:
    behavior = str(control["behavior"])
    target_speed = control["target"].get("target_speed_mps")
    compiled_maneuver = bool(
        control.get("path_type") == "SLOW"
        and control.get("source") == "QWEN_DECISION_PLAN"
    )
    if behavior in {"SET_SPEED", "SLOW_DOWN"}:
        if target_speed is None:
            raise ValueError(f"{behavior} requires target_speed_mps")
        intent = behavior
        parameters = {"speed": float(target_speed), "unit": "m/s"}
    elif behavior == "FOLLOW":
        intent = "SLOW_DOWN" if target_speed is not None else "KEEP_LANE"
        parameters = {} if target_speed is None else {"speed": float(target_speed), "unit": "m/s"}
    elif behavior in {"STOP", "HOLD"}:
        intent, parameters = "STOP", {}
    elif behavior == "EMERGENCY_STOP":
        intent, parameters = "EMERGENCY_STOP", {}
    elif behavior == "KEEP_LANE":
        intent, parameters = "KEEP_LANE", {}
    elif behavior in {"TURN_LEFT", "TURN_RIGHT"}:
        if not compiled_maneuver:
            raise ValueError(f"current deterministic runtime cannot execute slow behavior {behavior}")
        intent = "TURN"
        parameters = {"direction": behavior.rsplit("_", 1)[-1]}
    elif behavior in {"CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT"}:
        if not compiled_maneuver:
            raise ValueError(f"current deterministic runtime cannot execute slow behavior {behavior}")
        intent = "CHANGE_LANE"
        parameters = {"direction": behavior.rsplit("_", 1)[-1]}
    elif behavior == "PULL_OVER":
        if not compiled_maneuver:
            raise ValueError(f"current deterministic runtime cannot execute slow behavior {behavior}")
        intent, parameters = "PULL_OVER", {}
    else:
        raise ValueError(f"current deterministic runtime cannot execute slow behavior {behavior}")
    confidence = float(control.get("confidence", 1.0))
    return {
        "schema_version": "1.0",
        "command_id": control["command_id"],
        "source_text": source_text,
        "intent": intent,
        "parameters": parameters,
        "confidence": confidence,
        "intent_confidence": confidence,
        "status": "valid",
        "ambiguity_type": "NONE",
        "confirm_required": False,
        "compiled_maneuver": bool(
            compiled_maneuver and behavior in {
                "TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT",
                "CHANGE_LANE_RIGHT", "PULL_OVER",
            }
        ),
        "errors": [],
        "warnings": [{
            "code": ("QWEN_HIGH_LEVEL_PLAN" if control.get("path_type") == "SLOW"
                     else "CANONICAL_FAST_PATH"),
            "message": str(control.get("reason_code", "QWEN_DECISION")),
        }],
        "valid_duration_s": max(0.1, (int(control["deadline_ns"]) - int(control["issued_at_ns"])) / 1e9),
        "t_audio_start_ns": None,
        "t_asr_end_ns": None,
        "t_intent_end_ns": int(control["issued_at_ns"]),
    }


__all__ = [
    "control_command_to_voice_envelope",
    "perception_frame_to_state",
    "voice_envelope_to_driving_command",
]
