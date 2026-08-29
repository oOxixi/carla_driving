from __future__ import annotations

import json
from pathlib import Path

import pytest

from integration.scenario_execution import ScenarioSpec
from tools.validate_scenarios import validate_one


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "scenarios"
QWEN_SCENARIOS = tuple(sorted(
    path
    for folder in ("qwen_routing", "qwen_fullchain", "qwen_faults")
    for path in (SCENARIOS / folder).glob("*.json")
))


@pytest.mark.parametrize("path", QWEN_SCENARIOS, ids=lambda path: path.stem)
def test_qwen_scenarios_pass_repository_and_runtime_contracts(path):
    assert validate_one(path) == []
    spec = ScenarioSpec.load(path)
    assert spec.qwen_expected is not None
    assert spec.qwen_expected["forbidden_low_level_fields"] is True
    assert spec.qwen_expected["min_calls"] <= spec.qwen_expected["max_calls"]


def test_qwen_scenarios_pass_json_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((SCENARIOS / "scenario_schema.json").read_text(encoding="utf-8"))
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    for path in QWEN_SCENARIOS:
        validator.validate(json.loads(path.read_text(encoding="utf-8")))


def test_qwen_scenario_index_counts_match_filesystem():
    index = json.loads((SCENARIOS / "index.json").read_text(encoding="utf-8"))
    assert index["counts"]["qwen_routing"] == 4
    assert index["counts"]["qwen_fullchain"] == 2
    assert index["counts"]["qwen_faults"] == 3
    assert index["counts"]["total"] == sum(
        count for name, count in index["counts"].items() if name != "total"
    )


def test_qwen_fault_contracts_are_loaded_for_runtime_injection():
    timeout = ScenarioSpec.load(SCENARIOS / "qwen_faults" / "QWX_01_model_timeout.json")
    unsafe = ScenarioSpec.load(
        SCENARIOS / "qwen_faults" / "QWX_05_low_level_output_rejected.json"
    )
    safety = ScenarioSpec.load(
        SCENARIOS / "qwen_faults" / "QWX_06_pedestrian_safety_override.json"
    )

    assert timeout.qwen_fault == {"type": "TIMEOUT", "delay_ms": 6000}
    assert unsafe.qwen_fault == {
        "type": "LOW_LEVEL_FIELD", "field": "steer", "value": 0.8,
    }
    assert safety.qwen_fault is None
