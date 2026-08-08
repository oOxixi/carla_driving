"""Deterministic execution state machine for compiled ManeuverPlan V2 steps.

This layer interprets high-level completion/precondition facts only.  It never
creates low-level vehicle control and therefore remains downstream of planning
and upstream of B/C/D.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Any

from runtime.plan_compiler import CompiledManeuverPlan, CompiledPlanStep


TERMINAL_STATES = frozenset({
    "SUCCEEDED", "FAILED", "SAFETY_OVERRIDE", "SUPERSEDED", "CONFIRMING",
})
_STATE_BY_BEHAVIOR = {
    "WAIT_SAFE_GAP": "WAIT_SAFE_GAP",
    "TURN_LEFT": "TURNING",
    "TURN_RIGHT": "TURNING",
    "CHANGE_LANE_LEFT": "CHANGING_LANE",
    "CHANGE_LANE_RIGHT": "CHANGING_LANE",
    "AVOID_OBSTACLE": "AVOIDING",
    "PASS_TARGET": "AVOIDING",
    "RETURN_TO_LANE": "RETURNING_TO_LANE",
    "PULL_OVER": "PULLING_OVER",
}


@dataclass(frozen=True, slots=True)
class ManeuverEvent:
    event_type: str
    command_id: str
    plan_id: str
    step_id: str | None
    state: str
    reason_code: str
    now_s: float


@dataclass(frozen=True, slots=True)
class ManeuverUpdate:
    state: str
    current_step: CompiledPlanStep | None
    events: tuple[ManeuverEvent, ...]
    safe_behavior: str | None
    terminal: bool


class ManeuverFSM:
    def __init__(
        self,
        *,
        replan_cooldown_s: float = 2.0,
        max_replans_per_command: int = 2,
    ) -> None:
        if not math.isfinite(float(replan_cooldown_s)) or replan_cooldown_s < 0:
            raise ValueError("replan_cooldown_s must be finite and non-negative")
        if type(max_replans_per_command) is not int or max_replans_per_command < 0:
            raise ValueError("max_replans_per_command must be a non-negative integer")
        self.replan_cooldown_s = float(replan_cooldown_s)
        self.max_replans_per_command = max_replans_per_command
        self.state = "IDLE"
        self.plan: CompiledManeuverPlan | None = None
        self.step_index = 0
        self.step_started_s: float | None = None
        self._preconditions_latched = False
        self._completion_frames = 0
        self._terminal_emitted = False
        self._last_replan_s: float | None = None
        self._replan_count = 0

    @property
    def current_step(self) -> CompiledPlanStep | None:
        if self.plan is None or self.step_index >= len(self.plan.steps):
            return None
        return self.plan.steps[self.step_index]

    @property
    def replan_count(self) -> int:
        return self._replan_count

    def start(self, plan: CompiledManeuverPlan, *, now_s: float) -> ManeuverUpdate:
        now = _time(now_s)
        if not isinstance(plan, CompiledManeuverPlan):
            raise TypeError("plan must be CompiledManeuverPlan")
        events: list[ManeuverEvent] = []
        if self.plan is not None and self.state not in TERMINAL_STATES:
            events.append(self._event("qwen_terminal", now, "SUPERSEDED_BY_NEW_PLAN", state="SUPERSEDED"))
        self.plan = plan
        self.step_index = 0
        self.step_started_s = now
        self._preconditions_latched = False
        self._completion_frames = 0
        self._terminal_emitted = False
        self._last_replan_s = None
        self._replan_count = 0
        self.state = self._step_state(self.current_step)
        events.append(self._event("qwen_plan_started", now, "PLAN_ACCEPTED"))
        events.append(self._event("qwen_step_started", now, "STEP_ENTER"))
        return self._update(events=events)

    def update(self, snapshot: Mapping[str, Any], *, now_s: float) -> ManeuverUpdate:
        now = _time(now_s)
        if not isinstance(snapshot, Mapping):
            raise TypeError("snapshot must be a mapping")
        if self.plan is None:
            return ManeuverUpdate("IDLE", None, (), None, False)
        if self.state in TERMINAL_STATES:
            return self._update()
        step = self.current_step
        if step is None:
            return self._finish("SUCCEEDED", "PLAN_COMPLETE", now)
        if bool(snapshot.get("emergency", False)) or str(snapshot.get("risk_level", "")).upper() == "EMERGENCY":
            emergency_reason = str(
                snapshot.get("emergency_reason", "EMERGENCY_PREEMPT")
            ).strip().upper()
            return self._finish(
                "SAFETY_OVERRIDE",
                emergency_reason or "EMERGENCY_PREEMPT",
                now,
                safe_behavior="EMERGENCY_STOP",
            )
        replan_reason = self._replan_reason(snapshot)
        if replan_reason is not None:
            return self.request_replan(replan_reason, now_s=now)
        if self.step_started_s is None:
            self.step_started_s = now
        if now - self.step_started_s > step.timeout_s:
            return self._step_failure(step, "STEP_TIMEOUT", now)
        if not self._preconditions_latched:
            unmet = tuple(
                condition for condition in step.preconditions
                if not (
                    condition == "TARGET_VISIBLE"
                    and step.behavior == "PASS_TARGET"
                    and bool(snapshot.get("target_seen", False))
                )
                and not _precondition_satisfied(condition, snapshot)
            )
            if unmet:
                self._completion_frames = 0
                if any(condition.endswith("GAP_SAFE") for condition in unmet):
                    self.state = "WAIT_SAFE_GAP"
                else:
                    self.state = "PLAN_EXECUTING"
                return self._update(safe_behavior="SLOW_DOWN")
            # Preconditions gate entry into a step.  Re-evaluating relative
            # lane facts after a lane transition would make success
            # impossible (the former adjacent lane is now the current lane).
            # Emergency risk remains continuously enforced above this gate.
            self._preconditions_latched = True
        self.state = self._step_state(step)
        if _completion_satisfied(step.completion, snapshot):
            self._completion_frames += 1
        else:
            self._completion_frames = 0
        required_frames = int(step.completion["hold_frames"])
        if self._completion_frames < required_frames:
            return self._update()
        completed_event = self._event("qwen_step_completed", now, "COMPLETION_HELD")
        self.step_index += 1
        self._completion_frames = 0
        self.step_started_s = now
        self._preconditions_latched = False
        if self.current_step is None:
            return self._finish("SUCCEEDED", "PLAN_COMPLETE", now, events=[completed_event])
        self.state = self._step_state(self.current_step)
        return self._update(events=[
            completed_event,
            self._event("qwen_step_started", now, "STEP_ENTER"),
        ])

    def request_replan(self, reason_code: str, *, now_s: float) -> ManeuverUpdate:
        now = _time(now_s)
        if self.plan is None or self.state in TERMINAL_STATES:
            return self._update()
        reason = str(reason_code).strip().upper()
        if not reason:
            raise ValueError("reason_code must be non-empty")
        if self._last_replan_s is not None and now - self._last_replan_s < self.replan_cooldown_s:
            return self._update(events=[
                self._event("qwen_replan_suppressed", now, "REPLAN_COOLDOWN"),
            ], safe_behavior="SLOW_DOWN")
        if self._replan_count >= self.max_replans_per_command:
            return self._finish(
                "FAILED", "REPLAN_LIMIT_EXCEEDED", now, safe_behavior="STOP",
            )
        self._replan_count += 1
        self._last_replan_s = now
        self.state = "REPLAN_PENDING"
        return self._update(
            events=[self._event("qwen_replan_triggered", now, reason)],
            safe_behavior="SLOW_DOWN",
        )

    def fail(self, reason_code: str, *, now_s: float) -> ManeuverUpdate:
        return self._finish("FAILED", str(reason_code).upper(), _time(now_s), safe_behavior="STOP")

    def _step_failure(
        self, step: CompiledPlanStep, reason: str, now: float,
    ) -> ManeuverUpdate:
        if step.on_failure == "REPLAN":
            return self.request_replan(reason, now_s=now)
        if step.on_failure == "CONFIRM":
            return self._finish("CONFIRMING", reason, now, safe_behavior="STOP")
        safe = "STOP" if step.on_failure == "SAFE_STOP" else "KEEP_LANE"
        return self._finish("FAILED", reason, now, safe_behavior=safe)

    def _finish(
        self,
        state: str,
        reason: str,
        now: float,
        *,
        safe_behavior: str | None = None,
        events: list[ManeuverEvent] | None = None,
    ) -> ManeuverUpdate:
        if self.state in TERMINAL_STATES and self._terminal_emitted:
            return self._update(safe_behavior=safe_behavior)
        self.state = state
        terminal_events = [] if events is None else list(events)
        if not self._terminal_emitted:
            terminal_events.append(self._event("qwen_terminal", now, reason, state=state))
            self._terminal_emitted = True
        return self._update(events=terminal_events, safe_behavior=safe_behavior)

    def _replan_reason(self, snapshot: Mapping[str, Any]) -> str | None:
        if self.plan is None:
            return None
        declared = set(self.plan.replan_conditions)
        for reason, key in (
            ("TARGET_LOST", "target_lost"),
            ("LANE_BLOCKED", "lane_blocked"),
            ("ROUTE_MISMATCH", "route_mismatch"),
            ("NEW_EMERGENCY_OBJECT", "new_emergency_object"),
            ("PROGRESS_STALLED", "progress_stalled"),
            ("ROUTE_DEVIATION", "route_deviation"),
            ("PLAN_EXPIRING", "plan_expiring"),
        ):
            if reason in declared and bool(snapshot.get(key, False)):
                return reason
        return None

    def _event(
        self, event_type: str, now: float, reason: str, *, state: str | None = None,
    ) -> ManeuverEvent:
        assert self.plan is not None
        step = self.current_step
        return ManeuverEvent(
            event_type=event_type,
            command_id=self.plan.command_id,
            plan_id=self.plan.plan_id,
            step_id=None if step is None else step.step_id,
            state=self.state if state is None else state,
            reason_code=reason,
            now_s=now,
        )

    def _update(
        self,
        *,
        events: list[ManeuverEvent] | None = None,
        safe_behavior: str | None = None,
    ) -> ManeuverUpdate:
        return ManeuverUpdate(
            state=self.state,
            current_step=self.current_step,
            events=tuple(() if events is None else events),
            safe_behavior=safe_behavior,
            terminal=self.state in TERMINAL_STATES,
        )

    @staticmethod
    def _step_state(step: CompiledPlanStep | None) -> str:
        if step is None:
            return "SUCCEEDED"
        return _STATE_BY_BEHAVIOR.get(step.behavior, "PLAN_EXECUTING")


def _time(value: float) -> float:
    if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError("now_s must be finite")
    return float(value)


def _precondition_satisfied(condition: str, snapshot: Mapping[str, Any]) -> bool:
    mapping = {
        "PERCEPTION_FRESH": "perception_fresh",
        "LEFT_LANE_EXISTS": "left_lane_exists",
        "RIGHT_LANE_EXISTS": "right_lane_exists",
        "LEFT_GAP_SAFE": "left_gap_safe",
        "RIGHT_GAP_SAFE": "right_gap_safe",
        "TARGET_VISIBLE": "target_visible",
        "ROUTE_AVAILABLE": "route_available",
        "INTERSECTION_AHEAD": "intersection_ahead",
        "STOP_LINE_CLEAR": "stop_line_clear",
        "NO_EMERGENCY_RISK": "no_emergency_risk",
    }
    key = mapping[condition]
    if key == "perception_fresh":
        return bool(snapshot.get(key, not bool(snapshot.get("stale", False))))
    if key == "no_emergency_risk":
        return bool(snapshot.get(key, str(snapshot.get("risk_level", "LOW")).upper() != "EMERGENCY"))
    return bool(snapshot.get(key, False))


def _completion_satisfied(completion: Mapping[str, Any], snapshot: Mapping[str, Any]) -> bool:
    kind = str(completion["type"])
    value = completion.get("value")
    if kind == "SPEED_BELOW":
        return float(snapshot.get("speed_mps", math.inf)) <= float(value)
    if kind == "SPEED_REACHED":
        # Match the closed-loop acceptance tolerance (2 km/h ~= 0.56 m/s).
        # The former 0.35 m/s threshold could time out a physically stable
        # controller immediately before it entered the accepted speed band.
        tolerance = float(snapshot.get("speed_tolerance_mps", 0.6))
        return abs(float(snapshot.get("speed_mps", math.inf)) - float(value)) <= tolerance
    if kind == "LANE_CENTERED":
        return (
            str(snapshot.get("lane", "")).upper() == str(completion.get("lane", "")).upper()
            and abs(float(snapshot.get("lateral_error_m", math.inf)))
            <= float(snapshot.get("lane_center_tolerance_m", 0.3))
        )
    if kind == "JUNCTION_EXITED":
        return bool(snapshot.get("junction_exited", False))
    if kind == "TARGET_GAP_REACHED":
        return float(snapshot.get("target_gap_s", -math.inf)) >= float(value)
    if kind == "TARGET_PASSED":
        return bool(snapshot.get("target_passed", False))
    if kind == "STOPPED":
        return float(snapshot.get("speed_mps", math.inf)) <= float(snapshot.get("stopped_threshold_mps", 0.1))
    if kind == "HOLD_FRAMES":
        return bool(snapshot.get("hold_condition", True))
    raise ValueError(f"unsupported completion type: {kind}")


__all__ = ["ManeuverEvent", "ManeuverFSM", "ManeuverUpdate", "TERMINAL_STATES"]
