"""Stanley controller as a backup/comparison controller."""

from __future__ import annotations

import math
from dataclasses import dataclass
from strategy_config import DEFAULT_STRATEGY

from .lateral_controller_base import LateralController
from .path_utils import clamp, compute_path_heading, find_nearest_index, signed_cross_track_error, wrap_angle_rad
from .schemas import LateralOutput, RouteReference, VehiclePose


@dataclass(frozen=True)
class StanleyParams:
    gain: float = DEFAULT_STRATEGY.lateral.stanley_gain
    softening_speed_mps: float = DEFAULT_STRATEGY.lateral.stanley_softening_speed_mps
    curvature_gain: float = DEFAULT_STRATEGY.lateral.stanley_curvature_gain
    max_steer_angle_rad: float = DEFAULT_STRATEGY.lateral.max_steer_angle_rad
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
    # See PurePursuitParams.steer_sign for the CARLA 0.9.16 command mapping.
    steer_sign: float = DEFAULT_STRATEGY.lateral.steer_sign
    nearest_search_window: int | None = None

    def __post_init__(self) -> None:
        numeric = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "nearest_search_window"
        }
        if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in numeric.values()):
            raise ValueError("all Stanley parameters must be finite numbers")
        positive = set(numeric) - {"steer_sign"}
        if any(float(numeric[name]) < 0.0 for name in positive):
            raise ValueError("Stanley magnitudes must be non-negative")
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


class StanleyController(LateralController):
    def __init__(self, params: StanleyParams | None = None):
        self.params = params or StanleyParams()
        self._last_steer = 0.0
        self._last_nearest_index = 0

    def reset(self) -> None:
        self._last_steer = 0.0
        self._last_nearest_index = 0

    def step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput:
        p = self.params
        points = reference.points_xy_m
        nearest = find_nearest_index(points, vehicle.x_m, vehicle.y_m, self._last_nearest_index, p.nearest_search_window)
        self._last_nearest_index = nearest

        path_heading = compute_path_heading(points, nearest)
        heading_error = wrap_angle_rad(path_heading - vehicle.yaw_rad)
        cte = signed_cross_track_error(points, nearest, vehicle.x_m, vehicle.y_m)

        # cte>0 means vehicle is map-right of the path; correction is a
        # negative steering command toward map-left.
        scheduled_gain = p.gain * (1.0 + p.curvature_gain * abs(reference.curvature_per_m))
        cte_term = -math.atan2(scheduled_gain * cte, vehicle.speed_mps + p.softening_speed_mps)
        steer_math = wrap_angle_rad(heading_error + cte_term)
        steer = p.steer_sign * steer_math / max(p.max_steer_angle_rad, 1e-6)
        steer_limit = clamp(
            p.max_steer
            - p.high_speed_steer_reduction_per_mps * vehicle.speed_mps
            + p.curvature_steer_gain * abs(reference.curvature_per_m),
            p.min_steer_limit,
            p.max_steer,
        )
        steer = clamp(steer, -steer_limit, steer_limit)
        delta_limit = clamp(
            p.max_steer_delta_per_step
            * (1.0 + p.low_speed_steer_gain / (1.0 + vehicle.speed_mps))
            * (1.0 + p.curvature_rate_gain * abs(reference.curvature_per_m)
               + p.error_rate_gain * (abs(cte) + abs(heading_error))),
            p.min_steer_delta_per_step,
            max(p.adaptive_max_steer_delta_per_step, p.max_steer_delta_per_step),
        )
        delta = clamp(steer - self._last_steer, -delta_limit, delta_limit)
        steer = self._last_steer + delta
        self._last_steer = steer

        return LateralOutput(
            steer=steer,
            cross_track_error_m=cte,
            heading_error_rad=heading_error,
            target_point_xy_m=points[nearest],
            lookahead_distance_m=0.0,
            nearest_index=nearest,
            target_index=nearest,
            status="OK",
            reason="STANLEY",
        )
