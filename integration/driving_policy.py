"""Single validated policy source shared by perception and safety."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Mapping

from car_control_C.safety_state import SafetyStateParameters
from car_control_D.safety_supervisor import SafetyConfig


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "driving_policy.json"


def _number(values: Mapping[str, object], name: str, *, minimum: float = 0.0) -> float:
    value = values.get(name)
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"policy {name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"policy {name} must be finite and >= {minimum}")
    return result


@dataclass(frozen=True, slots=True)
class DrivingPolicy:
    source_path: Path
    perception: Mapping[str, object]
    safety: Mapping[str, object]

    def perception_parameters(
        self, *, visual_confidence_override: float | None = None,
    ) -> SafetyStateParameters:
        p = self.perception
        return SafetyStateParameters(
            visual_confidence_threshold=(
                _number(p, "visual_confidence_threshold")
                if visual_confidence_override is None else float(visual_confidence_override)
            ),
            caution_distance_m=_number(p, "caution_distance_floor_m"),
            emergency_distance_m=_number(p, "emergency_distance_floor_m"),
            vru_caution_distance_m=_number(p, "vru_caution_distance_floor_m"),
            vru_emergency_distance_m=_number(p, "vru_emergency_distance_floor_m"),
            vru_caution_speed_cap_mps=_number(p, "vru_caution_speed_cap_mps"),
            vru_caution_hold_s=_number(p, "vru_caution_hold_s"),
            caution_ttc_s=_number(p, "caution_ttc_s"),
            emergency_ttc_s=_number(p, "emergency_ttc_s"),
            max_observation_gap_s=_number(p, "max_observation_gap_s"),
            reaction_time_s=_number(p, "reaction_time_s"),
            emergency_reaction_time_s=_number(p, "emergency_reaction_time_s"),
            comfortable_deceleration_mps2=_number(p, "comfortable_deceleration_mps2", minimum=0.001),
            emergency_deceleration_mps2=_number(p, "emergency_deceleration_mps2", minimum=0.001),
            range_uncertainty_buffer_m=_number(p, "range_uncertainty_buffer_m"),
        )

    def safety_config(
        self,
        *,
        route_deviation_override_m: float | None = None,
        stop_line_guard_override_m: float | None = None,
    ) -> SafetyConfig:
        s = self.safety
        route_deviation = (
            _number(s, "severe_route_deviation_m")
            if route_deviation_override_m is None else float(route_deviation_override_m)
        )
        maximum_lane_offset = min(
            _number(s, "maximum_lane_offset_m"), route_deviation,
        )
        return SafetyConfig(
            min_front_distance_m=_number(s, "minimum_front_distance_floor_m"),
            low_ttc_s=_number(s, "low_ttc_s"),
            caution_ttc_s=_number(s, "caution_ttc_s"),
            stop_line_guard_m=(
                _number(s, "stop_line_guard_m")
                if stop_line_guard_override_m is None else float(stop_line_guard_override_m)
            ),
            max_lane_offset_m=maximum_lane_offset,
            severe_route_deviation_m=route_deviation,
            route_recovery_max_speed_mps=_number(s, "route_recovery_max_speed_mps"),
            low_confidence_threshold=_number(s, "low_confidence_threshold"),
            emergency_reaction_time_s=_number(s, "emergency_reaction_time_s"),
            emergency_deceleration_mps2=_number(s, "emergency_deceleration_mps2", minimum=0.001),
            range_uncertainty_buffer_m=_number(s, "range_uncertainty_buffer_m"),
        )


def load_driving_policy(path: str | Path | None = None) -> DrivingPolicy:
    source = DEFAULT_POLICY_PATH if path is None else Path(path).expanduser().resolve()
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != "1.0":
        raise ValueError("driving policy schema_version must be '1.0'")
    perception, safety = raw.get("perception"), raw.get("safety")
    if not isinstance(perception, dict) or not isinstance(safety, dict):
        raise TypeError("driving policy perception and safety must be objects")
    policy = DrivingPolicy(source, dict(perception), dict(safety))
    policy.perception_parameters()
    policy.safety_config()
    return policy


__all__ = ["DEFAULT_POLICY_PATH", "DrivingPolicy", "load_driving_policy"]
