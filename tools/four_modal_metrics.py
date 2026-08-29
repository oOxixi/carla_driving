"""Metric policy for the four-modal real-model benchmark."""
from __future__ import annotations

from collections import Counter
import math
import re
import statistics
from typing import Any, Callable


def summarize_latency(values: list[float]) -> dict[str, float]:
    """Return the fixed, nearest-rank timing summary used by gates."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("latency sample list is empty")

    def percentile(quantile: float) -> float:
        return ordered[min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1)]

    return {
        "count": len(ordered),
        "mean": statistics.fmean(ordered),
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": ordered[-1],
    }


def evaluate_official_gates(metrics: dict[str, object]) -> dict[str, object]:
    """Apply latency gates before the accuracy and stability phases."""
    end_to_end = metrics["end_to_end_ms"]
    if not isinstance(end_to_end, dict):
        raise ValueError("end_to_end_ms must be a timing summary")
    p95 = float(end_to_end["p95"])
    if p95 > 300.0:
        return {
            "status": "EARLY_STOP",
            "reason": "end_to_end_p95_over_300ms",
            "run_accuracy": False,
            "run_stability": False,
        }
    return {
        "status": "CONTINUE",
        "reason": None,
        "run_accuracy": True,
        "run_stability": p95 <= 150.0,
    }


def evaluate_official_verdict(
    metrics: dict[str, object],
    accuracy: dict[str, object],
    *,
    scenario_completion: float | None,
) -> dict[str, object]:
    """Aggregate only measured official thresholds without inventing scenarios."""
    instruction = metrics["instruction_parse_ms"]
    end_to_end = metrics["end_to_end_ms"]
    if not isinstance(instruction, dict) or not isinstance(end_to_end, dict):
        raise ValueError("timing summaries must be dictionaries")
    asr = accuracy.get("asr")
    multimodal = accuracy.get("multimodal")
    if not isinstance(asr, dict) or not isinstance(multimodal, dict):
        raise ValueError("accuracy must include ASR and multimodal summaries")
    asr_score = asr.get("intent_accuracy")
    multimodal_score = multimodal.get("action_target_contract_accuracy")
    gates: dict[str, bool | None] = {
        "instruction_parse_p95_le_50ms": float(instruction["p95"]) <= 50.0,
        "end_to_end_p95_le_150ms": float(end_to_end["p95"]) <= 150.0,
        "asr_intent_accuracy_ge_95pct": (
            None if asr_score is None else float(asr_score) >= 0.95
        ),
        "multimodal_action_target_accuracy_ge_98pct": (
            None if multimodal_score is None else float(multimodal_score) >= 0.98
        ),
        "scenario_completion_ge_90pct": (
            None if scenario_completion is None else scenario_completion >= 0.90
        ),
    }
    missing = [name for name, passed in gates.items() if passed is None]
    failures = [name for name, passed in gates.items() if passed is False]
    if float(end_to_end["p95"]) > 300.0:
        status = "EARLY_STOP"
    elif missing:
        status = "INCOMPLETE"
    elif failures:
        status = "FAIL"
    else:
        status = "PASS"
    return {
        "status": status,
        "passes": status == "PASS",
        "gates": gates,
        "missing": missing,
        "failures": failures,
        "thresholds": {
            "instruction_parse_p95_ms_max": 50.0,
            "end_to_end_p95_ms_max": 150.0,
            "asr_intent_accuracy_min": 0.95,
            "multimodal_action_target_accuracy_min": 0.98,
            "scenario_completion_min": 0.90,
        },
    }


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _latency(values: list[float]) -> dict[str, float | None]:
    return {
        "mean_ms": statistics.fmean(values) if values else None,
        "p50_ms": _percentile(values, 0.50),
        "p95_ms": _percentile(values, 0.95),
        "p99_ms": _percentile(values, 0.99),
        "max_ms": max(values) if values else None,
    }


def _is_safety_fault(record: dict[str, Any]) -> bool:
    return bool(record.get("expected", {}).get("safety_expectation"))


def _contract_pass(record: dict[str, Any]) -> bool:
    if _is_safety_fault(record):
        return bool(record["checks"]["safety"])
    return bool(record["checks"]["all"] and record["checks"]["safety"])


def _raw_target_ok(record: dict[str, Any]) -> bool:
    expected = record.get("expected", {}).get("target_track_id")
    if expected is None:
        return True
    grounding = record.get("target_grounding") or {}
    raw_target = grounding.get("qwen_target_track_id")
    if "qwen_target_track_id" not in grounding:
        raw_target = (record.get("decision") or {}).get("target_track_id")
    return raw_target == expected


def _asr_exact(record: dict[str, Any]) -> bool:
    expected = str(record.get("expected_transcript", ""))
    actual = str(record.get("asr_transcript", ""))
    normalize = lambda text: re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
    return bool(expected) and normalize(expected) == normalize(actual)


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Separate answerable perception from deliberate safety fault injection."""
    if not records:
        raise ValueError("records must not be empty")
    answerable = [record for record in records if not _is_safety_fault(record)]
    safety_faults = [record for record in records if _is_safety_fault(record)]

    def ratio(
        subset: list[dict[str, Any]],
        predicate: Callable[[dict[str, Any]], bool],
    ) -> float | None:
        if not subset:
            return None
        return sum(bool(predicate(record)) for record in subset) / len(subset)

    categories: dict[str, dict[str, Any]] = {}
    for category in sorted({record["category"] for record in records}):
        subset = [
            record for record in records if record["category"] == category
        ]
        subset_answerable = [
            record for record in subset if not _is_safety_fault(record)
        ]
        subset_safety = [
            record for record in subset if _is_safety_fault(record)
        ]
        categories[category] = {
            "count": len(subset),
            "answerable_count": len(subset_answerable),
            "safety_fault_count": len(subset_safety),
            "ready_rate": ratio(
                subset, lambda record: record["status"] == "READY"
            ),
            "asr_exact_accuracy": ratio(subset, _asr_exact),
            "answerable_joint_accuracy": ratio(
                subset_answerable, lambda record: record["checks"]["all"]
            ),
            "answerable_target_association_accuracy": ratio(
                subset_answerable,
                lambda record: record["checks"]["target_association"],
            ),
            "raw_qwen_target_association_accuracy": ratio(
                subset_answerable, _raw_target_ok
            ),
            "safety_fault_fail_closed_accuracy": ratio(
                subset_safety, lambda record: record["checks"]["safety"]
            ),
            "full_chain_contract_accuracy": ratio(subset, _contract_pass),
        }
    return {
        "case_count": len(records),
        "answerable_case_count": len(answerable),
        "safety_fault_case_count": len(safety_faults),
        "status_counts": dict(
            Counter(record["status"] for record in records)
        ),
        "asr_exact_accuracy": ratio(records, _asr_exact),
        "voice_command_valid_rate": ratio(
            records,
            lambda record: (
                record.get("voice_command", {}).get("status") == "valid"
            ),
        ),
        "answerable_joint_accuracy": ratio(
            answerable, lambda record: record["checks"]["all"]
        ),
        "answerable_semantic_accuracy": ratio(
            answerable, lambda record: record["checks"]["action"]
        ),
        "answerable_target_association_accuracy": ratio(
            answerable,
            lambda record: record["checks"]["target_association"],
        ),
        "raw_qwen_target_association_accuracy": ratio(
            answerable, _raw_target_ok
        ),
        "grounding_correction_count": sum(
            (record.get("target_grounding") or {}).get("status")
            == "CORRECTED_UNIQUE"
            for record in records
        ),
        "answerable_confirmation_accuracy": ratio(
            answerable, lambda record: record["checks"]["confirmation"]
        ),
        "safety_fault_fail_closed_accuracy": ratio(
            safety_faults, lambda record: record["checks"]["safety"]
        ),
        "full_chain_contract_accuracy": ratio(records, _contract_pass),
        "latency": {
            key: _latency([
                float(record["latency_ms"][key]) for record in records
            ])
            for key in (
                "voice",
                "qwen",
                "post_qwen_control",
                "audio_to_final_control",
            )
        },
        "categories": categories,
    }
