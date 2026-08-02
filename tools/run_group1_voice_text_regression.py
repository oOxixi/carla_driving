"""Run deterministic Group 1 task 5 NLU/safety regression from a voice manifest."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / "artifacts" / "group1_voice" / "manifests" / "data_short_clean_manifest.json"
)
DEFAULT_OUTPUT = ROOT / "artifacts" / "group1_voice" / "task5_text_regression_clean.json"


sys.path.insert(0, str(ROOT))
from voice_group.nlu_b2.parser import parse_command  # noqa: E402
from voice_group.vehicle_nlu.src.b1_service import process_asr_text  # noqa: E402


SAFETY_PROBES = [
    {
        "id": "unsafe_speed_120",
        "text": "速度设为120公里。",
        "expected_status": "unsafe",
        "expected_error": "UNSAFE_SLOT",
    },
    {
        "id": "conflict_lane_change",
        "text": "同时向左向右变道。",
        "expected_status": "conflict",
        "expected_error": "CONFLICT_SLOT",
    },
    {
        "id": "conflict_turn",
        "text": "到路口左转右转都行。",
        "expected_status": "conflict",
        "expected_error": "CONFLICT_SLOT",
    },
    {
        "id": "unknown_food_target",
        "text": "带我去吃饭。",
        "expected_status": "unknown",
        "expected_error": "B1_UNKNOWN",
    },
    {
        "id": "negated_stop",
        "text": "不要停车。",
        "expected_status": "unknown",
        "expected_error": "B1_UNKNOWN",
    },
]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else "unknown",
        "dirty": bool(status.stdout.strip()),
        "status": [line for line in status.stdout.splitlines() if line.strip()],
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return round(ordered[lower], 3)
    fraction = index - lower
    return round(ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction, 3)


def _latency_stats(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean_ms": round(statistics.fmean(values), 3) if values else None,
        "p95_ms": _percentile(values, 0.95),
        "p99_ms": _percentile(values, 0.99),
        "max_ms": round(max(values), 3) if values else None,
    }


def _run_text(text: str, request_id: str, asr_confidence: float | None) -> dict[str, Any]:
    b1 = process_asr_text(
        request_id=request_id,
        text=text,
        asr_confidence=asr_confidence,
    )
    b2 = parse_command(b1)
    return {"b1": b1, "b2": b2}


def _slots_match(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def _error_codes(command: dict[str, Any]) -> set[str]:
    return {item.get("code") for item in command.get("errors", [])}


def _record(item: dict[str, Any], asr_confidence: float) -> dict[str, Any]:
    started = time.perf_counter()
    result = _run_text(item["text"], item["id"], asr_confidence)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    b1 = result["b1"]
    b2 = result["b2"]
    expected_slots = item.get("slots") or {}
    expected_intent = item.get("intent", "UNKNOWN")
    intent_ok = b2.get("intent") == expected_intent
    slots_ok = _slots_match(b2.get("slots", {}), expected_slots)
    if expected_intent == "UNKNOWN":
        safety_ok = b2.get("status") != "valid"
    elif (
        expected_intent == "SET_SPEED"
        and isinstance(expected_slots.get("speed"), int)
        and expected_slots["speed"] > 80
    ):
        safety_ok = b2.get("status") == "unsafe"
    else:
        safety_ok = b2.get("status") == "valid"
    return {
        "id": item["id"],
        "source_id": item.get("source_id"),
        "language": item.get("lang"),
        "text": item["text"],
        "expected_intent": expected_intent,
        "actual_intent": b2.get("intent"),
        "expected_slots": expected_slots,
        "actual_slots": b2.get("slots", {}),
        "status": b2.get("status"),
        "reason": b2.get("reason"),
        "errors": b2.get("errors", []),
        "warnings": b2.get("warnings", []),
        "intent_ok": intent_ok,
        "slots_ok": slots_ok,
        "safety_ok": safety_ok,
        "latency": {
            "b1_ms": b1.get("latency_ms"),
            "b2_ms": b2.get("latency_ms"),
            "total_text_nlu_ms": elapsed_ms,
        },
    }


def _low_confidence_check(item: dict[str, Any], low_confidence: float) -> dict[str, Any]:
    result = _run_text(item["text"], f"{item['id']}__low_conf", low_confidence)
    b2 = result["b2"]
    return {
        "id": item["id"],
        "text": item["text"],
        "expected_intent": item.get("intent"),
        "actual_intent": b2.get("intent"),
        "status": b2.get("status"),
        "errors": b2.get("errors", []),
        "blocked": b2.get("status") == "low_confidence"
        and "LOW_ASR_CONFIDENCE" in _error_codes(b2),
    }


def _run_safety_probe(probe: dict[str, Any]) -> dict[str, Any]:
    result = _run_text(probe["text"], probe["id"], 1.0)
    b2 = result["b2"]
    status_ok = b2.get("status") == probe["expected_status"]
    error_ok = probe["expected_error"] in _error_codes(b2)
    return {
        **probe,
        "actual_intent": b2.get("intent"),
        "actual_status": b2.get("status"),
        "actual_errors": b2.get("errors", []),
        "passed": status_ok and error_ok,
    }


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    latency_values = {
        key: [
            float(record["latency"][key])
            for record in records
            if record.get("latency", {}).get(key) is not None
        ]
        for key in ("b1_ms", "b2_ms", "total_text_nlu_ms")
    }
    return {
        "total": total,
        "intent_accuracy": (
            round(sum(record["intent_ok"] for record in records) / total, 6)
            if total
            else 0.0
        ),
        "slot_accuracy": (
            round(sum(record["slots_ok"] for record in records) / total, 6)
            if total
            else 0.0
        ),
        "safety_contract_accuracy": (
            round(sum(record["safety_ok"] for record in records) / total, 6)
            if total
            else 0.0
        ),
        "status_distribution": dict(Counter(record["status"] for record in records)),
        "latency": {key: _latency_stats(values) for key, values in latency_values.items()},
    }


def _grouped_summary(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get(key))].append(record)
    return {name: _summarize(items) for name, items in sorted(grouped.items())}


def _markdown_report(report: dict[str, Any]) -> str:
    overall = report["overall"]
    gates = report["gates"]
    lines = [
        "# Group 1 Task 5 Text/Intent/Slot/Safety Regression",
        "",
        f"- Generated UTC: `{report['generated_at_utc']}`",
        f"- Manifest: `{report['manifest']}`",
        f"- Samples: `{overall['total']}`",
        f"- Intent accuracy: `{overall['intent_accuracy']:.2%}`",
        f"- Slot accuracy: `{overall['slot_accuracy']:.2%}`",
        f"- Safety contract accuracy: `{overall['safety_contract_accuracy']:.2%}`",
        f"- Low-confidence block rate: `{report['low_confidence']['block_rate']:.2%}`",
        f"- Safety rejection probe pass rate: `{report['safety_probes']['pass_rate']:.2%}`",
        "",
        "## Gates",
        "",
        f"- Intent >= `{gates['min_intent_accuracy']:.2%}`: `{gates['intent_pass']}`",
        f"- Slot >= `{gates['min_slot_accuracy']:.2%}`: `{gates['slot_pass']}`",
        f"- Low-confidence block = `100%`: `{gates['low_confidence_pass']}`",
        f"- Safety rejection = `100%`: `{gates['safety_rejection_pass']}`",
        f"- Overall pass: `{gates['overall_pass']}`",
        "",
        "## Latency",
        "",
        "| Stage | mean | P95 | P99 | max |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, label in (
        ("b1_ms", "B1 intent"),
        ("b2_ms", "B2 parser"),
        ("total_text_nlu_ms", "Text NLU total"),
    ):
        latency = overall["latency"][key]
        lines.append(
            f"| {label} | {latency['mean_ms']} ms | {latency['p95_ms']} ms | "
            f"{latency['p99_ms']} ms | {latency['max_ms']} ms |"
        )
    lines.extend(
        [
            "",
            "## Failure Samples",
            "",
        ]
    )
    failures = report["failures"][:20]
    if not failures:
        lines.append("- None")
    else:
        for failure in failures:
            lines.append(
                "- "
                f"`{failure['id']}` expected `{failure['expected_intent']}` got "
                f"`{failure['actual_intent']}` status `{failure['status']}` text `{failure['text']}`"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--asr-confidence", type=float, default=1.0)
    parser.add_argument("--low-asr-confidence", type=float, default=0.2)
    parser.add_argument("--min-intent-accuracy", type=float, default=0.98)
    parser.add_argument("--min-slot-accuracy", type=float, default=0.98)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.limit is not None:
        manifest = manifest[: args.limit]

    records = [_record(item, args.asr_confidence) for item in manifest]
    executable = [item for item in manifest if item.get("intent") != "UNKNOWN"]
    low_confidence = [
        _low_confidence_check(item, args.low_asr_confidence) for item in executable
    ]
    safety_probes = [_run_safety_probe(probe) for probe in SAFETY_PROBES]

    overall = _summarize(records)
    low_total = len(low_confidence)
    low_block_rate = (
        round(sum(item["blocked"] for item in low_confidence) / low_total, 6)
        if low_total
        else 0.0
    )
    safety_total = len(safety_probes)
    safety_pass_rate = (
        round(sum(item["passed"] for item in safety_probes) / safety_total, 6)
        if safety_total
        else 0.0
    )
    gates = {
        "min_intent_accuracy": args.min_intent_accuracy,
        "min_slot_accuracy": args.min_slot_accuracy,
        "intent_pass": overall["intent_accuracy"] >= args.min_intent_accuracy,
        "slot_pass": overall["slot_accuracy"] >= args.min_slot_accuracy,
        "low_confidence_pass": low_block_rate == 1.0,
        "safety_rejection_pass": safety_pass_rate == 1.0,
    }
    gates["overall_pass"] = all(
        gates[key]
        for key in (
            "intent_pass",
            "slot_pass",
            "low_confidence_pass",
            "safety_rejection_pass",
        )
    )

    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest.resolve()),
        "git": _git_state(),
        "overall": overall,
        "by_language": _grouped_summary(records, "language"),
        "by_intent": _grouped_summary(records, "expected_intent"),
        "low_confidence": {
            "tested": low_total,
            "asr_confidence": args.low_asr_confidence,
            "blocked": sum(item["blocked"] for item in low_confidence),
            "block_rate": low_block_rate,
            "failures": [item for item in low_confidence if not item["blocked"]][:50],
        },
        "safety_probes": {
            "tested": safety_total,
            "passed": sum(item["passed"] for item in safety_probes),
            "pass_rate": safety_pass_rate,
            "records": safety_probes,
        },
        "gates": gates,
        "failures": [
            record
            for record in records
            if not (record["intent_ok"] and record["slots_ok"] and record["safety_ok"])
        ],
    }
    _write_json(args.output, report)
    args.output.with_suffix(".md").write_text(_markdown_report(report), encoding="utf-8")

    print(f"output={args.output}")
    print(f"intent_accuracy={overall['intent_accuracy']:.4f}")
    print(f"slot_accuracy={overall['slot_accuracy']:.4f}")
    print(f"low_confidence_block_rate={low_block_rate:.4f}")
    print(f"safety_rejection_pass_rate={safety_pass_rate:.4f}")
    print(f"overall_pass={gates['overall_pass']}")
    return 0 if gates["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
