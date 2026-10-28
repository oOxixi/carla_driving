from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from qwen_service.service import QwenDecisionService
from qwen_service.task_understanding import (
    EXAMPLES, TaskUnderstandingPlanner, validate_extraction, evaluate_development_case,
    source_copy_schema,
    SequenceFirstUnderstandingPlanner,
)
from tools.qwen_planner_experiment import run_understand

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "先左转，再将车速设为30公里每小时"


def task():
    return {"steps": [
        {"evidence": "先左转", "action": "TURN_LEFT", "target_text": None,
         "direction": "LEFT", "speed_kph": None, "gap_m": None, "condition": None},
        {"evidence": "再将车速设为30公里每小时", "action": "SET_SPEED", "target_text": None,
         "direction": None, "speed_kph": 30, "gap_m": None, "condition": None},
    ], "prohibited_actions": {}, "requires_confirmation": False}


def planner(payload=None, *, raw=None, finish="stop"):
    calls = []
    content = raw if raw is not None else json.dumps(payload if payload is not None else task(), ensure_ascii=False)

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)])

    transport = SimpleNamespace(model_id="Qwen/Qwen3.5-2B", _client=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    return TaskUnderstandingPlanner(transport), calls


def test_understanding_preserves_two_model_steps_without_compilation():
    model, calls = planner()
    with pytest.raises(TypeError):
        QwenDecisionService(model)
    report = model.generate(SOURCE)
    assert report["validation"] == "INTENT_SCHEMA_PASS_ONLY"
    assert report["requested_tasks"] == task()
    assert report["ready_for_vehicle_execution"] is False
    assert report["image_sent"] is False
    assert "compiled_preview" not in report
    assert calls[0]["messages"][-1] == {"role": "user", "content": SOURCE}


def test_examples_are_literal_and_independent_of_development_labels():
    for text, steps, prohibitions in EXAMPLES:
        validate_extraction(text, {"steps": steps, "prohibited_actions": prohibitions, "requires_confirmation": False})
    cases = [json.loads(line) for line in (ROOT / "config/qwen_task_understanding_dev.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len({c["case_id"] for c in cases}) == len(cases) == 12
    assert not {c["source_text"] for c in cases}.intersection(text for text, _, _ in EXAMPLES)


@pytest.mark.parametrize("fault", ["evidence", "condition", "target", "prohibited", "control", "too_many"])
def test_bad_extraction_is_rejected_not_repaired(fault):
    payload = task()
    if fault == "evidence":
        payload["steps"][0]["evidence"] = "右转"
    elif fault == "condition":
        payload["steps"][1]["condition"] = "确认公交车已经离开"
    elif fault == "target":
        payload["steps"][0]["target_text"] = "actor_123"
    elif fault == "prohibited":
        payload["prohibited_actions"]["TURN_LEFT"] = True
    elif fault == "control":
        payload["steps"][0]["steer"] = 0.2
    else:
        payload["steps"] *= 5
    model, _ = planner(payload)
    report = model.generate(SOURCE)
    assert report["validation"] == "REJECTED"
    assert "requested_tasks" not in report


@pytest.mark.parametrize("finish", ["length", None])
def test_incomplete_generation_is_not_a_valid_task(finish):
    model, _ = planner(finish=finish)
    assert model.generate(SOURCE)["validation"] == "REJECTED"


def test_duplicate_keys_cannot_hide_a_step():
    model, _ = planner(raw='{"steps":[],"steps":[]}')
    assert model.generate(SOURCE)["validation"] == "REJECTED"


def test_labels_never_enter_model_prompt_and_task_hints_do_not_limit_intent():
    model, calls = planner()
    record = {"case_id": "DEV_PRIVATE_LABEL", "request": {
        "source_text": SOURCE, "command_hint": {"intent": "STOP"},
        "constraints": {"allowed_behaviors": ["STOP"]},
    }, "expected": {"action_sequences": [["TURN_LEFT", "SET_SPEED"]], "speed_kph": [None, 30]}}
    before = copy.deepcopy(record)
    report = list(run_understand([record], model))[0]
    assert report["development_evaluation"]["passed"] is True
    assert report["upstream_unavailable_actions"] == ["SET_SPEED", "TURN_LEFT"]
    prompt = json.dumps(calls[0]["messages"], ensure_ascii=False)
    assert "DEV_PRIVATE_LABEL" not in prompt
    assert "action_sequences" not in prompt
    assert "command_hint" not in prompt
    assert "allowed_behaviors" not in prompt
    assert record == before


def test_development_check_detects_missing_order_and_wrong_speed_without_filling():
    model, _ = planner()
    report = model.generate(SOURCE)
    expected = {"action_sequences": [["TURN_LEFT", "SET_SPEED"]], "speed_kph": [None, 30]}
    assert evaluate_development_case(report, expected)["passed"]
    missing = copy.deepcopy(report)
    missing["requested_tasks"]["steps"].pop()
    check = evaluate_development_case(missing, expected)
    assert not check["passed"] and not check["checks"]["step_count"]
    wrong = copy.deepcopy(report)
    wrong["requested_tasks"]["steps"].reverse()
    assert not evaluate_development_case(wrong, expected)["checks"]["action_order"]
    wrong = copy.deepcopy(report)
    wrong["requested_tasks"]["steps"][1]["speed_kph"] = 40
    assert not evaluate_development_case(wrong, expected)["checks"]["speed_kph"]


def test_literal_quote_is_not_claimed_to_prove_numeric_accuracy():
    payload = task()
    payload["steps"][1]["speed_kph"] = 50  # literal quote can be valid but extraction wrong
    model, _ = planner(payload)
    report = model.generate(SOURCE)
    assert report["validation"] == "INTENT_SCHEMA_PASS_ONLY"
    check = evaluate_development_case(report, {"action_sequences": [["TURN_LEFT", "SET_SPEED"]], "speed_kph": [None, 30]})
    assert not check["passed"]


def test_copy_grammar_contains_only_literal_spans_and_does_not_choose_tasks():
    schema = source_copy_schema(SOURCE)
    props = schema["properties"]["steps"]["items"]["properties"]
    for name in ("target_text", "condition"):
        assert all(value is None or value in SOURCE for value in props[name]["enum"])
        assert "恢复完成后" not in props[name]["enum"]
    assert props["action"]["enum"] == list(source_copy_schema("停车")["properties"]["steps"]["items"]["properties"]["action"]["enum"])
    assert "enum" not in source_copy_schema("前" * 257)["properties"]["steps"]["items"]["properties"]["condition"]


def test_self_referential_condition_is_rejected():
    payload = task()
    payload["steps"][1]["condition"] = payload["steps"][1]["evidence"]
    model, _ = planner(payload)
    assert model.generate(SOURCE)["validation"] == "REJECTED"


def test_review_never_receives_labels_or_repairs_missing_steps_in_code():
    answers = [task(), {**task(), "steps": task()["steps"][:1]}]
    calls = []

    def create(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(
            content=json.dumps(answers[len(calls) - 1], ensure_ascii=False)))])

    transport = SimpleNamespace(model_id="Qwen/Qwen3.5-2B", _client=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    model = TaskUnderstandingPlanner(transport, review_rounds=1)
    record = {"source_text": SOURCE, "expected": {"action_sequences": [["TURN_LEFT", "SET_SPEED"]]}}
    report = list(run_understand([record], model))[0]
    assert len(report["attempts"]) == 2
    assert len(report["requested_tasks"]["steps"]) == 1
    assert not report["development_evaluation"]["passed"]
    assert "action_sequences" not in json.dumps(calls)
    assert report["attempts"][0]["prompt_sha256"] != report["attempts"][1]["prompt_sha256"]
    assert len(calls[1]["messages"]) == 4


def test_review_error_preserves_first_attempt_without_fallback():
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            raise RuntimeError("transport failed")
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(task())))])

    transport = SimpleNamespace(model_id="Qwen/Qwen3.5-2B", _client=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    report = TaskUnderstandingPlanner(transport, review_rounds=1).generate(SOURCE)
    assert report["validation"] == "ERROR"
    assert len(report["attempts"]) == 2
    assert report["attempts"][0]["validation"] == "INTENT_SCHEMA_PASS_ONLY"
    assert "requested_tasks" not in report


def test_sequence_first_slots_come_from_model_not_evaluation_labels():
    outputs = [
        {"actions": ["TURN_LEFT", "SET_SPEED"], "prohibited_actions": {}, "requires_confirmation": False},
        {"step_1": task()["steps"][0], "step_2": task()["steps"][1]},
    ]
    calls = []

    def create(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(
            content=json.dumps(outputs[len(calls) - 1], ensure_ascii=False)))])

    transport = SimpleNamespace(model_id="Qwen/Qwen3.5-2B", _client=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    model = SequenceFirstUnderstandingPlanner(transport)
    with pytest.raises(TypeError):
        QwenDecisionService(model)
    result = list(run_understand([{"source_text": SOURCE, "expected": {
        "action_sequences": [["TURN_LEFT", "SET_SPEED"]]}}], model))[0]
    assert result["requested_tasks"] == task()
    assert result["development_evaluation"]["passed"]
    assert len(result["attempts"]) == 2
    wire = calls[1]["extra_body"]["structured_outputs"]["json"]
    assert wire["properties"]["step_2"]["properties"]["action"] == {"const": "SET_SPEED"}
    assert "action_sequences" not in json.dumps(calls)


def test_probe_cases_are_separate_from_examples_and_tuning_cases():
    dev = [json.loads(line) for line in (ROOT / "config/qwen_task_understanding_dev.jsonl").read_text(encoding="utf-8").splitlines()]
    probe = [json.loads(line) for line in (ROOT / "config/qwen_task_understanding_probe.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(probe) == 4
    assert not {r["source_text"] for r in probe}.intersection(r["source_text"] for r in dev)
    assert not {r["source_text"] for r in probe}.intersection(t for t, _, _ in EXAMPLES)


def test_development_errors_are_scored_as_failures_not_dropped():
    class Broken:
        def generate(self, source_text):
            raise RuntimeError("model unavailable")

    row = list(run_understand([{"source_text": SOURCE, "expected": {
        "action_sequences": [["TURN_LEFT", "SET_SPEED"]]}}], Broken()))[0]
    assert row["validation"] == "ERROR"
    assert row["development_evaluation"]["passed"] is False
