from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from qwen_service.clause_understanding import (
    CLAUSE_EXAMPLES, ClauseFocusedUnderstandingPlanner, split_clauses,
)
from qwen_service.service import QwenDecisionService
from qwen_service.task_understanding import _example_step, validate_extraction
from tools.qwen_planner_experiment import run_understand


def frame(*steps, prohibited=None):
    return {"steps": list(steps), "prohibited_actions": prohibited or {}, "requires_confirmation": False}


def planner(outputs):
    calls = []

    def create(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        value = outputs[len(calls) - 1]
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(
            content=json.dumps(value, ensure_ascii=False)))])

    transport = SimpleNamespace(model_id="Qwen/Qwen3.5-2B", _client=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    return ClauseFocusedUnderstandingPlanner(transport), calls


def test_segmentation_is_only_punctuation_and_preserves_decimal_speed():
    assert split_clauses("看到路牌，速度20.5公里每小时；继续") == ["看到路牌", "速度20.5公里每小时", "继续"]
    assert split_clauses("停车前先回原车道") == ["停车前先回原车道"]


def test_authored_clause_examples_have_literal_support():
    for text, steps, prohibited in CLAUSE_EXAMPLES:
        if steps:
            validate_extraction(text, frame(*steps, prohibited=prohibited))


def test_empty_background_is_not_expanded_and_labels_never_reach_model():
    source = "路边有小朋友，先左转，再将速度设为30公里每小时"
    left = _example_step("先左转", "TURN_LEFT", direction="LEFT")
    speed = _example_step("再将速度设为30公里每小时", "SET_SPEED", speed_kph=30)
    model, calls = planner([frame(), frame(left), frame(speed), {"position_1": 0, "position_2": 1}])
    with pytest.raises(TypeError):
        QwenDecisionService(model)
    row = list(run_understand([{"case_id": "PRIVATE_DEV_LABEL", "source_text": source,
        "expected": {"action_sequences": [["TURN_LEFT", "SET_SPEED"]]}}], model))[0]
    assert row["development_evaluation"]["passed"]
    assert row["requested_tasks"]["steps"] == [left, speed]
    assert len(row["clause_frames"]) == 3
    assert row["ready_for_vehicle_execution"] is False
    assert "PRIVATE_DEV_LABEL" not in json.dumps(calls)
    assert "action_sequences" not in json.dumps(calls)


def test_model_not_source_order_controls_final_permutation():
    left = _example_step("先左转", "TURN_LEFT", direction="LEFT")
    speed = _example_step("再将速度设为30公里每小时", "SET_SPEED", speed_kph=30)
    model, _ = planner([frame(left), frame(speed), {"position_1": 1, "position_2": 0}])
    row = model.generate("先左转，再将速度设为30公里每小时")
    assert row["requested_tasks"]["steps"] == [speed, left]
    assert row["model_order"] == [1, 0]


def test_duplicate_model_order_is_rejected_not_deduplicated():
    left = _example_step("先左转", "TURN_LEFT")
    speed = _example_step("再将速度设为30公里每小时", "SET_SPEED", speed_kph=30)
    model, _ = planner([frame(left), frame(speed), {"position_1": 0, "position_2": 0}])
    row = model.generate("先左转，再将速度设为30公里每小时")
    assert row["validation"] == "REJECTED"
    assert "requested_tasks" not in row
    assert "permutation" in row["rejection_reason"]


def test_cross_clause_repetition_is_rejected():
    wrong = _example_step("再将速度设为30公里每小时", "SET_SPEED", speed_kph=30)
    model, _ = planner([frame(wrong)])
    row = model.generate("先左转，再将速度设为30公里每小时")
    assert row["validation"] == "REJECTED"
    assert "different clause" in row["rejection_reason"]


def test_background_only_never_gets_a_default_control_action():
    model, _ = planner([frame()])
    row = model.generate("路边有小朋友")
    assert row["validation"] == "REJECTED"
    assert "requested_tasks" not in row


def test_model_extracted_prohibitions_survive_background_frames():
    keep = _example_step("保持车道", "KEEP_LANE")
    model, calls = planner([frame(prohibited={"CHANGE_LANE_LEFT": True}), frame(keep)])
    row = model.generate("不要向左变道，保持车道")
    assert row["requested_tasks"]["prohibited_actions"] == {"CHANGE_LANE_LEFT": True}
    assert len(calls) == 2  # no unnecessary order call for one task


def test_failed_clause_never_falls_back_to_prior_partial_tasks():
    left = _example_step("先左转", "TURN_LEFT")
    model, _ = planner([frame(left), RuntimeError("unavailable")])
    row = model.generate("先左转，再设定车速")
    assert row["validation"] != "INTENT_SCHEMA_PASS_ONLY"
    assert len(row["attempts"]) == 2
    assert len(row["clause_frames"]) == 1
    assert "requested_tasks" not in row
