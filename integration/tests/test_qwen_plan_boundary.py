from __future__ import annotations

import json
from pathlib import Path

import pytest

from integration.qwen_plan_adapter import (
    PLANNER_V2_SYSTEM_PROMPT,
    QwenPlanParseError,
    QwenPlannerV2Adapter,
    build_planner_v2_prompt,
    parse_maneuver_plan,
)
from runtime.complexity_router import ComplexityRouter


ROOT = Path(__file__).resolve().parents[2]


def _example(name):
    return json.loads((ROOT / "interfaces/examples" / f"{name}.json").read_text(encoding="utf-8"))


def _scene():
    scene = _example("perception_state")
    scene.update({
        "available_lanes": ["CURRENT", "LEFT_ADJACENT"],
        "left_lane_exists": True,
        "right_lane_exists": False,
        "left_gap_safe": True,
        "right_gap_safe": False,
        "route_available": True,
        "intersection_ahead": True,
        "stop_line_clear": True,
    })
    return scene


def test_prompt_contains_policy_and_input_without_answer_leakage():
    request = _example("model_request")
    command = {
        "source_text": request["source_text"], "intent": "FOLLOW",
        "parameters": {"target_id": request["targets"][0]["target_id"]},
        "confidence": 0.95,
    }
    routing = ComplexityRouter().decide(command, _example("perception_state"), {})
    prompt = build_planner_v2_prompt(request, routing, scene_capabilities=_scene())
    assert prompt.startswith(PLANNER_V2_SYSTEM_PROMPT)
    assert "throttle" in prompt and "Never output" in prompt
    assert request["request_id"] in prompt
    assert '"steps":[' not in prompt


@pytest.mark.parametrize("raw", [
    "```json\n{}\n```", "prefix {}", "{} suffix", "[]", "", b"\xff",
])
def test_parser_requires_one_bare_strict_json_object(raw):
    with pytest.raises(QwenPlanParseError):
        parse_maneuver_plan(raw)


def test_adapter_validates_and_compiles_model_output():
    request = _example("model_request")
    now = request["created_at_ns"]
    plan = _example("maneuver_plan")
    plan.update({
        "request_id": request["request_id"],
        "command_id": request["command_id"],
        "created_at_ns": now,
        "valid_until_ns": request["deadline_ns"],
    })
    command = {
        "source_text": "确认安全后向左变道", "intent": "CHANGE_LANE",
        "parameters": {"direction": "LEFT"}, "confidence": 0.95,
    }
    routing = ComplexityRouter().decide(command, _example("perception_state"), {})
    adapter = QwenPlannerV2Adapter(lambda _prompt, _image: json.dumps(plan, ensure_ascii=False))
    result = adapter.infer(request, routing=routing, scene=_scene())
    assert result.plan["schema_version"] == "2.0"
    assert result.compiled.steps[-1].behavior == "CHANGE_LANE_LEFT"
    assert adapter.last_error is None
