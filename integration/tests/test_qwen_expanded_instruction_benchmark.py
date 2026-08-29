from __future__ import annotations

import json

import pytest

from tools.run_qwen_expanded_instruction_benchmark import (
    ACTION_TO_CODE,
    build_case_prompt,
    summarize_records,
)


def test_expanded_action_codes_cover_frozen_dataset() -> None:
    with open(
        "CARLA-Language-Benchmark/datasets/final_benchmark/"
        "CARLA_language_benchmark_v1_normalized.json",
        encoding="utf-8",
    ) as stream:
        records = json.load(stream)

    assert {record["expected_action"] for record in records} == set(ACTION_TO_CODE)
    assert len(set(ACTION_TO_CODE.values())) == 11


def test_case_prompt_exposes_only_instruction_and_scene() -> None:
    record = {
        "id": "hidden-id",
        "category": "hidden-category",
        "template": "向左变道",
        "semantic_intent": "hidden-intent",
        "scene_constraints": {"conflict_reason": "unsafe gap"},
        "expected_action": "KEEP_LANE",
        "expected_parameters": {"hidden": 1},
        "safety_policy": "override",
    }

    prompt = build_case_prompt(record)

    assert "向左变道" in prompt
    assert "unsafe gap" in prompt
    for hidden in (
        "hidden-id",
        "hidden-category",
        "hidden-intent",
        "KEEP_LANE",
        "override",
    ):
        assert hidden not in prompt


def test_summary_reports_accuracy_groups_confusion_and_latency() -> None:
    records = [
        {
            "status": "READY",
            "correct": True,
            "category": "ordinary",
            "safety_policy": "normal",
            "expected_action": "KEEP_LANE",
            "predicted_action": "KEEP_LANE",
            "latency_ms": 100.0,
            "queue_wait_ms": 10.0,
            "end_to_end_latency_ms": 110.0,
            "confidence": 0.9,
        },
        {
            "status": "READY",
            "correct": False,
            "category": "conflict",
            "safety_policy": "override",
            "expected_action": "STOP",
            "predicted_action": "KEEP_LANE",
            "latency_ms": 200.0,
            "queue_wait_ms": 20.0,
            "end_to_end_latency_ms": 220.0,
            "confidence": 0.6,
        },
    ]

    summary = summarize_records(records)

    assert summary["action_accuracy"] == 0.5
    assert summary["strict_parse_rate"] == 1.0
    assert summary["macro_category_accuracy"] == 0.5
    assert summary["request_latency_ms_under_configured_concurrency"][
        "p95_ms"
    ] == pytest.approx(195.0)
    assert summary["end_to_end_latency_ms_including_local_queue"][
        "p95_ms"
    ] == pytest.approx(214.5)
    assert summary["by_safety_policy"]["override"]["accuracy"] == 0.0
    assert summary["confusion_matrix"]["STOP"] == {"KEEP_LANE": 1}
