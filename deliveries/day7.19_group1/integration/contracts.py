"""Small integration-only contracts shared by the runtime adapters.

These contracts deliberately contain no CARLA imports.  A real CARLA bridge can
populate them from sensors or from simulator ground truth, while tests can use
the same structures without starting Unreal.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from car_control_A import ControlOutput, ExecutionFeedback, LongitudinalOutput, RuntimeVehicleState
from car_control_B.schemas import LateralOutput


def _finite_or_none(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number or None")
    return float(value)


@dataclass(frozen=True, slots=True)
class DetectedObject:
    """One RGB road-user detection, optionally fused with a sensor distance."""

    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy_norm: tuple[float, float, float, float]
    distance_m: float | None = None

    def __post_init__(self) -> None:
        if type(self.class_id) is not int or self.class_id < 0:
            raise ValueError("class_id must be a non-negative integer")
        if type(self.class_name) is not str or not self.class_name:
            raise ValueError("class_name must be non-empty")
        if type(self.confidence) not in (int, float) or not math.isfinite(float(self.confidence)):
            raise ValueError("confidence must be finite")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if type(self.bbox_xyxy_norm) is not tuple or len(self.bbox_xyxy_norm) != 4:
            raise TypeError("bbox_xyxy_norm must be a four-number tuple")
        x1, y1, x2, y2 = (
            _finite_or_none(f"bbox_xyxy_norm[{index}]", value)
            for index, value in enumerate(self.bbox_xyxy_norm)
        )
        if any(value is None or value < 0.0 or value > 1.0 for value in (x1, y1, x2, y2)):
            raise ValueError("normalized detection box values must be in [0, 1]")
        if x2 <= x1 or y2 <= y1:
            raise ValueError("detection box must have positive width and height")
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "bbox_xyxy_norm", (x1, y1, x2, y2))
        distance = _finite_or_none("distance_m", self.distance_m)
        if distance is not None and distance < 0.0:
            raise ValueError("distance_m must be non-negative")
        object.__setattr__(self, "distance_m", distance)


@dataclass(frozen=True, slots=True)
class PerceptionFrame:
    """Frame-aligned scene facts consumed by C and D.

    The initial CARLA bridge may populate these values from simulator truth for
    validation. Replacing that bridge with RGB/LiDAR algorithms must preserve
    this contract and frame equality, rather than change the controller APIs.
    """
    frame: int
    sim_time_s: float
    lead_distance_m: float | None = None
    lead_speed_mps: float | None = None
    traffic_light: str = "UNKNOWN"
    distance_to_stop_line_m: float | None = None
    speed_limit_mps: float | None = None
    lane_offset_m: float | None = None
    route_deviation_m: float | None = None
    collision: bool = False
    red_light_violation: bool = False
    lane_invasion: bool = False
    detected_objects: tuple[DetectedObject, ...] = ()

    def __post_init__(self) -> None:
        if type(self.frame) is not int or self.frame < 0:
            raise ValueError("frame must be a non-negative integer")
        sim_time = _finite_or_none("sim_time_s", self.sim_time_s)
        if sim_time is None or sim_time < 0:
            raise ValueError("sim_time_s must be non-negative")
        object.__setattr__(self, "sim_time_s", sim_time)
        for name in ("lead_distance_m", "lead_speed_mps", "distance_to_stop_line_m", "speed_limit_mps", "lane_offset_m", "route_deviation_m"):
            value = _finite_or_none(name, getattr(self, name))
            if name in {"lead_distance_m", "lead_speed_mps", "distance_to_stop_line_m", "speed_limit_mps"} and value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)
        if self.traffic_light not in {"RED", "YELLOW", "GREEN", "UNKNOWN"}:
            raise ValueError("traffic_light must be RED/YELLOW/GREEN/UNKNOWN")
        for name in ("collision", "red_light_violation", "lane_invasion"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        if type(self.detected_objects) is not tuple or any(
            not isinstance(item, DetectedObject) for item in self.detected_objects
        ):
            raise TypeError("detected_objects must be a tuple of DetectedObject values")


@dataclass(frozen=True, slots=True)
class FrameResult:
    """Auditable output of one control frame; only ``final_control`` reaches CARLA."""
    vehicle: RuntimeVehicleState
    final_control: ControlOutput
    longitudinal: LongitudinalOutput | None
    safety_reason: str
    safety_override: bool
    feedback: tuple[ExecutionFeedback, ...] = ()
    # Fault-injection scenarios deliberately pass malformed mappings to D.
    # Keep the pre-D value as evidence even when it cannot be represented by
    # A's validated ControlOutput contract.
    raw_control: Any | None = None
    lateral: LateralOutput | None = None
