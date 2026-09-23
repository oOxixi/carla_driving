"""Long-duration soak with a memory/temperature drift check and recovery probe.

Structure follows the repo's ``tools/run_long_stability.py``: wall-clock is the
acceptance contract, telemetry is sampled continuously, and the run only counts
as successful if a fresh probe still behaves normally afterwards.

Two accounting rules exist because a first 30-minute run got them wrong:

* the per-iteration records are **streamed to disk** when a ``row_path`` is given.
  Holding 100k records (plus latencies and RSS samples) in a list made the
  harness itself grow by ~60 MiB, and the soak then reported its own bookkeeping
  as "runtime memory drift";
* the drift is measured from the telemetry monitor's time-based samples, not from
  a per-iteration sample, so the number is bounded by the run's duration instead
  of by how fast the runtime happens to be.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import random
import statistics
import time
from collections import deque
from typing import Any, Callable, Sequence

from .replay import ReplayCase
from .run_io import write_csv, write_json, write_jsonl
from .runtime_adapter import PlannerRuntime
from .columns import MEMORY_COLUMNS, SOAK_COLUMNS
from .samplers import BackgroundMonitor, TelemetrySpec, sample_process_memory
from .stages import percentile


RESULT_COLUMNS = SOAK_COLUMNS

#: Bounded in-memory aggregates kept while a soak streams its rows to disk.
LATENCY_HEAD_SAMPLES = 2000
LATENCY_TAIL_SAMPLES = 2000
LATENCY_RESERVOIR_SAMPLES = 20000
DRIFT_SOURCE = "telemetry_1hz"


def _window(rows: Sequence[dict[str, Any]], key: str, *, head: bool) -> list[float]:
    values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
    if not values:
        return []
    size = max(1, len(values) // 10)
    return values[:size] if head else values[-size:]


def _rss_kib_safe() -> float | str:
    """Per-iteration RSS for non-streaming runs; empty when the platform balks."""
    try:
        memory = sample_process_memory()
    except Exception:  # pragma: no cover - platform guard
        return ""
    value = memory.get("rss_kib")
    return float(value) if value is not None else ""


def run_soak(
    runtime: PlannerRuntime,
    cases: Sequence[ReplayCase],
    *,
    run_id: str,
    duration_s: float,
    telemetry: TelemetrySpec | None = None,
    recovery_probe_cases: int = 10,
    progress: Callable[[str], None] | None = None,
    row_path: str | Path | None = None,
) -> dict[str, Any]:
    if not cases:
        raise ValueError("soak requires at least one case")
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")

    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    monitor = BackgroundMonitor(telemetry, run_id=run_id, round_index=0)
    monitor.start()
    rows: list[dict[str, Any]] | None = None if row_path else []
    row_handle = Path(row_path).open("w", encoding="utf-8") if row_path else None
    started = time.monotonic()
    deadline = started + float(duration_s)
    iteration = 0
    outcomes: dict[str, int] = {}
    latency_head: list[float] = []
    latency_tail: deque[float] = deque(maxlen=LATENCY_TAIL_SAMPLES)
    latency_reservoir: list[float] = []
    latency_max: float | None = None
    latency_seen = 0
    latencies: list[float] = []  # only the head window; see latency_head
    reservoir_rng = random.Random(20260911)
    try:
        while time.monotonic() < deadline:
            case = cases[iteration % len(cases)]
            plan, trace = runtime.infer(
                case.request, case_id=case.case_id, round_index=0, phase="measured"
            )
            durations = trace.durations_ms()
            latency = durations.get("planner_e2e_ms") or durations.get("model_only_ms")
            outcome = trace.outcome or "UNKNOWN"
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            if isinstance(latency, float):
                latency_seen += 1
                latency_max = latency if latency_max is None else max(latency_max, latency)
                if len(latency_head) < LATENCY_HEAD_SAMPLES:
                    latency_head.append(latency)
                latency_tail.append(latency)
                if len(latency_reservoir) < LATENCY_RESERVOIR_SAMPLES:
                    latency_reservoir.append(latency)
                else:
                    index = reservoir_rng.randrange(latency_seen)
                    if index < LATENCY_RESERVOIR_SAMPLES:
                        latency_reservoir[index] = latency
            elapsed = time.monotonic() - started
            row = {
                "wall_time_utc": datetime.now(timezone.utc).isoformat(),
                "monotonic_ns": time.perf_counter_ns(),
                "iteration": iteration,
                "outcome": outcome,
                "latency_ms": latency,
                "rss_kib": "",
                "power_w": "",
                "bpu_percent": "",
                "temperature_c": "",
                "notes": trace.reason_code or "",
            }
            if rows is None and row_handle is not None:
                row_handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            else:
                row["rss_kib"] = _rss_kib_safe()
                if rows is not None:
                    rows.append(row)
            iteration += 1
            if iteration % 50 == 0:
                emit(f"soak iteration {iteration} at {elapsed:.0f}s")
    finally:
        if row_handle is not None:
            row_handle.close()
        monitor.stop()
    observed_duration = time.monotonic() - started

    probe_latencies: list[float] = []
    probe_outcomes: dict[str, int] = {}
    for index in range(recovery_probe_cases):
        case = cases[index % len(cases)]
        _, trace = runtime.infer(
            case.request, case_id=case.case_id, round_index=0, phase="measured"
        )
        durations = trace.durations_ms()
        latency = durations.get("planner_e2e_ms") or durations.get("model_only_ms")
        if isinstance(latency, float):
            probe_latencies.append(latency)
        key = trace.outcome or "UNKNOWN"
        probe_outcomes[key] = probe_outcomes.get(key, 0) + 1

    # Drift comes from the monitor's time-based samples: that series is bounded by
    # the run's duration, so the number describes the runtime rather than the
    # harness's own bookkeeping.
    memory_rows = [
        row
        for row in getattr(monitor, "memory_rows", [])
        if isinstance(row.get("rss_kib"), (int, float))
    ]
    rss_head = _window(memory_rows, "rss_kib", head=True)
    rss_tail = _window(memory_rows, "rss_kib", head=False)
    drift_kib = (
        statistics.fmean(rss_tail) - statistics.fmean(rss_head)
        if rss_head and rss_tail
        else None
    )
    overall_latency = latency_reservoir
    overall_bounded = latency_seen > len(latency_reservoir)
    errors = sum(count for key, count in outcomes.items() if key != "READY")
    probe_errors = sum(count for key, count in probe_outcomes.items() if key != "READY")
    telemetry_summary = monitor.summary()
    summary = {
        "requested_duration_s": float(duration_s),
        "observed_duration_s": observed_duration,
        "duration_met": observed_duration >= float(duration_s),
        "iterations": iteration,
        "outcomes": outcomes,
        "error_count": errors,
        "success_rate": (iteration - errors) / iteration if iteration else None,
        "latency_ms": {
            "first_window_p95": percentile(latency_head, 0.95),
            "last_window_p95": percentile(latency_tail, 0.95),
            "overall_p95": percentile(overall_latency, 0.95),
            "overall_max": latency_max,
            "samples": latency_seen,
            "overall_percentiles_bounded": overall_bounded,
        },
        "memory_drift_kib": drift_kib,
        "memory_drift_ratio": (
            (drift_kib / statistics.fmean(rss_head)) if drift_kib is not None and rss_head else None
        ),
        "memory_drift_source": DRIFT_SOURCE,
        "memory_drift_window_samples": {"head": len(rss_head), "tail": len(rss_tail)},
        "recovery_probe": {
            "requests": recovery_probe_cases,
            "outcomes": probe_outcomes,
            "errors": probe_errors,
            "p95_ms": percentile(probe_latencies, 0.95),
        },
        "telemetry": telemetry_summary,
        "success": bool(
            observed_duration >= float(duration_s)
            and iteration > 0
            and errors == 0
            and probe_errors == 0
            and not telemetry_summary.get("errors")
        ),
        "criteria": [
            "wall-clock duration met",
            "no failed request during the soak",
            "recovery probe produced no failed request",
            "no telemetry sampling error",
        ],
        "latency_note": (
            "soak latency includes the telemetry sampling used to detect drift; "
            "compare it with latency_raw.csv only as a trend, not as an absolute "
            "percentile. overall_p95 comes from a bounded reservoir when the run "
            "produced more samples than the reservoir holds."
        ),
        "drift_note": (
            "memory_drift_kib is measured from the monitor's time-based RSS samples "
            "(memory_during_soak.csv), not from a per-iteration sample, so it is not "
            "inflated by the harness's own bookkeeping. No drift threshold is frozen "
            "yet (B2/A4 own the criterion): the number is reported, not judged."
        ),
    }
    return {
        "summary": summary,
        "rows": rows,
        "row_path": str(row_path) if row_path else None,
        "telemetry_rows": monitor,
    }


def write_soak_files(run_dir, result: dict[str, Any]) -> dict[str, Any]:
    """Persist soak evidence under ``stability_logs/``."""
    monitor: BackgroundMonitor = result["telemetry_rows"]
    target = run_dir.path("stability_logs", "soak.jsonl")
    rows = result.get("rows")
    if rows is None:
        # Streaming mode: the rows were written during the run, precisely so the
        # soak's own footprint stays flat.
        if not target.is_file():
            raise FileNotFoundError(f"soak rows were streamed but {target} is missing")
    else:
        write_jsonl(target, rows)
    write_json(run_dir.path("stability_logs", "soak_summary.json"), result["summary"])
    write_csv(
        run_dir.path("stability_logs", "memory_during_soak.csv"),
        MEMORY_COLUMNS,
        monitor.memory_rows,
    )
    return result["summary"]


__all__ = ["run_soak", "write_soak_files", "RESULT_COLUMNS"]
