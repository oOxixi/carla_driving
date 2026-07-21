"""Adapters that accept dicts or A-side dataclasses."""

from __future__ import annotations

import math
from typing import Any, Mapping

from .schemas import RouteReference, VehiclePose


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def adapt_vehicle_pose(vehicle_state: Any) -> VehiclePose:
    """Convert A RuntimeVehicleState/dict into B VehiclePose.

    Supports both yaw_rad and yaw_deg. A handoff currently exposes yaw_deg, while
    some internal tests may use yaw_rad.
    """
    x = _get(vehicle_state, "x_m", _get(vehicle_state, "x", None))
    y = _get(vehicle_state, "y_m", _get(vehicle_state, "y", None))
    speed = _get(vehicle_state, "speed_mps", None)
    yaw_rad = _get(vehicle_state, "yaw_rad", None)
    if yaw_rad is None:
        yaw_deg = _get(vehicle_state, "yaw_deg", None)
        if yaw_deg is None:
            raise ValueError("vehicle_state must provide yaw_rad or yaw_deg")
        yaw_rad = math.radians(float(yaw_deg))
    return VehiclePose(
        x_m=float(x),
        y_m=float(y),
        yaw_rad=float(yaw_rad),
        speed_mps=float(speed),
        frame=_get(vehicle_state, "frame", _get(vehicle_state, "frame_id", None)),
        sim_time_s=_get(vehicle_state, "sim_time_s", _get(vehicle_state, "sim_time", None)),
    )


def adapt_route_reference(reference: Any) -> RouteReference:
    points = _get(reference, "points_xy_m", None)
    if points is None:
        points = _get(reference, "points", None)
    if points is None:
        raise ValueError("reference must provide points_xy_m")
    return RouteReference(
        points_xy_m=[tuple(p) for p in points],
        curvature_per_m=float(_get(reference, "curvature_per_m", 0.0)),
        target_speed_mps=float(_get(reference, "target_speed_mps", 5.0)),
        route_id=_get(reference, "route_id", None),
        metadata=dict(_get(reference, "metadata", {}) or {}),
    )
