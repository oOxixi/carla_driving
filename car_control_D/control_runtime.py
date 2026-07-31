"""D's unique final-control exit for canonical V1 pipeline objects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import statistics
import time
from typing import Any, Callable

from runtime.interface_registry import InterfaceRegistry, InterfaceValidationError
from .execution_feedback import ExecutionFeedbackTracker
from .safety_supervisor import SafetySupervisor
from .schemas import ControlOutput, SafetyDecision


@dataclass(frozen=True, slots=True)
class FinalControlFrame:
    command_id: str
    final_control: ControlOutput
    safety: SafetyDecision
    arbitration_ms: float
    feedback: Mapping[str, Any]


class DControlRuntime:
    """Validate high-level authority and expose the only final control value."""

    def __init__(
        self,
        *,
        supervisor: SafetySupervisor | None = None,
        registry: InterfaceRegistry | None = None,
        lifecycle: ExecutionFeedbackTracker | None = None,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.supervisor = supervisor or SafetySupervisor()
        self.registry = registry or InterfaceRegistry()
        self.lifecycle = lifecycle or ExecutionFeedbackTracker(registry=self.registry, clock_ns=clock_ns)
        self._clock_ns = clock_ns
        self._latencies_ms: list[float] = []
        self._last_apply_ns: int | None = None
        self._cadence_hz: list[float] = []

    def apply(
        self,
        control_command: Mapping[str, Any],
        perception_state: Mapping[str, Any],
        vehicle_state: Mapping[str, Any],
        planned_control: Any,
        *,
        now_ns: int | None = None,
    ) -> FinalControlFrame:
        now = self._clock_ns() if now_ns is None else now_ns
        if type(now) is not int or now < 0:
            raise ValueError("now_ns must be non-negative")
        command_id = str(control_command.get("command_id", "invalid-command")) if isinstance(control_command, Mapping) else "invalid-command"
        if command_id not in self.lifecycle.unfinished_command_ids:
            self.lifecycle.received(command_id, "validated command received by D", emitted_at_ns=now)
        watchdog: list[str] = []
        try:
            command = self.registry.validate("control_command", control_command)
            perception = self.registry.validate("perception_state", perception_state)
        except InterfaceValidationError:
            command = None
            perception = None
            watchdog.append("D_INTERFACE_INVALID")
        if command is not None and now >= command["deadline_ns"]:
            watchdog.append("D_COMMAND_EXPIRED")
        if perception is not None and (
            perception["stale"] or not perception["sync"]["within_tolerance"]
            or not perception["modality_valid"]["vehicle_state"]
        ):
            watchdog.append("D_PERCEPTION_INVALID")
        started = time.perf_counter_ns()
        command_view = None if command is None else self._command_view(command)
        vehicle_view = dict(vehicle_state)
        if perception is not None:
            vehicle_view.update({
                "front_distance_m": perception["min_gap_m"],
                "distance_to_stop_line_m": perception["distance_to_stop_line_m"],
                "traffic_light": perception["traffic_light"],
            })
        risk = {} if perception is None else {
            "ttc_s": perception["ttc_s"],
            "emergency_brake_requested": perception["risk_level"] == "EMERGENCY",
        }
        decision = self.supervisor.arbitrate(
            planned_control,
            vehicle_view,
            command_view,
            risk,
            watchdog,
        )
        elapsed_ms = (time.perf_counter_ns() - started) / 1e6
        self._latencies_ms.append(elapsed_ms)
        if self._last_apply_ns is not None and now > self._last_apply_ns:
            self._cadence_hz.append(1e9 / (now - self._last_apply_ns))
        self._last_apply_ns = now
        final_payload = decision.final_control.to_dict()
        raw_payload = decision.raw_control.to_dict() if decision.raw_control is not None else {
            "throttle": 0.0, "brake": 0.0, "steer": 0.0,
        }
        if decision.safety_override:
            feedback = self.lifecycle.safety_override(
                command_id,
                reason_code=decision.reason,
                raw_control=raw_payload,
                final_control=final_payload,
                emitted_at_ns=now,
            )
        else:
            feedback = self.lifecycle.executing(
                command_id,
                "D final control applied",
                t_action_apply_ns=now,
            )
        return FinalControlFrame(command_id, decision.final_control, decision, elapsed_ms, feedback)

    def complete(self, command_id: str, *, succeeded: bool, reason: str, now_ns: int | None = None) -> Mapping[str, Any]:
        return self.lifecycle.finish(
            command_id,
            "SUCCEEDED" if succeeded else "FAILED",
            "behavior completed" if succeeded else "behavior failed",
            reason,
            emitted_at_ns=now_ns,
        )

    def metrics(self) -> dict[str, Any]:
        values = sorted(self._latencies_ms)
        p95 = None if not values else values[min(len(values) - 1, max(0, int(0.95 * len(values) - 1)))]
        p99 = None if not values else values[min(len(values) - 1, max(0, int(0.99 * len(values) - 1)))]
        return {
            "frames": len(values),
            "arbitration_ms": {
                "mean": statistics.fmean(values) if values else None,
                "p95": p95,
                "p99": p99,
                "max": max(values) if values else None,
            },
            "cadence_hz": {
                "mean": statistics.fmean(self._cadence_hz) if self._cadence_hz else None,
                "min": min(self._cadence_hz) if self._cadence_hz else None,
                "max": max(self._cadence_hz) if self._cadence_hz else None,
                "within_20_50_hz_rate": (
                    sum(20.0 <= value <= 50.0 for value in self._cadence_hz) / len(self._cadence_hz)
                    if self._cadence_hz else None
                ),
            },
            "unfinished_command_ids": list(self.lifecycle.unfinished_command_ids),
        }

    @staticmethod
    def _command_view(command: Mapping[str, Any]) -> dict[str, Any]:
        behavior = str(command["behavior"])
        intent = {
            "EMERGENCY_STOP": "EMERGENCY_STOP",
            "STOP": "STOP",
            "SET_SPEED": "SET_SPEED",
            "SLOW_DOWN": "SLOW_DOWN",
            "KEEP_LANE": "KEEP_LANE",
        }.get(behavior, "FORWARD")
        parameters = {}
        if command["target"].get("target_speed_mps") is not None:
            parameters["speed"] = command["target"]["target_speed_mps"]
        return {
            "schema_version": "1.0",
            "command_id": command["command_id"],
            "source_text": command["reason_code"],
            "intent": intent,
            "parameters": parameters,
            "confidence": command.get("confidence", 1.0),
            "intent_confidence": command.get("confidence", 1.0),
            "status": "valid",
            "ambiguity_type": "NONE",
            "confirm_required": False,
        }


__all__ = ["DControlRuntime", "FinalControlFrame"]
