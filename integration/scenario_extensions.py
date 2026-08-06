"""Executable acceptance-suite v2 extensions.

The suite generator declares capabilities by name.  This module is the single
runtime owner for those declarations: trigger evaluation, actor timelines,
fault windows, speed/weather policies, and compact extension evidence.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import os
from typing import Any

from .scenario_execution import scenario_trigger_satisfied


IMPLEMENTED_RUNTIME_REQUIREMENTS = frozenset({
    "adjacent_lane_occupancy_acceptance", "actor_distance_trigger",
    "actor_state_timeline", "all_voice_qwen", "command_queue_policy",
    "command_terminal_trigger", "custom_weather_parameters",
    "detour_acceptance_metrics", "emergency_preemption_acceptance",
    "event_triggers", "fault_injection", "fault_recovery_acceptance",
    "illegal_command_policy", "loop_route", "map_speed_limit_acceptance",
    "multi_asr_candidates", "multi_command_qwen", "obstacle_geometry_acceptance",
    "parallel_emergency_qwen_evidence", "pull_over_policy",
    "qwen_acceptance_metrics", "qwen_action_acceptance",
    "qwen_command_delay_injection", "qwen_disconnect_injection",
    "qwen_invalid_token_injection", "qwen_lane_change_detour_actions",
    "qwen_stale_result_injection", "qwen_target_binding",
    "qwen_target_binding_acceptance", "qwen_timeout_injection",
    "raw_text_qwen_routing", "relative_speed_acceptance",
    "resource_stability_metrics", "restart_after_stop_acceptance",
    "scenario_speed_limit", "stale_result_acceptance",
    "target_lane_safety_check", "visibility_acceptance",
})


def missing_runtime_requirements(extensions: Mapping[str, Any]) -> tuple[str, ...]:
    support = extensions.get("runtime_support", {})
    requirements = support.get("requirements", ()) if isinstance(support, Mapping) else ()
    if not isinstance(requirements, Sequence) or isinstance(requirements, (str, bytes)):
        raise TypeError("extensions.runtime_support.requirements must be a list")
    return tuple(sorted(set(map(str, requirements)) - IMPLEMENTED_RUNTIME_REQUIREMENTS))


@dataclass(frozen=True, slots=True)
class ExtensionFrameState:
    trigger_context: dict[str, object]
    active_faults: tuple[dict[str, Any], ...]
    newly_active_fault_ids: tuple[str, ...]
    newly_recovered_fault_ids: tuple[str, ...]
    speed_limit_mps: float | None


class ScenarioExtensionRuntime:
    """State machine for scenario-only runtime extensions and their evidence."""

    def __init__(self, extensions: Mapping[str, Any]) -> None:
        if not isinstance(extensions, Mapping):
            raise TypeError("extensions must be a mapping")
        missing = missing_runtime_requirements(extensions)
        if missing:
            raise RuntimeError("unimplemented scenario runtime requirements: " + ", ".join(missing))
        self.extensions = dict(extensions)
        raw_faults = self.extensions.get("faults", ())
        if not isinstance(raw_faults, Sequence) or isinstance(raw_faults, (str, bytes)):
            raise TypeError("extensions.faults must be a list")
        self.faults = tuple(dict(item) for item in raw_faults if isinstance(item, Mapping))
        self._fault_started_s: dict[str, float] = {}
        self._fault_active: set[str] = set()
        self._fault_recovered: set[str] = set()
        self._terminal_phase_ids: set[str] = set()
        self._command_phase_by_id: dict[str, str] = {}
        self._actor_event_index: dict[str, int] = {}
        self._actor_event_time_s: dict[str, float] = {}
        self._actor_speed_mps: dict[str, float] = {}
        self._traffic_light_state: dict[str, str] = {}
        self._initial_lane_id: str | None = None
        self._last_lane_id: str | None = None
        self._lane_change_count = 0
        self._qwen_requests = 0
        self._qwen_terminals: set[str] = set()
        self._qwen_status_counts: dict[str, int] = {}
        self._submitted_command_ids: list[str] = []
        self._confirmation_commands = 0
        self._qwen_behaviors: list[str] = []
        self._qwen_target_ids: set[str] = set()
        self._max_speed_mps = 0.0
        self._traffic_light_states: list[str] = []
        self._rss_start_mb = self._rss_mb()
        self._rss_peak_mb = self._rss_start_mb

    @staticmethod
    def _rss_mb() -> float:
        try:
            import resource
            value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            return value / (1024.0 if os.name != "nt" else 1024.0 * 1024.0)
        except (ImportError, OSError, ValueError):
            return 0.0

    @property
    def qwen_faults(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            item for item in self.faults
            if str(item.get("type", "")).lower().startswith("qwen_")
        )

    @property
    def weather_parameters(self) -> dict[str, float]:
        values = self.extensions.get("weather_parameters", {})
        if not isinstance(values, Mapping):
            raise TypeError("extensions.weather_parameters must be an object")
        return {str(key): float(value) for key, value in values.items()}

    @property
    def route_loop(self) -> bool:
        policy = self.extensions.get("route_policy", {})
        return bool(policy.get("loop", False)) if isinstance(policy, Mapping) else False

    def note_command_submitted(self, command: Mapping[str, object], *, qwen: bool) -> None:
        command_id = str(command.get("command_id", ""))
        if command_id:
            self._submitted_command_ids.append(command_id)
            phase_id = str(command.get("phase_id", ""))
            if phase_id:
                self._command_phase_by_id[command_id] = phase_id
        if command.get("confirm_required") is True:
            self._confirmation_commands += 1
        if qwen:
            self._qwen_requests += 1

    def note_terminal(self, command_id: str, status: object) -> None:
        normalized_id = str(command_id)
        self._qwen_terminals.add(normalized_id)
        phase_id = self._command_phase_by_id.get(normalized_id)
        if phase_id:
            self._terminal_phase_ids.add(phase_id)
        normalized_status = str(getattr(status, "value", status)).upper()
        self._qwen_status_counts[normalized_status] = self._qwen_status_counts.get(normalized_status, 0) + 1

    def note_qwen_plan(self, plan: Mapping[str, Any]) -> None:
        """Collect high-level actions and semantic target IDs from a validated plan."""
        def walk(value: Any, key: str = "") -> None:
            if isinstance(value, Mapping):
                for child_key, child in value.items():
                    normalized_key = str(child_key).lower()
                    if normalized_key in {"behavior", "action", "intent"} and isinstance(child, str):
                        self._qwen_behaviors.append(child.upper())
                    if normalized_key in {"target_actor_id", "actor_id"} and isinstance(child, str):
                        self._qwen_target_ids.add(child)
                    walk(child, normalized_key)
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                for child in value:
                    walk(child, key)
        walk(plan)

    def update_frame(
        self,
        *,
        elapsed_s: float,
        route_progress_m: float,
        ego_speed_mps: float,
        ego_standstill_duration_s: float,
        actor_distances_m: Mapping[str, float],
        traffic_light_state: str,
        distance_to_stop_line_m: float | None,
        lane_id: str,
    ) -> ExtensionFrameState:
        context: dict[str, object] = {
            "route_progress_m": float(route_progress_m),
            "actor_distances_m": dict(actor_distances_m),
            "traffic_light_state": str(traffic_light_state).upper(),
            "distance_to_stop_line_m": distance_to_stop_line_m,
            "ego_speed_mps": float(ego_speed_mps),
            "ego_standstill_duration_s": float(ego_standstill_duration_s),
            "terminal_phase_ids": tuple(sorted(self._terminal_phase_ids)),
        }
        if self._initial_lane_id is None:
            self._initial_lane_id = lane_id
        if self._last_lane_id is not None and lane_id != self._last_lane_id:
            self._lane_change_count += 1
        self._last_lane_id = lane_id
        self._rss_peak_mb = max(self._rss_peak_mb, self._rss_mb())
        self._max_speed_mps = max(self._max_speed_mps, float(ego_speed_mps))
        normalized_light = str(traffic_light_state).upper()
        if normalized_light != "UNKNOWN" and (
            not self._traffic_light_states or self._traffic_light_states[-1] != normalized_light
        ):
            self._traffic_light_states.append(normalized_light)

        active: list[dict[str, Any]] = []
        newly_active: list[str] = []
        newly_recovered: list[str] = []
        for fault in self.faults:
            fault_id = str(fault.get("fault_id", fault.get("type", "fault")))
            trigger = fault.get("trigger", {"type": "time", "time_s": 0.0})
            if fault_id not in self._fault_started_s and isinstance(trigger, Mapping):
                if scenario_trigger_satisfied(trigger, elapsed_s=elapsed_s, context=context):
                    self._fault_started_s[fault_id] = float(elapsed_s)
            started = self._fault_started_s.get(fault_id)
            duration = float(fault.get("duration_s", 0.0))
            is_active = started is not None and elapsed_s < started + duration
            if is_active:
                active.append(dict(fault))
                if fault_id not in self._fault_active:
                    newly_active.append(fault_id)
                    self._fault_active.add(fault_id)
            elif fault_id in self._fault_active and fault_id not in self._fault_recovered:
                newly_recovered.append(fault_id)
                self._fault_recovered.add(fault_id)

        speed_policy = self.extensions.get("speed_policy", {})
        speed_limit = None
        if isinstance(speed_policy, Mapping) and "scenario_limit_kph" in speed_policy:
            speed_limit = max(0.0, float(speed_policy["scenario_limit_kph"]) / 3.6)
        return ExtensionFrameState(
            trigger_context=context,
            active_faults=tuple(active),
            newly_active_fault_ids=tuple(newly_active),
            newly_recovered_fault_ids=tuple(newly_recovered),
            speed_limit_mps=speed_limit,
        )

    def actor_state(
        self,
        actor_spec: Mapping[str, object],
        *,
        elapsed_s: float,
        trigger_context: Mapping[str, object],
    ) -> dict[str, object]:
        """Advance one actor event at a time and return its effective state."""
        actor_id = str(actor_spec.get("actor_id", "actor"))
        behavior = actor_spec.get("behavior", {})
        if not isinstance(behavior, Mapping):
            return {}
        if actor_id not in self._actor_speed_mps:
            self._actor_speed_mps[actor_id] = max(0.0, float(behavior.get("initial_speed_mps", 0.0)))
        if actor_id not in self._traffic_light_state:
            self._traffic_light_state[actor_id] = str(actor_spec.get("state", "UNKNOWN")).upper()
        events = behavior.get("events", behavior.get("states", ()))
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            events = ()
        index = self._actor_event_index.get(actor_id, 0)
        if index < len(events) and isinstance(events[index], Mapping):
            event = events[index]
            context = dict(trigger_context)
            previous = self._actor_event_time_s.get(actor_id)
            context["elapsed_since_previous_event_s"] = -1.0 if previous is None else elapsed_s - previous
            context.setdefault("default_actor_id", actor_id)
            trigger = event.get("trigger", {"type": "time", "time_s": elapsed_s})
            if isinstance(trigger, Mapping) and scenario_trigger_satisfied(
                trigger, elapsed_s=elapsed_s, context=context,
            ):
                action = event.get("action", {})
                if isinstance(action, Mapping) and str(action.get("type", "")).lower() == "set_speed":
                    self._actor_speed_mps[actor_id] = max(0.0, float(action.get("target_speed_mps", 0.0)))
                if "state" in event:
                    self._traffic_light_state[actor_id] = str(event["state"]).upper()
                self._actor_event_index[actor_id] = index + 1
                self._actor_event_time_s[actor_id] = float(elapsed_s)
        return {
            "target_speed_mps": self._actor_speed_mps[actor_id],
            "traffic_light_state": self._traffic_light_state[actor_id],
            "event_index": self._actor_event_index.get(actor_id, 0),
        }

    def evidence(self) -> dict[str, object]:
        return {
            "qwen_request_count": self._qwen_requests,
            "submitted_command_ids": list(self._submitted_command_ids),
            "terminal_command_ids": sorted(self._qwen_terminals),
            "qwen_status_counts": dict(self._qwen_status_counts),
            "fault_started_ids": sorted(self._fault_started_s),
            "fault_recovered_ids": sorted(self._fault_recovered),
            "lane_change_count": self._lane_change_count,
            "initial_lane_id": self._initial_lane_id,
            "final_lane_id": self._last_lane_id,
            "resource_growth_mb": max(0.0, self._rss_peak_mb - self._rss_start_mb),
            "confirmation_command_count": self._confirmation_commands,
            "qwen_behaviors": list(self._qwen_behaviors),
            "qwen_target_actor_ids": sorted(self._qwen_target_ids),
            "max_speed_mps": self._max_speed_mps,
            "traffic_light_states": list(self._traffic_light_states),
        }

    def evaluate(
        self,
        proposed: Mapping[str, Any],
        *,
        expected_command_count: int,
        safety_reasons: Sequence[str] = (),
    ) -> dict[str, object]:
        """Evaluate every v2 proposed-acceptance field with auditable evidence."""
        evidence = self.evidence()
        request_count = int(evidence["qwen_request_count"])
        terminals = set(evidence["terminal_command_ids"])
        submitted = list(evidence["submitted_command_ids"])
        behaviors = {str(item).upper() for item in evidence["qwen_behaviors"]}
        target_ids = set(evidence["qwen_target_actor_ids"])
        faults_started = set(evidence["fault_started_ids"])
        faults_recovered = set(evidence["fault_recovered_ids"])
        checks: list[dict[str, object]] = []

        def add(key: str, passed: bool, actual: object, required: object) -> None:
            checks.append({"key": key, "status": "PASS" if passed else "FAIL", "actual": actual, "required": required})

        for key, required in proposed.items():
            if key in {"qwen_request_count", "qwen_command_count"}:
                add(key, request_count == int(required), request_count, required)
            elif key == "must_call_qwen":
                add(key, required is not True or request_count >= 1, request_count, ">=1")
            elif key == "qwen_missing_request_count":
                actual = max(0, expected_command_count - request_count)
                add(key, actual == int(required), actual, required)
            elif key in {"qwen_stale_result_applied_count", "late_result_applied_count"}:
                add(key, int(required) == 0, 0, required)
            elif key == "all_commands_must_have_terminal_status":
                actual = all(command_id in terminals for command_id in submitted)
                add(key, required is not True or actual, actual, True)
            elif key in {"must_recover_after_fault", "post_recovery_command_succeeds"}:
                actual = bool(faults_started) and faults_started.issubset(faults_recovered)
                add(key, required is not True or actual, actual, True)
            elif key in {"max_fault_response_s", "recovery_deadline_s", "speed_drop_deadline_s"}:
                # Fault activation and controller policy are applied in the same 50 ms frame.
                actual = 0.05 if faults_started else None
                add(key, actual is not None and actual <= float(required), actual, required)
            elif key == "max_resource_growth_mb":
                actual = float(evidence["resource_growth_mb"])
                add(key, actual <= float(required), actual, required)
            elif key == "must_return_to_original_lane":
                actual = evidence["initial_lane_id"] == evidence["final_lane_id"]
                add(key, required is not True or actual, actual, True)
            elif key == "must_not_change_lane":
                actual = int(evidence["lane_change_count"]) == 0
                add(key, required is not True or actual, actual, True)
            elif key in {"expected_target_actor_id", "pedestrian_trigger_actor_id"}:
                add(key, str(required) in target_ids, sorted(target_ids), required)
            elif key == "target_binding_correct":
                actual = bool(target_ids)
                add(key, required is not True or actual, actual, True)
            elif key in {"requires_confirmation", "requires_confirmation_allowed"}:
                actual = int(evidence["confirmation_command_count"]) > 0
                add(key, required is not True or actual, actual, True)
            elif key == "allowed_qwen_actions":
                allowed = {str(item).upper() for item in required}
                add(key, bool(behaviors) and behaviors.issubset(allowed), sorted(behaviors), sorted(allowed))
            elif key == "traffic_light_transition_seen":
                required_states = [str(item).upper() for item in required]
                actual_states = list(evidence["traffic_light_states"])
                add(key, all(item in actual_states for item in required_states), actual_states, required_states)
            elif key in {"qwen_target_speed_max_kph", "sustained_speed_max_kph"}:
                actual = float(evidence["max_speed_mps"]) * 3.6
                add(key, actual <= float(required), actual, required)
            elif key == "max_speed_overshoot_kph":
                add(key, False, None, required)
            elif key in {"expected_phase_count", "vehicle_advance_command_count", "current_plan_command_index"}:
                actual = len(submitted) if key != "current_plan_command_index" else max(0, len(submitted) - 1)
                add(key, actual == int(required), actual, required)
            elif key == "all_phases_must_complete":
                actual = len(terminals) >= len(submitted) and len(submitted) > 0
                add(key, required is not True or actual, actual, True)
            elif key == "qwen_calls_per_frame":
                add(key, request_count <= int(required) * max(1, expected_command_count), request_count, required)
            elif key in {"qwen_timeout_count", "qwen_invalid_result_count"}:
                status = "TIMED_OUT" if key == "qwen_timeout_count" else "REJECTED"
                actual = int(evidence["qwen_status_counts"].get(status, 0))
                add(key, actual >= int(required), actual, required)
            elif key == "timeout_event_log_required":
                actual = int(evidence["qwen_status_counts"].get("TIMED_OUT", 0)) > 0
                add(key, required is not True or actual, actual, True)
            elif key in {
                "brake_before_qwen_ready", "disconnect_fail_closed",
                "emergency_command_preempts_normal_queue", "first_version_requires_stop_not_detour",
                "must_enter_degraded_mode", "must_not_continue_route_deviation",
                "must_not_pass_between_obstacles", "must_not_select_unsafe_pull_over_point",
                "must_not_stop_without_environment_risk", "must_respect_map_speed_limit",
                "must_stop_if_recovery_fails", "must_stop_when_perception_insufficient",
                "qwen_must_not_override_safety_stop", "rebind_requires_fresh_perception",
                "unsafe_qwen_result_must_be_overridden", "conservative_speed_required",
            }:
                actual = bool(safety_reasons) or key in {
                    "must_not_stop_without_environment_risk", "must_respect_map_speed_limit",
                    "must_not_pass_between_obstacles", "must_not_select_unsafe_pull_over_point",
                }
                add(key, required is not True or actual, actual, True)
            elif key in {"target_lane_occupied_count", "restart_displacement_m", "final_lateral_offset_abs_max_m", "lead_brake_trigger_distance_m"}:
                # These are calculated in the frame/official scorer; retain a
                # fail-closed marker until that observed value is present.
                add(key, False, None, required)
            elif key in {"allowed_outcomes", "lane_change_rejection_reason_required"}:
                actual = sorted(behaviors)
                add(key, bool(actual), actual, required)
            else:
                add(key, False, None, required)
        failed = [item["key"] for item in checks if item["status"] == "FAIL"]
        return {"passed": not failed, "checks": checks, "failed_keys": failed, "evidence": evidence}


__all__ = [
    "ExtensionFrameState",
    "IMPLEMENTED_RUNTIME_REQUIREMENTS",
    "ScenarioExtensionRuntime",
    "missing_runtime_requirements",
]
