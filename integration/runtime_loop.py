"""The single pure-Python composition point for A/B/C/D.

``ControlRuntime.step`` is CARLA-independent. A CARLA runner calls it once
after its sole ``session.tick()`` and applies only the returned final control.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from car_control_A import ControlOutput, DrivingCommand, ExecutionFeedback, ExecutionStatus, RuntimeVehicleState
from car_control_A.behavior_fsm import BehaviorFSM
from car_control_A.routing import RouteReference
from car_control_B.lateral_controller_base import LateralController
from car_control_C import FuzzyCommandPolicy, LongitudinalController
from car_control_D import SafetySupervisor

from .contracts import FrameResult, PerceptionFrame
from .perception_bridge import longitudinal_request, safety_vehicle_state
from .voice_adapter import AdaptedVoiceCommand, VoiceCommandAdapter


class ControlRuntime:
    """Owns command state and composes B/C/D in one deterministic frame order."""
    def __init__(self, lateral: LateralController, *, longitudinal: LongitudinalController | None = None,
                 safety: SafetySupervisor | None = None, voice_adapter: VoiceCommandAdapter | None = None,
                 default_speed_mps: float = 5.0, command_timeout_s: float = 15.0) -> None:
        if default_speed_mps < 0.0 or command_timeout_s <= 0.0:
            raise ValueError("default_speed_mps must be non-negative and command_timeout_s must be positive")
        self.lateral = lateral
        self.longitudinal = longitudinal or LongitudinalController()
        self.safety = safety or SafetySupervisor()
        self.voice_adapter = voice_adapter or VoiceCommandAdapter()
        self.fsm = BehaviorFSM(command_timeout_s=command_timeout_s)
        self.fuzzy_policy = FuzzyCommandPolicy()
        self.requested_speed_mps = float(default_speed_mps)
        self._active_voice: dict[str, object] | None = None
        self._active_command_id: str | None = None
        self._active_command: DrivingCommand | None = None
        self._pending_feedback: list[ExecutionFeedback] = []
        self._success_frames = 0
        self._stop_hold = False
        self._latched_alerts: list[str] = []

    def submit_voice(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand:
        """Accept a voice result at the CARLA-time boundary and retain JSON for D."""
        adapted = self.voice_adapter.adapt(envelope, now_s=now_s)
        if not adapted.control_authorized:
            if adapted.feedback is not None:
                self._pending_feedback.append(adapted.feedback)
            return adapted
        if self._active_command_id is not None and self._active_command_id != adapted.command.command_id:
            superseded = self.fsm.fail(self._active_command_id, now_s=now_s,
                                       detail="superseded by a newer command")
            if superseded is not None:
                self._pending_feedback.append(superseded)
            self._clear_active_command()
        submitted = self.fsm.submit(adapted.command, now_s=now_s)
        if submitted.feedback is not None:
            self._pending_feedback.append(submitted.feedback)
            return replace(adapted, control_authorized=False, feedback=submitted.feedback)
        self._active_voice = dict(envelope)
        self._active_command_id = adapted.command.command_id
        self._active_command = adapted.command
        self._success_frames = 0
        if adapted.command.action == "SET_SPEED" and adapted.command.target_speed_mps is not None and not adapted.command.requires_confirmation:
            self.requested_speed_mps = adapted.command.target_speed_mps
            self._stop_hold = False
        elif adapted.command.action in {"STOP", "EMERGENCY_BRAKE"}:
            self.requested_speed_mps = 0.0
        return adapted

    @property
    def safety_latched(self) -> bool:
        return bool(self._latched_alerts)

    @property
    def active_command_id(self) -> str | None:
        return self._active_command_id

    def confirm_voice(self, command_id: str, *, approved: bool, now_s: float) -> ExecutionFeedback | None:
        """Resolve a confirmation gate without importing or mutating voice code.

        Approval only unlocks commands this runtime can execute
        deterministically. A complex multimodal action still fails closed until
        a decision provider supplies a concrete manoeuvre.
        """
        if type(command_id) is not str or not command_id:
            raise ValueError("command_id must be a non-empty string")
        if type(approved) is not bool:
            raise TypeError("approved must be bool")
        result = self.fsm.confirm(command_id, approved=approved, now_s=now_s)
        if result.feedback is not None:
            self._pending_feedback.append(result.feedback)
            if command_id == self._active_command_id:
                self.requested_speed_mps = 0.0
                self._stop_hold = True
                self._clear_active_command()
            return result.feedback
        command = self._active_command
        if command is None or command.command_id != command_id:
            return None
        if command.action == "MULTIMODAL_DECISION":
            failed = self.fsm.fail(
                command_id,
                now_s=now_s,
                detail="confirmation received but no concrete multimodal decision is available",
            )
            if failed is not None:
                self._pending_feedback.append(failed)
            self.requested_speed_mps = 0.0
            self._stop_hold = True
            self._clear_active_command()
            return failed
        self._active_command = replace(
            command,
            confidence=1.0,
            is_ambiguous=False,
            confirmation_requested=False,
        )
        if self._active_voice is not None:
            self._active_voice["confidence"] = 1.0
            self._active_voice["intent_confidence"] = 1.0
            self._active_voice["confirm_required"] = False
            self._active_voice["ambiguity_type"] = "NONE"
        if command.action == "SET_SPEED" and command.target_speed_mps is not None:
            self.requested_speed_mps = command.target_speed_mps
            self._stop_hold = False
        elif command.action in {"STOP", "EMERGENCY_BRAKE"}:
            self.requested_speed_mps = 0.0
        return None

    def reset_safety_latch(self) -> None:
        """Explicitly release a persistent watchdog/integration stop after recovery."""
        self._latched_alerts.clear()

    def fail_active(self, *, now_s: float, detail: str) -> ExecutionFeedback | None:
        """Terminate the active command when its outer runtime cannot continue."""
        command_id = self._active_command_id
        if command_id is None:
            return None
        feedback = self.fsm.fail(command_id, now_s=now_s, detail=detail)
        self.requested_speed_mps = 0.0
        self._stop_hold = True
        self._clear_active_command()
        return feedback

    def step(self, vehicle: RuntimeVehicleState, scene: PerceptionFrame, route: RouteReference, *, dt_s: float,
             watchdog_alerts: tuple[str, ...] = ()) -> FrameResult:
        """Compose lateral, longitudinal and final safety arbitration for one aligned frame."""
        feedback = list(self._pending_feedback)
        self._pending_feedback.clear()
        lifecycle_feedback = self.fsm.tick(now_s=vehicle.sim_time_s)
        feedback.extend(lifecycle_feedback)
        if watchdog_alerts:
            for alert in watchdog_alerts:
                if alert not in self._latched_alerts:
                    self._latched_alerts.append(alert)
            self.requested_speed_mps = 0.0
            if self._active_command_id is not None:
                failed = self.fsm.fail(self._active_command_id, now_s=vehicle.sim_time_s,
                                       detail="watchdog alert: " + ", ".join(watchdog_alerts))
                if failed is not None:
                    feedback.append(failed)
                self._clear_active_command()
        expired_alerts = list(self._latched_alerts)
        # Adapter rejections are audit-only NO_OP results. Even if a faulty
        # upstream producer reuses the active command_id, they must never
        # terminate or replace the currently authorised command.
        for item in lifecycle_feedback:
            if item.command_id == self._active_command_id and item.status in {
                ExecutionStatus.EXPIRED, ExecutionStatus.TIMED_OUT, ExecutionStatus.REJECTED, ExecutionStatus.FAILED,
            }:
                # No stale voice command may retain propulsion authority after a
                # terminal failure/expiry. D receives the alert and becomes the
                # one final brake authority for this frame.
                self.requested_speed_mps = 0.0
                expired_alerts.append(f"COMMAND_{item.status.value}")
                self._clear_active_command()
        try:
            lateral = self.lateral.step_any(vehicle, route)
            request = longitudinal_request(vehicle, scene, requested_speed_mps=self.requested_speed_mps,
                                           path_curvature_per_m=route.curvature_per_m)
            if self._active_command is not None and self._active_command.requires_confirmation:
                fuzzy = self.fuzzy_policy.evaluate(self._active_command, request)
                longitudinal = fuzzy.output if fuzzy.intervened else self.longitudinal.step(fuzzy.request, dt_s)
                if fuzzy.feedback is not None:
                    feedback.append(fuzzy.feedback)
            else:
                longitudinal = self.longitudinal.step(request, dt_s)
            if longitudinal is None:
                raise RuntimeError("fuzzy policy intervened without a longitudinal output")
            should_hold = self._stop_hold or (
                self._active_command is not None and
                self._active_command.action in {"STOP", "EMERGENCY_BRAKE"} and
                vehicle.speed_mps <= self.fuzzy_policy.config.standstill_speed_mps
            )
            if should_hold:
                hold_brake = self.longitudinal.parameters.hold_brake
                longitudinal = replace(
                    longitudinal,
                    control=ControlOutput(0.0, max(hold_brake, longitudinal.control.brake)),
                    target_accel_mps2=min(0.0, longitudinal.target_accel_mps2),
                    target_speed_mps=0.0,
                    state="HOLD",
                    reason="command_stop_hold",
                )
            raw = ControlOutput(longitudinal.control.throttle, longitudinal.control.brake, lateral.steer)
            safety_command = self._active_voice
            if self._active_command is not None and (
                self._active_command.action == "STOP" or self._active_command.requires_confirmation
            ):
                # C owns comfortable STOP/confirmation deceleration. D still
                # receives vehicle/risk/watchdog facts and remains final arbiter.
                safety_command = None
            safety = self.safety.arbitrate(raw, safety_vehicle_state(vehicle, scene), safety_command,
                                           longitudinal.risk, tuple(expired_alerts))
            final = ControlOutput(safety.final_control.throttle, safety.final_control.brake, safety.final_control.steer)
            completed = self._completion_feedback(vehicle)
            if completed is not None:
                feedback.append(completed)
            return FrameResult(vehicle, final, longitudinal, safety.reason, safety.safety_override,
                               tuple(feedback), raw, lateral)
        except Exception:
            if "INTEGRATION_FAILURE" not in self._latched_alerts:
                self._latched_alerts.append("INTEGRATION_FAILURE")
            self.requested_speed_mps = 0.0
            if self._active_command_id is not None:
                failed = self.fsm.fail(self._active_command_id, now_s=vehicle.sim_time_s,
                                       detail="integration failure")
                if failed is not None:
                    feedback.append(failed)
                self._clear_active_command()
            fail_control = ControlOutput(0.0, 1.0, 0.0)
            return FrameResult(vehicle, fail_control, None, "INTEGRATION_FAILURE", True,
                               tuple(feedback), fail_control)

    def _completion_feedback(self, vehicle: RuntimeVehicleState) -> ExecutionFeedback | None:
        command = self._active_command
        if command is None:
            return None
        succeeded = False
        detail = ""
        if command.action == "SET_SPEED" and command.target_speed_mps is not None:
            if abs(vehicle.speed_mps - command.target_speed_mps) <= 0.25:
                self._success_frames += 1
            else:
                self._success_frames = 0
            succeeded = self._success_frames >= 3
            detail = "target speed reached and settled"
        elif command.action in {"STOP", "EMERGENCY_BRAKE"}:
            succeeded = vehicle.speed_mps <= self.fuzzy_policy.config.standstill_speed_mps
            detail = "vehicle stopped"
        if not succeeded:
            return None
        result = self.fsm.complete(command.command_id, now_s=vehicle.sim_time_s, detail=detail)
        if command.action in {"STOP", "EMERGENCY_BRAKE"}:
            self._stop_hold = True
        self._clear_active_command()
        return result

    def _clear_active_command(self) -> None:
        self._active_command_id = None
        self._active_command = None
        self._active_voice = None
        self._success_frames = 0
