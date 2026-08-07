from __future__ import annotations

import json
from pathlib import Path

import pytest

from integration.scenario_acceptance import evaluate_expected
from integration.scenario_execution import ScenarioSpec


SCENARIOS_ROOT = Path(__file__).resolve().parents[2] / "scenarios"
SUITE_ROOT = SCENARIOS_ROOT / "acceptance_suite"


def _scenario_files() -> list[Path]:
    return sorted(path for path in SUITE_ROOT.rglob("*.json") if path.name != "matrix.json")


def test_acceptance_suite_has_exactly_84_loadable_scenarios() -> None:
    files = _scenario_files()
    assert len(files) == 84
    ids: set[str] = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        spec = ScenarioSpec.load(path)
        assert spec.scenario_id == path.stem
        assert spec.category in {"smoke", "lateral_B", "safety_D", "regression"}
        assert spec.scenario_id not in ids
        assert not evaluate_expected(spec.expected, {})["unsupported_keys"]
        assert max(command.time_s for command in spec.commands) <= spec.duration_s
        assert data["extensions"]["suite_version"] == "acceptance-suite-2026.08-v2"
        ids.add(spec.scenario_id)
    assert "CX_MAIN_01_safe_urban_mission" in ids
    assert "CX06_multi_command_full_trip" not in ids


def test_acceptance_matrix_matches_files_and_required_counts() -> None:
    matrix = json.loads((SUITE_ROOT / "matrix.json").read_text(encoding="utf-8"))
    entries = matrix["scenarios"]
    counts = matrix["counts"]
    assert counts["total"] == 84
    assert {key: counts[key] for key in ("P0", "P1", "P2", "P3")} == {
        "P0": 18,
        "P1": 54,
        "P2": 6,
        "P3": 6,
    }
    assert {
        key: counts[key]
        for key in (
            "basic_scoring", "advanced_scoring", "challenge_scoring",
            "complex_regression", "system_stability",
        )
    } == {
        "basic_scoring": 18,
        "advanced_scoring": 30,
        "challenge_scoring": 24,
        "complex_regression": 6,
        "system_stability": 6,
    }
    assert counts["current_runtime"] + counts["extension_required"] == 84
    matrix_paths = {item["path"] for item in entries}
    actual_paths = {path.relative_to(SUITE_ROOT).as_posix() for path in _scenario_files()}
    assert matrix_paths == actual_paths


def test_repository_index_includes_acceptance_suite_without_changing_categories() -> None:
    index = json.loads((SCENARIOS_ROOT / "index.json").read_text(encoding="utf-8"))
    assert index["counts"]["acceptance_suite"] == 84
    assert index["counts"]["total"] == sum(
        count for name, count in index["counts"].items() if name != "total"
    )


def test_v2_supplemental_counts_and_main_complex_contract() -> None:
    expected = {
        "basic": 6,
        "advanced": 18,
        "challenge": 12,
        "system": 5,
    }
    for folder, count in expected.items():
        assert len(list((SUITE_ROOT / "supplemental" / folder).glob("*.json"))) == count

    main = json.loads(
        (SUITE_ROOT / "complex" / "CX_MAIN_01_safe_urban_mission.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(main["commands"]) == 7
    assert main["extensions"]["proposed_acceptance"]["expected_phase_count"] == 9
    assert main["extensions"]["qwen_policy"]["required_for_every_voice_event"] is True
    assert main["extensions"]["runtime_support"]["status"] == "current"
    assert not (SUITE_ROOT / "complex" / "CX06_multi_command_full_trip.json").exists()
    assert (SUITE_ROOT / "BUILD_SUMMARY.md").exists()


def test_acceptance_suite_passes_repository_json_schema() -> None:
    import jsonschema

    schema = json.loads((SCENARIOS_ROOT / "scenario_schema.json").read_text(encoding="utf-8"))
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    for path in _scenario_files():
        validator.validate(json.loads(path.read_text(encoding="utf-8")))


def test_steer_bias_scenario_measures_recovery_not_brake_response() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "challenge" / "ACC_C06_dynamic_route_deviation.json")
        .read_text(encoding="utf-8")
    )
    proposed = scenario["extensions"]["proposed_acceptance"]

    assert proposed["recovery_deadline_s"] == 1.0
    assert "max_fault_response_s" not in proposed


def test_var_b02_declares_the_speed_limit_used_by_its_oracle() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "variants" / "VAR_B02_set_speed_30_limit.json")
        .read_text(encoding="utf-8")
    )

    assert scenario["extensions"]["speed_policy"]["scenario_limit_kph"] == 30


def test_var_b04_oracle_allows_safe_slowdown_before_stop() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "variants" / "VAR_B04_stop_on_mild_curve.json")
        .read_text(encoding="utf-8")
    )
    allowed = set(scenario["extensions"]["oracle"]["expected_behaviors"])

    assert {"KEEP_LANE", "SLOW_DOWN", "STOP"}.issubset(allowed)


