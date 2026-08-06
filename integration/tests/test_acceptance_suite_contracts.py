from __future__ import annotations

import json
from pathlib import Path

from integration.scenario_acceptance import evaluate_expected
from integration.scenario_execution import ScenarioSpec


SCENARIOS_ROOT = Path(__file__).resolve().parents[2] / "scenarios"
SUITE_ROOT = SCENARIOS_ROOT / "acceptance_suite"


def _scenario_files() -> list[Path]:
    return sorted(path for path in SUITE_ROOT.rglob("*.json") if path.name != "matrix.json")


def test_acceptance_suite_has_exactly_43_loadable_scenarios() -> None:
    files = _scenario_files()
    assert len(files) == 43
    ids: set[str] = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        spec = ScenarioSpec.load(path)
        assert spec.scenario_id == path.stem
        assert spec.category in {"smoke", "lateral_B", "safety_D", "regression"}
        assert spec.scenario_id not in ids
        assert not evaluate_expected(spec.expected, {})["unsupported_keys"]
        assert max(command.time_s for command in spec.commands) <= spec.duration_s
        assert data["extensions"]["suite_version"] == "acceptance-suite-2026.08-v1"
        ids.add(spec.scenario_id)


def test_acceptance_matrix_matches_files_and_required_counts() -> None:
    matrix = json.loads((SUITE_ROOT / "matrix.json").read_text(encoding="utf-8"))
    entries = matrix["scenarios"]
    counts = matrix["counts"]
    assert counts["total"] == 43
    assert {key: counts[key] for key in ("P0", "P1", "P2", "P3")} == {
        "P0": 18,
        "P1": 18,
        "P2": 6,
        "P3": 1,
    }
    assert counts["current_runtime"] + counts["extension_required"] == 43
    matrix_paths = {item["path"] for item in entries}
    actual_paths = {str(path.relative_to(SUITE_ROOT)) for path in _scenario_files()}
    assert matrix_paths == actual_paths


def test_repository_index_includes_acceptance_suite_without_changing_categories() -> None:
    index = json.loads((SCENARIOS_ROOT / "index.json").read_text(encoding="utf-8"))
    assert index["counts"]["acceptance_suite"] == 43
    assert index["counts"]["total"] == sum(
        count for name, count in index["counts"].items() if name != "total"
    )
