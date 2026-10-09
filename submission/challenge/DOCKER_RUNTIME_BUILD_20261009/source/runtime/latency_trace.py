"""Full-chain monotonic timestamp collection and percentile reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
from threading import Lock
import time
from typing import Any, Callable, Mapping


STAGES = (
    "audio_start",
    "vad_end",
    "asr_end",
    "nlu_end",
    "perception_ready",
    "qwen_start",
    "qwen_end",
    "planning_end",
    "arbitration_end",
    "action_apply",
)
STAGE_INDEX = {name: index for index, name in enumerate(STAGES)}


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _statistics(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": statistics.fmean(values) if values else None,
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "max": max(values) if values else None,
    }


@dataclass(slots=True)
class StageTrace:
    """One command trace; stages may be skipped but never reordered."""

    trace_id: str
    path_type: str
    clock_ns: Callable[[], int] = time.monotonic_ns
    timestamps_ns: dict[str, int] = field(default_factory=dict)
    outcome: str | None = None
    reason_code: str | None = None

    def mark(self, stage: str, *, timestamp_ns: int | None = None) -> int:
        if stage not in STAGE_INDEX:
            raise ValueError(f"unknown latency stage: {stage!r}")
        if stage in self.timestamps_ns:
            raise ValueError(f"latency stage already marked: {stage}")
        value = self.clock_ns() if timestamp_ns is None else timestamp_ns
        if type(value) is not int or value < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if self.timestamps_ns:
            last_stage = max(self.timestamps_ns, key=lambda item: STAGE_INDEX[item])
            if STAGE_INDEX[stage] <= STAGE_INDEX[last_stage]:
                raise ValueError(f"latency stage {stage} is out of order after {last_stage}")
            if value < self.timestamps_ns[last_stage]:
                raise ValueError("latency timestamps must be monotonic")
        self.timestamps_ns[stage] = value
        return value

    def finish(self, outcome: str, *, reason_code: str | None = None) -> None:
        if type(outcome) is not str or not outcome:
            raise ValueError("outcome must be non-empty")
        self.outcome = outcome
        self.reason_code = reason_code

    def durations_ms(self) -> dict[str, float]:
        marked = sorted(self.timestamps_ns, key=lambda name: STAGE_INDEX[name])
        durations: dict[str, float] = {}
        for first, second in zip(marked, marked[1:]):
            durations[f"{first}_to_{second}"] = (
                self.timestamps_ns[second] - self.timestamps_ns[first]
            ) / 1e6
        if "audio_start" in self.timestamps_ns and "action_apply" in self.timestamps_ns:
            durations["end_to_end"] = (
                self.timestamps_ns["action_apply"] - self.timestamps_ns["audio_start"]
            ) / 1e6
        if "nlu_end" in self.timestamps_ns and "action_apply" in self.timestamps_ns:
            durations["post_nlu_to_action"] = (
                self.timestamps_ns["action_apply"] - self.timestamps_ns["nlu_end"]
            ) / 1e6
        if "qwen_start" in self.timestamps_ns and "qwen_end" in self.timestamps_ns:
            durations["qwen_inference"] = (
                self.timestamps_ns["qwen_end"] - self.timestamps_ns["qwen_start"]
            ) / 1e6
        if "planning_end" in self.timestamps_ns and "arbitration_end" in self.timestamps_ns:
            durations["control_and_safety"] = (
                self.timestamps_ns["arbitration_end"] - self.timestamps_ns["planning_end"]
            ) / 1e6
        return durations

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "path_type": self.path_type,
            "timestamps_ns": dict(self.timestamps_ns),
            "durations_ms": self.durations_ms(),
            "outcome": self.outcome,
            "reason_code": self.reason_code,
        }


class LatencyCollector:
    """Thread-safe collection of completed command traces."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._lock = Lock()

    def add(self, trace: StageTrace) -> None:
        if not isinstance(trace, StageTrace):
            raise TypeError("trace must be StageTrace")
        if trace.outcome is None:
            raise ValueError("trace must be finished before collection")
        with self._lock:
            self._records.append(trace.to_dict())

    def report(self) -> dict[str, Any]:
        with self._lock:
            records = json.loads(json.dumps(self._records, allow_nan=False))
        metric_names = sorted({
            name for record in records for name in record["durations_ms"]
        })
        paths = sorted({str(record["path_type"]) for record in records})
        metrics: dict[str, Any] = {}
        for metric in metric_names:
            values = [
                float(record["durations_ms"][metric])
                for record in records
                if metric in record["durations_ms"]
            ]
            metrics[metric] = _statistics(values)
        by_path: dict[str, Any] = {}
        for path in paths:
            selected = [record for record in records if record["path_type"] == path]
            path_metrics: dict[str, Any] = {}
            for metric in metric_names:
                values = [
                    float(record["durations_ms"][metric])
                    for record in selected
                    if metric in record["durations_ms"]
                ]
                if values:
                    path_metrics[metric] = _statistics(values)
            by_path[path] = {"count": len(selected), "metrics_ms": path_metrics}
        return {
            "schema_version": "1.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "clock": "time.monotonic_ns",
            "trace_count": len(records),
            "metrics_ms": metrics,
            "by_path": by_path,
            "records": records,
        }

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.report(), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        return target


def summarize_latency_records(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Small utility for existing JSONL timestamps and benchmark scripts."""
    collector = LatencyCollector()
    for record in records:
        trace = StageTrace(str(record["trace_id"]), str(record["path_type"]))
        stamps = record.get("timestamps_ns", {})
        for stage in STAGES:
            if stage in stamps:
                trace.mark(stage, timestamp_ns=int(stamps[stage]))
        trace.finish(str(record.get("outcome", "UNKNOWN")), reason_code=record.get("reason_code"))
        collector.add(trace)
    return collector.report()


__all__ = [
    "STAGES",
    "LatencyCollector",
    "StageTrace",
    "summarize_latency_records",
]
