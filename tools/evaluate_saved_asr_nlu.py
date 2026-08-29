"""Re-evaluate saved ASR transcripts through the current NLU implementation.

This deliberately consumes ``asr_text`` rather than audio: it measures whether
NLU changes tolerate already-observed recognition errors without changing or
overstating ASR accuracy.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice_group.nlu_b2.parser import parse_command
from voice_group.vehicle_nlu.src.b1_service import process_asr_text


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def evaluate_saved_transcripts(
    payload: dict[str, Any], *, warmup: int = 20, latency_samples: int = 50,
) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    by_language: dict[str, Counter[str]] = defaultdict(Counter)
    failures: list[dict[str, Any]] = []
    records = list(payload.get("records", []))
    if records:
        for index in range(max(0, warmup)):
            record = records[index % len(records)]
            parse_command(process_asr_text(
                request_id=f"warmup-{index:03d}",
                text=str(record["asr_text"]),
                asr_confidence=1.0,
            ))
    latency_ms: list[float] = []

    for index, record in enumerate(records):
        started_ns = time.perf_counter_ns()
        result = parse_command(
            process_asr_text(
                request_id=f"saved-asr-{index:03d}",
                text=str(record["asr_text"]),
                asr_confidence=1.0,
            )
        )
        if len(latency_ms) < max(0, latency_samples):
            latency_ms.append((time.perf_counter_ns() - started_ns) / 1_000_000.0)
        expected_intent = str(record["expected_intent"])
        expected_slots = dict(record.get("expected_slots", {}))
        intent_ok = result["intent"] == expected_intent
        slots_ok = all(
            result["slots"].get(name) == value
            for name, value in expected_slots.items()
        )
        language = str(record.get("language", "unknown"))
        for stats in (totals, by_language[language]):
            stats["total"] += 1
            stats["intent_ok"] += int(intent_ok)
            stats["slots_ok"] += int(slots_ok)
        if not intent_ok or not slots_ok:
            failures.append(
                {
                    "id": record.get("id"),
                    "language": language,
                    "asr_text": record["asr_text"],
                    "expected_intent": expected_intent,
                    "predicted_intent": result["intent"],
                    "expected_slots": expected_slots,
                    "predicted_slots": result["slots"],
                }
            )

    def summary(stats: Counter[str]) -> dict[str, Any]:
        total = stats["total"]
        return {
            "total": total,
            "intent_accuracy": round(stats["intent_ok"] / total, 4) if total else 0.0,
            "slot_accuracy": round(stats["slots_ok"] / total, 4) if total else 0.0,
        }

    return {
        "overall": summary(totals),
        "by_language": {
            language: summary(stats)
            for language, stats in sorted(by_language.items())
        },
        "failures": failures,
        "source_asr": payload.get("overall", {}).get("asr_character_accuracy"),
        "nlu_latency_ms": {
            "warmup": max(0, warmup),
            "count": len(latency_ms),
            "mean": sum(latency_ms) / len(latency_ms) if latency_ms else None,
            "p50": _percentile(latency_ms, 0.50),
            "p95": _percentile(latency_ms, 0.95),
            "max": max(latency_ms) if latency_ms else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--failures", action="store_true")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--latency-samples", type=int, default=50)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = evaluate_saved_transcripts(
        payload, warmup=args.warmup, latency_samples=args.latency_samples,
    )
    if not args.failures:
        result.pop("failures", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
