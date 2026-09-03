import json

import pytest

from integration.driving_policy import load_driving_policy


def test_default_policy_drives_both_perception_and_safety() -> None:
    policy = load_driving_policy()
    perception = policy.perception_parameters()
    safety = policy.safety_config()
    assert perception.emergency_ttc_s == safety.low_ttc_s
    assert perception.caution_ttc_s == safety.caution_ttc_s
    assert perception.emergency_deceleration_mps2 == safety.emergency_deceleration_mps2
    assert perception.emergency_reaction_time_s == safety.emergency_reaction_time_s
    assert perception.range_uncertainty_buffer_m == safety.range_uncertainty_buffer_m


def test_scenario_route_threshold_override_does_not_mutate_policy() -> None:
    policy = load_driving_policy()
    overridden = policy.safety_config(route_deviation_override_m=1.0)
    default = policy.safety_config()
    assert overridden.severe_route_deviation_m == 1.0
    assert overridden.max_lane_offset_m == 1.0
    assert default.severe_route_deviation_m == 3.0


def test_invalid_policy_fails_before_carla_mutation(tmp_path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps({
        "schema_version": "1.0",
        "perception": {},
        "safety": {},
    }), encoding="utf-8")
    with pytest.raises(TypeError, match="must be a number"):
        load_driving_policy(source)

