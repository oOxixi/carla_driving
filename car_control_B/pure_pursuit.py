"""Pure Pursuit lateral controller for CARLA."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .lateral_controller_base import LateralController
from .path_utils import (
    clamp,
    compute_path_heading,
    find_lookahead_index,
    find_nearest_index,
    max_abs_curvature_ahead,
    signed_cross_track_error,
    wrap_angle_rad,
)
from .schemas import LateralOutput, RouteReference, VehiclePose


@dataclass(frozen=True)
class PurePursuitParams:
    wheel_base_m: float = 2.8
    base_lookahead_m: float = 2.0
    speed_gain_s: float = 0.40
    curvature_lookahead_gain: float = 4.0
    min_lookahead_m: float = 2.0
    max_lookahead_m: float = 8.0
    max_steer_angle_rad: float = 0.60
    steer_gain: float = 1.0
    max_steer: float = 1.0
    max_steer_delta_per_step: float = 0.08
    # On the CARLA 0.9.16 Model 3, positive VehicleControl steering follows
    # positive map-right local_y.  This is verified by the CARLA closed-loop
    # acceptance smoke test; do not invert it from a screenshot alone.
    steer_sign: float = 1.0
    nearest_search_window: int | None = None


class PurePursuitController(LateralController):
    def __init__(self, params: PurePursuitParams | None = None):
        self.params = params or PurePursuitParams()
        self._last_steer = 0.0
        self._last_nearest_index = 0
        self._active_route_key: int | None = None
        self._nearest_index_by_route: dict[int, int] = {}

    def reset(self) -> None:
        self._last_steer = 0.0
        self._last_nearest_index = 0
        self._active_route_key = None
        self._nearest_index_by_route.clear()

    def _lookahead(self, speed_mps: float, curvature_per_m: float = 0.0) -> float:
        p = self.params
        nominal = p.base_lookahead_m + p.speed_gain_s * speed_mps
        adapted = nominal / (
            1.0 + p.curvature_lookahead_gain * abs(curvature_per_m)
        )
        return clamp(adapted, p.min_lookahead_m, p.max_lookahead_m)

    def step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput:
        p = self.params
        points = reference.points_xy_m
        route_key = id(points)
        if route_key != self._active_route_key:
            # A compiled manoeuvre can temporarily replace a long mission
            # route and later restore the exact same point tuple.  Remember
            # progress per route so the restoration cannot globally snap to a
            # geometrically overlapping occurrence kilometres ahead.
            self._last_nearest_index = self._nearest_index_by_route.get(
                route_key,
                find_nearest_index(points, vehicle.x_m, vehicle.y_m),
            )
            self._active_route_key = route_key
        nearest = find_nearest_index(
            points,
            vehicle.x_m,
            vehicle.y_m,
            start_index=self._last_nearest_index,
            search_window=p.nearest_search_window,
        )
        self._last_nearest_index = nearest
        self._nearest_index_by_route[route_key] = nearest

        local_curvature = max_abs_curvature_ahead(
            points, nearest, horizon_m=max(15.0, vehicle.speed_mps * 4.0),
        )
        lookahead = self._lookahead(vehicle.speed_mps, local_curvature)
        target_idx = find_lookahead_index(points, nearest, (vehicle.x_m, vehicle.y_m), lookahead)
        target = points[target_idx]

        dx = target[0] - vehicle.x_m
        dy = target[1] - vehicle.y_m

        # CARLA map/ego frame: local_x is forward and local_y is map-right.
        local_x = math.cos(vehicle.yaw_rad) * dx + math.sin(vehicle.yaw_rad) * dy
        local_y = -math.sin(vehicle.yaw_rad) * dx + math.cos(vehicle.yaw_rad) * dy

        target_is_behind = local_x <= 0.05
        if target_is_behind:
            steer_math = 0.0
        else:
            alpha = math.atan2(local_y, local_x)
            curvature = 2.0 * math.sin(alpha) / max(lookahead, 1e-6)
            steer_angle = math.atan(p.wheel_base_m * curvature)
            steer_math = steer_angle / max(p.max_steer_angle_rad, 1e-6)

        steer = p.steer_sign * p.steer_gain * steer_math
        steer = clamp(steer, -p.max_steer, p.max_steer)

        delta = clamp(steer - self._last_steer, -p.max_steer_delta_per_step, p.max_steer_delta_per_step)
        steer = self._last_steer + delta
        self._last_steer = steer

        path_heading = compute_path_heading(points, nearest)
        heading_error = wrap_angle_rad(path_heading - vehicle.yaw_rad)
        cte = signed_cross_track_error(points, nearest, vehicle.x_m, vehicle.y_m)

        return LateralOutput(
            steer=steer,
            cross_track_error_m=cte,
            heading_error_rad=heading_error,
            target_point_xy_m=target,
            lookahead_distance_m=lookahead,
            nearest_index=nearest,
            target_index=target_idx,
            status="INVALID" if target_is_behind else "OK",
            reason="TARGET_BEHIND_EGO" if target_is_behind else "PURE_PURSUIT",
        )
