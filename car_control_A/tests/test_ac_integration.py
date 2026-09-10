"""CARLA-free A/C control and safety regression tests.

Voice interpretation is intentionally absent: production voice commands enter
this control layer only after a validated Qwen plan has been compiled.
"""

from __future__ import annotations

from car_control_A import (
    ControlOutput,
    DrivingCommand,
    LongitudinalRequest,
    RuntimeVehicleState,
)
from car_control_A.behavior_fsm import BehaviorFSM, BehaviorState
from car_control_A.watchdog import RuntimeWatchdog
from car_control_C import FuzzyCommandPolicy, LongitudinalController


def _vehicle(*, sim_time_s: float = 10.0, speed_mps: float = 0.0) -> RuntimeVehicleState:
    return RuntimeVehicleState(42, sim_time_s, speed_mps, 1.0, 2.0, 0.0, 0.0, "lane-1")


def _request(vehicle: RuntimeVehicleState, *, target_speed_mps: float,
             lead_distance_m: float | None = None,
             closing_speed_mps: float | None = None) -> LongitudinalRequest:
    return LongitudinalRequest(vehicle, target_speed_mps, 0.0, None,
                               lead_distance_m, closing_speed_mps)


def test_low_confidence_command_enters_confirmation_and_c_safe_stop_preserves_ttc() -> None:
    command = DrivingCommand("voice-low-ttc", 10.0, 15.0, 0.1, "SET_SPEED", 12.0)
    fsm = BehaviorFSM()
    assert fsm.submit(command, now_s=10.0).state is BehaviorState.CONFIRMING

    request = _request(_vehicle(speed_mps=8.0), target_speed_mps=12.0,
                       lead_distance_m=2.0, closing_speed_mps=4.0)
    decision = FuzzyCommandPolicy().evaluate(command, request)
    assert decision.intervened and decision.requires_confirmation
    assert decision.request.requested_speed_mps == 0.0
    assert decision.output is not None
    assert decision.output.control.throttle == 0.0
    assert decision.output.risk.ttc_s == 0.5
    assert decision.output.risk.emergency_brake_requested
    assert decision.output.control.brake > 0.0

    declined = fsm.confirm(command.command_id, approved=False, now_s=10.1)
    assert declined.feedback is not None
    assert declined.feedback.status.value == "REJECTED"


def test_watchdog_failure_bypasses_normal_command_control_with_full_brake() -> None:
    watchdog = RuntimeWatchdog(timeout_s=0.5, required_modules=("command_runtime",),
                               started_at_s=0.0)
    emergency = watchdog.check(now_s=0.5)
    assert emergency == ControlOutput(0.0, 1.0, 0.0)
