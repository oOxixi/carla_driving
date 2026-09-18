"""Measure how much of A3 Val can be solved by request hints without RGB."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

from challenge.student.preprocess import _expanded_allowed_behaviors

from .dataset import load_jsonl
from .label_encoder import DistillationLabelEncoder


def _first_behavior(row: Mapping[str, Any]) -> str:
    teacher = row.get("teacher")
    plan = teacher.get("maneuver_plan") if isinstance(teacher, Mapping) else None
    plan = plan or row.get("teacher_plan") or row.get("maneuver_plan")
    return str(plan["steps"][0]["behavior"])


def _request(row: Mapping[str, Any]) -> Mapping[str, Any]:
    request = row.get("input", row.get("model_request"))
    if not isinstance(request, Mapping):
        raise ValueError("record lacks ModelRequest V1")
    return request


def _hint_behavior(request: Mapping[str, Any]) -> str | None:
    hint = request.get("command_hint") or {}
    intent = str(hint.get("intent") or "").upper()
    direction = str(hint.get("direction") or "").upper()
    if intent == "EMERGENCY_STOP":
        return "STOP"
    if intent in {"TURN", "CHANGE_LANE"} and direction in {"LEFT", "RIGHT"}:
        return f"{intent}_{direction}"
    if intent in {"TURN", "CHANGE_LANE"}:
        return None
    return intent or None


def _plan_signature(row: Mapping[str, Any], encoder: DistillationLabelEncoder) -> tuple[Any, ...]:
    teacher = row.get("teacher")
    plan = teacher.get("maneuver_plan") if isinstance(teacher, Mapping) else None
    plan = plan or row.get("teacher_plan") or row.get("maneuver_plan")
    labels = encoder.encode(_request(row), plan)
    active = range(sum(labels["step_mask"]))
    return (
        labels["plan_length"],
        tuple(
            (
                labels["behavior"][index],
                labels["target_pointer"][index],
                labels["target_lane"][index],
                labels["completion_type"][index],
                labels["on_failure"][index],
            )
            for index in active
        ),
    )


def probe_records(
    train_rows: list[Mapping[str, Any]],
    val_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    train_texts = {str(_request(row)["source_text"]) for row in train_rows}
    train_scenarios = {str(row.get("metadata", {}).get("scenario_id")) for row in train_rows}
    train_first = Counter(_first_behavior(row) for row in train_rows)
    majority = train_first.most_common(1)[0][0]
    encoder = DistillationLabelEncoder()
    text_plan_counts: dict[str, Counter[tuple[Any, ...]]] = {}
    for row in train_rows:
        text_plan_counts.setdefault(str(_request(row)["source_text"]), Counter())[
            _plan_signature(row, encoder)
        ] += 1
    counts: Counter[str] = Counter()
    for row in val_rows:
        request = _request(row)
        teacher = _first_behavior(row)
        allowed = _expanded_allowed_behaviors(request)
        hint = _hint_behavior(request)
        if len(allowed) == 1:
            counts["singleton_allowed"] += 1
            counts["singleton_allowed_correct"] += int(next(iter(allowed)) == teacher)
        if hint is not None:
            counts["resolved_hint"] += 1
            counts["resolved_hint_correct"] += int(hint == teacher)
        prediction = next(iter(allowed)) if len(allowed) == 1 else (hint or majority)
        counts["rule_correct"] += int(prediction == teacher)
        counts["text_seen_in_train"] += int(str(request["source_text"]) in train_texts)
        counts["scenario_seen_in_train"] += int(
            str(row.get("metadata", {}).get("scenario_id")) in train_scenarios
        )
        plans_for_text = text_plan_counts.get(str(request["source_text"]))
        if plans_for_text:
            counts["text_only_plan_covered"] += 1
            predicted_plan = plans_for_text.most_common(1)[0][0]
            counts["text_only_plan_correct"] += int(
                predicted_plan == _plan_signature(row, encoder)
            )
    total = len(val_rows)
    return {
        "train_samples": len(train_rows),
        "val_samples": total,
        "train_unique_source_texts": len(train_texts),
        "val_unique_source_texts": len({str(_request(row)["source_text"]) for row in val_rows}),
        "val_text_seen_in_train": counts["text_seen_in_train"],
        "val_scenario_seen_in_train": counts["scenario_seen_in_train"],
        "val_singleton_allowed": counts["singleton_allowed"],
        "val_singleton_allowed_correct": counts["singleton_allowed_correct"],
        "val_resolved_hint": counts["resolved_hint"],
        "val_resolved_hint_correct": counts["resolved_hint_correct"],
        "val_rule_first_behavior_correct": counts["rule_correct"],
        "val_rule_first_behavior_accuracy": counts["rule_correct"] / total,
        "val_text_only_plan_covered": counts["text_only_plan_covered"],
        "val_text_only_plan_correct": counts["text_only_plan_correct"],
        "val_text_only_plan_accuracy_on_covered": (
            counts["text_only_plan_correct"] / counts["text_only_plan_covered"]
            if counts["text_only_plan_covered"] else None
        ),
        "note": (
            "These are no-RGB request-hint/text-lookup baselines, not a Student or "
            "Teacher comparison. The text-only signature uses the same categorical "
            "plan fields as plan_sequence_accuracy, excluding numeric speed. "
            "Shared templates are diagnostic, not "
            "proof of split leakage."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit request-hint shortcuts in A3 D2 Val")
    parser.add_argument("--view-dir", type=Path, default=Path("artifacts/a3_d2_v1_1_positive_view_v1"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/a3_d2_prep/shortcut_probe.json"))
    args = parser.parse_args()
    report = probe_records(
        load_jsonl(args.view_dir / "train.jsonl"),
        load_jsonl(args.view_dir / "val.jsonl"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
