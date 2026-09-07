"""Auditable RGB/LiDAR safety-state fusion for member C.

The module is deliberately detector-agnostic.  The vision group may provide a
``VisualObservation``; C associates its semantic class with the frame-aligned
front LiDAR range and derives closing speed/TTC.  Missing visual semantics are
reported as invalid and are never replaced with a guessed class.  A missing
LiDAR frame, or a visual hazard with no usable range, is fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from car_control_A import ControlOutput
from strategy_config import DEFAULT_STRATEGY, dynamic_safety_distance

from .validation import finite


SAFETY_STATE_SCHEMA_VERSION = "1.0"


def _optional_non_negative(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    return finite(name, value, minimum=0.0)


def _source(name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class VisualObservation:
    """One upstream RGB semantic result for an exact control frame.

    ``valid=False`` requires the semantic fields to be absent.  This makes an
    unavailable/failed detector distinguishable from a confident UNKNOWN
    classification and prevents C from inventing visual evidence.
    """

    frame: int
    valid: bool
    object_class: str | None = None
    confidence: float | None = None
    source: str = "RGB_DETECTOR"

    def __post_init__(self) -> None:
        if type(self.frame) is not int or self.frame < 0:
            raise ValueError("frame must be a non-negative integer")
        if type(self.valid) is not bool:
            raise TypeError("valid must be bool")
        object.__setattr__(self, "source", _source("source", self.source))
        if not self.valid:
            if self.object_class is not None or self.confidence is not None:
                raise ValueError("invalid visual observations must not carry semantic values")
            return
        if type(self.object_class) is not str or not self.object_class.strip():
            raise ValueError("a valid visual observation needs object_class")
        confidence = finite("confidence", self.confidence, minimum=0.0, maximum=1.0)
        object.__setattr__(self, "object_class", self.object_class.strip().upper())
        object.__setattr__(self, "confidence", confidence)

    @classmethod
    def unavailable(cls, frame: int, *, source: str = "RGB_DETECTOR_UNAVAILABLE") -> "VisualObservation":
        return cls(frame=frame, valid=False, source=source)


@dataclass(frozen=True, slots=True)
class SafetyStateParameters:
    """C-side perception policy; distance thresholds are computed per frame."""

    visual_confidence_threshold: float = DEFAULT_STRATEGY.perception_safety.visual_confidence_threshold
    vru_caution_speed_cap_mps: float = DEFAULT_STRATEGY.perception_safety.vru_caution_speed_cap_mps
    vru_caution_hold_s: float = DEFAULT_STRATEGY.perception_safety.vru_caution_hold_s
    caution_ttc_s: float = DEFAULT_STRATEGY.common.caution_ttc_s
    emergency_ttc_s: float = DEFAULT_STRATEGY.common.emergency_ttc_s
    max_observation_gap_s: float = DEFAULT_STRATEGY.perception_safety.max_observation_gap_s
    full_brake: float = DEFAULT_STRATEGY.common.emergency_brake

    def __post_init__(self) -> None:
        finite("visual_confidence_threshold", self.visual_confidence_threshold,
               minimum=0.0, maximum=1.0)
        for name in ("vru_caution_speed_cap_mps", "vru_caution_hold_s",
                     "caution_ttc_s", "emergency_ttc_s", "max_observation_gap_s"):
            finite(name, getattr(self, name), positive=True)
        finite("full_brake", self.full_brake, positive=True, maximum=1.0)
        if self.emergency_ttc_s > self.caution_ttc_s:
            raise ValueError("emergency_ttc_s must not exceed caution_ttc_s")


@dataclass(frozen=True, slots=True)
class SafetyStateSummary:
    """Serializable C output for Qwen/D/logging and on-site monitoring."""

    frame: int
    sim_time_s: float
    front_distance_m: float | None
    closing_speed_mps: float | None
    ttc_s: float | None
    object_class: str | None
    object_confidence: float | None
    visual_valid: bool
    lidar_valid: bool
    fused_valid: bool
    fusion_mode: str
    recommended_action: str
    recommended_speed_cap_mps: float | None
    dynamic_caution_distance_m: float | None
    dynamic_emergency_distance_m: float | None
    safety_distance_components: Mapping[str, float]
    reason: str
    source_by_field: Mapping[str, str]

    @property
    def fail_closed(self) -> bool:
        return self.recommended_action in {"FULL_BRAKE", "EMERGENCY_BRAKE"}

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SAFETY_STATE_SCHEMA_VERSION,
            "frame": self.frame,
            "sim_time_s": self.sim_time_s,
            "front_distance_m": self.front_distance_m,
            "closing_speed_mps": self.closing_speed_mps,
            "ttc_s": self.ttc_s,
            "object_class": self.object_class,
            "object_confidence": self.object_confidence,
            "visual_valid": self.visual_valid,
            "lidar_valid": self.lidar_valid,
            "fused_valid": self.fused_valid,
            "fusion_mode": self.fusion_mode,
            "recommended_action": self.recommended_action,
            "recommended_speed_cap_mps": self.recommended_speed_cap_mps,
            "dynamic_caution_distance_m": self.dynamic_caution_distance_m,
            "dynamic_emergency_distance_m": self.dynamic_emergency_distance_m,
            "safety_distance_components": dict(self.safety_distance_components),
            "reason": self.reason,
            "source_by_field": dict(self.source_by_field),
        }


class ConservativeSensorFusion:
    """Fuse exact-frame RGB semantics with front LiDAR range conservatively."""

    _HAZARD_CLASSES = frozenset({
        "PEDESTRIAN", "PERSON", "VEHICLE", "CAR", "TRUCK", "BUS",
        "CYCLIST", "BICYCLE", "MOTORCYCLE", "OBSTACLE", "UNKNOWN",
    })
    _VRU_CLASSES = frozenset({"PEDESTRIAN", "PERSON", "CYCLIST", "BICYCLE", "MOTORCYCLE"})

    def __init__(self, parameters: SafetyStateParameters | None = None) -> None:
        self.parameters = parameters or SafetyStateParameters()
        self._previous_frame: int | None = None
        self._previous_time_s: float | None = None
        self._previous_distance_m: float | None = None
        self._vru_caution_until_s: float | None = None

    def reset(self) -> None:
        self._previous_frame = None
        self._previous_time_s = None
        self._previous_distance_m = None
        self._vru_caution_until_s = None

    def update(
        self,
        *,
        frame: int,
        sim_time_s: float,
        ego_speed_mps: float,
        front_distance_m: float | None,
        lidar_valid: bool,
        visual: VisualObservation | None = None,
        lead_speed_mps: float | None = None,
        road_curvature_per_m: float = 0.0,
        sensor_margin_scale: float = 1.0,
        lidar_source: str = "LIDAR_FRONT_CORRIDOR",
        lead_speed_source: str = "LEAD_TRACKER",
    ) -> SafetyStateSummary:
        if type(frame) is not int or frame < 0:
            raise ValueError("frame must be a non-negative integer")
        sim_time_s = finite("sim_time_s", sim_time_s, minimum=0.0)
        ego_speed_mps = finite("ego_speed_mps", ego_speed_mps, minimum=0.0)
        front_distance_m = _optional_non_negative("front_distance_m", front_distance_m)
        lead_speed_mps = _optional_non_negative("lead_speed_mps", lead_speed_mps)
        road_curvature_per_m = finite("road_curvature_per_m", road_curvature_per_m)
        sensor_margin_scale = finite("sensor_margin_scale", sensor_margin_scale, minimum=0.0)
        if type(lidar_valid) is not bool:
            raise TypeError("lidar_valid must be bool")
        if self._previous_frame is not None and frame <= self._previous_frame:
            raise ValueError("fusion frames must be strictly increasing; call reset() for a new episode")
        if self._previous_time_s is not None and sim_time_s <= self._previous_time_s:
            raise ValueError("sim_time_s must be strictly increasing; call reset() for a new episode")
        if not lidar_valid and (front_distance_m is not None or lead_speed_mps is not None):
            raise ValueError("an invalid LiDAR observation must not carry range or lead speed")
        if front_distance_m is None and lead_speed_mps is not None:
            raise ValueError("lead_speed_mps requires front_distance_m")

        visual = visual or VisualObservation.unavailable(frame)
        if visual.frame != frame:
            raise ValueError("visual and LiDAR observations must use the same frame")
        visual_valid = bool(
            visual.valid and visual.confidence is not None
            and visual.confidence >= self.parameters.visual_confidence_threshold
        )
        object_class = visual.object_class if visual_valid else None
        object_confidence = visual.confidence if visual_valid else None
        sources: dict[str, str] = {
            "lidar": _source("lidar_source", lidar_source),
            "visual": visual.source,
        }

        closing_speed: float | None = None
        envelope_closing_speed: float | None = None
        if lidar_valid and front_distance_m is not None:
            if lead_speed_mps is not None:
                envelope_closing_speed = max(0.0, ego_speed_mps - lead_speed_mps)
                closing_speed = envelope_closing_speed
                sources["closing_speed_mps"] = _source("lead_speed_source", lead_speed_source)
            elif self._previous_distance_m is not None and self._previous_time_s is not None:
                dt_s = sim_time_s - self._previous_time_s
                if dt_s <= self.parameters.max_observation_gap_s:
                    closing_speed = (self._previous_distance_m - front_distance_m) / dt_s
                    envelope_closing_speed = max(0.0, closing_speed)
                    sources["closing_speed_mps"] = "LIDAR_TEMPORAL_DIFFERENCE"
            if closing_speed is not None and closing_speed <= 0.0:
                closing_speed = None

        ttc_s = None
        if front_distance_m is not None and closing_speed is not None:
            ttc_s = front_distance_m / closing_speed
            sources["ttc_s"] = "FRONT_DISTANCE_DIVIDED_BY_CLOSING_SPEED"

        envelope = None
        if lidar_valid and front_distance_m is not None:
            envelope = dynamic_safety_distance(
                ego_speed_mps=ego_speed_mps,
                closing_speed_mps=envelope_closing_speed,
                curvature_per_m=road_curvature_per_m,
                actor_type=object_class,
                sensor_margin_scale=sensor_margin_scale,
            )
            sources["dynamic_safety_distance"] = "STRATEGY_CONFIG_KINEMATIC_MODEL"

        vru_in_caution_zone = bool(
            visual_valid
            and object_class in self._VRU_CLASSES
            and front_distance_m is not None
            and envelope is not None
            and front_distance_m <= envelope.caution_distance_m
        )
        if vru_in_caution_zone:
            self._vru_caution_until_s = sim_time_s + self.parameters.vru_caution_hold_s

        if not lidar_valid:
            mode, action, reason = "FAIL_CLOSED", "FULL_BRAKE", "lidar_invalid"
        elif visual_valid and front_distance_m is None and object_class in self._HAZARD_CLASSES:
            mode, action, reason = "RGB_ONLY", "FULL_BRAKE", "visual_hazard_without_range"
        elif visual_valid and front_distance_m is not None:
            mode, action, reason = self._range_action(
                front_distance_m, ttc_s, "RGB_LIDAR", envelope=envelope,
                object_class=object_class,
            )
        elif front_distance_m is not None:
            mode, action, reason = self._range_action(
                front_distance_m, ttc_s, "LIDAR_ONLY", envelope=envelope,
            )
        elif visual_valid:
            mode, action, reason = "RGB_ONLY", "KEEP_SPEED", "visual_non_hazard_without_range"
        else:
            mode, action, reason = "NO_OBSTACLE", "KEEP_SPEED", "no_front_hazard_observed"

        vru_hold_active = bool(
            self._vru_caution_until_s is not None
            and sim_time_s <= self._vru_caution_until_s
        )
        speed_cap_mps: float | None = None
        if vru_hold_active and action == "KEEP_SPEED":
            mode, action, reason = "VRU_CAUTION_HOLD", "SLOW_DOWN", "vru_caution_hold"
        if vru_hold_active and action == "SLOW_DOWN":
            speed_cap_mps = self.parameters.vru_caution_speed_cap_mps
            sources["vru_speed_cap"] = "RGB_LIDAR_VRU_CAUTION_HOLD"
        elif action == "SLOW_DOWN" and envelope is not None and front_distance_m is not None:
            available = max(
                0.0,
                front_distance_m
                - DEFAULT_STRATEGY.safety_distance.standstill_gap_m
                - envelope.sensor_margin_m,
            )
            speed_cap_mps = min(
                ego_speed_mps,
                (2.0 * DEFAULT_STRATEGY.common.comfortable_decel_mps2 * available) ** 0.5,
            )
            sources["hazard_speed_cap"] = "DYNAMIC_SAFETY_DISTANCE"

        fused_valid = visual_valid and lidar_valid and front_distance_m is not None
        summary = SafetyStateSummary(
            frame=frame,
            sim_time_s=sim_time_s,
            front_distance_m=front_distance_m,
            closing_speed_mps=closing_speed,
            ttc_s=ttc_s,
            object_class=object_class,
            object_confidence=object_confidence,
            visual_valid=visual_valid,
            lidar_valid=lidar_valid,
            fused_valid=fused_valid,
            fusion_mode=mode,
            recommended_action=action,
            recommended_speed_cap_mps=speed_cap_mps,
            dynamic_caution_distance_m=None if envelope is None else envelope.caution_distance_m,
            dynamic_emergency_distance_m=None if envelope is None else envelope.emergency_distance_m,
            safety_distance_components=MappingProxyType(
                {} if envelope is None else envelope.to_dict()
            ),
            reason=reason,
            source_by_field=MappingProxyType(sources),
        )
        self._previous_frame = frame
        self._previous_time_s = sim_time_s
        self._previous_distance_m = front_distance_m if lidar_valid else None
        return summary

    def fail_closed_control(self) -> ControlOutput:
        return ControlOutput(0.0, self.parameters.full_brake)

    def _range_action(
        self,
        distance_m: float,
        ttc_s: float | None,
        mode: str,
        *,
        envelope: object,
        object_class: str | None = None,
    ) -> tuple[str, str, str]:
        if envelope is None:
            raise ValueError("a range action requires a dynamic safety envelope")
        caution_distance_m = float(getattr(envelope, "caution_distance_m"))
        emergency_distance_m = float(getattr(envelope, "emergency_distance_m"))
        if ttc_s is not None and ttc_s <= self.parameters.emergency_ttc_s:
            return mode, "EMERGENCY_BRAKE", "low_ttc"
        if distance_m <= emergency_distance_m:
            reason = "vru_dynamic_emergency_distance" if object_class in self._VRU_CLASSES else "dynamic_emergency_distance"
            return mode, "EMERGENCY_BRAKE", reason
        if ttc_s is not None and ttc_s <= self.parameters.caution_ttc_s:
            return mode, "SLOW_DOWN", "caution_ttc"
        if distance_m <= caution_distance_m:
            return mode, "SLOW_DOWN", "dynamic_caution_distance"
        return mode, "KEEP_SPEED", "front_hazard_outside_dynamic_envelope"
