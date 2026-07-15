"""Deterministic safe fallback for ambiguous or untrusted voice commands.

This is C's local longitudinal constraint.  It never claims to replace D's
final safety supervisor, and it never forwards an unsafe command speed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from car_control_A import (
    ControlOutput,
    DrivingCommand,
    ExecutionFeedback,
    ExecutionStatus,
    LongitudinalOutput,
    LongitudinalRequest,
    RiskMetrics,
)

from .config import FuzzyCommandPolicyConfig
from .following_controller import FollowingController


@dataclass(frozen=True, slots=True)
class FuzzyCommandDecision:
    """Result passed to C's controller or A's command/FSM layer.

    A clear command has ``intervened=False`` and preserves the caller's request.
    A policy intervention always replaces its requested speed with zero.
    """

    request: LongitudinalRequest
    intervened: bool
    requires_confirmation: bool
    output: LongitudinalOutput | None
    feedback: ExecutionFeedback | None


class FuzzyCommandPolicy:
    """Reject expiry and stop safely before requesting a voice confirmation."""

    def __init__(self, config: FuzzyCommandPolicyConfig | None = None) -> None:
        self.config = config or FuzzyCommandPolicyConfig()
        self._following = FollowingController()

    def evaluate(self, command: DrivingCommand, request: LongitudinalRequest) -> FuzzyCommandDecision:
        if not isinstance(command, DrivingCommand):
            raise TypeError("command must be DrivingCommand")
        if not isinstance(request, LongitudinalRequest):
            raise TypeError("request must be LongitudinalRequest")
        now = request.vehicle.sim_time_s
        # Do not discard a frame-aligned lead observation merely because the
        # voice command is untrusted.  D still owns final arbitration, but C's
        # local fallback must surface its TTC request.
        risk = self._following.risk(
            ego_speed_mps=request.vehicle.speed_mps,
            lead_distance_m=request.lead_distance_m,
            closing_speed_mps=request.closing_speed_mps,
        )
        safe_request = replace(request, requested_speed_mps=0.0)
        if command.is_expired_at(now):
            output = self._safe_output(request, "REJECTED", "command_expired", risk)
            feedback = ExecutionFeedback(command.command_id, ExecutionStatus.EXPIRED, now,
                                         "command expired before longitudinal execution")
            return FuzzyCommandDecision(safe_request, True, False, output, feedback)
        needs_confirmation = (command.confidence < self.config.confidence_threshold or
                              command.is_ambiguous or command.confirmation_requested)
        if not needs_confirmation:
            return FuzzyCommandDecision(request, False, False, None, None)
        state = "EMERGENCY_BRAKE" if risk.emergency_brake_requested else "CONFIRMING"
        reason = "confirmation_required_low_ttc" if risk.emergency_brake_requested else "confirmation_required"
        output = self._safe_output(request, state, reason, risk)
        return FuzzyCommandDecision(safe_request, True, True, output, None)

    def _safe_output(self, request: LongitudinalRequest, state: str, reason: str,
                     risk: RiskMetrics) -> LongitudinalOutput:
        stopped = request.vehicle.speed_mps <= self.config.standstill_speed_mps
        brake = self.config.hold_brake if stopped else min(
            1.0, self.config.comfort_decel_mps2 / self.config.max_decel_mps2)
        if risk.emergency_brake_requested:
            brake = max(brake, self.config.emergency_brake)
        return LongitudinalOutput(
            ControlOutput(0.0, brake),
            -self.config.comfort_decel_mps2,
            0.0,
            "HOLD" if stopped and state not in {"REJECTED", "EMERGENCY_BRAKE"} else state,
            reason,
            risk,
        )
