from __future__ import annotations

import math
from pathlib import Path

import pytest

from integration.scenario_execution import (
    CommandTimeline,
    ScenarioSpec,
    resolve_scenario_command,
    select_best_route_anchor,
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
    assert route[-1] == pytest.approx((100.0, 260.0))
    assert max(math.dist(first, second) for first, second in zip(route, route[1:])) <= 1.0 + 1e-9


def test_world_route_honours_contract_resample_interval() -> None:
    spec = ScenarioSpec.load(SCENARIO_ROOT / "lateral_B" / "B06_left_turn.json")
    route = spec.world_route(0.0, 0.0, 0.0)
    assert spec.route_resample_interval_m == 1.0
    assert route[0] == (0.0, 0.0)
    assert route[-1] == (30.0, 25.0)
    assert len(route) > len(spec.local_route_xy_m)
    assert max(math.dist(first, second) for first, second in zip(route, route[1:])) <= 1.0 + 1e-9


def test_scenario_ego_offset_is_loaded_separately_from_route_anchor() -> None:
    spec = ScenarioSpec.load(SCENARIO_ROOT / "safety_D" / "D04_lane_deviation.json")
    assert spec.ego_spawn_xyzyaw == (0.0, 2.4, 0.5, 0.0)
    assert spec.local_route_xy_m[0] == (0.0, 0.0)


def test_best_route_anchor_prefers_drivable_shape_not_first_spawn() -> None:
    anchors = ((0.0, 10.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0))
    route = ((0.0, 0.0), (20.0, 0.0))
    index, score = select_best_route_anchor(
        anchors,
        route,
        lambda _x, y, _z: abs(y),
        sample_interval_m=1.0,
    )
    assert index == 1
    assert score == pytest.approx(0.0)


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


@pytest.mark.parametrize(
    ("relative_path", "expected_original_intent", "expected_speed"),
    [
        ("lateral_B/B06_left_turn.json", "TURN_LEFT", 10.0 / 3.6),
        ("lateral_B/B07_right_turn.json", "TURN_RIGHT", 10.0 / 3.6),
        ("lateral_B/B08_lane_change_left.json", "CHANGE_LANE_LEFT", 15.0 / 3.6),
        ("lateral_B/B09_lane_change_right.json", "CHANGE_LANE_RIGHT", 15.0 / 3.6),
        ("safety_D/D01_red_light_stop.json", "KEEP_LANE", 20.0 / 3.6),
    ],
)
def test_trusted_route_manoeuvre_uses_scenario_route_and_concrete_speed(
    relative_path: str,
    expected_original_intent: str,
    expected_speed: float,
) -> None:
    spec = ScenarioSpec.load(SCENARIO_ROOT / relative_path)
    resolved = resolve_scenario_command(spec.commands[0].envelope, requested_speed_mps=0.0)
    assert resolved["intent"] == "SET_SPEED"
    assert resolved["scenario_original_intent"] == expected_original_intent
    assert resolved["parameters"] == {"speed": pytest.approx(expected_speed), "unit": "m/s"}