def test_var_b05_oracle_excludes_local_fast_emergency_stop() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "variants" / "VAR_B05_emergency_stop_25kph.json")
        .read_text(encoding="utf-8")
    )

    assert scenario["extensions"]["oracle"]["expected_behaviors"] == ["SET_SPEED"]


def test_var_a02_accepts_proactive_stop_before_emergency_is_needed() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "variants" / "VAR_A02_low_ttc_stationary_lead.json")
        .read_text(encoding="utf-8")
    )
    expected = scenario["expected"]

    assert expected["must_stop_after_last_command"] is True
    assert expected["stop_within_s"] == 2.0
    assert "must_emergency_brake" not in expected
    assert "expected_safety_override" not in expected


def test_yellow_to_red_scenario_must_approach_before_signal_transition() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "supplemental" / "advanced" / "SUP_A06_yellow_to_red.json")
        .read_text(encoding="utf-8")
    )
    signal = scenario["actors"][0]
    states = signal["behavior"]["states"]
    acceptance = scenario["extensions"]["proposed_acceptance"]

    assert signal["state"] == "green"
    assert [item["state"] for item in states] == ["yellow", "red"]
    assert acceptance["pre_red_max_speed_min_mps"] == 0.5
    assert acceptance["minimum_red_stop_line_clearance_m"] == 0.0
    assert acceptance["must_stop_on_red_before_stop_line"] is True


def test_sup_a15_places_a_real_actor_in_the_commanded_left_lane() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "supplemental" / "advanced" / "SUP_A15_lane_change_blocked.json")
        .read_text(encoding="utf-8")
    )
    occupant = next(
        item for item in scenario["actors"] if item["actor_id"] == "left_lane_occupant"
    )
    acceptance = scenario["extensions"]["proposed_acceptance"]

    # The CARLA road selected for this scenario points west. In the scenario's
    # conventional positive-left coordinates, physical left is local -Y.
    assert occupant["spawn"]["y"] == -3.5
    assert occupant["behavior"]["initial_speed_mps"] == 0.0
    assert occupant["behavior"]["target_speed_mps"] == 0.0
    assert acceptance["target_lane_occupied_min_count"] == 1


@pytest.mark.parametrize("filename", [
    "SUP_A17_detour_left_construction.json",
    "SUP_A18_detour_return_original_lane.json",
])
def test_prevalidated_left_detour_routes_use_physical_left(filename: str) -> None:
    scenario = json.loads(
        (SUITE_ROOT / "supplemental" / "advanced" / filename)
        .read_text(encoding="utf-8")
    )
    command = scenario["commands"][0]
    lateral_offsets = [point[1] for point in scenario["route"]["points_xy_m"]]

    assert command["parameters"]["direction"] == "LEFT"
    assert min(lateral_offsets) == -3.5
    assert max(lateral_offsets) == 0


def test_low_visibility_contract_accepts_bounded_slowdown_or_stop() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "supplemental" / "challenge" / "SUP_C02_low_visibility_rain_fog.json")
        .read_text(encoding="utf-8")
    )
    acceptance = scenario["extensions"]["proposed_acceptance"]

    assert acceptance == {"conservative_speed_required": True}
    assert scenario["expected"]["max_speed_mps"] == 3.5
    assert set(scenario["extensions"]["oracle"]["expected_behaviors"]) == {
        "SLOW_DOWN", "STOP",
    }


def test_var_c05_oracle_separates_prefault_motion_from_fail_closed_response() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "variants" / "VAR_C05_rgb_lidar_blackout.json")
        .read_text(encoding="utf-8")
    )

    assert scenario["commands"][0]["intent"] == "KEEP_LANE"
    assert "KEEP_LANE" in scenario["extensions"]["oracle"]["expected_behaviors"]
    assert scenario["extensions"]["proposed_acceptance"]["max_fault_response_s"] == 1.0


def test_var_c06_uses_early_route_deviation_stop_threshold() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "variants" / "VAR_C06_large_route_deviation.json")
        .read_text(encoding="utf-8")
    )

    assert scenario["expected"]["route_deviation_trigger_m"] == 1.4
    assert scenario["expected"]["expected_route_deviation_event"] is True
    assert "expected_safety_override_allowed" not in scenario["expected"]
    assert "KEEP_LANE" in scenario["extensions"]["oracle"]["expected_behaviors"]
    assert scenario["extensions"]["proposed_acceptance"]["max_fault_response_s"] == 1.0


def test_cx04_ambiguous_multi_target_requires_confirmation_not_target_guess() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "complex" / "CX04_heavy_rain_ambiguous_multi_target.json")
        .read_text(encoding="utf-8")
    )

    assert scenario["commands"][0]["confirm_required"] is True
    assert scenario["extensions"]["proposed_acceptance"]["requires_confirmation"] is True
    assert "expected_target_actor_id" not in scenario["extensions"]["oracle"]


