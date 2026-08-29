"""D-owned command lifecycle with schema-validated terminal feedback."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import time
from typing import Any, Callable

from runtime.interface_registry import InterfaceRegistry


TERMINAL = frozenset({
    "SUCCEEDED", "FAILED", "REJECTED", "EXPIRED", "TIMED_OUT", "SAFETY_OVERRIDE",
})


@dataclass(slots=True)
class _Lifecycle:
    status: str
    received_at_ns: int
    t_action_apply_ns: int | None = None
    terminal_feedback: dict[str, Any] | None = None


class ExecutionFeedbackTracker:
    """Guarantee deterministic transitions and at most one terminal per ID."""

    def __init__(
        self,
        *,
        registry: InterfaceRegistry | None = None,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.registry = registry or InterfaceRegistry()
        self._clock_ns = clock_ns
        self._commands: dict[str, _Lifecycle] = {}
        self._events: list[dict[str, Any]] = []

    def received(self, command_id: str, action_summary: str, *, emitted_at_ns: int | None = None) -> dict[str, Any]:
        now = self._now(emitted_at_ns)
        self._identity(command_id)
        existing = self._commands.get(command_id)
        if existing is not None:
            if existing.terminal_feedback is not None:
                return dict(existing.terminal_feedback)
            return self._emit(command_id, existing.status, action_summary, now, existing.t_action_apply_ns, None, None)
        self._commands[command_id] = _Lifecycle("RECEIVED", now)
        feedback = self._emit(command_id, "RECEIVED", action_summary, now, None, None, None)
        self._events.append(feedback)
        return feedback

    def executing(self, command_id: str, action_summary: str, *, t_action_apply_ns: int | None = None) -> dict[str, Any]:
        now = self._now(t_action_apply_ns)
        lifecycle = self._require_active(command_id)
        if lifecycle.terminal_feedback is not None:
            return dict(lifecycle.terminal_feedback)
        if now < lifecycle.received_at_ns:
            raise ValueError("action timestamp precedes command receipt")
        lifecycle.status = "EXECUTING"
        lifecycle.t_action_apply_ns = now
        feedback = self._emit(
            command_id, "EXECUTING", action_summary, now, now,
            (now - lifecycle.received_at_ns) / 1e6, None,
        )
        self._events.append(feedback)
        return feedback

    def finish(
        self,
        command_id: str,
        status: str,
        action_summary: str,
        terminal_reason: str,
        *,
        emitted_at_ns: int | None = None,
    ) -> dict[str, Any]:
        if status not in TERMINAL - {"SAFETY_OVERRIDE"}:
            raise ValueError("finish status must be a non-safety terminal status")
        now = self._now(emitted_at_ns)
        lifecycle = self._require_active(command_id)
        if lifecycle.terminal_feedback is not None:
            return dict(lifecycle.terminal_feedback)
        feedback = self._emit(
            command_id, status, action_summary, now, lifecycle.t_action_apply_ns,
            None if lifecycle.t_action_apply_ns is None else (lifecycle.t_action_apply_ns - lifecycle.received_at_ns) / 1e6,
            terminal_reason,
        )
        lifecycle.status = status
        lifecycle.terminal_feedback = feedback
        self._events.append(feedback)
        return feedback

    def safety_override(
        self,
        command_id: str,
        *,
        reason_code: str,
        raw_control: Mapping[str, Any],
        final_control: Mapping[str, Any],
        action_summary: str = "D safety override applied",
        emitted_at_ns: int | None = None,
    ) -> dict[str, Any]:
        now = self._now(emitted_at_ns)
        lifecycle = self._require_active(command_id)
        if lifecycle.terminal_feedback is not None:
            return dict(lifecycle.terminal_feedback)
        safety_event = {
            "reason_code": reason_code,
            # Raw evidence may deliberately contain the invalid overlap which
            # triggered D. Only the final output is required to be conflict-free.
            "raw_control": self._control(raw_control, allow_overlap=True),
            "final_control": self._control(final_control, allow_overlap=False),
        }
        feedback = self.registry.validate("execution_feedback", {
            "schema_version": "1.0",
            "command_id": command_id,
            "status": "SAFETY_OVERRIDE",
            "action_summary": action_summary,
            "emitted_at_ns": now,
            "t_action_apply_ns": lifecycle.t_action_apply_ns,
            "latency_ms": None if lifecycle.t_action_apply_ns is None else (lifecycle.t_action_apply_ns - lifecycle.received_at_ns) / 1e6,
            "safety_event": safety_event,
            "terminal_reason": reason_code,
        })
        lifecycle.status = "SAFETY_OVERRIDE"
        lifecycle.terminal_feedback = feedback
        self._events.append(feedback)
        return feedback

    def fail_unfinished(self, *, reason: str, emitted_at_ns: int | None = None) -> tuple[dict[str, Any], ...]:
        now = self._now(emitted_at_ns)
        results = []
        for command_id, lifecycle in tuple(self._commands.items()):
            if lifecycle.terminal_feedback is None:
                results.append(self.finish(command_id, "FAILED", "runtime shutdown", reason, emitted_at_ns=now))
        return tuple(results)

    @property
    def events(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(dict(item) for item in self._events)

    @property
    def unfinished_command_ids(self) -> tuple[str, ...]:
        return tuple(sorted(
            command_id for command_id, lifecycle in self._commands.items()
            if lifecycle.terminal_feedback is None
        ))

    def _emit(
        self,
        command_id: str,
        status: str,
        summary: str,
        now: int,
        applied: int | None,
        latency: float | None,
        terminal_reason: str | None,
    ) -> dict[str, Any]:
        return self.registry.validate("execution_feedback", {
            "schema_version": "1.0",
            "command_id": command_id,
            "status": status,
            "action_summary": summary,
            "emitted_at_ns": now,
            "t_action_apply_ns": applied,
            "latency_ms": latency,
            "safety_event": None,
            "terminal_reason": terminal_reason,
        })

    def _require_active(self, command_id: str) -> _Lifecycle:
        self._identity(command_id)
        try:
            return self._commands[command_id]
        except KeyError as error:
            raise KeyError(f"command has not been received: {command_id}") from error

    @staticmethod
    def _identity(command_id: str) -> None:
        if type(command_id) is not str or not command_id:
            raise ValueError("command_id must be non-empty")

    @staticmethod
    def _control(control: Mapping[str, Any], *, allow_overlap: bool) -> dict[str, float]:
        values = {name: float(control[name]) for name in ("throttle", "brake", "steer")}
        if not allow_overlap and values["throttle"] > 0.0 and values["brake"] > 0.0:
            raise ValueError("feedback control cannot contain throttle/brake overlap")
        return values

    def _now(self, value: int | None) -> int:
        result = self._clock_ns() if value is None else value
        if type(result) is not int or result < 0:
            raise ValueError("timestamp must be a non-negative integer")
        return result


__all__ = ["ExecutionFeedbackTracker", "TERMINAL"]
