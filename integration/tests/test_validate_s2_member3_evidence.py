from __future__ import annotations

from tools.validate_s2_member3_evidence import SCENARIO_ID, validate_evidence


def _passing_evidence():
    command_ids = [f"scenario_cmd_{index:03d}" for index in range(5)]
    records = [{
        "record_type": "run_start",
        "config": {
            "seed": 20260202,
            "code_version": "abc123",
            "config_path": "scenarios/official_competition/S2_complex_avoidance_8km.json",
        },
    }]
    records.extend({
        "record_type": "command",
        "command_id": command_id,
        "disposition": "SCENARIO_SLOW_PENDING",
    } for command_id in command_ids)
    records.extend({
        "record_type": "canonical_routing",
        "phase": "MISSION_ROUTE_RESTORED",
    } for _ in range(2))
    extension_checks = [
        {"key": key, "status": "PASS", "actual": True}
        for key in (
            "expected_phase_count",
            "all_phases_must_complete",
            "must_return_to_original_lane",
            "minimum_actor_distances_m",
            "maximum_route_deviation_m",
        )
    ]
    summary = {
        "scenario_id": SCENARIO_ID,
        "status": "SUCCEEDED",
        "collision_count": 0,
        "lane_invasion_count": 0,
        "command_terminal_statuses": {command_id: "SUCCEEDED" for command_id in command_ids},
        "latency": {"sensor_to_trajectory_max_ms": 149.0},
        "acceptance": {"metrics": {
            "qwen_acceptance": {
                "passed": True,
                "checks": {"low_level_boundary": True},
                "observed": {
                    "qwen_calls": 5,
                    "routes": ["QWEN_PLAN"] * 5,
                    "behaviors": [
                        "KEEP_LANE", "SLOW_DOWN", "WAIT_SAFE_GAP",
                        "CHANGE_LANE_LEFT", "PASS_TARGET", "RETURN_TO_LANE",
                    ],
                    "terminal_counts": {command_id: 1 for command_id in command_ids},
                },
            },
            "extension_acceptance": {
                "passed": True,
                "failed_keys": [],
                "checks": extension_checks,
            },
        }},
    }
    return summary, records


def test_member3_evidence_accepts_complete_s2_chain():
    summary, records = _passing_evidence()
    report = validate_evidence(summary, records)
    assert report["passed"] is True
    assert report["failed_keys"] == []


def test_member3_evidence_rejects_missing_return_and_close_bicycle():
    summary, records = _passing_evidence()
    records.pop()
    extension = summary["acceptance"]["metrics"]["extension_acceptance"]
    distance = next(
        item for item in extension["checks"]
        if item["key"] == "minimum_actor_distances_m"
    )
    distance["status"] = "FAIL"
    distance["actual"] = {"bicycle_right": 2.7}
    extension["passed"] = False
    extension["failed_keys"] = ["minimum_actor_distances_m"]

    report = validate_evidence(summary, records)

    assert report["passed"] is False
    assert "mission_route_restored" in report["failed_keys"]
    assert "extension_minimum_actor_distances_m" in report["failed_keys"]


def test_member3_functional_profile_reports_but_does_not_block_on_latency():
    summary, records = _passing_evidence()
    summary["latency"]["sensor_to_trajectory_max_ms"] = 215.0

    competition = validate_evidence(summary, records)
    functional = validate_evidence(summary, records, functional_only=True)

    assert competition["passed"] is False
    assert competition["functional_passed"] is True
    assert competition["performance_passed"] is False
    assert competition["failed_keys"] == ["sensor_to_trajectory_max_ms"]
    assert functional["passed"] is True
    assert functional["evaluation_profile"] == "functional"
    assert functional["failed_keys"] == []
    assert functional["performance_failed_keys"] == ["sensor_to_trajectory_max_ms"]


def test_member3_functional_profile_still_blocks_functional_failures():
    summary, records = _passing_evidence()
    summary["collision_count"] = 1
    summary["latency"]["sensor_to_trajectory_max_ms"] = 215.0

    report = validate_evidence(summary, records, functional_only=True)

    assert report["passed"] is False
    assert report["failed_keys"] == ["collision_count"]
    assert report["performance_failed_keys"] == ["sensor_to_trajectory_max_ms"]
