from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if not isinstance(result, Mapping):
            raise TypeError("safety_state.to_dict() must return a mapping")
        return dict(result)

    if is_dataclass(value):
        return asdict(value)

    raise TypeError("safety_state must be a mapping, dataclass, or expose to_dict()")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None

    return number


def _confidence(value: Any, default: float = 1.0) -> float:
    number = _optional_float(value)
    if number is None:
        return default
    return max(0.0, min(1.0, number))


def normalize_safety_state(state: Any) -> dict[str, Any]:
    """
    把第二组C/A/D状态归一化为Day22读取视图。

    不猜测目标类别，不修改第二组原始对象。
    """

    raw = _as_mapping(state)

    object_class = raw.get("object_class")
    if isinstance(object_class, str):
        object_class = object_class.strip().upper() or None
    else:
        object_class = None

    traffic_light = raw.get("traffic_light", "UNKNOWN")
    if isinstance(traffic_light, str):
        traffic_light = traffic_light.strip().upper() or "UNKNOWN"
    else:
        traffic_light = "UNKNOWN"

    recommended_action = raw.get("recommended_action", "NONE")
    if isinstance(recommended_action, str):
        recommended_action = recommended_action.strip().upper() or "NONE"
    else:
        recommended_action = "NONE"

    fusion_mode = raw.get("fusion_mode", "UNKNOWN")
    if isinstance(fusion_mode, str):
        fusion_mode = fusion_mode.strip().upper() or "UNKNOWN"
    else:
        fusion_mode = "UNKNOWN"

    visual_valid = raw.get("visual_valid")
    lidar_valid = raw.get("lidar_valid")
    fused_valid = raw.get("fused_valid")

    input_confidence = raw.get(
        "input_confidence",
        raw.get("confidence", 1.0),
    )

    return {
        "schema_version": str(raw.get("schema_version", "1.0")),
        "frame": raw.get("frame"),
        "sim_time_s": _optional_float(raw.get("sim_time_s")),
        "front_distance_m": _optional_float(
            raw.get("front_distance_m", raw.get("nearest_object_distance_m"))
        ),
        "closing_speed_mps": _optional_float(raw.get("closing_speed_mps")),
        "ttc_s": _optional_float(raw.get("ttc_s")),
        "object_class": object_class,
        "object_confidence": _confidence(
            raw.get("object_confidence"),
            default=0.0,
        ),
        "visual_valid": visual_valid if isinstance(visual_valid, bool) else None,
        "lidar_valid": lidar_valid if isinstance(lidar_valid, bool) else None,
        "fused_valid": fused_valid if isinstance(fused_valid, bool) else None,
        "fusion_mode": fusion_mode,
        "recommended_action": recommended_action,
        "reason": str(raw.get("reason", "")),
        "source_by_field": dict(raw.get("source_by_field", {}) or {}),
        "traffic_light": traffic_light,
        "distance_to_stop_line_m": _optional_float(
            raw.get(
                "distance_to_stop_line_m",
                raw.get("stop_line_distance_m"),
            )
        ),
        "input_confidence": _confidence(input_confidence),
        "weather": str(raw.get("weather", "clear")).strip().lower(),
    }
