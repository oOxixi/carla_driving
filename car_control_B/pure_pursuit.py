"""Pure Pursuit lateral controller for CARLA."""

from __future__ import annotations

import math
from dataclasses import dataclass
from strategy_config import DEFAULT_STRATEGY

from .lateral_controller_base import LateralController
from .path_utils import (
    clamp,
    compute_path_heading,
    find_lookahead_index,
    find_nearest_index,
    signed_cross_track_error,
    wrap_angle_rad,
)
from .schemas import LateralOutput, RouteReference, VehiclePose


@dataclass(frozen=True)
class PurePursuitParams:
    wheel_base_m: float = DEFAULT_STRATEGY.lateral.wheel_base_m
    base_lookahead_m: float = DEFAULT_STRATEGY.lateral.base_lookahead_m
    speed_gain_s: float = DEFAULT_STRATEGY.lateral.speed_gain_s
    min_lookahead_m: float = DEFAULT_STRATEGY.lateral.min_lookahead_m
    max_lookahead_m: float = DEFAULT_STRATEGY.lateral.max_lookahead_m
    curvature_lookahead_gain: float = DEFAULT_STRATEGY.lateral.curvature_lookahead_gain
    error_lookahead_gain: float = DEFAULT_STRATEGY.lateral.error_lookahead_gain
    max_steer_angle_rad: float = DEFAULT_STRATEGY.lateral.max_steer_angle_rad
    steer_gain: float = DEFAULT_STRATEGY.lateral.steer_gain
    max_steer: float = DEFAULT_STRATEGY.lateral.max_steer
    min_steer_limit: float = DEFAULT_STRATEGY.lateral.min_steer_limit
    high_speed_steer_reduction_per_mps: float = DEFAULT_STRATEGY.lateral.high_speed_steer_reduction_per_mps
    curvature_steer_gain: float = DEFAULT_STRATEGY.lateral.curvature_steer_gain
    max_steer_delta_per_step: float = DEFAULT_STRATEGY.lateral.base_steer_delta_per_step
    min_steer_delta_per_step: float = DEFAULT_STRATEGY.lateral.min_steer_delta_per_step
    adaptive_max_steer_delta_per_step: float = DEFAULT_STRATEGY.lateral.max_steer_delta_per_step
    low_speed_steer_gain: float = DEFAULT_STRATEGY.lateral.low_speed_steer_gain
    curvature_rate_gain: float = DEFAULT_STRATEGY.lateral.curvature_rate_gain
    error_rate_gain: float = DEFAULT_STRATEGY.lateral.error_rate_gain
    # On the CARLA 0.9.16 Model 3, positive VehicleControl steering follows
    # positive map-right local_y.  This is verified by the CARLA closed-loop
    # acceptance smoke test; do not invert it from a screenshot alone.
    steer_sign: float = DEFAULT_STRATEGY.lateral.steer_sign
    nearest_search_window: int | None = None

    def __post_init__(self) -> None:
        numeric = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "nearest_search_window"
        }
        if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in numeric.values()):
            raise ValueError("all Pure Pursuit parameters must be finite numbers")
        positive = set(numeric) - {"steer_sign"}
        if any(float(numeric[name]) < 0.0 for name in positive):
            raise ValueError("Pure Pursuit magnitudes must be non-negative")
        if self.min_lookahead_m > self.max_lookahead_m:
            raise ValueError("min_lookahead_m must not exceed max_lookahead_m")
        if self.min_steer_limit > self.max_steer:
            raise ValueError("min_steer_limit must not exceed max_steer")
        if self.min_steer_delta_per_step > self.adaptive_max_steer_delta_per_step:
            raise ValueError("adaptive steer delta limits are inverted")
        if self.steer_sign not in {-1.0, 1.0}:
            raise ValueError("steer_sign must be -1 or 1")
        if self.nearest_search_window is not None and (
            type(self.nearest_search_window) is not int or self.nearest_search_window <= 0
        ):
            raise ValueError("nearest_search_window must be a positive integer or None")


class PurePursuitController(LateralController):
    def __init__(self, params: PurePursuitParams | None = None):
        self.params = params or PurePursuitParams()
        self._last_steer = 0.0
        self._last_nearest_index = 0

    def reset(self) -> None:
        self._last_steer = 0.0
        self._last_nearest_index = 0

    def _lookahead(self, speed_mps: float, curvature_per_m: float = 0.0,
                   cross_track_error_m: float = 0.0,
                   heading_error_rad: float = 0.0) -> float:
        p = self.params
        speed_lookahead = p.base_lookahead_m + p.speed_gain_s * speed_mps
        geometry_penalty = (
            1.0
            + p.curvature_lookahead_gain * abs(curvature_per_m)
            + p.error_lookahead_gain * (
                abs(cross_track_error_m) + p.wheel_base_m * abs(heading_error_rad)
            )
        )
        return clamp(speed_lookahead / geometry_penalty, p.min_lookahead_m, p.max_lookahead_m)

    def _steer_limit(self, speed_mps: float, curvature_per_m: float) -> float:
        p = self.params
        scheduled = (
            p.max_steer
            - p.high_speed_steer_reduction_per_mps * speed_mps
            + p.curvature_steer_gain * abs(curvature_per_m)
        )
        return clamp(scheduled, p.min_steer_limit, p.max_steer)

    def _steer_delta_limit(self, speed_mps: float, curvature_per_m: float,
                           cross_track_error_m: float, heading_error_rad: float) -> float:
        p = self.params
        low_speed_multiplier = 1.0 + p.low_speed_steer_gain / (1.0 + speed_mps)
        geometry_multiplier = (
            1.0
            + p.curvature_rate_gain * abs(curvature_per_m)
            + p.error_rate_gain * (abs(cross_track_error_m) + abs(heading_error_rad))
        )
        return clamp(
            p.max_steer_delta_per_step * low_speed_multiplier * geometry_multiplier,
            p.min_steer_delta_per_step,
            max(p.adaptive_max_steer_delta_per_step, p.max_steer_delta_per_step),
        )

    def step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput:
        p = self.params
        points = reference.points_xy_m
        nearest = find_nearest_index(
            points,
            vehicle.x_m,
            vehicle.y_m,
            start_index=self._last_nearest_index,
            search_window=p.nearest_search_window,
        )
        self._last_nearest_index = nearest

        path_heading = compute_path_heading(points, nearest)
        heading_error = wrap_angle_rad(path_heading - vehicle.yaw_rad)
        cte = signed_cross_track_error(points, nearest, vehicle.x_m, vehicle.y_m)
        lookahead = self._lookahead(
            vehicle.speed_mps,
            reference.curvature_per_m,
            cte,
            heading_error,
        )
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
        steer_limit = self._steer_limit(vehicle.speed_mps, reference.curvature_per_m)
        steer = clamp(steer, -steer_limit, steer_limit)

        delta_limit = self._steer_delta_limit(
            vehicle.speed_mps, reference.curvature_per_m, cte, heading_error,
        )
        delta = clamp(steer - self._last_steer, -delta_limit, delta_limit)
        steer = self._last_steer + delta
        self._last_steer = steer

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
