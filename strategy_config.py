"""Single, strict configuration source for generalized control and safety.

``strategy_config.yaml`` deliberately uses JSON syntax.  JSON is a valid YAML
1.2 document, so the file remains consumable by YAML tooling while the runtime
can parse it with Python's standard library and introduces no PyYAML dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
import math
from pathlib import Path
from typing import Any, Mapping, TypeVar


STRATEGY_SCHEMA_VERSION = "1.0"
DEFAULT_STRATEGY_PATH = Path(__file__).with_name("strategy_config.yaml")


def _number(name: str, value: object, *, minimum: float = 0.0,
            maximum: float | None = None, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if positive and number <= 0.0:
        raise ValueError(f"{name} must be positive")
    if number < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return number


@dataclass(frozen=True, slots=True)
class CommonStrategy:
    command_confidence_threshold: float
    standstill_speed_mps: float
    comfortable_decel_mps2: float
    max_decel_mps2: float
    hold_brake: float
    emergency_brake: float
    caution_ttc_s: float
    emergency_ttc_s: float


@dataclass(frozen=True, slots=True)
class SafetyDistanceStrategy:
    standstill_gap_m: float
    reaction_time_s: float
    emergency_reaction_time_s: float
    sensor_base_margin_m: float
    sensor_uncertainty_time_s: float
    curvature_margin_gain: float
    vru_distance_factor: float
    vru_emergency_distance_factor: float
    vru_minimum_emergency_distance_m: float
    large_vehicle_distance_factor: float
    unknown_actor_distance_factor: float
    minimum_emergency_distance_m: float


@dataclass(frozen=True, slots=True)
class PerceptionSafetyStrategy:
    visual_confidence_threshold: float
    max_observation_gap_s: float
    vru_caution_speed_cap_mps: float
    vru_caution_hold_s: float


@dataclass(frozen=True, slots=True)
class LongitudinalStrategy:
    max_lateral_accel_mps2: float
    command_accel_mps2: float
    command_decel_mps2: float
    max_accel_mps2: float
    max_control_delta_per_s: float
    creep_speed_mps: float
    stop_hold_distance_m: float
    pid_kp: float
    pid_ki: float
    pid_kd: float
    pid_integral_limit: float
    pid_target_step_reset_mps: float


@dataclass(frozen=True, slots=True)
class LateralStrategy:
    wheel_base_m: float
    base_lookahead_m: float
    speed_gain_s: float
    min_lookahead_m: float
    max_lookahead_m: float
    curvature_lookahead_gain: float
    error_lookahead_gain: float
    max_steer_angle_rad: float
    steer_gain: float
    max_steer: float
    min_steer_limit: float
    high_speed_steer_reduction_per_mps: float
    curvature_steer_gain: float
    base_steer_delta_per_step: float
    min_steer_delta_per_step: float
    max_steer_delta_per_step: float
    low_speed_steer_gain: float
    curvature_rate_gain: float
    error_rate_gain: float
    stanley_gain: float
    stanley_softening_speed_mps: float
    stanley_curvature_gain: float
    steer_sign: float


@dataclass(frozen=True, slots=True)
class SupervisorStrategy:
    stop_line_guard_m: float
    max_lane_offset_m: float
    minimum_lane_offset_m: float
    severe_route_deviation_m: float
    minimum_severe_route_deviation_m: float
    route_speed_sensitivity: float
    route_curvature_sensitivity: float
    route_recovery_max_speed_mps: float
    route_recovery_throttle: float
    route_recovery_steer_limit: float
    route_deviation_brake: float
    caution_brake: float


@dataclass(frozen=True, slots=True)
class SensorFaultStrategy:
    single_sensor_speed_cap_mps: float
    speed_cap_tolerance_mps: float
    speed_cap_base_brake: float
    speed_cap_brake_gain: float


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    schema_version: str
    common: CommonStrategy
    safety_distance: SafetyDistanceStrategy
    perception_safety: PerceptionSafetyStrategy
    longitudinal: LongitudinalStrategy
    lateral: LateralStrategy
    supervisor: SupervisorStrategy
    sensor_fault: SensorFaultStrategy


T = TypeVar("T")


def _section(name: str, payload: object, cls: type[T]) -> T:
    if type(payload) is not dict:
        raise TypeError(f"strategy section {name!r} must be an object")
    expected = {item.name for item in fields(cls)}
    actual = set(payload)
    if actual != expected:
        raise ValueError(
            f"strategy section {name!r} fields mismatch; "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )
    values = {
        key: _number(
            f"{name}.{key}", value,
            minimum=-1.0 if key == "steer_sign" else 0.0,
        )
        for key, value in payload.items()
    }
    return cls(**values)


def load_strategy_config(path: str | Path = DEFAULT_STRATEGY_PATH) -> StrategyConfig:
    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"strategy config must be valid JSON-compatible YAML: {error}") from error
    if type(payload) is not dict:
        raise TypeError("strategy config root must be an object")
    expected = {
        "schema_version", "common", "safety_distance", "perception_safety",
        "longitudinal", "lateral", "supervisor", "sensor_fault",
    }
    if set(payload) != expected:
        raise ValueError(
            "strategy config fields mismatch; "
            f"missing={sorted(expected - set(payload))}, unknown={sorted(set(payload) - expected)}"
        )
    if payload["schema_version"] != STRATEGY_SCHEMA_VERSION:
        raise ValueError(f"unsupported strategy schema_version={payload['schema_version']!r}")
    config = StrategyConfig(
        schema_version=STRATEGY_SCHEMA_VERSION,
        common=_section("common", payload["common"], CommonStrategy),
        safety_distance=_section("safety_distance", payload["safety_distance"], SafetyDistanceStrategy),
        perception_safety=_section("perception_safety", payload["perception_safety"], PerceptionSafetyStrategy),
        longitudinal=_section("longitudinal", payload["longitudinal"], LongitudinalStrategy),
        lateral=_section("lateral", payload["lateral"], LateralStrategy),
        supervisor=_section("supervisor", payload["supervisor"], SupervisorStrategy),
        sensor_fault=_section("sensor_fault", payload["sensor_fault"], SensorFaultStrategy),
    )
    _validate_relations(config)
    return config


def _validate_relations(config: StrategyConfig) -> None:
    common = config.common
    if common.comfortable_decel_mps2 > common.max_decel_mps2:
        raise ValueError("comfortable_decel_mps2 must not exceed max_decel_mps2")
    if common.emergency_ttc_s > common.caution_ttc_s:
        raise ValueError("emergency_ttc_s must not exceed caution_ttc_s")
    for name in ("command_confidence_threshold", "hold_brake", "emergency_brake"):
        if getattr(common, name) > 1.0:
            raise ValueError(f"common.{name} must be <= 1.0")
    perception = config.perception_safety
    if perception.visual_confidence_threshold > 1.0:
        raise ValueError("perception_safety.visual_confidence_threshold must be <= 1.0")
    lateral = config.lateral
    if lateral.min_lookahead_m > lateral.max_lookahead_m:
        raise ValueError("lateral min_lookahead_m must not exceed max_lookahead_m")
    if not lateral.min_steer_delta_per_step <= lateral.base_steer_delta_per_step <= lateral.max_steer_delta_per_step:
        raise ValueError("lateral steer delta limits must contain the base value")
    if lateral.min_steer_limit > lateral.max_steer:
        raise ValueError("lateral min_steer_limit must not exceed max_steer")
    if lateral.steer_sign not in {-1.0, 1.0}:
        raise ValueError("lateral.steer_sign must be -1 or 1")
    supervisor = config.supervisor
    if supervisor.minimum_lane_offset_m > supervisor.max_lane_offset_m:
        raise ValueError("minimum lane offset must not exceed maximum lane offset")
    if supervisor.minimum_severe_route_deviation_m > supervisor.severe_route_deviation_m:
        raise ValueError("minimum severe deviation must not exceed maximum severe deviation")
    for name in (
        "route_recovery_throttle", "route_recovery_steer_limit",
        "route_deviation_brake", "caution_brake",
    ):
        if getattr(supervisor, name) > 1.0:
            raise ValueError(f"supervisor.{name} must be <= 1.0")


DEFAULT_STRATEGY = load_strategy_config()


@dataclass(frozen=True, slots=True)
class SafetyDistanceEnvelope:
    caution_distance_m: float
    emergency_distance_m: float
    reaction_distance_m: float
    braking_distance_m: float
    sensor_margin_m: float
    curvature_multiplier: float
    actor_multiplier: float
    emergency_actor_multiplier: float

    def to_dict(self) -> dict[str, float]:
        return {
            item.name: float(getattr(self, item.name))
            for item in fields(self)
        }


_VRU_TYPES = frozenset({"PEDESTRIAN", "PERSON", "CYCLIST", "BICYCLE", "MOTORCYCLE"})
_LARGE_VEHICLE_TYPES = frozenset({"TRUCK", "BUS"})


def dynamic_safety_distance(
    *,
    ego_speed_mps: float,
    closing_speed_mps: float | None = None,
    curvature_per_m: float = 0.0,
    actor_type: str | None = None,
    sensor_margin_scale: float = 1.0,
    config: StrategyConfig = DEFAULT_STRATEGY,
) -> SafetyDistanceEnvelope:
    """Return a kinematic, speed/curvature/sensor/actor-aware envelope."""
    speed = _number("ego_speed_mps", ego_speed_mps)
    closing = speed if closing_speed_mps is None else max(0.0, _number(
        "closing_speed_mps", closing_speed_mps, minimum=-math.inf,
    ))
    curvature = abs(_number("curvature_per_m", curvature_per_m, minimum=-math.inf))
    margin_scale = _number("sensor_margin_scale", sensor_margin_scale)
    policy = config.safety_distance
    common = config.common
    actor = str(actor_type or "UNKNOWN").strip().upper()
    if actor in _VRU_TYPES:
        actor_multiplier = policy.vru_distance_factor
        emergency_actor_multiplier = policy.vru_emergency_distance_factor
    elif actor in _LARGE_VEHICLE_TYPES:
        actor_multiplier = policy.large_vehicle_distance_factor
        emergency_actor_multiplier = actor_multiplier
    elif actor in {"VEHICLE", "CAR"}:
        actor_multiplier = 1.0
        emergency_actor_multiplier = 1.0
    else:
        actor_multiplier = policy.unknown_actor_distance_factor
        emergency_actor_multiplier = actor_multiplier
    lateral_demand = speed * speed * curvature
    curvature_multiplier = 1.0 + policy.curvature_margin_gain * min(
        1.0, lateral_demand / max(config.longitudinal.max_lateral_accel_mps2, 1e-6),
    )
    sensor_margin = margin_scale * (
        policy.sensor_base_margin_m + policy.sensor_uncertainty_time_s * speed
    )
    reaction_distance = speed * policy.reaction_time_s
    braking_distance = closing * closing / (2.0 * common.comfortable_decel_mps2)
    caution = actor_multiplier * curvature_multiplier * (
        policy.standstill_gap_m + reaction_distance + braking_distance
    ) + sensor_margin
    emergency_reaction = speed * policy.emergency_reaction_time_s
    emergency_braking = closing * closing / (2.0 * common.max_decel_mps2)
    emergency_floor = (
        policy.vru_minimum_emergency_distance_m
        if actor in _VRU_TYPES else policy.minimum_emergency_distance_m
    )
    emergency = max(
        emergency_floor,
        emergency_actor_multiplier * math.sqrt(curvature_multiplier)
        * (policy.standstill_gap_m * 0.5 + emergency_reaction + emergency_braking)
        + 0.5 * sensor_margin,
    )
    emergency = min(emergency, caution)
    return SafetyDistanceEnvelope(
        caution_distance_m=caution,
        emergency_distance_m=emergency,
        reaction_distance_m=reaction_distance,
        braking_distance_m=braking_distance,
        sensor_margin_m=sensor_margin,
        curvature_multiplier=curvature_multiplier,
        actor_multiplier=actor_multiplier,
        emergency_actor_multiplier=emergency_actor_multiplier,
    )


__all__ = [
    "DEFAULT_STRATEGY", "DEFAULT_STRATEGY_PATH", "STRATEGY_SCHEMA_VERSION",
    "SafetyDistanceEnvelope", "StrategyConfig", "dynamic_safety_distance",
    "load_strategy_config",
]
