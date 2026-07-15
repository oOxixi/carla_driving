"""C's CARLA-independent longitudinal orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass

from car_control_A import ControlOutput, LongitudinalOutput, LongitudinalRequest, RiskMetrics

from .following_controller import FollowingController, FollowingParameters
from .speed_pid import SpeedPID
from .speed_planner import SpeedPlanner, SpeedPlannerParameters
from .stop_controller import StopController, StopParameters, StopState
from .traffic_rules import TrafficRulePlanner
from .validation import finite


@dataclass(frozen=True, slots=True)
class LongitudinalParameters:
    """Explicit, SI-only tuning for C; final safety arbitration belongs to D."""

    max_lateral_accel_mps2: float = 2.5
    command_accel_mps2: float = 1.5
    command_decel_mps2: float = 3.0
    max_accel_mps2: float = 2.5
    max_decel_mps2: float = 5.0
    max_control_delta_per_s: float = 2.0
    hold_brake: float = 0.55
    emergency_brake: float = 0.85
    standstill_gap_m: float = 3.0
    time_gap_s: float = 1.5
    emergency_ttc_s: float = 1.5
    comfortable_decel_mps2: float = 3.0

    def __post_init__(self) -> None:
        for name in ("max_lateral_accel_mps2", "command_accel_mps2", "command_decel_mps2",
                     "max_accel_mps2", "max_decel_mps2", "max_control_delta_per_s",
                     "time_gap_s", "emergency_ttc_s", "comfortable_decel_mps2"):
            finite(name, getattr(self, name), positive=True)
        finite("standstill_gap_m", self.standstill_gap_m, minimum=0.0)
        finite("hold_brake", self.hold_brake, positive=True, maximum=1.0)
        finite("emergency_brake", self.emergency_brake, minimum=0.0, maximum=1.0)


class LongitudinalController:
    """Plans a speed and maps it to exclusive throttle/brake controls.

    It intentionally emits ``RiskMetrics`` instead of overriding a future D
    supervisor. ``target_accel_mps2`` is C's requested acceleration, not a
    final vehicle-authority command; D retains final arbitration.  The
    emergency-brake control here is a local C fallback only.
    """

    def __init__(self, parameters: LongitudinalParameters | None = None) -> None:
        self.parameters = parameters or LongitudinalParameters()
        stop = StopController(StopParameters(max_decel_mps2=self.parameters.max_decel_mps2,
                                              comfortable_decel_mps2=self.parameters.comfortable_decel_mps2,
                                              hold_brake=self.parameters.hold_brake))
        following = FollowingController(FollowingParameters(
            standstill_gap_m=self.parameters.standstill_gap_m,
            time_gap_s=self.parameters.time_gap_s,
            emergency_ttc_s=self.parameters.emergency_ttc_s,
            comfortable_decel_mps2=self.parameters.comfortable_decel_mps2,
        ))
        self.traffic_rules = TrafficRulePlanner()
        self.stop_controller = stop
        self.following_controller = following
        self.speed_planner = SpeedPlanner(SpeedPlannerParameters(
            max_lateral_accel_mps2=self.parameters.max_lateral_accel_mps2,
            command_accel_mps2=self.parameters.command_accel_mps2,
            command_decel_mps2=self.parameters.command_decel_mps2,
        ), self.traffic_rules, stop, following)
        self.pid = SpeedPID(accel_min_mps2=-self.parameters.max_decel_mps2,
                            accel_max_mps2=self.parameters.max_accel_mps2)
        self._last_throttle = 0.0
        self._last_brake = 0.0

    def _rate_limited_control(self, accel_mps2: float, dt_s: float) -> ControlOutput:
        if accel_mps2 >= 0.0:
            desired_throttle = min(1.0, accel_mps2 / self.parameters.max_accel_mps2)
            desired_brake = 0.0
        else:
            desired_throttle = 0.0
            desired_brake = min(1.0, -accel_mps2 / self.parameters.max_decel_mps2)
        delta = self.parameters.max_control_delta_per_s * dt_s
        throttle = max(0.0, min(desired_throttle, self._last_throttle + delta))
        throttle = max(throttle, self._last_throttle - delta)
        brake = max(0.0, min(desired_brake, self._last_brake + delta))
        brake = max(brake, self._last_brake - delta)
        # Never crossfade actuators: remove propulsion before applying braking,
        # or remove braking before allowing acceleration.
        if desired_brake > 0.0:
            throttle = 0.0
        elif desired_throttle > 0.0:
            brake = 0.0
        self._last_throttle, self._last_brake = throttle, brake
        return ControlOutput(throttle, brake)

    def step(self, request: LongitudinalRequest, dt_s: float) -> LongitudinalOutput:
        if not isinstance(request, LongitudinalRequest):
            raise TypeError("request must be LongitudinalRequest")
        dt_s = finite("dt_s", dt_s, positive=True)
        stop_distance = self.traffic_rules.stop_distance_m(request.traffic)
        stop_state = self.stop_controller.state_for(request.vehicle.speed_mps, stop_distance)
        risk = self.following_controller.risk(ego_speed_mps=request.vehicle.speed_mps,
            lead_distance_m=request.lead_distance_m, closing_speed_mps=request.closing_speed_mps)
        target = self.speed_planner.plan(request, dt_s)
        if stop_state is StopState.HOLD:
            self._last_throttle = 0.0
            self._last_brake = max(self.parameters.hold_brake, self._last_brake)
            return LongitudinalOutput(ControlOutput(0.0, self._last_brake), -self.parameters.max_decel_mps2,
                0.0, StopState.HOLD.value, "stop_line_hold", risk)
        if (stop_distance is not None and
                self.stop_controller.required_decel_mps2(request.vehicle.speed_mps, stop_distance) >= self.parameters.max_decel_mps2):
            self._last_throttle, self._last_brake = 0.0, 1.0
            return LongitudinalOutput(ControlOutput(0.0, 1.0), -self.parameters.max_decel_mps2,
                target, "EMERGENCY_BRAKE", "stop_unreachable_fallback", risk)
        accel = self.pid.step(target, request.vehicle.speed_mps, dt_s)
        if risk.emergency_brake_requested:
            self._last_throttle = 0.0
            self._last_brake = max(self.parameters.emergency_brake, self._last_brake)
            return LongitudinalOutput(ControlOutput(0.0, self._last_brake), -self.parameters.max_decel_mps2,
                target, "EMERGENCY_BRAKE", "local_ttc_risk", risk)
        control = self._rate_limited_control(accel, dt_s)
        if stop_state is not StopState.CRUISE:
            state, reason = stop_state.value, "traffic_stop_constraint"
        elif request.lead_distance_m is not None:
            state, reason = "FOLLOWING", "lead_vehicle_constraint"
        else:
            state, reason = "LANE_FOLLOW", "requested_speed"
        return LongitudinalOutput(control, accel, target, state, reason, risk)

    def reset(self) -> None:
        """Forget all episode-local histories before a CARLA respawn/reset."""
        self.pid.reset()
        self.speed_planner.reset()
        self._last_throttle = 0.0
        self._last_brake = 0.0
