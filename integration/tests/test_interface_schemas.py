from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
INTERFACES = ROOT / "interfaces"
NAMES = (
    "driving_command",
    "model_request",
    "decision_plan",
    "perception_state",
    "control_command",
    "execution_feedback",
)


def _validator(name: str):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((INTERFACES / f"{name}.schema.json").read_text(encoding="utf-8"))
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


@pytest.mark.parametrize("name", NAMES)
def test_frozen_interface_examples_pass_schema(name: str) -> None:
    payload = json.loads((INTERFACES / "examples" / f"{name}.json").read_text(encoding="utf-8"))
    _validator(name).validate(payload)


@pytest.mark.parametrize("name", NAMES)
def test_frozen_interfaces_reject_unknown_fields_and_versions(name: str) -> None:
    payload = json.loads((INTERFACES / "examples" / f"{name}.json").read_text(encoding="utf-8"))
    unknown = copy.deepcopy(payload)
    unknown["unexpected"] = True
    with pytest.raises(Exception):
        _validator(name).validate(unknown)
    wrong_version = copy.deepcopy(payload)
    wrong_version["schema_version"] = "2.0"
    with pytest.raises(Exception):
        _validator(name).validate(wrong_version)


def test_decision_plan_cannot_contain_low_level_control() -> None:
    payload = json.loads((INTERFACES / "examples" / "decision_plan.json").read_text(encoding="utf-8"))
    for forbidden in ("throttle", "brake", "steer"):
        invalid = copy.deepcopy(payload)
        invalid[forbidden] = 0.5
        with pytest.raises(Exception):
            _validator("decision_plan").validate(invalid)


def test_set_speed_requires_si_target_speed() -> None:
    payload = json.loads((INTERFACES / "examples" / "driving_command.json").read_text(encoding="utf-8"))
    payload["parameters"] = {}
    with pytest.raises(Exception):
        _validator("driving_command").validate(payload)
