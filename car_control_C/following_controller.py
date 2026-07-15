"""Time-gap following and local TTC risk estimation."""

from __future__ import annotations

from dataclasses import dataclass

from car_control_A import RiskMetrics
from .validation import finite


@dataclass(frozen=True, slots=True)
class FollowingParameters:
    standstill_gap_m: float = 3.0
    time_gap_s: float = 1.5
    emergency_ttc_s: float = 1.5
    comfortable_decel_mps2: float = 3.0

    def __post_init__(self) -> None:
        finite("standstill_gap_m", self.standstill_gap_m, minimum=0.0)
        finite("time_gap_s", self.time_gap_s, positive=True)
        finite("emergency_ttc_s", self.emergency_ttc_s, positive=True)
        finite("comfortable_decel_mps2", self.comfortable_decel_mps2, positive=True)


class FollowingController:
    def __init__(self, parameters: FollowingParameters | None = None) -> None:
        self.parameters = parameters or FollowingParameters()

    def desired_gap_m(self, ego_speed_mps: float) -> float:
        return self.parameters.standstill_gap_m + self.parameters.time_gap_s * finite("ego_speed_mps", ego_speed_mps, minimum=0.0)

    def risk(self, *, ego_speed_mps: float, lead_distance_m: float | None,
             closing_speed_mps: float | None) -> RiskMetrics:
        ego_speed_mps = finite("ego_speed_mps", ego_speed_mps, minimum=0.0)
        desired = self.desired_gap_m(ego_speed_mps)
        if lead_distance_m is None or closing_speed_mps is None:
            return RiskMetrics(None, desired, False)
        lead_distance_m = finite("lead_distance_m", lead_distance_m, minimum=0.0)
        closing_speed_mps = finite("closing_speed_mps", closing_speed_mps)
        if closing_speed_mps <= 0.0:
            return RiskMetrics(None, desired, False)
        ttc = lead_distance_m / closing_speed_mps
        emergency = ttc <= self.parameters.emergency_ttc_s
        return RiskMetrics(ttc, desired, emergency)

    def speed_cap_mps(self, *, ego_speed_mps: float, lead_distance_m: float | None,
                      closing_speed_mps: float | None) -> float | None:
        ego_speed_mps = finite("ego_speed_mps", ego_speed_mps, minimum=0.0)
        if lead_distance_m is None or closing_speed_mps is None:
            return None
        lead_distance_m = finite("lead_distance_m", lead_distance_m, minimum=0.0)
        closing_speed_mps = finite("closing_speed_mps", closing_speed_mps)
        gap_error = lead_distance_m - self.desired_gap_m(ego_speed_mps)
        # The relative-speed allowance follows v_rel^2 = 2*a*d using the
        # configured comfortable deceleration.  It is a hard planner ceiling.
        lead_speed = max(0.0, ego_speed_mps - closing_speed_mps)
        allowance = (2.0 * self.parameters.comfortable_decel_mps2 * max(0.0, gap_error)) ** 0.5
        return max(0.0, lead_speed + allowance)
