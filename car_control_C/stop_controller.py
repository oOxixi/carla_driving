"""Four-phase longitudinal stopping policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from .validation import finite


class StopState(StrEnum):
    CRUISE = "CRUISE"
    DECELERATE = "DECELERATE"
    CREEP = "CREEP"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class StopParameters:
    max_decel_mps2: float = 4.0
    comfortable_decel_mps2: float = 3.0
    creep_speed_mps: float = 0.5
    hold_distance_m: float = 0.8
    hold_speed_mps: float = 0.15
    hold_brake: float = 0.55

    def __post_init__(self) -> None:
        finite("max_decel_mps2", self.max_decel_mps2, positive=True)
        finite("comfortable_decel_mps2", self.comfortable_decel_mps2, positive=True)
        finite("creep_speed_mps", self.creep_speed_mps, minimum=0.0)
        finite("hold_distance_m", self.hold_distance_m, minimum=0.0)
        finite("hold_speed_mps", self.hold_speed_mps, minimum=0.0)
        finite("hold_brake", self.hold_brake, positive=True, maximum=1.0)


class StopController:
    def __init__(self, parameters: StopParameters | None = None) -> None:
        self.parameters = parameters or StopParameters()

    def state_for(self, speed_mps: float, distance_m: float | None) -> StopState:
        speed_mps = finite("speed_mps", speed_mps, minimum=0.0)
        if distance_m is not None:
            distance_m = finite("distance_m", distance_m, minimum=0.0)
        if distance_m is None:
            return StopState.CRUISE
        if distance_m <= self.parameters.hold_distance_m and speed_mps <= self.parameters.hold_speed_mps:
            return StopState.HOLD
        if distance_m <= max(2.0, self.parameters.hold_distance_m * 3.0):
            return StopState.CREEP
        return StopState.DECELERATE

    def speed_cap_mps(self, speed_mps: float, distance_m: float | None, dt_s: float = 0.0) -> float | None:
        speed_mps = finite("speed_mps", speed_mps, minimum=0.0)
        dt_s = finite("dt_s", dt_s, minimum=0.0)
        if distance_m is not None:
            distance_m = finite("distance_m", distance_m, minimum=0.0)
        if distance_m is None:
            return None
        state = self.state_for(speed_mps, distance_m)
        if state is StopState.HOLD:
            return 0.0
        if state is StopState.CREEP:
            return self.parameters.creep_speed_mps
        # v^2 = 2 a d.  Nominal planning deliberately uses comfortable
        # deceleration; the caller separately detects an unreachable stop.
        kinematic_cap = max(0.0, (2.0 * self.parameters.comfortable_decel_mps2 * max(0.0, distance_m - self.parameters.hold_distance_m)) ** 0.5)
        # Once a stop constraint exists it authorises deceleration, never a
        # fresh acceleration toward the line.
        return min(speed_mps - self.parameters.comfortable_decel_mps2 * max(0.0, dt_s), kinematic_cap)

    def required_decel_mps2(self, speed_mps: float, distance_m: float | None) -> float:
        speed_mps = finite("speed_mps", speed_mps, minimum=0.0)
        if distance_m is not None:
            distance_m = finite("distance_m", distance_m, minimum=0.0)
        if distance_m is None or speed_mps <= 0.0:
            return 0.0
        usable_distance = max(1e-3, distance_m - self.parameters.hold_distance_m)
        return speed_mps * speed_mps / (2.0 * usable_distance)
