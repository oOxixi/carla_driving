from pathlib import Path
from types import SimpleNamespace

import pytest

from car_control_A.routing import RouteReference
from integration.execution_stage import RouteProgressTracker
from integration.planning_stage import prepare_scenario_route
from integration.scenario_execution import ScenarioSpec
from integration.scoring_stage import build_acceptance_context


ROOT = Path(__file__).resolve().parents[2]


def test_planning_stage_rejects_short_topology_before_actor_creation() -> None:
    spec = ScenarioSpec.load(
        ROOT / "scenarios" / "official_competition" / "S1_basic_voice_control_5km.json"
    )
    anchor = SimpleNamespace(
        location=SimpleNamespace(x=0.0, y=0.0),
        rotation=SimpleNamespace(yaw=0.0),
    )
    with pytest.raises(RuntimeError, match="distance contract"):
        prepare_scenario_route(
            spec,
            anchor,
            5.0,
            RouteReference(((0.0, 0.0), (100.0, 0.0)), 0.0, 5.0),
        )


def test_execution_progress_is_monotonic_across_route_overlap() -> None:
    tracker = RouteProgressTracker(((0.0, 0.0), (10.0, 0.0), (0.0, 0.0)))
    observed = [
        tracker.update(x, 0.0, speed_mps=2.0, delta_s=0.05)
        for x in (0.0, 4.0, 8.0, 9.0, 5.0, 1.0)
    ]
    assert observed == sorted(observed)
    assert observed[-1] == pytest.approx(19.0)


def test_scoring_stage_is_read_only_and_keeps_control_policy_separate() -> None:
    spec = ScenarioSpec.load(
        ROOT / "scenarios" / "safety_D" / "D04_lane_deviation.json"
    )
    policy_before = dict(spec.control_policy)
    context = build_acceptance_context(
        spec,
        final_route_end_distance_m=0.5,
        final_route_remaining_m=0.5,
        configured_route_deviation_trigger_m=2.0,
        spawned_scenario_actor_types=("vehicle", "vehicle"),
        extension_acceptance=None,
        qwen_acceptance=None,
        extension_event_count=1,
    )
    assert context["route_finished"] is True
    assert context["spawned_scenario_actor_types"] == ["vehicle"]
    assert context["configured_route_deviation_trigger_m"] == 2.0
    assert spec.control_policy == policy_before


def test_expected_threshold_does_not_implicitly_become_control_policy() -> None:
    spec = ScenarioSpec.load(
        ROOT / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    )
    assert "route_deviation_trigger_m" not in spec.control_policy

