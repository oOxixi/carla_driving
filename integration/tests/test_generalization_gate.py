import json
from pathlib import Path

import pytest

from integration.generalization_gate import load_generalization_matrix, perturb_scenario
from integration.scenario_builder import validate_actor_route_coverage
from integration.scenario_execution import ScenarioSpec


ROOT = Path(__file__).resolve().parents[2]


def test_matrix_covers_all_competition_maps_weather_and_timing() -> None:
    matrix = load_generalization_matrix()
    cases = tuple(matrix.cases("base"))
    assert len(cases) == 27
    assert {case.map_name for case in cases} == {"Town03", "Town04", "Town05"}
    assert {case.weather for case in cases} == {"ClearNoon", "CloudySunset", "HardRainNight"}
    assert {case.fixed_delta_s for case in cases} == {0.05, 0.10}
    assert {case.actor_speed_scale for case in cases} == {0.8, 1.0, 1.2}
    assert {case.brake_time_offset_s for case in cases} == {-1.0, 0.0, 1.0}
    assert {case.pedestrian_start_offset_s for case in cases} == {-0.5, 0.0, 0.5}
    assert {case.actor_count_scale for case in cases} == {0.8, 1.0, 1.2}
    assert {case.target_lane_relation for case in cases} == {
        "CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT",
    }
    assert {case.sensor_condition for case in cases} == {
        "nominal", "reduced_rgb", "sparse_lidar",
    }


@pytest.mark.parametrize(
    "relative_path",
    [
        "scenarios/official_competition/S1_basic_voice_control_5km.json",
        "scenarios/official_competition/S2_complex_avoidance_8km.json",
        "scenarios/official_competition/S3_extreme_emergency_6km.json",
    ],
)
def test_official_scenarios_survive_all_in_memory_perturbations(relative_path: str) -> None:
    source = ROOT / relative_path
    raw = json.loads(source.read_text(encoding="utf-8"))
    base_commands = raw["commands"]
    matrix = load_generalization_matrix()
    for case in matrix.cases(raw["scenario_id"]):
        variant = perturb_scenario(raw, case)
        assert variant["commands"] == base_commands
        route_length = float(variant["route"].get("distance_contract_m", 0.0))
        if route_length > 0.0:
            validate_actor_route_coverage(variant.get("actors", ()), route_length)


def test_holdout_set_is_frozen_and_loadable() -> None:
    matrix = load_generalization_matrix()
    assert len(matrix.holdout_scenarios) >= 3
    for relative_path in matrix.holdout_scenarios:
        path = ROOT / relative_path
        assert path.is_file()
        ScenarioSpec.load(path)


def test_cross_map_case_drops_town_specific_anchor_and_labels_unseen() -> None:
    raw = json.loads((
        ROOT / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    ).read_text(encoding="utf-8"))
    case = next(
        item for item in load_generalization_matrix().cases(raw["scenario_id"])
        if item.map_name != raw["map"]
    )
    variant = perturb_scenario(raw, case)
    assert "route_anchor_spawn_index" not in variant["extensions"]
    assert variant["extensions"]["generalization_case"]["kind"] == "unseen"


def test_walker_perturbation_preserves_crossing_vector() -> None:
    raw = json.loads((
        ROOT / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    ).read_text(encoding="utf-8"))
    case = next(iter(load_generalization_matrix().cases(raw["scenario_id"])))
    variant = perturb_scenario(raw, case)
    actor = next(item for item in variant["actors"] if item["actor_id"] == "crossing_pedestrian")
    start = actor["route_position"]
    target = actor["behavior"]["target_route_position"]
    assert start["s_m"] == pytest.approx(target["s_m"])
    assert start["lateral_offset_m"] - target["lateral_offset_m"] == pytest.approx(12.0)


def test_s2_actor_events_cover_the_full_route_and_use_explicit_route_positions() -> None:
    raw = json.loads((
        ROOT / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    ).read_text(encoding="utf-8"))
    positions = {
        actor["actor_id"]: float(actor["route_position"]["s_m"])
        for actor in raw["actors"]
    }
    assert min(positions.values()) <= 500.0
    assert max(positions.values()) >= 7000.0
    assert all("route_position" in actor for actor in raw["actors"])
    slow = next(item for item in raw["actors"] if item["actor_id"] == "slow_vehicle")
    assert slow["behavior"]["events"][0]["trigger"]["all"][1]["actor_id"] == "slow_vehicle"


def test_generalized_core_modules_contain_no_official_scene_or_town_special_cases() -> None:
    modules = (
        "integration/route_geometry.py",
        "integration/scenario_builder.py",
        "integration/planning_stage.py",
        "integration/perception_stage.py",
        "integration/execution_stage.py",
        "integration/scoring_stage.py",
        "integration/driving_policy.py",
    )
    forbidden = ("OFFICIAL_S1", "OFFICIAL_S2", "OFFICIAL_S3", "Town03", "Town04", "Town05")
    for relative_path in modules:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), relative_path

