from __future__ import annotations

import json
from pathlib import Path

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
    actual_paths = {str(path.relative_to(SUITE_ROOT)) for path in _scenario_files()}
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
    assert main["extensions"]["runtime_support"]["status"] == "extension_required"
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
