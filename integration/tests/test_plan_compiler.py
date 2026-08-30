from __future__ import annotations

import json
from pathlib import Path

from runtime.plan_compiler import PlanCompiler


ROOT = Path(__file__).resolve().parents[2]


def _plan():
    return json.loads((ROOT / "interfaces/examples/maneuver_plan.json").read_text(encoding="utf-8"))


def test_primitive_steps_compile_without_low_level_control():
    compiled = PlanCompiler().compile(_plan())
    assert [step.behavior for step in compiled.steps] == ["SLOW_DOWN", "CHANGE_LANE_LEFT"]
    payload = compiled.to_dict()
    assert not {"throttle", "brake", "steer"}.intersection(str(payload))


def test_avoid_expands_to_deterministic_slow_gap_lane_and_pass_steps():
    plan = _plan()
    plan["steps"] = [{
        "step_id": "avoid", "behavior": "AVOID_OBSTACLE",
        "target": {
            "target_id": "vehicle-1", "target_lane": "LEFT_ADJACENT",
            "target_speed_mps": 3.0, "time_gap_s": None, "route_direction": None,
        },
        "preconditions": ["PERCEPTION_FRESH"],
        "completion": {"type": "TARGET_PASSED", "value": None, "lane": None, "hold_frames": 3},
        "timeout_s": 8.0, "on_failure": "REPLAN",
    }]
    compiled = PlanCompiler().compile(plan, scene={"left_lane_exists": True})
    assert [step.behavior for step in compiled.steps] == [
        "SLOW_DOWN", "WAIT_SAFE_GAP", "CHANGE_LANE_LEFT", "PASS_TARGET",
    ]
    assert compiled.steps[1].preconditions[-2:] == ("LEFT_LANE_EXISTS", "LEFT_GAP_SAFE")
    assert compiled.steps[-1].preconditions == (
        "PERCEPTION_FRESH", "TARGET_VISIBLE", "NO_EMERGENCY_RISK",
    )


def test_return_to_lane_uses_explicit_deterministic_direction():
    plan = _plan()
    plan["steps"] = [{
        "step_id": "return", "behavior": "RETURN_TO_LANE",
        "target": {
            "target_id": None, "target_lane": "CURRENT", "target_speed_mps": 3.0,
            "time_gap_s": None, "route_direction": None,
        },
        "preconditions": ["PERCEPTION_FRESH", "RIGHT_GAP_SAFE"],
        "completion": {"type": "LANE_CENTERED", "value": None, "lane": "CURRENT", "hold_frames": 5},
        "timeout_s": 8.0, "on_failure": "SAFE_STOP",
    }]
    compiled = PlanCompiler().compile(plan, scene={"return_direction": "RIGHT"})
    assert compiled.steps[0].behavior == "CHANGE_LANE_RIGHT"
    assert compiled.steps[0].completion["lane"] == "CURRENT"
    assert compiled.steps[0].preconditions == (
        "PERCEPTION_FRESH", "RIGHT_GAP_SAFE", "RIGHT_LANE_EXISTS",
        "NO_EMERGENCY_RISK",
    )


def test_avoid_then_return_derives_opposite_direction_from_avoid_lane():
    plan = _plan()
    plan["steps"] = [
        {
            "step_id": "avoid", "behavior": "AVOID_OBSTACLE",
            "target": {
                "target_id": "obstacle-1", "target_lane": "LEFT_ADJACENT",
                "target_speed_mps": 3.0, "time_gap_s": None, "route_direction": None,
            },
            "preconditions": ["PERCEPTION_FRESH"],
            "completion": {
                "type": "TARGET_PASSED", "value": None,
                "lane": None, "hold_frames": 3,
            },
            "timeout_s": 8.0, "on_failure": "REPLAN",
        },
        {
            "step_id": "return", "behavior": "RETURN_TO_LANE",
            "target": {
                "target_id": None, "target_lane": "CURRENT",
                "target_speed_mps": 3.0, "time_gap_s": None,
                "route_direction": None,
            },
            "preconditions": ["PERCEPTION_FRESH", "RIGHT_GAP_SAFE"],
            "completion": {
                "type": "LANE_CENTERED", "value": None,
                "lane": "CURRENT", "hold_frames": 5,
            },
            "timeout_s": 8.0, "on_failure": "SAFE_STOP",
        },
    ]

    compiled = PlanCompiler().compile(plan, scene={"left_lane_exists": True})

    assert compiled.steps[-1].behavior == "CHANGE_LANE_RIGHT"
    assert compiled.steps[-1].target["target_lane"] == "CURRENT"
    assert "RIGHT_LANE_EXISTS" in compiled.steps[-1].preconditions
    assert "RIGHT_GAP_SAFE" in compiled.steps[-1].preconditions
    assert "NO_EMERGENCY_RISK" in compiled.steps[-1].preconditions
