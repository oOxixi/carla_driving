"""Tests for the chosen FLOPs option and the same-protocol decay comparison."""
from __future__ import annotations

import json
from pathlib import Path

from ..harness.x86_sim.flops_ratio import compute, tier_points
from ..harness.x86_sim.teacher_student_protocol_decay import compare


def test_rule_tiers_match_the_judging_rules() -> None:
    assert tier_points(0.17691258021763392) == 15
    assert tier_points(0.5) == 15
    assert tier_points(0.5000001) == 10
    assert tier_points(0.7) == 10
    assert tier_points(0.7000001) == 5
    assert tier_points(0.9) == 5
    assert tier_points(0.91) == 0


def test_chosen_option_recomputes_and_cross_checks(tmp_path: Path) -> None:
    options = tmp_path / "flops_options.json"
    options.write_text(json.dumps({
        "candidates": [
            {"id": "fixed_teacher_conv_linear", "baseline": "Pinned Teacher", "scope": "Conv/Linear",
             "numerator": 498640896, "denominator": 892929605632, "ratio": 0.0005584324820847111},
        ]
    }), encoding="utf-8")
    report = tmp_path / "flops_report.json"
    report.write_text(json.dumps({"flops_per_fixed_batch": 498640896}), encoding="utf-8")

    record = compute(options, "fixed_teacher_conv_linear", report)
    assert record["ratio"] == 498640896 / 892929605632
    assert record["rule_tier"]["points_if_accepted"] == 15
    assert record["numerator_cross_check"]["matches"] is True


def _release_row(scenario: str, passed: bool, seed: int = 1) -> dict:
    return {
        "metadata": {"scenario_id": scenario, "scenario_config_path": f"scenarios/acceptance_suite/{scenario}.json",
                     "seed": seed},
        "closed_loop_quality": {"available": True, "scenario_acceptance_passed": passed},
    }


def test_same_protocol_decay_uses_shared_scenarios(tmp_path: Path) -> None:
    releases = tmp_path / "val.jsonl"
    lines = [
        _release_row("ACC_B01_start_keep_lane", True),
        _release_row("ACC_B02_set_speed_20", True),
        _release_row("ACC_B02_set_speed_20", False, seed=2),
        _release_row("ACC_A03_pedestrian_crossing", True),
        _release_row("ACC_A03_pedestrian_crossing", True, seed=3),
        _release_row("ACC_ONLY_IN_RELEASES", True),
    ]
    releases.write_text("\n".join(json.dumps(item) for item in lines), encoding="utf-8")
    suite = tmp_path / "suite.json"
    suite.write_text(json.dumps({"scenarios": [
        {"scenario": "ACC_B01_start_keep_lane", "status": "SUCCEEDED", "failed_keys": []},
        {"scenario": "ACC_B02_set_speed_20", "status": "FAILED", "failed_keys": ["target_speed_kph"]},
        {"scenario": "ACC_A03_pedestrian_crossing", "status": "FAILED", "failed_keys": []},
        {"scenario": "ACC_ONLY_IN_STUDENT", "status": "SUCCEEDED"},
    ]}), encoding="utf-8")

    report = compare([releases], suite)
    assert report["coverage"] == {
        "teacher_scenarios": 4, "teacher_rows": 6,
        "student_scenarios": 4, "shared_scenarios": 3,
    }
    assert report["result"]["teacher_macro_pass_rate"] == (1.0 + 0.5 + 1.0) / 3
    assert report["result"]["student_macro_pass_rate"] == 1 / 3
    assert report["result"]["student_passed"] == 1
    # only scenarios where every Teacher run passed and the Student failed
    assert report["teacher_passed_student_failed"] == ["ACC_A03_pedestrian_crossing"]
    assert report["student_passed_teacher_had_failures"] == []