def test_sup_c03_vague_slow_allows_safe_hold_and_requires_confirmation() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "supplemental" / "challenge" / "SUP_C03_vague_slow.json")
        .read_text(encoding="utf-8")
    )

    proposed = scenario["extensions"]["proposed_acceptance"]
    assert scenario["commands"][0]["confirm_required"] is True
    assert proposed["requires_confirmation"] is True
    assert "HOLD" in proposed["allowed_qwen_actions"]
    assert "HOLD" in scenario["extensions"]["oracle"]["expected_behaviors"]


def test_sup_c08_exercises_stale_rejection_then_fresh_rebind() -> None:
    scenario = json.loads(
        (
            SUITE_ROOT / "supplemental" / "challenge"
            / "SUP_C08_target_occluded_stale_rejection.json"
        ).read_text(encoding="utf-8")
    )

    assert len(scenario["commands"]) == 3
    assert scenario["commands"][0]["time_s"] >= 1
    assert scenario["commands"][-1]["time_s"] > 13
    delay_fault = next(
        item for item in scenario["extensions"]["faults"]
        if item["type"] == "qwen_response_delay"
    )
    assert delay_fault["trigger"]["time_s"] == 12
    assert delay_fault["delay_ms"] > 300
    proposed = scenario["extensions"]["proposed_acceptance"]
    assert proposed["qwen_stale_result_applied_count"] == 0
    assert proposed["rebind_requires_fresh_perception"] is True
    assert proposed["post_recovery_command_succeeds"] is True
    assert proposed["target_binding_correct"] is True
    assert "STOP" in scenario["extensions"]["oracle"]["expected_behaviors"]


def test_sup_c10_scopes_safety_stop_to_blackout_window() -> None:
    scenario = json.loads(
        (
            SUITE_ROOT / "supplemental" / "challenge"
            / "SUP_C10_rgb_lidar_blackout.json"
        ).read_text(encoding="utf-8")
    )

    proposed = scenario["extensions"]["proposed_acceptance"]
    assert proposed["max_fault_response_s"] == 1.0
    assert proposed["qwen_must_not_override_safety_stop"] is True
    assert proposed["must_recover_after_fault"] is True
    assert "KEEP_LANE" in scenario["extensions"]["oracle"]["expected_behaviors"]


def test_sup_c12_uses_reachable_large_deviation_stop_threshold() -> None:
    scenario = json.loads(
        (
            SUITE_ROOT / "supplemental" / "challenge"
            / "SUP_C12_large_deviation_stop.json"
        ).read_text(encoding="utf-8")
    )

    assert scenario["expected"]["route_deviation_trigger_m"] == 1.0
    proposed = scenario["extensions"]["proposed_acceptance"]
    assert proposed["must_stop_if_recovery_fails"] is True
    assert proposed["must_not_continue_route_deviation"] is True
    assert proposed["max_fault_response_s"] <= 1.5


def test_sys03_releases_single_worker_before_replacement_command() -> None:
    scenario = json.loads(
        (
            SUITE_ROOT / "supplemental" / "system"
            / "SYS_03_qwen_stale_result.json"
        ).read_text(encoding="utf-8")
    )

    delay = scenario["extensions"]["faults"][0]["delay_ms"]
    assert 300 < delay < scenario["commands"][1]["time_s"] * 1000
    proposed = scenario["extensions"]["proposed_acceptance"]
    assert proposed["qwen_timeout_count"] == 1
    assert proposed["qwen_stale_result_applied_count"] == 0
    assert proposed["current_plan_command_index"] == 1
    assert scenario["extensions"]["oracle"]["expected_behaviors"] == ["STOP"]


def test_sys04_disconnect_contract_expects_failed_middle_command() -> None:
    scenario = json.loads(
        (
            SUITE_ROOT / "supplemental" / "system"
            / "SYS_04_qwen_disconnect_recovery.json"
        ).read_text(encoding="utf-8")
    )

    assert "must_execute_commands_in_order" not in scenario["expected"]
    proposed = scenario["extensions"]["proposed_acceptance"]
    assert proposed["disconnect_fail_closed"] is True
    assert proposed["post_recovery_command_succeeds"] is True
    assert proposed["qwen_request_count"] == 3
    assert proposed["current_plan_command_index"] == 2
    assert "SET_SPEED" not in scenario["extensions"]["oracle"]["expected_behaviors"]


def test_cx05_keep_lane_route_and_recovery_contract_are_consistent() -> None:
    scenario = json.loads(
        (SUITE_ROOT / "complex" / "CX05_sensor_dropout_route_recovery.json")
        .read_text(encoding="utf-8")
    )

    assert max(abs(point[1]) for point in scenario["route"]["points_xy_m"]) <= 1.5
    proposed = scenario["extensions"]["proposed_acceptance"]
    assert proposed["must_recover_after_fault"] is True
    assert proposed["recovery_deadline_s"] == 1.0
    assert "max_fault_response_s" not in proposed
