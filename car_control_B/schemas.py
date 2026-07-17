"""Data contracts for member B lateral control.

B owns lateral tracking only. It does not control throttle/brake and does not
call CARLA apply_control directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple
import math

SCHEMA_VERSION = "1.0"

Point2D = Tuple[float, float]


class SchemaError(ValueError):
    """Raised when an input contract is invalid."""


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise SchemaError(f"{name} must be finite")
    return value


def _point_list(points: Sequence[Sequence[float]]) -> List[Point2D]:
    if points is None or len(points) < 2:
        raise SchemaError("points_xy_m must contain at least two points")
    out: List[Point2D] = []
    for idx, item in enumerate(points):
        if len(item) != 2:
            raise SchemaError(f"points_xy_m[{idx}] must be length 2")
        out.append((_finite(f"points_xy_m[{idx}][0]", item[0]), _finite(f"points_xy_m[{idx}][1]", item[1])))
    return out


@dataclass(frozen=True)
class VehiclePose:
    """Frame-aligned ego pose consumed by B.

    yaw_rad is the vehicle heading in radians, x-axis points forward in the map
    coordinate convention used by the route points.
    """

    x_m: float
    y_m: float
    yaw_rad: float
    speed_mps: float
    frame: Optional[int] = None
    sim_time_s: Optional[float] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "x_m", _finite("x_m", self.x_m))
        object.__setattr__(self, "y_m", _finite("y_m", self.y_m))
        object.__setattr__(self, "yaw_rad", _finite("yaw_rad", self.yaw_rad))
        speed = _finite("speed_mps", self.speed_mps)
        if speed < 0:
            raise SchemaError("speed_mps must be non-negative")
        object.__setattr__(self, "speed_mps", speed)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        return data


@dataclass(frozen=True)
class RouteReference:
    """Local route reference from A to B.

    points_xy_m must be in map/world meters and preferably equally spaced.
    target_speed_mps is advisory for gain scheduling only; C still owns speed.
    """

    points_xy_m: List[Point2D]
    curvature_per_m: float = 0.0
    target_speed_mps: float = 5.0
    route_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "points_xy_m", _point_list(self.points_xy_m))
        object.__setattr__(self, "curvature_per_m", _finite("curvature_per_m", self.curvature_per_m))
        target_speed = _finite("target_speed_mps", self.target_speed_mps)
        if target_speed < 0:
            raise SchemaError("target_speed_mps must be non-negative")
        object.__setattr__(self, "target_speed_mps", target_speed)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        return data


@dataclass(frozen=True)
class LateralOutput:
    """B output to A/D.

    ``steer`` is passed directly to ``carla.VehicleControl``.  Its physical
    left/right mapping is selected by the controller's ``steer_sign``
    calibration rather than inferred by a downstream consumer.
    """

    steer: float
    cross_track_error_m: float
    heading_error_rad: float
    target_point_xy_m: Point2D
    lookahead_distance_m: float
    nearest_index: int
    target_index: int
    status: str = "OK"
    reason: str = "NONE"

    def __post_init__(self) -> None:
        steer = _finite("steer", self.steer)
        if not -1.0 <= steer <= 1.0:
            raise SchemaError("steer must be in [-1, 1]")
        object.__setattr__(self, "steer", steer)
        object.__setattr__(self, "cross_track_error_m", _finite("cross_track_error_m", self.cross_track_error_m))
        object.__setattr__(self, "heading_error_rad", _finite("heading_error_rad", self.heading_error_rad))
        object.__setattr__(self, "lookahead_distance_m", _finite("lookahead_distance_m", self.lookahead_distance_m))
        if self.nearest_index < 0 or self.target_index < 0:
            raise SchemaError("nearest_index and target_index must be non-negative")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        return data
