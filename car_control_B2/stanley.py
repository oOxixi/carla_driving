"""Stanley controller as a backup/comparison controller."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .lateral_controller_base import LateralController
from .path_utils import clamp, compute_path_heading, find_nearest_index, signed_cross_track_error, wrap_angle_rad
from .schemas import LateralOutput, RouteReference, VehiclePose


@dataclass(frozen=True)
class StanleyParams:
    gain: float = 0.8
    softening_speed_mps: float = 1.0
    max_steer_angle_rad: float = 0.60
    max_steer: float = 1.0
    max_steer_delta_per_step: float = 0.08
    # See PurePursuitParams.steer_sign for the CARLA 0.9.16 command mapping.
    steer_sign: float = 1.0
    nearest_search_window: int | None = None


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
        cte_term = -math.atan2(p.gain * cte, vehicle.speed_mps + p.softening_speed_mps)
        steer_math = wrap_angle_rad(heading_error + cte_term)
        steer = p.steer_sign * steer_math / max(p.max_steer_angle_rad, 1e-6)
        steer = clamp(steer, -p.max_steer, p.max_steer)
        delta = clamp(steer - self._last_steer, -p.max_steer_delta_per_step, p.max_steer_delta_per_step)
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
