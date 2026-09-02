from __future__ import annotations

from tools.validate_s3_member4_evidence import SCENARIO_ID, validate_evidence


def _passing_evidence():
    command_ids = [f"scenario_cmd_{index:03d}" for index in range(4)]
    records = [{
        "record_type": "run_start",
        "config": {
            "seed": 20260303,
            "code_version": "abc123",
            "config_path": "scenarios/official_competition/S3_extreme_emergency_6km.json",
            "qwen_model": "Qwen/Qwen2.5-VL-7B-Instruct",
        },
    }]
    records.extend({
        "record_type": "command",
        "command_id": command_id,
        "disposition": "SCENARIO_FAST" if index >= 2 else "SCENARIO_SLOW_PENDING",
    } for index, command_id in enumerate(command_ids))
    records.extend({
        "record_type": "qwen_trajectory",
        "request_id": f"request-{index}",
        "latency": {"sensor_to_trajectory_ms": 80.0},
    } for index in range(2))
    records.append({
        "record_type": "frame",
        "latency": {"sensor_to_control_ms": 12.0},
        "longitudinal": {"risk": {"ttc_s": 1.2}},
    })
    extension_checks = [
        {"key": key, "status": "PASS", "actual": True}
        for key in (
            "expected_phase_count", "all_phases_must_complete",
            "required_emergency_event_ids", "emergency_response_p95_max_ms",
            "emergency_response_absolute_max_ms", "required_emergency_recovery_ids",
        )
    ]
    events = {
        actor_id: {
            "danger_timestamp_s": 10.0,
            "perception_timestamp_s": 10.05,
            "decision_timestamp_s": 10.05,
            "safety_override_timestamp_s": 10.05,
            "control_effect_timestamp_s": 10.05,
            "recovery_timestamp_s": 16.05,
            "hold_duration_s": 6.0,
            "response_ms": 50.0,
        }
        for actor_id in ("cut_in_vehicle", "emergency_pedestrian")
    }
    summary = {
        "scenario_id": SCENARIO_ID,
        "status": "SUCCEEDED",
        "collision_count": 0,
        "lane_invasion_count": 0,
        "red_light_violation_count": 0,
        "serious_route_deviation": 0,
        "safety_override_frames": 2,
        "final_speed_mps": 0.0,
        "command_terminal_statuses": {command_id: "SUCCEEDED" for command_id in command_ids},
        "acceptance": {"metrics": {
            "emergency_brake_seen": True,
            "qwen_acceptance": {
                "passed": True,
                "failures": [],
                "observed": {
                    "qwen_calls": 2,
                    "routes": ["QWEN_PLAN", "QWEN_PLAN", "FAST_LOCAL", "FAST_LOCAL"],
                },
            },
            "extension_acceptance": {
                "passed": True,
                "failed_keys": [],
                "checks": extension_checks,
                "evidence": {
                    "emergency_events": events,
                    "emergency_response_p95_ms": 50.0,
                    "emergency_response_max_ms": 50.0,
                },
            },
        }},
    }
    return summary, records


def test_member4_evidence_accepts_complete_s3_chain():
    summary, records = _passing_evidence()
    report = validate_evidence(summary, records)
    assert report["passed"] is True
    assert report["semantic_alignment"] == 1.0
    assert report["failed_keys"] == []


def test_member4_evidence_rejects_missing_pedestrian_timestamps():
    summary, records = _passing_evidence()
    extension = summary["acceptance"]["metrics"]["extension_acceptance"]
    extension["evidence"]["emergency_events"]["emergency_pedestrian"]["perception_timestamp_s"] = None

    report = validate_evidence(summary, records)

    assert report["passed"] is False
    assert "emergency_event_timestamps" in report["failed_keys"]


def test_member4_evidence_rejects_non_7b_model_and_route_mismatch():
    summary, records = _passing_evidence()
    records[0]["config"]["qwen_model"] = "Qwen/Qwen3-VL-2B-Instruct"
    summary["acceptance"]["metrics"]["qwen_acceptance"]["observed"]["routes"] = [
        "QWEN_PLAN", "QWEN_PLAN", "QWEN_PLAN", "FAST_LOCAL",
    ]

    report = validate_evidence(summary, records)

    assert report["passed"] is False
    assert "qwen_7b_model" in report["failed_keys"]
    assert "mixed_route_counts" in report["failed_keys"]


def test_member4_functional_profile_reports_but_does_not_block_latency():
    summary, records = _passing_evidence()
    evidence = summary["acceptance"]["metrics"]["extension_acceptance"]["evidence"]
    evidence["emergency_response_p95_ms"] = 130.0
    evidence["emergency_response_max_ms"] = 150.0

    competition = validate_evidence(summary, records)
    functional = validate_evidence(summary, records, functional_only=True)

    assert competition["passed"] is False
    assert functional["passed"] is True
    assert functional["performance_passed"] is False
