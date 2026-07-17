"""The single pure-Python composition point for A/B/C/D.

``ControlRuntime.step`` is CARLA-independent. A CARLA runner calls it once
after its sole ``session.tick()`` and applies only the returned final control.
"""
from __future__ import annotations

from collections.abc import Mapping

from car_control_A import ControlOutput, ExecutionStatus, RuntimeVehicleState
from car_control_A.behavior_fsm import BehaviorFSM
from car_control_A.routing import RouteReference
from car_control_B.lateral_controller_base import LateralController
from car_control_C import LongitudinalController
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
        self.requested_speed_mps = float(default_speed_mps)
        self._active_voice: dict[str, object] | None = None
        self._active_command_id: str | None = None

    def submit_voice(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand:
        """Accept a voice result at the CARLA-time boundary and retain JSON for D."""
        adapted = self.voice_adapter.adapt(envelope, now_s=now_s)
        self._active_voice = dict(envelope)
        self.fsm.submit(adapted.command, now_s=now_s)
        self._active_command_id = adapted.command.command_id
        if adapted.command.action == "SET_SPEED" and adapted.command.target_speed_mps is not None and not adapted.command.requires_confirmation:
            self.requested_speed_mps = adapted.command.target_speed_mps
        return adapted

    def step(self, vehicle: RuntimeVehicleState, scene: PerceptionFrame, route: RouteReference, *, dt_s: float,
             watchdog_alerts: tuple[str, ...] = ()) -> FrameResult:
        """Compose lateral, longitudinal and final safety arbitration for one aligned frame."""
        feedback = self.fsm.tick(now_s=vehicle.sim_time_s)
        expired_alerts = list(watchdog_alerts)
        for item in feedback:
            if item.command_id == self._active_command_id and item.status in {
                ExecutionStatus.EXPIRED, ExecutionStatus.TIMED_OUT, ExecutionStatus.REJECTED, ExecutionStatus.FAILED,
            }:
                # No stale voice command may retain propulsion authority after a
                # terminal failure/expiry. D receives the alert and becomes the
                # one final brake authority for this frame.
                self.requested_speed_mps = 0.0
                expired_alerts.append(f"COMMAND_{item.status.value}")
                self._active_command_id = None
        try:
            lateral = self.lateral.step_any(vehicle, route)
            request = longitudinal_request(vehicle, scene, requested_speed_mps=self.requested_speed_mps,
                                           path_curvature_per_m=route.curvature_per_m)
            longitudinal = self.longitudinal.step(request, dt_s)
            raw = ControlOutput(longitudinal.control.throttle, longitudinal.control.brake, lateral.steer)
            safety = self.safety.arbitrate(raw, safety_vehicle_state(vehicle, scene), self._active_voice,
                                           longitudinal.risk, tuple(expired_alerts))
            final = ControlOutput(safety.final_control.throttle, safety.final_control.brake, safety.final_control.steer)
            return FrameResult(vehicle, final, longitudinal, safety.reason, safety.safety_override, feedback)
        except Exception:
            return FrameResult(vehicle, ControlOutput(0.0, 1.0, 0.0), None, "INTEGRATION_FAILURE", True, feedback)
