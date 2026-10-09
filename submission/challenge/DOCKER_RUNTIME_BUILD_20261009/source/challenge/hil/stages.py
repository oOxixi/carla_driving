"""Challenge-chain latency instrumentation and percentile statistics.

Mirrors the collector conventions of `runtime/latency_trace.py` (monotonic
nanosecond marks, strictly increasing stage order, linear-interpolation
percentiles) without modifying that A-owned file.  The stage list differs on
purpose: this one describes the Student planner chain, not the voice chain.

Clock choice matters: on Windows ``time.monotonic_ns`` is backed by
``GetTickCount64`` and only advances every ~15.6 ms, which silently rounds a
sub-20 ms inference to zero.  The harness therefore uses
``time.perf_counter_ns``, which is high-resolution on both Windows and Linux,
and records the clock identity and resolution with every run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import statistics
import time
from typing import Any, Callable, Iterable, Mapping

from .columns import LATENCY_COLUMNS


STAGES: tuple[str, ...] = (
    "input_arrival",
    "preprocess_end",
    "packing_end",
    "inference_start",
    "inference_end",
    "postprocess_end",
    "adapter_end",
    "plan_ready",
)
STAGE_INDEX = {name: index for index, name in enumerate(STAGES)}

# (segment name, later stage, earlier stage)
_SEGMENTS: tuple[tuple[str, str, str], ...] = (
    ("preprocess_ms", "preprocess_end", "input_arrival"),
    ("packing_ms", "packing_end", "preprocess_end"),
    ("inference_setup_ms", "inference_start", "packing_end"),
    ("model_inference_ms", "inference_end", "inference_start"),
    ("postprocess_ms", "postprocess_end", "inference_end"),
    ("adapter_ms", "adapter_end", "postprocess_end"),
    ("plan_validation_ms", "plan_ready", "adapter_end"),
)

_ROLLUPS: tuple[tuple[str, str, str], ...] = (
    ("pre_model_ms", "inference_start", "input_arrival"),
    ("post_model_ms", "plan_ready", "inference_end"),
    ("planner_e2e_ms", "plan_ready", "input_arrival"),
)

SEGMENT_NAMES: tuple[str, ...] = tuple(name for name, _, _ in _SEGMENTS) + tuple(
    name for name, _, _ in _ROLLUPS
) + ("model_only_ms", "planner_overhead_ms")

CLOCK_SOURCE = "perf_counter_ns"


def clock_resolution_ns() -> float:
    """Resolution of the monotonic clock used for every latency mark."""
    return float(time.get_clock_info("perf_counter").resolution) * 1e9


def percentile(values: Iterable[float], quantile: float) -> float | None:
    """Linear interpolation percentile, matching runtime/latency_trace.py."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be within [0, 1]")
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def summarize(values: Iterable[float]) -> dict[str, float | int | None]:
    numbers = [float(value) for value in values]
    if not numbers:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "p99": None, "max": None}
    return {
        "count": len(numbers),
        "mean": statistics.fmean(numbers),
        "p50": percentile(numbers, 0.50),
        "p95": percentile(numbers, 0.95),
        "p99": percentile(numbers, 0.99),
        "max": max(numbers),
    }


class StageOrderError(ValueError):
    """A mark violated the declared stage order or monotonicity."""


