from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from runtime.plan_validator import PlanValidationError, PlanValidator


ROOT = Path(__file__).resolve().parents[2]


def _plan():
    return json.loads((ROOT / "interfaces/examples/maneuver_plan.json").read_text(encoding="utf-8"))


def _scene(**updates):
    scene = {
        "objects": [{"track_id": "vehicle-1"}],
        "traffic_light": "GREEN",
        "distance_to_stop_line_m": None,
        "risk_level": "LOW",
        "speed_limit_mps": 8.0,
        "stale": False,
        "sync": {"within_tolerance": True},
        "available_lanes": ["CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT"],
        "left_lane_exists": True,
        "right_lane_exists": True,
        "left_gap_safe": True,
        "right_gap_safe": True,
        "route_available": True,
        "intersection_ahead": True,
        "stop_line_clear": True,
    }
    scene.update(updates)
    return scene


def test_valid_example_passes_schema_and_scene_boundary():
    plan = _plan()
    result = PlanValidator().validate(
        plan, scene=_scene(), expected_request_id=plan["request_id"],
        expected_command_id=plan["command_id"], now_ns=2_000_000_000,
    )
    assert result == plan


@pytest.mark.parametrize("field", ["throttle", "brake", "steer", "wheel_angle"])
def test_low_level_fields_are_rejected_at_any_depth(field):
    plan = _plan()
    plan["steps"][0]["target"][field] = 0.5
    with pytest.raises(PlanValidationError, match="LOW_LEVEL_OUTPUT_FORBIDDEN"):
        PlanValidator().validate(plan, scene=_scene(), now_ns=2_000_000_000)


def test_unknown_fields_and_too_many_steps_are_rejected():
    unknown = _plan()
    unknown["unexpected"] = True
    with pytest.raises(PlanValidationError, match="INVALID_PLAN_SCHEMA"):
        PlanValidator().validate(unknown, scene=_scene(), now_ns=2_000_000_000)
    too_many = _plan()
    too_many["steps"] = [copy.deepcopy(too_many["steps"][0]) for _ in range(5)]
    for index, step in enumerate(too_many["steps"]):
        step["step_id"] = f"s{index}"
    with pytest.raises(PlanValidationError, match="INVALID_PLAN_SCHEMA"):
        PlanValidator().validate(too_many, scene=_scene(), now_ns=2_000_000_000)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda plan: plan.update(request_id="wrong"), "REQUEST_ID_MISMATCH"),
        (lambda plan: plan.update(command_id="wrong"), "COMMAND_ID_MISMATCH"),
        (lambda plan: plan.update(valid_until_ns=1_500_000_000), "PLAN_EXPIRED"),
    ],
)
def test_ids_and_expiry_are_enforced(mutation, reason):
    plan = _plan()
    request_id, command_id = plan["request_id"], plan["command_id"]
    mutation(plan)
    with pytest.raises(PlanValidationError, match=reason):
        PlanValidator().validate(
            plan, scene=_scene(), expected_request_id=request_id,
            expected_command_id=command_id, now_ns=2_000_000_000,
        )


def test_invented_target_speeding_and_missing_lane_context_are_rejected():
    target = _plan()
    target["steps"][0]["behavior"] = "FOLLOW"
    target["steps"][0]["target"]["target_id"] = "invented"
    target["steps"][0]["target"]["time_gap_s"] = 2.0
    target["steps"][0]["completion"] = {
        "type": "TARGET_GAP_REACHED", "value": 2.0, "lane": None, "hold_frames": 3,
    }
    with pytest.raises(PlanValidationError, match="TARGET_NOT_FOUND"):
        PlanValidator().validate(target, scene=_scene(), now_ns=2_000_000_000)
    grounded = copy.deepcopy(target)
    PlanValidator().validate(
        grounded,
        scene=_scene(grounded_target_ids=["invented"]),
        now_ns=2_000_000_000,
    )
    speeding = _plan()
    speeding["steps"][0]["target"]["target_speed_mps"] = 20.0
    with pytest.raises(PlanValidationError, match="SPEED_LIMIT_EXCEEDED"):
        PlanValidator().validate(speeding, scene=_scene(), now_ns=2_000_000_000)
    no_lanes = _plan()
    scene = _scene()
    for key in ("available_lanes", "left_lane_exists", "right_lane_exists"):
        scene.pop(key)
    with pytest.raises(PlanValidationError, match="LANE_CONTEXT_MISSING"):
        PlanValidator().validate(no_lanes, scene=scene, now_ns=2_000_000_000)


def test_red_light_forbids_advancing_plan_and_missing_completion_value_fails():
    with pytest.raises(PlanValidationError, match="MUST_STOP_PROPULSION_FORBIDDEN"):
        PlanValidator().validate(
            _plan(), scene=_scene(traffic_light="RED", distance_to_stop_line_m=8.0),
            now_ns=2_000_000_000,
        )
    missing = _plan()
    missing["steps"][0]["completion"]["value"] = None
    with pytest.raises(PlanValidationError, match="COMPLETION_VALUE_REQUIRED"):
        PlanValidator().validate(missing, scene=_scene(), now_ns=2_000_000_000)
