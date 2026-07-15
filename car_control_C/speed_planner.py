"""Multi-constraint target-speed planner."""

from __future__ import annotations

from dataclasses import dataclass
import math

from car_control_A import LongitudinalRequest
from .following_controller import FollowingController
from .stop_controller import StopController
from .traffic_rules import TrafficRulePlanner
from .validation import finite


@dataclass(frozen=True, slots=True)
class SpeedPlannerParameters:
    max_lateral_accel_mps2: float = 2.5
    command_accel_mps2: float = 1.5
    command_decel_mps2: float = 3.0

    def __post_init__(self) -> None:
        finite("max_lateral_accel_mps2", self.max_lateral_accel_mps2, positive=True)
        finite("command_accel_mps2", self.command_accel_mps2, positive=True)
        finite("command_decel_mps2", self.command_decel_mps2, positive=True)


class SpeedPlanner:
    def __init__(self, parameters: SpeedPlannerParameters | None = None,
                 traffic_rules: TrafficRulePlanner | None = None,
                 stop_controller: StopController | None = None,
                 following_controller: FollowingController | None = None) -> None:
        self.parameters = parameters or SpeedPlannerParameters()
        self.traffic_rules = traffic_rules or TrafficRulePlanner()
        self.stop_controller = stop_controller or StopController()
        self.following_controller = following_controller or FollowingController()
        self._previous_target: float | None = None

    def plan(self, request: LongitudinalRequest, dt_s: float) -> float:
        if not isinstance(request, LongitudinalRequest):
            raise TypeError("request must be LongitudinalRequest")
        dt_s = finite("dt_s", dt_s, positive=True)
        curvature = abs(request.path_curvature_per_m)
        curve_cap = math.inf if curvature <= 1e-9 else math.sqrt(self.parameters.max_lateral_accel_mps2 / curvature)
        # Curvature, traffic, stopping and lead constraints are hard safety
        # ceilings.  The command ramp is comfort-only and may never exceed them.
        hard_caps = [curve_cap]
        speed_limit = self.traffic_rules.speed_limit_mps(request.traffic)
        if speed_limit is not None:
            hard_caps.append(speed_limit)
        stop_cap = self.stop_controller.speed_cap_mps(request.vehicle.speed_mps,
            self.traffic_rules.stop_distance_m(request.traffic), dt_s)
        if stop_cap is not None:
            hard_caps.append(stop_cap)
        lead_cap = self.following_controller.speed_cap_mps(ego_speed_mps=request.vehicle.speed_mps,
            lead_distance_m=request.lead_distance_m, closing_speed_mps=request.closing_speed_mps)
        if lead_cap is not None:
            hard_caps.append(lead_cap)
        hard_cap = max(0.0, min(hard_caps))
        base = request.vehicle.speed_mps if self._previous_target is None else self._previous_target
        if request.requested_speed_mps >= base:
            comfort_target = min(request.requested_speed_mps, base + self.parameters.command_accel_mps2 * dt_s)
        else:
            comfort_target = max(request.requested_speed_mps, base - self.parameters.command_decel_mps2 * dt_s)
        target = min(comfort_target, hard_cap)
        self._previous_target = max(0.0, target)
        return self._previous_target

    def reset(self) -> None:
        """Forget target history at the start of an independent episode."""
        self._previous_target = None
