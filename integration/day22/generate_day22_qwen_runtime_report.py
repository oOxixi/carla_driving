"""Generate a report for real Day22 Qwen runtime validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path(
    "integration/day22/day22_qwen_runtime_results.json"
)

DEFAULT_OUTPUT = Path(
    "integration/day22/day22_qwen_runtime_report.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )

    return parser.parse_args()


def parsed_qwen_action(record: dict[str, Any]) -> str | None:
    validation = record.get("qwen_validation", {})
    parsed = validation.get("parsed")

    if not isinstance(parsed, dict):
        return None

    action = parsed.get("action")

    if not isinstance(action, str):
        return None

    action = action.strip().upper()

    return action or None


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    records = json.loads(
        input_path.read_text(encoding="utf-8")
    )

    if not isinstance(records, list):
        raise TypeError("runtime results must be a JSON list")

    total = len(records)

    runtime_success = 0
    format_valid = 0
    action_valid = 0
    short_explanations = 0
    qwen_raw_correct = 0
    final_action_correct = 0
    final_confirmation_correct = 0
    image_cases = 0

    forbidden_cases: list[dict[str, Any]] = []
    hallucination_cases: list[dict[str, Any]] = []
    qwen_wrong_action_cases: list[dict[str, Any]] = []
    safety_override_cases: list[dict[str, Any]] = []
    runtime_error_cases: list[dict[str, Any]] = []
    latencies: list[float] = []

    for item in records:
        case_name = str(item.get("case", "UNKNOWN"))
        expected = str(
            item.get("expected_final_action", "")
        ).upper()

        validation = item.get("qwen_validation", {})
        final_decision = item.get("final_decision", {})

        if item.get("runtime_error") is None:
            runtime_success += 1

            latency = item.get("latency_s")
            if isinstance(latency, (int, float)):
                latencies.append(float(latency))
        else:
            runtime_error_cases.append({
                "case": case_name,
                "error": item.get("runtime_error"),
            })

        if item.get("multimodal_image_used") is True:
            image_cases += 1

        if validation.get("format_valid") is True:
            format_valid += 1

        if validation.get("action_valid") is True:
            action_valid += 1

        if validation.get("explanation_short") is True:
            short_explanations += 1

        forbidden = validation.get(
            "forbidden_control_fields",
            [],
        )

        if forbidden:
            forbidden_cases.append({
                "case": case_name,
                "fields": forbidden,
            })

        hallucinations = validation.get(
            "hallucination_flags",
            [],
        )

        if hallucinations:
            hallucination_cases.append({
                "case": case_name,
                "flags": hallucinations,
            })

        qwen_action = parsed_qwen_action(item)

        if qwen_action == expected:
            qwen_raw_correct += 1
        else:
            qwen_wrong_action_cases.append({
                "case": case_name,
                "expected": expected,
                "qwen_raw_action": qwen_action,
                "qwen_reason": (
                    validation.get("parsed", {}) or {}
                ).get(
                    "reason_zh",
                    (
                        validation.get("parsed", {}) or {}
                    ).get("reason"),
                ),
                "final_action": final_decision.get("action"),
                "final_source": final_decision.get(
                    "decision_source"
                ),
            })

        if item.get("final_action_correct") is True:
            final_action_correct += 1

        if item.get("final_confirmation_correct") is True:
            final_confirmation_correct += 1

        final_action = str(
            final_decision.get("action", "")
        ).upper()

        final_source = str(
            final_decision.get("decision_source", "")
        ).upper()

        if (
            qwen_action is not None
            and final_action != qwen_action
            and final_source != "QWEN"
        ):
            safety_override_cases.append({
                "case": case_name,
                "qwen_raw_action": qwen_action,
                "final_action": final_action,
                "final_source": final_source,
                "final_reason": final_decision.get(
                    "reason_zh"
                ),
            })

    report = {
        "schema_version": "1.1",
        "validation_type": "REAL_QWEN2_5_VL_RUNTIME",
        "total_cases": total,

        "runtime_success": runtime_success,
        "runtime_success_rate": (
            runtime_success / total if total else 0.0
        ),

        "multimodal_image_cases": image_cases,
        "text_only_cases": total - image_cases,

        "qwen_format_valid": format_valid,
        "qwen_format_valid_rate": (
            format_valid / total if total else 0.0
        ),

        "qwen_action_valid": action_valid,
        "qwen_action_valid_rate": (
            action_valid / total if total else 0.0
        ),

        "qwen_raw_action_correct": qwen_raw_correct,
        "qwen_raw_action_accuracy": (
            qwen_raw_correct / total if total else 0.0
        ),
        "qwen_wrong_action_cases": qwen_wrong_action_cases,

        "short_explanation_cases": short_explanations,
        "short_explanation_rate": (
            short_explanations / total if total else 0.0
        ),

        "forbidden_control_field_cases": forbidden_cases,
        "hallucination_cases": hallucination_cases,

        "safety_override_count": len(
            safety_override_cases
        ),
        "safety_override_cases": safety_override_cases,

        "final_action_correct": final_action_correct,
        "final_action_accuracy": (
            final_action_correct / total if total else 0.0
        ),

        "final_confirmation_correct": (
            final_confirmation_correct
        ),
        "final_confirmation_accuracy": (
            final_confirmation_correct / total
            if total
            else 0.0
        ),

        "runtime_error_cases": runtime_error_cases,

        "latency_s": {
            "count": len(latencies),
            "mean": (
                sum(latencies) / len(latencies)
                if latencies
                else None
            ),
            "max": max(latencies) if latencies else None,
            "min": min(latencies) if latencies else None,
        },

        "notes": [
            "Qwen raw semantic accuracy and final safety-covered accuracy are reported separately.",
            "A wrong Qwen action may be overridden by deterministic safety policy.",
            "Second-group control consumes only the final command.",
            "Model weights are local dependencies and are not committed to Git."
        ],
    }

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
