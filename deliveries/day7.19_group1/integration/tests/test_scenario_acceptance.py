from __future__ import annotations

import json
from pathlib import Path

from integration.scenario_acceptance import evaluate_expected


SCENARIO_ROOT = Path(__file__).resolve().parents[2] / "scenarios"


def _passing_metrics(expected: dict[str, object]) -> dict[str, object]:
    initial_offset = float(expected.get("initial_offset_y_m", 0.0))
    final_speed = float(expected.get("target_speed_kph", 0.0)) / 3.6
    reasons = [str(item) for item in expected.get("expected_reason_contains", ["EXPECTED_EVENT"])]
    return {
        "carla_started": True,
        "spawned_ego": True,
        "called_B": True,
        "called_C": True,
        "called_D": True,
        "logs_generated": True,
        "route_finished": True,
        "configured_route_deviation_trigger_m": float(expected.get("route_deviation_trigger_m", 3.0)),
        "commands_in_order": True,
        "final_control_all_finite": True,
        "cross_track_error_decreased": True,
        "collision_count": 0,
        "route_deviation_count": 1 if expected.get("expected_route_deviation_event") is True else 0,
        "route_deviation_event_seen": expected.get("expected_route_deviation_event") is True,
        "red_light_violation_count": 0,
        "max_abs_cross_track_error_m": abs(initial_offset),
        "mean_abs_cross_track_error_m": 0.0,
        "final_abs_cross_track_error_m": 0.0,
        "initial_cross_track_error_m": initial_offset,
        "max_abs_steer": 0.0,
        "max_steer_rate_per_s": 0.0,
        "max_speed_mps": max(final_speed, 1.0),
        "final_speed_mps": final_speed,
        "min_gap_m": 10.0,
        "duration_s": 120.0,
        "final_lateral_shift_m": float(expected.get("final_lateral_shift_m", 0.0)),
        "turn_direction": str(expected.get("turn_direction", "STRAIGHT")),
        "safety_override_frames": 1,
        "safety_reasons": reasons,
        "event_count": 1,
        "emergency_brake_seen": True,
        "final_control_overlap_count": 0,
        "stopped_before_stop_line": True,
        "safety_priority_observed": True,
        "stop_latency_s": 0.5,
        "speed_before_decrease_marker_mps": 3.0,
        "speed_after_decrease_marker_mps": 1.0,
    }


def test_every_repository_expected_key_is_supported() -> None:
    for path in sorted(SCENARIO_ROOT.rglob("*.json")):
        if path.name in {"index.json", "scenario_schema.json"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = data.get("expected", {})
        report = evaluate_expected(expected, _passing_metrics(expected))
        assert report["unsupported_keys"] == [], data["scenario_id"]
        assert report["passed"] is True, (data["scenario_id"], report["failed_keys"])


def test_metric_violation_and_unknown_key_fail_closed() -> None:
    report = evaluate_expected(
        {"max_cross_track_error_m": 0.5, "future_rule": True},
        {"max_abs_cross_track_error_m": 0.8},
    )
    assert report["passed"] is False
    assert report["failed_keys"] == ["max_cross_track_error_m", "future_rule"]
    assert report["unsupported_keys"] == ["future_rule"]
