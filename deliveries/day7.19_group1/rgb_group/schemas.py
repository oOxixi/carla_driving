from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math

SCHEMA_VERSION = "1.0"
BBox = Tuple[int, int, int, int]

ALLOWED_CATEGORIES = {
    "VEHICLE", "PEDESTRIAN", "TRAFFIC_CONE", "ROADBLOCK",
    "BICYCLE", "MOTORCYCLE", "TRAFFIC_LIGHT", "UNKNOWN",
}
ALLOWED_LIGHT_STATES = {"RED", "YELLOW", "GREEN", "OFF", "UNKNOWN"}
ALLOWED_STATUS = {"OK", "DEGRADED", "TIMEOUT", "ERROR", "UNAVAILABLE", "STALE"}


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


@dataclass(frozen=True)
class Detection:
    track_id: str
    category: str
    confidence: float
    bbox_xyxy: BBox
    image_region: str
    in_danger_zone: bool
    source: str = "ONNX"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        category = str(self.category).upper()
        object.__setattr__(self, "category", category if category in ALLOWED_CATEGORIES else "UNKNOWN")
        confidence = _finite("confidence", self.confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        object.__setattr__(self, "confidence", confidence)
        if len(self.bbox_xyxy) != 4:
            raise ValueError("bbox_xyxy must contain four integers")
        x1, y1, x2, y2 = (int(v) for v in self.bbox_xyxy)
        if x2 <= x1 or y2 <= y1:
            raise ValueError("bbox_xyxy must have positive area")
        object.__setattr__(self, "bbox_xyxy", (x1, y1, x2, y2))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrafficLightObservation:
    state: str = "UNKNOWN"
    confidence: float = 0.0
    visible: bool = False
    bbox_xyxy: Optional[BBox] = None
    source: str = "NONE"

    def __post_init__(self) -> None:
        state = str(self.state).upper()
        object.__setattr__(self, "state", state if state in ALLOWED_LIGHT_STATES else "UNKNOWN")
        confidence = _finite("traffic_light.confidence", self.confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("traffic light confidence must be in [0, 1]")
        object.__setattr__(self, "confidence", confidence)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VisionObservation:
    frame: int
    sim_time_s: float
    sensor_id: str
    image_width: int
    image_height: int
    objects: List[Detection] = field(default_factory=list)
    traffic_light: TrafficLightObservation = field(default_factory=TrafficLightObservation)
    perception_status: str = "OK"
    latency_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.frame < 0:
            raise ValueError("frame must be non-negative")
        object.__setattr__(self, "sim_time_s", _finite("sim_time_s", self.sim_time_s))
        object.__setattr__(self, "latency_ms", _finite("latency_ms", self.latency_ms))
        if self.image_width <= 0 or self.image_height <= 0:
            raise ValueError("image dimensions must be positive")
        status = str(self.perception_status).upper()
        object.__setattr__(self, "perception_status", status if status in ALLOWED_STATUS else "ERROR")

    @property
    def scene_summary(self) -> Dict[str, bool]:
        categories = {obj.category for obj in self.objects if obj.in_danger_zone}
        return {
            "front_vehicle": "VEHICLE" in categories,
            "front_pedestrian": "PEDESTRIAN" in categories,
            "front_obstacle": bool(categories & {"VEHICLE", "PEDESTRIAN", "TRAFFIC_CONE", "ROADBLOCK", "BICYCLE", "MOTORCYCLE"}),
            "red_light": self.traffic_light.state == "RED",
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["scene_summary"] = self.scene_summary
        return data
