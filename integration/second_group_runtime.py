"""Live adapter from frozen A/B/C interfaces to the existing D runtime.

The class deliberately owns no CARLA objects.  It lets ``carla_runner`` keep
one 20--50 Hz control loop while Qwen inference runs only in A's background
worker.  Every slow request first installs a deterministic STOP hold; only a
validated, current high-level result may replace that hold.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import time
from typing import Any
from uuid import uuid4

from runtime.interface_registry import InterfaceRegistry
from runtime.orchestrator import OrchestrationResult, PipelineOrchestrator

from .canonical_bridge import (
    control_command_to_voice_envelope,
    perception_frame_to_state,
    voice_envelope_to_driving_command,
)
from .contracts import PerceptionFrame


_TERMINAL_STATUSES = frozenset({
    "SUCCEEDED", "FAILED", "REJECTED", "EXPIRED", "TIMED_OUT", "SAFETY_OVERRIDE",
})


@dataclass(frozen=True, slots=True)
class CanonicalSubmission:
    canonical_command: Mapping[str, Any]
    perception_state: Mapping[str, Any]
    orchestration: OrchestrationResult
    runtime_adapted: Any | None
    safety_envelope: Mapping[str, Any] | None
    safety_adapted: Any | None
    feedbacks: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class CanonicalResolution:
    command_id: str
    disposition: str
    runtime_envelope: Mapping[str, Any] | None
    runtime_adapted: Any | None
    feedbacks: tuple[Mapping[str, Any], ...]
    vehicle_feedback: Any | None = None


@dataclass(frozen=True, slots=True)
class _PendingSlow:
    command_id: str
    source_text: str
    wait_command_id: str


class CanonicalRuntimeBridge:
    """Coordinate canonical routing without granting Qwen direct control."""

    def __init__(
        self,
        vehicle_runtime: Any,
        orchestrator: PipelineOrchestrator,
        *,
        registry: InterfaceRegistry | None = None,
        clock_ns: Any = time.monotonic_ns,
    ) -> None:
        self.vehicle_runtime = vehicle_runtime
        self.orchestrator = orchestrator
        self.registry = registry or InterfaceRegistry()
        self._clock_ns = clock_ns
        self._pending: dict[str, _PendingSlow] = {}
        self._latest_command_id: str | None = None

    def submit(
        self,
        envelope: Mapping[str, Any],
        scene: PerceptionFrame,
        vehicle: Any,
        *,
        sim_time_s: float,
        perception_mode: str,
        received_at_ns: int | None = None,
        rgb_ref: str | None = None,
    ) -> CanonicalSubmission:
        received = self._clock_ns() if received_at_ns is None else received_at_ns
        state = self._publish_state(scene, vehicle, perception_mode, received)
        canonical = voice_envelope_to_driving_command(
            envelope,
            received_at_ns=received,
            registry=self.registry,
        )
        self._latest_command_id = canonical["command_id"]

        if str(envelope.get("status", "valid")).lower() != "valid":
            result = self._rejection(
                canonical["command_id"], received, "VOICE_INPUT_INVALID",
                "voice envelope status is not valid",
            )
        else:
            result = self.orchestrator.submit_command(
                canonical, state, now_ns=received, rgb_ref=rgb_ref,
            )

        feedbacks = () if result.feedback is None else (result.feedback,)
        if result.disposition == "FAST" and result.control_command is not None:
            runtime_envelope = self._runtime_envelope(result.control_command, envelope)
            adapted = self.vehicle_runtime.submit_voice(runtime_envelope, now_s=sim_time_s)
            if not adapted.control_authorized:
                local = self._feedback(
                    canonical["command_id"], received, "REJECTED",
                    "D runtime rejected canonical fast command", "D_RUNTIME_REJECTED",
                )
                feedbacks = feedbacks + (local,)
            return CanonicalSubmission(
                canonical, state, result, adapted, None, None, feedbacks,
            )

        wait_envelope = self._wait_stop_envelope(canonical)
        wait_adapted = self.vehicle_runtime.submit_voice(wait_envelope, now_s=sim_time_s)
        if result.disposition == "SLOW_PENDING":
            self._pending[canonical["command_id"]] = _PendingSlow(
                canonical["command_id"], canonical["source_text"],
                str(wait_envelope["command_id"]),
            )
        return CanonicalSubmission(
            canonical, state, result, None, wait_envelope, wait_adapted, feedbacks,
        )

    def poll(
        self,
        scene: PerceptionFrame,
        vehicle: Any,
        *,
        sim_time_s: float,
        perception_mode: str,
        captured_at_ns: int | None = None,
    ) -> tuple[CanonicalResolution, ...]:
        captured = self._clock_ns() if captured_at_ns is None else captured_at_ns
        current_state = self._publish_state(scene, vehicle, perception_mode, captured)
        resolutions: list[CanonicalResolution] = []
        for result in self.orchestrator.poll_slow(now_ns=captured):
            pending = self._pending.pop(result.command_id, None)
            if result.disposition != "SLOW_READY" or result.control_command is None:
                vehicle_feedback = self._fail_wait_if_current(
                    pending, result.command_id, sim_time_s, result.reason_code,
                )
                feedbacks = () if result.feedback is None else (result.feedback,)
                resolutions.append(CanonicalResolution(
                    result.command_id, result.disposition, None, None,
                    feedbacks, vehicle_feedback,
                ))
                continue

            if result.command_id != self._latest_command_id:
                feedback = self._feedback(
                    result.command_id, captured, "REJECTED",
                    "slow result was superseded by a newer driving command",
                    "SUPERSEDED_BY_NEWER_COMMAND",
                )
                resolutions.append(CanonicalResolution(
                    result.command_id, "REJECTED", None, None, (feedback,), None,
                ))
                continue

            target_id = result.control_command["target"].get("target_id")
            current_targets = {item["track_id"] for item in current_state["objects"]}
            if target_id is not None and target_id not in current_targets:
                feedback = self._feedback(
                    result.command_id, captured, "REJECTED",
                    "Qwen target is absent from the latest perception frame",
                    "QWEN_TARGET_STALE",
                )
                vehicle_feedback = self._fail_wait_if_current(
                    pending, result.command_id, sim_time_s, "QWEN_TARGET_STALE",
                )
                resolutions.append(CanonicalResolution(
                    result.command_id, "REJECTED", None, None, (feedback,), vehicle_feedback,
                ))
                continue

            source_text = pending.source_text if pending is not None else "<Qwen decision>"
            try:
                runtime_envelope = control_command_to_voice_envelope(
                    result.control_command,
                    source_text=source_text,
                )
            except (KeyError, TypeError, ValueError) as error:
                feedback = self._feedback(
                    result.command_id, captured, "REJECTED",
                    f"D runtime cannot execute Qwen behavior: {error}",
                    "QWEN_BEHAVIOR_UNSUPPORTED",
                )
                vehicle_feedback = self._fail_wait_if_current(
                    pending, result.command_id, sim_time_s, "QWEN_BEHAVIOR_UNSUPPORTED",
                )
                resolutions.append(CanonicalResolution(
                    result.command_id, "REJECTED", None, None, (feedback,), vehicle_feedback,
                ))
                continue

            adapted = self.vehicle_runtime.submit_voice(runtime_envelope, now_s=sim_time_s)
            if not adapted.control_authorized:
                feedback = self._feedback(
                    result.command_id, captured, "REJECTED",
                    "D runtime rejected validated Qwen behavior",
                    "D_RUNTIME_REJECTED",
                )
                vehicle_feedback = self._fail_wait_if_current(
                    pending, result.command_id, sim_time_s, "D_RUNTIME_REJECTED",
                )
                resolutions.append(CanonicalResolution(
                    result.command_id, "REJECTED", runtime_envelope, adapted,
                    (feedback,), vehicle_feedback,
                ))
                continue
            feedbacks = () if result.feedback is None else (result.feedback,)
            resolutions.append(CanonicalResolution(
                result.command_id, result.disposition, runtime_envelope, adapted,
                feedbacks, None,
            ))
        return tuple(resolutions)

    def fail_all_pending(
        self,
        *,
        sim_time_s: float,
        emitted_at_ns: int | None = None,
        reason_code: str = "RUNTIME_ENDED",
    ) -> tuple[CanonicalResolution, ...]:
        """Give every still-pending canonical command one explicit terminal."""
        emitted = self._clock_ns() if emitted_at_ns is None else emitted_at_ns
        resolutions: list[CanonicalResolution] = []
        for command_id, pending in tuple(self._pending.items()):
            del self._pending[command_id]
            feedback = self._feedback(
                command_id, emitted, "FAILED",
                "CARLA runtime ended before the Qwen request resolved",
                reason_code,
            )
            vehicle_feedback = self._fail_wait_if_current(
                pending, command_id, sim_time_s, reason_code,
            )
            resolutions.append(CanonicalResolution(
                command_id, "REJECTED", None, None,
                (feedback,), vehicle_feedback,
            ))
        return tuple(resolutions)

    def _publish_state(
        self,
        scene: PerceptionFrame,
        vehicle: Any,
        perception_mode: str,
        captured_at_ns: int,
    ) -> Mapping[str, Any]:
        state = perception_frame_to_state(
            scene,
            vehicle,
            captured_at_ns=captured_at_ns,
            perception_mode=perception_mode,
            registry=self.registry,
        )
        self.orchestrator.publish_perception(state)
        latest = self.orchestrator.latest_perception()
        if latest is None:
            raise RuntimeError("canonical perception queue lost the published state")
        return latest

    def _runtime_envelope(
        self,
        control: Mapping[str, Any],
        original: Mapping[str, Any],
    ) -> dict[str, Any]:
        envelope = control_command_to_voice_envelope(
            control,
            source_text=str(original.get("source_text", "<unavailable>")),
        )
        for name in ("t_audio_start_ns", "t_asr_end_ns", "t_intent_end_ns"):
            envelope[name] = original.get(name)
        return envelope

    @staticmethod
    def _wait_stop_envelope(command: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "command_id": f"qwen-wait-{uuid4().hex}",
            "source_text": f"Qwen 安全等待: {command['source_text']}",
            "intent": "STOP",
            "parameters": {},
            "confidence": 1.0,
            "intent_confidence": 1.0,
            "status": "valid",
            "ambiguity_type": "NONE",
            "confirm_required": False,
            "errors": [],
            "warnings": [{
                "code": "QWEN_PENDING_FAIL_CLOSED",
                "message": f"waiting for canonical command {command['command_id']}",
            }],
            "valid_duration_s": 3.0,
            "t_audio_start_ns": None,
            "t_asr_end_ns": None,
            "t_intent_end_ns": None,
        }

    def _fail_wait_if_current(
        self,
        pending: _PendingSlow | None,
        command_id: str,
        sim_time_s: float,
        reason_code: str,
    ) -> Any | None:
        if pending is None:
            return None
        if self._latest_command_id != command_id:
            return None
        if self.vehicle_runtime.active_command_id != pending.wait_command_id:
            return None
        return self.vehicle_runtime.fail_active(
            now_s=sim_time_s,
            detail=f"Qwen slow path failed closed: {reason_code}",
        )

    def _rejection(
        self,
        command_id: str,
        now_ns: int,
        reason_code: str,
        detail: str,
    ) -> OrchestrationResult:
        feedback = self._feedback(
            command_id, now_ns, "REJECTED", detail, reason_code,
        )
        return OrchestrationResult(
            "REJECTED", command_id, feedback=feedback,
            reason_code=reason_code, queues=self.orchestrator.queue_snapshot(),
        )

    def _feedback(
        self,
        command_id: str,
        now_ns: int,
        status: str,
        detail: str,
        reason_code: str,
    ) -> Mapping[str, Any]:
        if status not in _TERMINAL_STATUSES:
            terminal_reason = None
        else:
            terminal_reason = reason_code
        return self.registry.validate("execution_feedback", {
            "schema_version": "1.0",
            "command_id": command_id,
            "status": status,
            "action_summary": detail,
            "emitted_at_ns": now_ns,
            "t_action_apply_ns": None,
            "latency_ms": None,
            "safety_event": None,
            "terminal_reason": terminal_reason,
        })


__all__ = [
    "CanonicalResolution",
    "CanonicalRuntimeBridge",
    "CanonicalSubmission",
]
