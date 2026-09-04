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


TIME_COMPARISON_EPSILON_S = 1e-6


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
    "dynamic_out_and_back_route", "per_actor_minimum_distance_acceptance",
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
    speed_limit_override: bool


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
        self._fault_recovered_s: dict[str, float] = {}
        self._fault_response_s: dict[str, float] = {}
        self._fault_recovery_response_s: dict[str, float] = {}
        self._fault_active: set[str] = set()
        self._fault_recovered: set[str] = set()
        self._terminal_phase_ids: set[str] = set()
        self._completed_phase_ids: set[str] = set()
        self._command_phase_by_id: dict[str, str] = {}
        self._command_intent_by_id: dict[str, str] = {}
        self._actor_event_index: dict[str, int] = {}
        self._actor_event_count = 0
        self._actor_event_time_s: dict[str, float] = {}
        self._actor_speed_mps: dict[str, float] = {}
        self._minimum_actor_distances_m: dict[str, float] = {}
        self._actor_distances_m: dict[str, float] = {}
        self._traffic_light_state: dict[str, str] = {}
        self._initial_lane_id: str | None = None
        self._last_lane_id: str | None = None
        self._lane_change_count = 0
        self._qwen_requests = 0
        self._qwen_terminals: set[str] = set()
        self._qwen_status_counts: dict[str, int] = {}
        self._successful_terminal_s: dict[str, float] = {}
        self._submitted_command_ids: list[str] = []
        self._confirmation_commands = 0
        self._qwen_behaviors: list[str] = []
        self._qwen_target_ids: set[str] = set()
        self._qwen_target_speeds_kph: list[float] = []
        self._qwen_outcomes: list[str] = []
        self._qwen_resolution_reasons: list[str] = []
        self._qwen_stale_results = 0
        self._qwen_stale_results_applied = 0
        self._qwen_late_results_applied = 0
        self._qwen_invalid_results = 0
        self._qwen_timeouts = 0
        self._vehicle_advance_commands = 0
        self._latest_applied_command_index: int | None = None
        self._qwen_applied_s: list[float] = []
        self._first_qwen_plan_s: float | None = None
        self._max_speed_mps = 0.0
        self._min_speed_after_command_mps: float | None = None
        self._last_speed_mps = 0.0
        self._requested_speed_kph: float | None = None
        self._traffic_light_states: list[str] = []
        self._pre_red_max_speed_mps = 0.0
        self._minimum_red_stop_line_clearance_m: float | None = None
        self._stopped_on_red_before_stop_line = False
        self._last_elapsed_s = 0.0
        self._last_route_progress_m = 0.0
        self._restart_route_progress_m: float | None = None
        self._restart_displacement_m: float | None = None
        self._stop_seen = False
        self._slow_command_s: float | None = None
        self._slow_command_speed_mps: float | None = None
        self._speed_drop_latency_s: float | None = None
        self._last_lateral_offset_m: float | None = None
        self._last_route_deviation_m: float | None = None
        self._max_route_deviation_m = 0.0
        self._first_brake_s: float | None = None
        self._safety_reasons: set[str] = set()
        self._safety_first_s: float | None = None
        self._collision_seen = False
        self._degraded_mode_entered = False
        self._target_lane_occupied_count: int | None = None
        self._mission_route_restore_count = 0
        self._lead_brake_trigger_distance_m: float | None = None
        self._actor_trigger_ids: set[str] = set()
        self._actor_trigger_time_s: dict[str, float] = {}
        self._actor_perception_time_s: dict[str, float] = {}
        self._actor_decision_time_s: dict[str, float] = {}
        self._actor_safety_override_time_s: dict[str, float] = {}
        self._actor_control_effect_time_s: dict[str, float] = {}
        self._actor_recovery_time_s: dict[str, float] = {}
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
        intent = str(command.get("intent", "")).upper()
        if command_id:
            self._submitted_command_ids.append(command_id)
            self._command_intent_by_id[command_id] = intent
            phase_id = str(command.get("phase_id", ""))
            if phase_id:
                self._command_phase_by_id[command_id] = phase_id
        if command.get("confirm_required") is True:
            self._confirmation_commands += 1
        parameters = command.get("parameters", {})
        if isinstance(parameters, Mapping):
            speed = parameters.get("speed")
            if type(speed) in (int, float) and not isinstance(speed, bool):
                unit = str(parameters.get("unit", "km/h")).lower().replace(" ", "")
                self._requested_speed_kph = float(speed) * (
                    3.6 if unit in {"m/s", "mps", "m／s"} else 1.0
                )
        if qwen:
            self._qwen_requests += 1
        if intent in {"STOP", "EMERGENCY_STOP"}:
            self._stop_seen = True
        elif self._stop_seen and intent in {"KEEP_LANE", "START", "SET_SPEED"}:
            self._restart_route_progress_m = self._last_route_progress_m
        if intent == "SLOW_DOWN":
            self._slow_command_s = self._last_elapsed_s
            self._slow_command_speed_mps = self._last_speed_mps

    def note_terminal(self, command_id: str, status: object) -> None:
        normalized_id = str(command_id)
        self._qwen_terminals.add(normalized_id)
        phase_id = self._command_phase_by_id.get(normalized_id)
        if phase_id:
            self._terminal_phase_ids.add(phase_id)
            self._completed_phase_ids.add(phase_id)
        normalized_status = str(getattr(status, "value", status)).upper()
        self._qwen_status_counts[normalized_status] = self._qwen_status_counts.get(normalized_status, 0) + 1
        if normalized_status == "SUCCEEDED":
            self._successful_terminal_s[normalized_id] = self._last_elapsed_s

    def note_qwen_plan(self, plan: Mapping[str, Any], *, elapsed_s: float | None = None) -> None:
        """Collect high-level actions and semantic target IDs from a validated plan."""
        if self._first_qwen_plan_s is None:
            self._first_qwen_plan_s = self._last_elapsed_s if elapsed_s is None else float(elapsed_s)

        def walk(value: Any, key: str = "") -> None:
            if isinstance(value, Mapping):
                for child_key, child in value.items():
                    normalized_key = str(child_key).lower()
                    if normalized_key in {"behavior", "action", "intent"} and isinstance(child, str):
                        self._qwen_behaviors.append(child.upper())
                    if normalized_key in {"target_actor_id", "actor_id", "target_id"} and isinstance(child, str):
                        self._qwen_target_ids.add(child)
                    if normalized_key == "target_speed_mps" and type(child) in (int, float) and not isinstance(child, bool):
                        self._qwen_target_speeds_kph.append(float(child) * 3.6)
                    if normalized_key == "target_speed_kph" and type(child) in (int, float) and not isinstance(child, bool):
                        self._qwen_target_speeds_kph.append(float(child))
                    walk(child, normalized_key)
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                for child in value:
                    walk(child, key)
        walk(plan)

    def note_qwen_resolution(
        self,
        *,
        disposition: str,
        reason_code: str | None,
        applied: bool,
        command_id: str | None = None,
    ) -> None:
        normalized_disposition = str(disposition).upper()
        normalized_reason = str(reason_code or "").upper()
        self._qwen_outcomes.append(normalized_disposition)
        if normalized_reason:
            self._qwen_resolution_reasons.append(normalized_reason)
        stale = "STALE" in normalized_disposition or "STALE" in normalized_reason
        late = "LATE" in normalized_disposition or "LATE" in normalized_reason
        invalid = any(token in normalized_reason for token in ("INVALID", "SCHEMA", "TOKEN")) or any(
            str(item.get("type", "")).lower() == "qwen_invalid_token"
            for item in self.qwen_faults
        )
        timed_out = "TIMEOUT" in normalized_disposition or "TIMEOUT" in normalized_reason
        if stale:
            self._qwen_stale_results += 1
            if applied:
                self._qwen_stale_results_applied += 1
        if late and applied:
            self._qwen_late_results_applied += 1
        if invalid:
            self._qwen_invalid_results += 1
        if timed_out:
            self._qwen_timeouts += 1
        if applied:
            self._vehicle_advance_commands += 1
            self._qwen_applied_s.append(self._last_elapsed_s)
            if command_id in self._submitted_command_ids:
                self._latest_applied_command_index = self._submitted_command_ids.index(command_id)

    def note_phase_completed(self, phase_id: str) -> None:
        normalized = str(phase_id).strip()
        if normalized:
            self._completed_phase_ids.add(normalized)

    def note_actor_trigger(self, actor_id: str, *, elapsed_s: float | None = None) -> None:
        normalized = str(actor_id).strip()
        if normalized:
            self._actor_trigger_ids.add(normalized)
            self._actor_trigger_time_s.setdefault(
                normalized,
                self._last_elapsed_s if elapsed_s is None else float(elapsed_s),
            )

    def note_perception_observation(
        self,
        *,
        elapsed_s: float,
        detected_actor_ids: Sequence[str],
    ) -> None:
        """Record the first sensor-derived observation after an actor hazard starts."""
        detected = {str(actor_id).strip() for actor_id in detected_actor_ids if str(actor_id).strip()}
        for actor_id in self._actor_trigger_time_s:
            if actor_id in detected:
                self._actor_perception_time_s.setdefault(actor_id, float(elapsed_s))

    def ready_emergency_recovery(self, *, elapsed_s: float) -> tuple[str, float] | None:
        """Return one configured hazard whose minimum stop hold has elapsed."""
        recovery = self.extensions.get("emergency_recovery", {})
        if not isinstance(recovery, Mapping):
            raise TypeError("extensions.emergency_recovery must be an object")
        for actor_id, raw_policy in recovery.items():
            normalized_id = str(actor_id)
            if normalized_id in self._actor_recovery_time_s:
                continue
            control_s = self._actor_control_effect_time_s.get(normalized_id)
            if control_s is None:
                continue
            if not isinstance(raw_policy, Mapping):
                raise TypeError("emergency recovery policies must be objects")
            hold_s = float(raw_policy.get("minimum_hold_s", 0.0))
            minimum_clearance_m = float(raw_policy.get("minimum_clearance_m", 0.0))
            resume_speed_kph = float(raw_policy.get("resume_speed_kph", 0.0))
            if hold_s <= 0.0 or minimum_clearance_m < 0.0 or resume_speed_kph <= 0.0:
                raise ValueError(
                    "emergency recovery hold/resume speed must be positive and clearance non-negative"
                )
            actor_distance_m = self._actor_distances_m.get(normalized_id)
            hazard_clear = (
                minimum_clearance_m <= 0.0
                or (
                    actor_distance_m is not None
                    and actor_distance_m >= minimum_clearance_m
                )
            )
            if (
                hazard_clear
                and float(elapsed_s) + TIME_COMPARISON_EPSILON_S >= control_s + hold_s
            ):
                return normalized_id, resume_speed_kph / 3.6
        return None

    def note_emergency_recovered(self, actor_id: str, *, elapsed_s: float) -> None:
        normalized = str(actor_id).strip()
        if normalized not in self._actor_control_effect_time_s:
            raise ValueError("emergency recovery requires prior control-effect evidence")
        self._actor_recovery_time_s.setdefault(normalized, float(elapsed_s))

    def note_target_lane_occupancy(self, count: int) -> None:
        if type(count) is not int or count < 0:
            raise ValueError("target lane occupancy must be a non-negative integer")
        self._target_lane_occupied_count = count

    def note_mission_route_restored(self) -> None:
        """Record a successful manoeuvre return to the saved mission route."""
        self._mission_route_restore_count += 1

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
        lateral_offset_m: float | None = None,
        route_deviation_m: float | None = None,
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
        self._actor_distances_m = {
            str(actor_id): float(distance_m)
            for actor_id, distance_m in actor_distances_m.items()
        }
        for actor_id, distance_m in actor_distances_m.items():
            distance = float(distance_m)
            if not math.isfinite(distance) or distance < 0.0:
                raise ValueError("actor distances must be finite and non-negative")
            normalized_id = str(actor_id)
            previous = self._minimum_actor_distances_m.get(normalized_id)
            self._minimum_actor_distances_m[normalized_id] = (
                distance if previous is None else min(previous, distance)
            )
        if self._initial_lane_id is None:
            self._initial_lane_id = lane_id
        if self._last_lane_id is not None and lane_id != self._last_lane_id:
            self._lane_change_count += 1
        self._last_lane_id = lane_id
        self._last_elapsed_s = float(elapsed_s)
        self._last_route_progress_m = float(route_progress_m)
        self._last_speed_mps = float(ego_speed_mps)
        if self._submitted_command_ids:
            self._min_speed_after_command_mps = (
                float(ego_speed_mps)
                if self._min_speed_after_command_mps is None
                else min(self._min_speed_after_command_mps, float(ego_speed_mps))
            )
        if lateral_offset_m is not None:
            self._last_lateral_offset_m = abs(float(lateral_offset_m))
        if route_deviation_m is not None:
            self._last_route_deviation_m = abs(float(route_deviation_m))
            self._max_route_deviation_m = max(
                self._max_route_deviation_m, self._last_route_deviation_m,
            )
        if self._restart_route_progress_m is not None:
            self._restart_displacement_m = max(
                0.0, self._last_route_progress_m - self._restart_route_progress_m,
            )
        self._rss_peak_mb = max(self._rss_peak_mb, self._rss_mb())
        self._max_speed_mps = max(self._max_speed_mps, float(ego_speed_mps))
        normalized_light = str(traffic_light_state).upper()
        if normalized_light != "UNKNOWN" and (
            not self._traffic_light_states or self._traffic_light_states[-1] != normalized_light
        ):
            self._traffic_light_states.append(normalized_light)
        if normalized_light != "RED":
            self._pre_red_max_speed_mps = max(
                self._pre_red_max_speed_mps, float(ego_speed_mps),
            )
        elif distance_to_stop_line_m is not None:
            clearance = float(distance_to_stop_line_m)
            self._minimum_red_stop_line_clearance_m = (
                clearance
                if self._minimum_red_stop_line_clearance_m is None
                else min(self._minimum_red_stop_line_clearance_m, clearance)
            )
            if clearance >= 0.0 and float(ego_speed_mps) <= 0.15:
                self._stopped_on_red_before_stop_line = True

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
                self._fault_recovered_s[fault_id] = float(elapsed_s)

        speed_policy = self.extensions.get("speed_policy", {})
        speed_limit = None
        speed_limit_override = False
        if isinstance(speed_policy, Mapping) and "scenario_limit_kph" in speed_policy:
            speed_limit = max(0.0, float(speed_policy["scenario_limit_kph"]) / 3.6)
            speed_limit_override = bool(speed_policy.get("override_map_limit", False))
        return ExtensionFrameState(
            trigger_context=context,
            active_faults=tuple(active),
            newly_active_fault_ids=tuple(newly_active),
            newly_recovered_fault_ids=tuple(newly_recovered),
            speed_limit_mps=speed_limit,
            speed_limit_override=speed_limit_override,
        )

    def note_control_observation(
        self,
        *,
        elapsed_s: float,
        speed_mps: float,
        route_progress_m: float,
        brake: float,
        throttle: float = 0.0,
        safety_override: bool,
        safety_reason: str,
        route_deviation_m: float | None,
        collision: bool = False,
        lateral_offset_m: float | None = None,
    ) -> None:
        """Record the actually applied control outcome for acceptance timing."""
        now = float(elapsed_s)
        speed = float(speed_mps)
        self._last_elapsed_s = now
        self._last_speed_mps = speed
        self._last_route_progress_m = float(route_progress_m)
        self._collision_seen = self._collision_seen or bool(collision)
        if lateral_offset_m is not None:
            self._last_lateral_offset_m = abs(float(lateral_offset_m))
        if route_deviation_m is not None:
            deviation = abs(float(route_deviation_m))
            self._last_route_deviation_m = deviation
            self._max_route_deviation_m = max(self._max_route_deviation_m, deviation)
        if float(brake) >= 0.5 and self._first_brake_s is None:
            self._first_brake_s = now
        normalized_reason = str(safety_reason).strip().upper()
        meaningful_safety = bool(safety_override and normalized_reason not in {"", "NONE"})
        active_sensor_faults = {
            str(item.get("sensor", ""))
            for item in self.faults
            if str(item.get("fault_id", item.get("type", "fault"))) in self._fault_active
            and str(item.get("type", "")).lower() in {"sensor_blackout", "sensor_stale"}
        }
        if active_sensor_faults and not {"front_rgb", "lidar"}.issubset(active_sensor_faults):
            self._degraded_mode_entered = True
        if meaningful_safety:
            self._safety_reasons.add(normalized_reason)
            if self._safety_first_s is None:
                self._safety_first_s = now
        emergency_brake = float(brake) >= 0.5 and float(throttle) <= 0.03
        responded = meaningful_safety or emergency_brake
        if responded:
            # In S3 the FAST_LOCAL emergency command is itself the safety
            # preemption, even when D need not override the already-safe raw
            # control a second time.
            for actor_id in self._actor_trigger_time_s:
                self._actor_decision_time_s.setdefault(actor_id, now)
                self._actor_safety_override_time_s.setdefault(actor_id, now)
                if emergency_brake:
                    self._actor_control_effect_time_s.setdefault(actor_id, now)
            for fault_id, started_s in self._fault_started_s.items():
                if fault_id in self._fault_active and fault_id not in self._fault_response_s:
                    self._fault_response_s[fault_id] = max(0.0, now - started_s)
        for fault_id, recovered_s in self._fault_recovered_s.items():
            if fault_id in self._fault_recovery_response_s:
                continue
            recovered_control = not meaningful_safety
            recovered_route = route_deviation_m is None or abs(float(route_deviation_m)) <= 1.0
            if recovered_control and recovered_route:
                self._fault_recovery_response_s[fault_id] = max(0.0, now - recovered_s)
        if (
            self._slow_command_s is not None
            and self._slow_command_speed_mps is not None
            and self._speed_drop_latency_s is None
            and speed < self._slow_command_speed_mps - 0.1
        ):
            self._speed_drop_latency_s = max(0.0, now - self._slow_command_s)
        if self._restart_route_progress_m is not None:
            self._restart_displacement_m = max(
                0.0, self._last_route_progress_m - self._restart_route_progress_m,
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
                previous_speed = self._actor_speed_mps.get(actor_id, math.inf)
                if isinstance(action, Mapping) and str(action.get("type", "")).lower() == "set_speed":
                    self._actor_speed_mps[actor_id] = max(0.0, float(action.get("target_speed_mps", 0.0)))
                if "state" in event:
                    self._traffic_light_state[actor_id] = str(event["state"]).upper()
                self._actor_event_index[actor_id] = index + 1
                self._actor_event_count += 1
                self._actor_event_time_s[actor_id] = float(elapsed_s)
                phase_id = str(event.get("phase_id", ""))
                if phase_id:
                    self.note_phase_completed(phase_id)
                self.note_actor_trigger(actor_id, elapsed_s=elapsed_s)
                distances = context.get("actor_distances_m", {})
                if isinstance(distances, Mapping) and actor_id in distances:
                    action = event.get("action", {})
                    target_speed = action.get("target_speed_mps") if isinstance(action, Mapping) else None
                    if type(target_speed) in (int, float) and float(target_speed) < previous_speed:
                        self._lead_brake_trigger_distance_m = float(distances[actor_id])
        return {
            "target_speed_mps": self._actor_speed_mps[actor_id],
            "traffic_light_state": self._traffic_light_state[actor_id],
            "event_index": self._actor_event_index.get(actor_id, 0),
            "elapsed_since_event_s": (
                None
                if actor_id not in self._actor_event_time_s
                else max(0.0, float(elapsed_s) - self._actor_event_time_s[actor_id])
            ),
        }

    def evidence(self) -> dict[str, object]:
        emergency_events: dict[str, dict[str, float | None]] = {}
        for actor_id, danger_s in sorted(self._actor_trigger_time_s.items()):
            control_s = self._actor_control_effect_time_s.get(actor_id)
            emergency_events[actor_id] = {
                "danger_timestamp_s": danger_s,
                "perception_timestamp_s": self._actor_perception_time_s.get(actor_id),
                "decision_timestamp_s": self._actor_decision_time_s.get(actor_id),
                "safety_override_timestamp_s": self._actor_safety_override_time_s.get(actor_id),
                "control_effect_timestamp_s": control_s,
                "recovery_timestamp_s": self._actor_recovery_time_s.get(actor_id),
                "hold_duration_s": (
                    None
                    if control_s is None or actor_id not in self._actor_recovery_time_s
                    else max(0.0, self._actor_recovery_time_s[actor_id] - control_s)
                ),
                "response_ms": (
                    None if control_s is None else max(0.0, control_s - danger_s) * 1000.0
                ),
            }
        response_samples_ms = [
            float(event["response_ms"])
            for event in emergency_events.values()
            if event["response_ms"] is not None
        ]
        return {
            "qwen_request_count": self._qwen_requests,
            "submitted_command_ids": list(self._submitted_command_ids),
            "terminal_command_ids": sorted(self._qwen_terminals),
            "qwen_status_counts": dict(self._qwen_status_counts),
            "successful_terminal_s": dict(self._successful_terminal_s),
            "fault_started_ids": sorted(self._fault_started_s),
            "fault_recovered_ids": sorted(self._fault_recovered),
            "fault_response_s": dict(self._fault_response_s),
            "fault_recovery_response_s": dict(self._fault_recovery_response_s),
            "lane_change_count": self._lane_change_count,
            "initial_lane_id": self._initial_lane_id,
            "final_lane_id": self._last_lane_id,
            "resource_growth_mb": max(0.0, self._rss_peak_mb - self._rss_start_mb),
            "confirmation_command_count": self._confirmation_commands,
            "qwen_behaviors": list(self._qwen_behaviors),
            "qwen_target_actor_ids": sorted(self._qwen_target_ids),
            "qwen_target_speeds_kph": list(self._qwen_target_speeds_kph),
            "minimum_actor_distances_m": dict(sorted(self._minimum_actor_distances_m.items())),
            "qwen_outcomes": list(self._qwen_outcomes),
            "qwen_resolution_reasons": list(self._qwen_resolution_reasons),
            "qwen_stale_result_count": self._qwen_stale_results,
            "qwen_stale_result_applied_count": self._qwen_stale_results_applied,
            "late_result_applied_count": self._qwen_late_results_applied,
            "qwen_invalid_result_count": self._qwen_invalid_results,
            "qwen_timeout_count": self._qwen_timeouts,
            "vehicle_advance_command_count": self._vehicle_advance_commands,
            "current_plan_command_index": self._latest_applied_command_index,
            "qwen_applied_s": list(self._qwen_applied_s),
            "max_speed_mps": self._max_speed_mps,
            "min_speed_after_command_mps": self._min_speed_after_command_mps,
            "final_speed_mps": self._last_speed_mps,
            "requested_speed_kph": self._requested_speed_kph,
            "traffic_light_states": list(self._traffic_light_states),
            "pre_red_max_speed_mps": self._pre_red_max_speed_mps,
            "minimum_red_stop_line_clearance_m": self._minimum_red_stop_line_clearance_m,
            "stopped_on_red_before_stop_line": self._stopped_on_red_before_stop_line,
            "completed_phase_ids": sorted(self._completed_phase_ids),
            "target_lane_occupied_count": self._target_lane_occupied_count,
            "mission_route_restore_count": self._mission_route_restore_count,
            "restart_displacement_m": self._restart_displacement_m,
            "final_lateral_offset_abs_m": self._last_lateral_offset_m,
            "lead_brake_trigger_distance_m": self._lead_brake_trigger_distance_m,
            "actor_trigger_ids": sorted(self._actor_trigger_ids),
            "emergency_events": emergency_events,
            "emergency_response_samples_ms": response_samples_ms,
            "emergency_response_p95_ms": self._percentile(response_samples_ms, 0.95),
            "emergency_response_max_ms": max(response_samples_ms, default=None),
            "scenario_event_count": self._actor_event_count,
            "runtime_event_count": (
                self._actor_event_count
                + len(self._fault_started_s)
                + len(self._fault_recovered_s)
            ),
            "first_brake_s": self._first_brake_s,
            "first_qwen_plan_s": self._first_qwen_plan_s,
            "safety_reasons": sorted(self._safety_reasons),
            "safety_first_s": self._safety_first_s,
            "last_route_deviation_m": self._last_route_deviation_m,
            "max_route_deviation_m": self._max_route_deviation_m,
            "collision_seen": self._collision_seen,
            "degraded_mode_entered": self._degraded_mode_entered,
            "speed_drop_latency_s": self._speed_drop_latency_s,
        }

    @staticmethod
    def _percentile(values: Sequence[float], quantile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(float(value) for value in values)
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * quantile
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    def evaluate(
        self,
        proposed: Mapping[str, Any],
        *,
        expected_command_count: int,
        safety_reasons: Sequence[str] = (),
        oracle: Mapping[str, Any] | None = None,
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
        oracle_contract = {} if oracle is None else oracle
        if not isinstance(oracle_contract, Mapping):
            raise TypeError("extensions.oracle must be an object")
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
                actual = int(evidence[key])
                add(key, actual == int(required), actual, required)
            elif key == "all_commands_must_have_terminal_status":
                actual = all(command_id in terminals for command_id in submitted)
                add(key, required is not True or actual, actual, True)
            elif key == "must_recover_after_fault":
                recovered_responses = set(evidence["fault_recovery_response_s"])
                actual = (
                    bool(faults_started)
                    and faults_started.issubset(faults_recovered)
                    and faults_started.issubset(recovered_responses)
                )
                add(key, required is not True or actual, actual, True)
            elif key == "post_recovery_command_succeeds":
                recovered_at = max(self._fault_recovered_s.values(), default=None)
                actual = recovered_at is not None and any(
                    float(item) >= recovered_at
                    for item in evidence["successful_terminal_s"].values()
                )
                add(key, required is not True or actual, actual, True)
            elif key == "max_fault_response_s":
                samples = list(evidence["fault_response_s"].values())
                actual = max(samples) if samples else None
                add(
                    key,
                    actual is not None
                    and actual <= float(required) + TIME_COMPARISON_EPSILON_S,
                    actual,
                    required,
                )
            elif key == "recovery_deadline_s":
                samples = list(evidence["fault_recovery_response_s"].values())
                actual = max(samples) if samples else None
                add(key, actual is not None and actual <= float(required), actual, required)
            elif key == "speed_drop_deadline_s":
                actual = evidence["speed_drop_latency_s"]
                add(key, actual is not None and actual <= float(required), actual, required)
            elif key == "max_resource_growth_mb":
                actual = float(evidence["resource_growth_mb"])
                add(key, actual <= float(required), actual, required)
            elif key == "must_return_to_original_lane":
                actual = (
                    int(evidence["mission_route_restore_count"]) > 0
                    or (
                        evidence["initial_lane_id"] == evidence["final_lane_id"]
                        and int(evidence["lane_change_count"]) >= 2
                    )
                )
                add(key, required is not True or actual, actual, True)
            elif key == "minimum_actor_distances_m":
                if not isinstance(required, Mapping):
                    raise TypeError("minimum_actor_distances_m must be an object")
                actual_distances = evidence["minimum_actor_distances_m"]
                checks_by_actor = {
                    str(actor_id): (
                        actual_distances.get(str(actor_id)) is not None
                        and float(actual_distances[str(actor_id)]) >= float(minimum_m)
                    )
                    for actor_id, minimum_m in required.items()
                }
                add(
                    key,
                    bool(checks_by_actor) and all(checks_by_actor.values()),
                    {
                        actor_id: actual_distances.get(actor_id)
                        for actor_id in checks_by_actor
                    },
                    dict(required),
                )
            elif key == "maximum_route_deviation_m":
                actual = float(evidence["max_route_deviation_m"])
                add(key, actual <= float(required), actual, required)
            elif key == "must_not_change_lane":
                actual = int(evidence["lane_change_count"]) == 0
                add(key, required is not True or actual, actual, True)
            elif key == "expected_target_actor_id":
                add(key, str(required) in target_ids, sorted(target_ids), required)
            elif key == "pedestrian_trigger_actor_id":
                actual_ids = set(evidence["actor_trigger_ids"])
                add(key, str(required) in actual_ids, sorted(actual_ids), required)
            elif key == "required_emergency_event_ids":
                required_ids = {str(item) for item in required}
                actual_events = evidence["emergency_events"]
                actual_ids = set(actual_events)
                complete_ids = {
                    actor_id for actor_id, event in actual_events.items()
                    if all(event.get(field) is not None for field in (
                        "danger_timestamp_s", "perception_timestamp_s",
                        "decision_timestamp_s", "safety_override_timestamp_s",
                        "control_effect_timestamp_s", "response_ms",
                    ))
                }
                add(
                    key,
                    required_ids.issubset(actual_ids) and required_ids.issubset(complete_ids),
                    {"observed": sorted(actual_ids), "complete": sorted(complete_ids)},
                    sorted(required_ids),
                )
            elif key == "required_emergency_recovery_ids":
                required_ids = {str(item) for item in required}
                actual_ids = set(self._actor_recovery_time_s)
                add(
                    key,
                    required_ids.issubset(actual_ids),
                    sorted(actual_ids),
                    sorted(required_ids),
                )
            elif key in {"emergency_response_p95_max_ms", "emergency_response_absolute_max_ms"}:
                evidence_key = (
                    "emergency_response_p95_ms"
                    if key == "emergency_response_p95_max_ms"
                    else "emergency_response_max_ms"
                )
                actual = evidence[evidence_key]
                add(
                    key,
                    actual is not None and float(actual) <= float(required),
                    actual,
                    required,
                )
            elif key == "target_binding_correct":
                expected_target = oracle_contract.get("expected_target_actor_id")
                actual = (
                    str(expected_target) in target_ids
                    if expected_target is not None
                    else len(target_ids) == 1
                )
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
            elif key == "pre_red_max_speed_min_mps":
                actual = float(evidence["pre_red_max_speed_mps"])
                add(key, actual >= float(required), actual, required)
            elif key == "minimum_red_stop_line_clearance_m":
                actual = evidence["minimum_red_stop_line_clearance_m"]
                add(
                    key,
                    actual is not None and float(actual) >= float(required),
                    actual,
                    required,
                )
            elif key == "must_stop_on_red_before_stop_line":
                actual = bool(evidence["stopped_on_red_before_stop_line"])
                clearance = evidence["minimum_red_stop_line_clearance_m"]
                passed = (
                    required is not True
                    or (
                        actual
                        and clearance is not None
                        and float(clearance) >= 0.0
                    )
                )
                add(key, passed, actual, True)
            elif key == "qwen_target_speed_max_kph":
                speeds = list(evidence["qwen_target_speeds_kph"])
                actual = max(speeds) if speeds else None
                add(key, actual is not None and actual <= float(required), actual, required)
            elif key == "sustained_speed_max_kph":
                actual = float(evidence["max_speed_mps"]) * 3.6
                add(key, actual <= float(required), actual, required)
            elif key == "max_speed_overshoot_kph":
                requested = evidence["requested_speed_kph"]
                actual = (
                    None if requested is None
                    else max(0.0, float(evidence["max_speed_mps"]) * 3.6 - float(requested))
                )
                add(key, actual is not None and actual <= float(required), actual, required)
            elif key == "expected_phase_count":
                phase_plan = self.extensions.get("phase_plan", ())
                actual = len(phase_plan) if isinstance(phase_plan, Sequence) and not isinstance(phase_plan, (str, bytes)) else 0
                add(key, actual == int(required), actual, required)
            elif key == "vehicle_advance_command_count":
                actual = int(evidence["vehicle_advance_command_count"])
                add(key, actual == int(required), actual, required)
            elif key == "current_plan_command_index":
                actual = evidence["current_plan_command_index"]
                add(key, actual == int(required), actual, required)
            elif key == "all_phases_must_complete":
                phase_plan = self.extensions.get("phase_plan", ())
                required_phases = {
                    str(item) for item in phase_plan
                } if isinstance(phase_plan, Sequence) and not isinstance(phase_plan, (str, bytes)) else set()
                actual = bool(required_phases) and required_phases.issubset(
                    set(evidence["completed_phase_ids"])
                )
                add(key, required is not True or actual, actual, True)
            elif key == "qwen_calls_per_frame":
                # Qwen is event-driven: every counted request is tied to one
                # submitted voice command. Any excess is a forbidden frame poll.
                actual = max(0, request_count - len(submitted))
                add(key, actual <= int(required), actual, required)
            elif key in {"qwen_timeout_count", "qwen_invalid_result_count"}:
                actual = int(evidence[key])
                add(key, actual >= int(required), actual, required)
            elif key == "timeout_event_log_required":
                actual = int(evidence["qwen_timeout_count"]) > 0
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
                final_speed = float(evidence["final_speed_mps"])
                first_brake = evidence["first_brake_s"]
                first_plan = evidence["first_qwen_plan_s"]
                reasons = {
                    str(item).upper()
                    for item in (*evidence["safety_reasons"], *safety_reasons)
                    if str(item).upper() not in {"", "NONE", "PERCEPTION_STARTUP_GRACE"}
                }
                outcomes = {str(item).upper() for item in evidence["qwen_outcomes"]}
                resolution_reasons = {
                    str(item).upper() for item in evidence["qwen_resolution_reasons"]
                }
                if key == "brake_before_qwen_ready":
                    actual = first_brake is not None and (first_plan is None or first_brake <= first_plan)
                elif key == "disconnect_fail_closed":
                    actual = any("DISCONNECT" in item for item in resolution_reasons) and first_brake is not None
                elif key == "emergency_command_preempts_normal_queue":
                    intents = [self._command_intent_by_id.get(item, "") for item in submitted]
                    emergency = [i for i, item in enumerate(intents) if item in {"STOP", "EMERGENCY_STOP"}]
                    actual = (
                        bool(emergency)
                        and emergency[-1] == len(intents) - 1
                        and submitted[emergency[-1]] in terminals
                    )
                elif key == "first_version_requires_stop_not_detour":
                    detour_behaviors = {
                        "AVOID_OBSTACLE", "CHANGE_LANE",
                        "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT", "PULL_OVER",
                    }
                    actual = (
                        bool(behaviors)
                        and behaviors.isdisjoint(detour_behaviors)
                        and int(evidence["lane_change_count"]) == 0
                        and final_speed <= 0.3
                    )
                elif key == "must_enter_degraded_mode":
                    actual = bool(evidence["degraded_mode_entered"])
                elif key == "must_not_continue_route_deviation":
                    peak = float(evidence["max_route_deviation_m"])
                    final_deviation = float(evidence["last_route_deviation_m"])
                    actual = peak > 0.0 and (
                        final_speed <= 0.3
                        or (
                            final_deviation < peak
                            and final_deviation <= 1.0
                        )
                    )
                elif key == "must_not_pass_between_obstacles":
                    actual = not bool(evidence["collision_seen"]) and final_speed <= 0.3
                elif key == "must_not_select_unsafe_pull_over_point":
                    actual = "PULL_OVER" not in behaviors and bool(behaviors)
                elif key == "must_not_stop_without_environment_risk":
                    actual = final_speed > 0.3 or bool(reasons)
                elif key == "must_respect_map_speed_limit":
                    speed_policy = self.extensions.get("speed_policy", {})
                    limit = speed_policy.get("scenario_limit_kph") if isinstance(speed_policy, Mapping) else None
                    actual = limit is not None and float(evidence["max_speed_mps"]) * 3.6 <= float(limit) + 0.5
                elif key == "must_stop_if_recovery_fails":
                    recovery_succeeded = (
                        float(evidence["last_route_deviation_m"]) <= 1.0
                    )
                    actual = bool(faults_started) and (
                        recovery_succeeded or final_speed <= 0.3
                    )
                elif key == "must_stop_when_perception_insufficient":
                    actual = final_speed <= 0.3 and any("PERCEPTION" in item for item in reasons)
                elif key == "qwen_must_not_override_safety_stop":
                    safety_first = evidence["safety_first_s"]
                    recovered_at = max(self._fault_recovered_s.values(), default=None)
                    actual = (
                        bool(reasons)
                        and safety_first is not None
                        and first_brake is not None
                        and not any(
                            float(item) >= float(safety_first)
                            and (
                                recovered_at is None
                                or float(item) < float(recovered_at)
                            )
                            for item in evidence["qwen_applied_s"]
                        )
                    )
                elif key == "rebind_requires_fresh_perception":
                    actual = int(evidence["qwen_stale_result_applied_count"]) == 0 and any(
                        "STALE" in item or "TIMEOUT" in item
                        for item in resolution_reasons
                    )
                elif key == "unsafe_qwen_result_must_be_overridden":
                    actual = bool(reasons) and final_speed <= 0.3
                elif key == "conservative_speed_required":
                    requested = evidence["requested_speed_kph"]
                    target_speeds = list(evidence["qwen_target_speeds_kph"])
                    actual = bool(behaviors.intersection({"SLOW_DOWN", "STOP", "HOLD"})) or (
                        bool(target_speeds)
                        and max(target_speeds) <= (
                            float(requested) if requested is not None else 15.0
                        )
                    )
                else:
                    actual = False
                add(key, required is not True or actual, actual, True)
            elif key in {
                "target_lane_occupied_count", "target_lane_occupied_min_count",
                "restart_displacement_m", "final_lateral_offset_abs_max_m",
                "lead_brake_trigger_distance_m",
            }:
                evidence_key = {
                    "target_lane_occupied_count": "target_lane_occupied_count",
                    "target_lane_occupied_min_count": "target_lane_occupied_count",
                    "restart_displacement_m": "restart_displacement_m",
                    "final_lateral_offset_abs_max_m": "final_lateral_offset_abs_m",
                    "lead_brake_trigger_distance_m": "lead_brake_trigger_distance_m",
                }[key]
                actual = evidence[evidence_key]
                if key in {"restart_displacement_m", "target_lane_occupied_min_count"}:
                    passed = actual is not None and float(actual) >= float(required)
                else:
                    passed = actual is not None and float(actual) <= float(required)
                add(key, passed, actual, required)
            elif key == "allowed_outcomes":
                allowed = {str(item).upper() for item in required}
                actual_set = set(behaviors)
                for item in evidence["qwen_outcomes"]:
                    normalized = str(item).upper()
                    if "REJECT" in normalized or "ERROR" in normalized:
                        actual_set.add("REJECT")
                clipped_to_limit = False
                for item in evidence["qwen_resolution_reasons"]:
                    if "CLIP" in str(item).upper() or "SPEED_LIMIT" in str(item).upper():
                        clipped_to_limit = True
                speed_policy = self.extensions.get("speed_policy", {})
                limit_kph = (
                    speed_policy.get("scenario_limit_kph")
                    if isinstance(speed_policy, Mapping)
                    else None
                )
                requested_kph = evidence["requested_speed_kph"]
                target_speeds = list(evidence["qwen_target_speeds_kph"])
                if (
                    type(limit_kph) in (int, float)
                    and not isinstance(limit_kph, bool)
                    and requested_kph is not None
                    and float(requested_kph) > float(limit_kph) + 0.5
                    and bool(target_speeds)
                    and max(float(item) for item in target_speeds) <= float(limit_kph) + 0.5
                ):
                    clipped_to_limit = True
                if clipped_to_limit:
                    actual_set.discard("SET_SPEED")
                    actual_set.add("CLIP_TO_LIMIT")
                add(key, bool(actual_set) and actual_set.issubset(allowed), sorted(actual_set), sorted(allowed))
            elif key == "lane_change_rejection_reason_required":
                explicit_tokens = (
                    "NO_SAFE_ADJACENT_LANE",
                    "TARGET_LANE_OCCUPIED",
                    "ADJACENT_LANE_OCCUPIED",
                    "LANE_CHANGE_REJECT",
                    "UNSAFE_LANE_CHANGE",
                    "LANE_GAP_UNSAFE",
                )
                actual = [
                    str(item).upper()
                    for item in (*evidence["qwen_resolution_reasons"], *safety_reasons)
                    if any(token in str(item).upper() for token in explicit_tokens)
                ]
                add(key, bool(actual), actual, required)
            else:
                add(key, False, None, required)

        expected_behaviors = oracle_contract.get("expected_behaviors")
        valid_model_output_expected = not any(
            int(proposed.get(key, 0) or 0) > 0
            for key in ("qwen_timeout_count", "qwen_invalid_result_count")
        )
        if expected_behaviors is not None and valid_model_output_expected:
            if not isinstance(expected_behaviors, Sequence) or isinstance(
                expected_behaviors, (str, bytes),
            ):
                raise TypeError("extensions.oracle.expected_behaviors must be a list")
            allowed = {str(item).upper() for item in expected_behaviors}
            requires_full_coverage = (
                expected_command_count > 1
                and len(allowed) == expected_command_count
            )
            add(
                "oracle_expected_behaviors",
                bool(behaviors)
                and behaviors.issubset(allowed)
                and (not requires_full_coverage or allowed.issubset(behaviors)),
                sorted(behaviors),
                sorted(allowed),
            )
        expected_target = oracle_contract.get("expected_target_actor_id")
        if (
            expected_target is not None
            and valid_model_output_expected
            and "expected_target_actor_id" not in proposed
        ):
            add(
                "oracle_expected_target_actor_id",
                str(expected_target) in target_ids,
                sorted(target_ids),
                expected_target,
            )
        failed = [item["key"] for item in checks if item["status"] == "FAIL"]
        return {"passed": not failed, "checks": checks, "failed_keys": failed, "evidence": evidence}


__all__ = [
    "ExtensionFrameState",
    "IMPLEMENTED_RUNTIME_REQUIREMENTS",
    "ScenarioExtensionRuntime",
    "missing_runtime_requirements",
]
