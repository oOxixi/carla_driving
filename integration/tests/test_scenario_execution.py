from __future__ import annotations

import math
from pathlib import Path

import pytest

from integration.scenario_execution import (
    CommandTimeline,
    ScenarioSpec,
    resolve_scenario_command,
)


SCENARIO_ROOT = Path(__file__).resolve().parents[2] / "scenarios"


def test_all_repository_scenarios_load() -> None:
    paths = sorted(SCENARIO_ROOT.glob("*/*.json"))
    specs = [ScenarioSpec.load(path) for path in paths]
    assert len(specs) == 34
    assert {spec.official_level for spec in specs} == {"basic", "advanced", "challenge"}
    assert all(spec.frame_count > 0 for spec in specs)


def test_speed_command_is_normalized_for_voice_adapter() -> None:
    spec = ScenarioSpec.load(SCENARIO_ROOT / "smoke" / "S01_set_speed_20.json")
    command = spec.commands[0].envelope
    assert command["intent"] == "SET_SPEED"
    assert command["parameters"] == {"speed": 20, "unit": "km/h"}


def test_world_route_rotates_local_template_around_spawn() -> None:
    spec = ScenarioSpec.load(SCENARIO_ROOT / "smoke" / "S01_set_speed_20.json")
    route = spec.world_route(100.0, 200.0, 90.0)
    assert route[0] == (100.0, 200.0)
    assert math.isclose(route[1][0], 100.0, abs_tol=1e-9)
    assert math.isclose(route[1][1], 210.0, abs_tol=1e-9)


def test_timeline_emits_each_command_once_and_in_order() -> None:
    spec = ScenarioSpec.load(SCENARIO_ROOT / "regression" / "REG_011_challenge_multi_command.json")
    timeline = CommandTimeline(spec.commands)
    assert [item["intent"] for item in timeline.due(0.0)] == ["SET_SPEED"]
    assert timeline.due(0.0) == ()
    assert [item["intent"] for item in timeline.due(7.0)] == ["SLOW_DOWN"]
    assert [item["intent"] for item in timeline.due(30.0)] == ["STOP"]


@pytest.mark.parametrize(
    ("scenario_name", "command_index", "current_speed", "expected_speed"),
    [
        ("S00_chain_start.json", 0, 5.0, 3.0),
        ("S02_slow_down.json", 1, 20.0 / 3.6, 15.0 / 3.6),
    ],
)
def test_trusted_smoke_shorthand_resolves_to_concrete_set_speed(
    scenario_name: str,
    command_index: int,
    current_speed: float,
    expected_speed: float,
) -> None:
    spec = ScenarioSpec.load(SCENARIO_ROOT / "smoke" / scenario_name)
    original = spec.commands[command_index].envelope
    resolved = resolve_scenario_command(original, requested_speed_mps=current_speed)
    assert resolved["intent"] == "SET_SPEED"
    assert resolved["scenario_original_intent"] == original["intent"]
    assert resolved["parameters"] == {"speed": pytest.approx(expected_speed), "unit": "m/s"}
