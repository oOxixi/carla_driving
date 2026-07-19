"""Strict evaluation of scenario ``expected`` contracts.

Every declared key produces an auditable PASS/FAIL check. Unknown keys fail
closed so adding a scenario requirement can never silently create a false
positive.
"""
from __future__ import annotations

import math
from typing import Any, Mapping


def _number(value: object) -> float | None:
    if type(value) not in (int, float) or isinstance(value, bool):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def evaluate_expected(expected: Mapping[str, object], metrics: Mapping[str, object]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(key: str, passed: bool, actual: object, required: object, detail: str) -> None:
        checks.append({
            "key": key,
            "status": "PASS" if passed else "FAIL",
            "actual": actual,
            "required": required,
            "detail": detail,
        })

    def maximum(key: str, metric: str) -> None:
        actual, required = _number(metrics.get(metric)), _number(expected[key])
        add(key, actual is not None and required is not None and actual <= required,
            actual, required, f"{metric} must be <= expected maximum")

    def minimum(key: str, metric: str) -> None:
        actual, required = _number(metrics.get(metric)), _number(expected[key])
        add(key, actual is not None and required is not None and actual >= required,
            actual, required, f"{metric} must be >= expected minimum")

    bool_metrics = {
        "must_start_carla": "carla_started",
        "must_spawn_ego": "spawned_ego",
        "must_call_B": "called_B",
        "must_call_C": "called_C",
        "must_call_D": "called_D",
        "must_generate_logs": "logs_generated",
        "must_finish_route": "route_finished",
        "must_execute_commands_in_order": "commands_in_order",
        "final_control_must_be_finite": "final_control_all_finite",
        "cross_track_error_should_decrease": "cross_track_error_decreased",
    }
    max_metrics = {
        "max_cross_track_error_m": "max_abs_cross_track_error_m",
        "max_allowed_cross_track_error_m": "max_abs_cross_track_error_m",
        "mean_cross_track_error_m": "mean_abs_cross_track_error_m",
        "final_cross_track_error_m": "final_abs_cross_track_error_m",
        "max_abs_steer": "max_abs_steer",
        "max_steer_rate_per_s": "max_steer_rate_per_s",
        "max_speed_mps": "max_speed_mps",
        "stop_within_s": "stop_latency_s",
    }
    min_metrics = {
        "min_front_gap_m": "min_gap_m",
        "min_run_time_s": "duration_s",
    }

    supported: set[str] = set()
    for key, metric in bool_metrics.items():
        if key in expected:
            supported.add(key)
            required = expected[key] is True
            actual = metrics.get(metric) is True
            add(key, (not required) or actual, actual, expected[key], f"requires {metric}")
    for key, metric in max_metrics.items():
        if key in expected:
            supported.add(key)
            maximum(key, metric)
    for key, metric in min_metrics.items():
        if key in expected:
            supported.add(key)
            minimum(key, metric)

    simple_no_event = {
        "must_no_collision": "collision_count",
        "must_no_pedestrian_collision": "collision_count",
        "must_no_route_deviation": "route_deviation_count",
    }
    for key, metric in simple_no_event.items():
        if key in expected:
            supported.add(key)
            actual = int(metrics.get(metric, 0) or 0)
            add(key, expected[key] is not True or actual == 0, actual, 0, f"{metric} must be zero")

    if "initial_offset_y_m" in expected:
        supported.add("initial_offset_y_m")
        actual, required = _number(metrics.get("initial_cross_track_error_m")), _number(expected["initial_offset_y_m"])
        passed = actual is not None and required is not None and abs(actual - required) <= 0.35
        add("initial_offset_y_m", passed, actual, required, "initial signed CTE tolerance is 0.35 m")

    if "final_lateral_shift_m" in expected:
        supported.add("final_lateral_shift_m")
        actual, required = _number(metrics.get("final_lateral_shift_m")), _number(expected["final_lateral_shift_m"])
        passed = actual is not None and required is not None and abs(actual - required) <= 0.75
        add("final_lateral_shift_m", passed, actual, required, "signed lateral-shift tolerance is 0.75 m")

    if "turn_direction" in expected:
        supported.add("turn_direction")
        actual = str(metrics.get("turn_direction", "UNKNOWN")).upper()
        required = str(expected["turn_direction"]).upper()
        add("turn_direction", actual == required, actual, required, "net ego yaw change determines turn direction")

    if "expected_safety_override" in expected:
        supported.add("expected_safety_override")
        actual = int(metrics.get("safety_override_frames", 0) or 0)
        add("expected_safety_override", expected["expected_safety_override"] is not True or actual > 0,
            actual, "> 0 frames", "a safety takeover must be observed")

    if "expected_safety_override_allowed" in expected:
        supported.add("expected_safety_override_allowed")
        actual = int(metrics.get("safety_override_frames", 0) or 0)
        add("expected_safety_override_allowed", True, actual, "allowed", "permission only; takeover is not required")

    if "expected_reason_contains" in expected:
        supported.add("expected_reason_contains")
        reasons = [str(item) for item in metrics.get("safety_reasons", [])]
        tokens = [str(item).lower() for item in expected["expected_reason_contains"]]
        joined = " ".join(reasons).lower()
        add("expected_reason_contains", bool(tokens) and any(token in joined for token in tokens),
            reasons, expected["expected_reason_contains"], "at least one expected token must appear")

    if "expected_route_deviation_event" in expected:
        supported.add("expected_route_deviation_event")
        actual = metrics.get("route_deviation_event_seen") is True
        add("expected_route_deviation_event", expected["expected_route_deviation_event"] is not True or actual,
            actual, True, "an intentional D route-recovery event must be observed")

    if "route_deviation_trigger_m" in expected:
        supported.add("route_deviation_trigger_m")
        actual = _number(metrics.get("configured_route_deviation_trigger_m"))
        required = _number(expected["route_deviation_trigger_m"])
        add("route_deviation_trigger_m", actual is not None and required is not None and abs(actual - required) <= 1e-9,
            actual, required, "D must use the scenario-declared route recovery trigger")

    if "must_generate_event" in expected:
        supported.add("must_generate_event")
        actual = int(metrics.get("event_count", 0) or 0)
        add("must_generate_event", expected["must_generate_event"] is not True or actual > 0,
            actual, "> 0 events", "safety/event evidence must exist")

    if "must_emergency_brake" in expected:
        supported.add("must_emergency_brake")
        actual = metrics.get("emergency_brake_seen") is True
        add("must_emergency_brake", expected["must_emergency_brake"] is not True or actual,
            actual, True, "a full emergency brake frame must be observed")

    if "final_control_no_throttle_brake_overlap" in expected:
        supported.add("final_control_no_throttle_brake_overlap")
        actual = int(metrics.get("final_control_overlap_count", 0) or 0)
        add("final_control_no_throttle_brake_overlap", actual == 0, actual, 0,
            "applied final controls must never overlap throttle and brake")

    if "must_stop_before_stop_line" in expected:
        supported.add("must_stop_before_stop_line")
        actual = metrics.get("stopped_before_stop_line") is True
        add("must_stop_before_stop_line", expected["must_stop_before_stop_line"] is not True or actual,
            actual, True, "vehicle must stop without a red-light violation")

    if "safety_priority_over_command" in expected:
        supported.add("safety_priority_over_command")
        actual = metrics.get("safety_priority_observed") is True
        add("safety_priority_over_command", expected["safety_priority_over_command"] is not True or actual,
            actual, True, "D must override the conflicting command and stop")

    if "must_stop_after_command" in expected or "must_stop_after_last_command" in expected:
        for key in ("must_stop_after_command", "must_stop_after_last_command"):
            if key not in expected:
                continue
            supported.add(key)
            threshold = float(expected.get("stop_speed_threshold_mps", 0.3))
            actual_speed = _number(metrics.get("final_speed_mps"))
            stopped = actual_speed is not None and actual_speed <= threshold and metrics.get("stop_latency_s") is not None
            add(key, expected[key] is not True or stopped, actual_speed, f"<= {threshold} m/s",
                "vehicle must stop after the applicable command")

    if "stop_speed_threshold_mps" in expected:
        supported.add("stop_speed_threshold_mps")
        maximum("stop_speed_threshold_mps", "final_speed_mps")

    if "target_speed_kph" in expected:
        supported.add("target_speed_kph")
        actual = _number(metrics.get("final_speed_mps"))
        actual_kph = None if actual is None else actual * 3.6
        required = float(expected["target_speed_kph"])
        tolerance = float(expected.get("speed_tolerance_kph", 0.0))
        add("target_speed_kph", actual_kph is not None and abs(actual_kph - required) <= tolerance,
            actual_kph, {"target": required, "tolerance": tolerance}, "final speed must meet target tolerance")

    if "speed_tolerance_kph" in expected:
        supported.add("speed_tolerance_kph")
        add("speed_tolerance_kph", "target_speed_kph" in expected, expected["speed_tolerance_kph"],
            "paired with target_speed_kph", "evaluated by target_speed_kph check")

    if "speed_should_decrease_after_s" in expected:
        supported.add("speed_should_decrease_after_s")
        before = _number(metrics.get("speed_before_decrease_marker_mps"))
        after = _number(metrics.get("speed_after_decrease_marker_mps"))
        passed = before is not None and after is not None and after < before - 0.1
        add("speed_should_decrease_after_s", passed, {"before": before, "after": after},
            expected["speed_should_decrease_after_s"], "speed after marker must decrease by more than 0.1 m/s")

    unsupported = sorted(set(expected) - supported)
    for key in unsupported:
        add(key, False, None, expected[key], "unsupported expected key; failing closed")
    failed = [item["key"] for item in checks if item["status"] == "FAIL"]
    return {
        "passed": not failed,
        "checks": checks,
        "failed_keys": failed,
        "unsupported_keys": unsupported,
        "check_count": len(checks),
    }


__all__ = ["evaluate_expected"]