@dataclass(slots=True)
class StageTrace:
    """One planner invocation's monotonic timestamps.

    Stages may be skipped (a rejected request never reaches ``plan_ready``) but
    must never be reordered or stamped with a decreasing clock value.
    """

    trace_id: str
    case_id: str = ""
    round_index: int = 0
    phase: str = "measured"
    clock_ns: Callable[[], int] = time.perf_counter_ns
    timestamps_ns: dict[str, int] = field(default_factory=dict)
    outcome: str | None = None
    reason_code: str | None = None
    outcome_detail: str | None = None
    stage_source: str = "INSTRUMENTED"
    clock_domain: str = "monotonic_host"

    def __post_init__(self) -> None:
        if not isinstance(self.trace_id, str) or not self.trace_id:
            raise ValueError("trace_id must be a non-empty string")
        if self.phase not in {"warmup", "measured"}:
            raise ValueError("phase must be 'warmup' or 'measured'")
        if self.stage_source not in {"INSTRUMENTED", "NOT_INSTRUMENTED", "PARTIAL"}:
            raise ValueError("unsupported stage_source")

    def mark(self, stage: str, timestamp_ns: int | None = None) -> int:
        if stage not in STAGE_INDEX:
            raise ValueError(f"unknown latency stage: {stage!r}")
        if stage in self.timestamps_ns:
            raise StageOrderError(f"stage already marked: {stage}")
        value = self.clock_ns() if timestamp_ns is None else timestamp_ns
        if type(value) is not int or value < 0:
            raise StageOrderError("timestamp_ns must be a non-negative integer")
        if self.timestamps_ns:
            last = max(self.timestamps_ns, key=lambda name: STAGE_INDEX[name])
            if STAGE_INDEX[stage] <= STAGE_INDEX[last]:
                raise StageOrderError(f"{stage} is out of order after {last}")
            if value < self.timestamps_ns[last]:
                raise StageOrderError("timestamps must be non-decreasing")
        self.timestamps_ns[stage] = value
        return value

    def finish(
        self,
        outcome: str,
        *,
        reason_code: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Close the trace.

        ``outcome="READY"`` has exactly one meaning on every chain: **a plan was
        produced**.  Whether that plan passed a `PlanValidator` is *not* encoded
        here — it is recorded by the chain's capabilities (`full_chain`,
        `plan_validator`) and, for chains without a validator, spelled out in
        ``outcome_detail`` (``plan_validated=false``).  Keeping those two facts
        apart is what stops "READY" from quietly meaning different things per
        adapter.
        """
        if not isinstance(outcome, str) or not outcome:
            raise ValueError("outcome must be a non-empty string")
        self.outcome = outcome
        self.reason_code = reason_code
        self.outcome_detail = detail

    def durations_ms(self) -> dict[str, float]:
        durations: dict[str, float] = {}
        for name, later, earlier in _SEGMENTS:
            if later in self.timestamps_ns and earlier in self.timestamps_ns:
                durations[name] = (
                    self.timestamps_ns[later] - self.timestamps_ns[earlier]
                ) / 1e6
        for name, later, earlier in _ROLLUPS:
            if later in self.timestamps_ns and earlier in self.timestamps_ns:
                durations[name] = (
                    self.timestamps_ns[later] - self.timestamps_ns[earlier]
                ) / 1e6
        if "model_inference_ms" in durations:
            durations["model_only_ms"] = durations["model_inference_ms"]
        if "planner_e2e_ms" in durations and "model_only_ms" in durations:
            durations["planner_overhead_ms"] = (
                durations["planner_e2e_ms"] - durations["model_only_ms"]
            )
        return durations

    def missing_stages(self) -> tuple[str, ...]:
        return tuple(name for name in STAGES if name not in self.timestamps_ns)

    def to_csv_row(
        self,
        *,
        run_id: str,
        identity: Mapping[str, str],
        wall_time_utc: str | None = None,
    ) -> dict[str, Any]:
        durations = self.durations_ms()
        row: dict[str, Any] = {
            "run_id": run_id,
            "round": self.round_index,
            "phase": self.phase,
            "case_id": self.case_id,
            "request_id": self.trace_id,
            "outcome": self.outcome or "",
            "reason_code": self.reason_code or "",
            "missing_stages": "|".join(self.missing_stages()),
            "stage_source": self.stage_source,
            "outcome_detail": self.outcome_detail or "",
            "wall_time_utc": wall_time_utc or datetime.now(timezone.utc).isoformat(),
        }
        for name in STAGES:
            row[f"t{STAGE_INDEX[name]}_{name}_ns"] = self.timestamps_ns.get(name, "")
        for name in SEGMENT_NAMES:
            row[name] = durations.get(name, "")
        for key in ("git_sha", "model_id", "model_sha256", "dataset_version", "config_id"):
            row[key] = identity.get(key, "")
        return {column: row.get(column, "") for column in LATENCY_COLUMNS}

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "case_id": self.case_id,
            "round": self.round_index,
            "phase": self.phase,
            "timestamps_ns": dict(self.timestamps_ns),
            "durations_ms": self.durations_ms(),
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "outcome_detail": self.outcome_detail,
            "missing_stages": list(self.missing_stages()),
            "stage_source": self.stage_source,
            "clock_domain": self.clock_domain,
        }


class LatencyCollector:
    """Collect finished traces and aggregate them by phase and round."""

    def __init__(self) -> None:
        self._traces: list[StageTrace] = []

    def add(self, trace: StageTrace) -> None:
        if trace.outcome is None:
            raise ValueError("trace must be finished before collection")
        self._traces.append(trace)

    def __len__(self) -> int:
        return len(self._traces)

    def traces(self) -> tuple[StageTrace, ...]:
        return tuple(self._traces)

    def report(self, *, run_id: str, identity: Mapping[str, str]) -> dict[str, Any]:
        measured = [
            trace
            for trace in self._traces
            if trace.phase == "measured" and trace.outcome == "READY"
        ]
        warmup = [trace for trace in self._traces if trace.phase == "warmup"]
        rounds: dict[str, Any] = {}
        for round_index in sorted({trace.round_index for trace in measured}):
            selected = [trace for trace in measured if trace.round_index == round_index]
            rounds[str(round_index)] = {
                "count": len(selected),
                "metrics_ms": self._metrics(selected),
            }
        return {
            "schema_version": "1.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "clock": CLOCK_SOURCE,
            "clock_resolution_ns": clock_resolution_ns(),
            "run_id": run_id,
            "identity": dict(identity),
            "trace_count": len(self._traces),
            "measured_ready_count": len(measured),
            "warmup_count": len(warmup),
            "outcome_counts": self._outcome_counts(),
            "rounds": rounds,
            "metrics_ms": self._metrics(measured),
            "rows": [
                trace.to_csv_row(run_id=run_id, identity=identity)
                for trace in self._traces
            ],
        }

    def _metrics(self, traces: list[StageTrace]) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        for name in SEGMENT_NAMES:
            values = [
                trace.durations_ms()[name]
                for trace in traces
                if name in trace.durations_ms()
            ]
            if values:
                metrics[name] = summarize(values)
        return metrics

    def _outcome_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for trace in self._traces:
            key = trace.outcome or "UNFINISHED"
            counts[key] = counts.get(key, 0) + 1
        return counts


__all__ = [
    "STAGES",
    "STAGE_INDEX",
    "SEGMENT_NAMES",
    "StageTrace",
    "StageOrderError",
    "LatencyCollector",
    "percentile",
    "summarize",
]
