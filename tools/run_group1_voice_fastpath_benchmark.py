"""Benchmark Group 1 task 6 NLU fast path and cascade trigger policy."""

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
DEFAULT_OUTPUT = ROOT / "artifacts" / "group1_voice" / "task6_fastpath_clean.json"


sys.path.insert(0, str(ROOT))
from voice_group.asr_cascade import needs_verification  # noqa: E402
from voice_group.nlu_b2.parser import parse_command  # noqa: E402
from voice_group.vehicle_nlu.src.b1_service import process_asr_text  # noqa: E402


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


def _verification_reason(command: dict[str, Any]) -> str:
    intent = str(command.get("intent", "")).upper()
    if intent in {
        "SET_SPEED",
        "CHANGE_LANE",
        "PULL_OVER",
        "AVOID_OBSTACLE",
        "TURN",
        "SLOW_DOWN",
        "SPEED_UP",
    }:
        return "risky_intent"
    if any(char.isdigit() for char in str(command.get("source_text", ""))):
        return "numeric_text"
    if command.get("status") != "valid" and intent != "UNKNOWN":
        return "invalid_non_unknown"
    return "fast_path"


def _run_item(item: dict[str, Any], asr_confidence: float) -> dict[str, Any]:
    started = time.perf_counter()
    b1 = process_asr_text(
        request_id=item["id"],
        text=item["text"],
        asr_confidence=asr_confidence,
    )
    b2 = parse_command(b1)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    command = {
        "source_text": item["text"],
        "intent": b2.get("intent"),
        "parameters": b2.get("slots", {}),
        "status": b2.get("status"),
        "confirm_required": b2.get("status") != "valid",
    }
    verification = needs_verification(command)
    return {
        "id": item["id"],
        "source_id": item.get("source_id"),
        "language": item.get("lang"),
        "expected_intent": item.get("intent"),
        "actual_intent": b2.get("intent"),
        "status": b2.get("status"),
        "text": item["text"],
        "verification_triggered": verification,
        "verification_reason": _verification_reason(command) if verification else "fast_path",
        "latency": {
            "b1_ms": b1.get("latency_ms"),
            "b2_ms": b2.get("latency_ms"),
            "total_text_nlu_ms": elapsed_ms,
        },
    }


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    triggered = sum(record["verification_triggered"] for record in records)
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
        "fast_path_count": total - triggered,
        "verification_triggered": triggered,
        "verification_trigger_rate": round(triggered / total, 6) if total else 0.0,
        "by_status": dict(Counter(record["status"] for record in records)),
        "by_reason": dict(Counter(record["verification_reason"] for record in records)),
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
        "# Group 1 Task 6 Fast-Path Benchmark",
        "",
        f"- Generated UTC: `{report['generated_at_utc']}`",
        f"- Manifest: `{report['manifest']}`",
        f"- Samples: `{overall['total']}`",
        f"- Fast path: `{overall['fast_path_count']}`",
        f"- Verification triggered: `{overall['verification_triggered']}` (`{overall['verification_trigger_rate']:.2%}`)",
        f"- Text NLU P95: `{overall['latency']['total_text_nlu_ms']['p95_ms']} ms`",
        f"- Text NLU <= `{gates['text_nlu_p95_target_ms']} ms`: `{gates['text_nlu_p95_pass']}`",
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
            "## Trigger Reasons",
            "",
            "| Reason | Count |",
            "|---|---:|",
        ]
    )
    for reason, count in sorted(overall["by_reason"].items()):
        lines.append(f"| {reason} | {count} |")
    lines.extend(
        [
            "",
            "## ASR+NLU Note",
            "",
            "- This benchmark validates the resident B1/B2 fast path and cascade policy only.",
            "- Final ASR+NLU P95 evidence should be produced by `tools/evaluate_voice_audio.py` on a machine with SenseVoice/FunASR runtime available.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--asr-confidence", type=float, default=1.0)
    parser.add_argument("--text-nlu-p95-target-ms", type=float, default=60.0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.limit is not None:
        manifest = manifest[: args.limit]

    records = [_run_item(item, args.asr_confidence) for item in manifest]
    overall = _summarize(records)
    text_p95 = overall["latency"]["total_text_nlu_ms"]["p95_ms"]
    gates = {
        "text_nlu_p95_target_ms": args.text_nlu_p95_target_ms,
        "text_nlu_p95_pass": (
            text_p95 is not None and text_p95 <= args.text_nlu_p95_target_ms
        ),
        "cascade_policy_present": True,
        "overall_pass": (
            text_p95 is not None and text_p95 <= args.text_nlu_p95_target_ms
        ),
    }
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest.resolve()),
        "git": _git_state(),
        "overall": overall,
        "by_language": _grouped_summary(records, "language"),
        "by_intent": _grouped_summary(records, "expected_intent"),
        "gates": gates,
        "sample_records": records[:50],
    }
    _write_json(args.output, report)
    args.output.with_suffix(".md").write_text(_markdown_report(report), encoding="utf-8")

    print(f"output={args.output}")
    print(f"text_nlu_p95_ms={text_p95}")
    print(f"verification_triggered={overall['verification_triggered']}")
    print(f"verification_trigger_rate={overall['verification_trigger_rate']:.4f}")
    print(f"overall_pass={gates['overall_pass']}")
    return 0 if gates["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
