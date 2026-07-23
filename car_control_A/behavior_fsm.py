"""Auditable command lifecycle and high-level behaviour state machine."""

from __future__ import annotations

from dataclasses import dataclass

from compat import StrEnum
from .contracts import DrivingCommand, ExecutionFeedback, ExecutionStatus


class BehaviorState(StrEnum):
    IDLE = "IDLE"
    LANE_FOLLOW = "LANE_FOLLOW"
    APPROACH_STOP = "APPROACH_STOP"
    STOPPED = "STOPPED"
    FOLLOWING = "FOLLOWING"
    YIELDING = "YIELDING"
    CONFIRMING = "CONFIRMING"
    EMERGENCY_BRAKE = "EMERGENCY_BRAKE"
    RECOVERING = "RECOVERING"


@dataclass(frozen=True, slots=True)
class BehaviorResult:
    state: BehaviorState
    feedback: ExecutionFeedback | None = None


@dataclass(slots=True)
class _ActiveCommand:
    command: DrivingCommand
    started_at_s: float


class BehaviorFSM:
    def __init__(self, *, command_timeout_s: float = 15.0) -> None:
        if command_timeout_s <= 0.0:
            raise ValueError("command_timeout_s must be positive")
        self._timeout_s = float(command_timeout_s)
        self._state = BehaviorState.IDLE
        self._active: dict[str, _ActiveCommand] = {}
        self._terminal: dict[str, ExecutionFeedback] = {}

    @property
    def state(self) -> BehaviorState:
        return self._state

    def submit(self, command: DrivingCommand, *, now_s: float) -> BehaviorResult:
        previous = self._terminal.get(command.command_id)
        if previous is not None:
            return BehaviorResult(self._state, previous)
        if command.command_id in self._active:
            return BehaviorResult(self._state)
        if command.is_expired_at(now_s):
            return self._finish(command.command_id, ExecutionStatus.EXPIRED, now_s, "command expired", command)
        # There is deliberately one global behaviour state and therefore one
        # owner command.  Superseding it first prevents a stale completion or
        # timeout from changing the new command's state later.
        for active_id in tuple(self._active):
            self._finish(active_id, ExecutionStatus.FAILED, now_s, "superseded by a newer command")
        self._active[command.command_id] = _ActiveCommand(command, now_s)
        if command.requires_confirmation:
            self._state = BehaviorState.CONFIRMING
        else:
            self._state = self._state_for(command.action)
        return BehaviorResult(self._state)

    def confirm(self, command_id: str, *, approved: bool, now_s: float) -> BehaviorResult:
        active = self._active.get(command_id)
        if active is None:
            return BehaviorResult(self._state, self._terminal.get(command_id))
        due = self._due_feedback(command_id, now_s)
        if due is not None:
            return BehaviorResult(self._state, due)
        if not approved:
            return self._finish(command_id, ExecutionStatus.REJECTED, now_s, "confirmation declined")
        self._state = self._state_for(active.command.action)
        return BehaviorResult(self._state)

    def complete(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None:
        active = self._active.get(command_id)
        if active is None:
            return self._terminal.get(command_id)
        due = self._due_feedback(command_id, now_s)
        if due is not None:
            return due
        return self._finish(command_id, ExecutionStatus.SUCCEEDED, now_s, detail).feedback

    def fail(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None:
        if command_id not in self._active:
            return self._terminal.get(command_id)
        due = self._due_feedback(command_id, now_s)
        if due is not None:
            return due
        return self._finish(command_id, ExecutionStatus.FAILED, now_s, detail).feedback

    def tick(self, *, now_s: float) -> tuple[ExecutionFeedback, ...]:
        feedback: list[ExecutionFeedback] = []
        for command_id in tuple(self._active):
            due = self._due_feedback(command_id, now_s)
            if due is not None:
                feedback.append(due)
        return tuple(feedback)

    def _due_feedback(self, command_id: str, now_s: float) -> ExecutionFeedback | None:
        """Finish an active command whose authority has elapsed, if any.

        Every operation that could complete or alter an active command calls
        this first.  Thus callers cannot bypass a missed ``tick`` and report a
        stale command as successful or normally failed.
        """
        active = self._active.get(command_id)
        if active is None:
            return None
        if active.command.is_expired_at(now_s):
            return self._finish(command_id, ExecutionStatus.EXPIRED, now_s, "command expired").feedback
        if now_s - active.started_at_s > self._timeout_s:
            return self._finish(command_id, ExecutionStatus.TIMED_OUT, now_s, "command timed out").feedback
        return None

    def _finish(self, command_id: str, status: ExecutionStatus, now_s: float, detail: str,
                command: DrivingCommand | None = None) -> BehaviorResult:
        existing = self._terminal.get(command_id)
        if existing is not None:
            return BehaviorResult(self._state, existing)
        self._active.pop(command_id, None)
        feedback = ExecutionFeedback(command_id, status, now_s, detail)
        self._terminal[command_id] = feedback
        self._state = BehaviorState.STOPPED if status is ExecutionStatus.SUCCEEDED else BehaviorState.RECOVERING
        return BehaviorResult(self._state, feedback)

    @staticmethod
    def _state_for(action: str) -> BehaviorState:
        return {
            "STOP": BehaviorState.APPROACH_STOP,
            "EMERGENCY_BRAKE": BehaviorState.EMERGENCY_BRAKE,
            "KEEP_LANE": BehaviorState.LANE_FOLLOW,
            "SET_SPEED": BehaviorState.LANE_FOLLOW,
            "FOLLOW": BehaviorState.FOLLOWING,
            "YIELD": BehaviorState.YIELDING,
        }.get(action, BehaviorState.RECOVERING)
