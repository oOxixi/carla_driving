"""Long-duration soak with a memory/temperature drift check and recovery probe.

Structure follows the repo's ``tools/run_long_stability.py``: wall-clock is the
acceptance contract, telemetry is sampled continuously, and the run only counts
as successful if a fresh probe still behaves normally afterwards.
"""

from __future__ import annotations

from datetime import datetime, timezone
import statistics
import time
from typing import Any, Callable, Sequence

from .replay import ReplayCase
from .run_io import write_csv, write_json, write_jsonl
from .runtime_adapter import PlannerRuntime
from .columns import MEMORY_COLUMNS, SOAK_COLUMNS
from .samplers import BackgroundMonitor, TelemetrySpec, sample_process_memory
from .stages import percentile


RESULT_COLUMNS = SOAK_COLUMNS


def _window(rows: Sequence[dict[str, Any]], key: str, *, head: bool) -> list[float]:
    values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
    if not values:
        return []
    size = max(1, len(values) // 10)
    return values[:size] if head else values[-size:]


def run_soak(
    runtime: PlannerRuntime,
    cases: Sequence[ReplayCase],
    *,
    run_id: str,
    duration_s: float,
    telemetry: TelemetrySpec | None = None,
    recovery_probe_cases: int = 10,
    progress: Callable[[str], None] | None = None,
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
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    deadline = started + float(duration_s)
    iteration = 0
    outcomes: dict[str, int] = {}
    latencies: list[float] = []
    rss_samples: list[tuple[float, float]] = []
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
                latencies.append(latency)
            try:
                memory = sample_process_memory()
                rss = float(memory["rss_kib"]) if memory["rss_kib"] is not None else None
            except Exception:  # pragma: no cover - platform guard
                rss = None
            elapsed = time.monotonic() - started
            if rss is not None:
                rss_samples.append((elapsed, rss))
            rows.append(
                {
                    "wall_time_utc": datetime.now(timezone.utc).isoformat(),
                    "monotonic_ns": time.perf_counter_ns(),
                    "iteration": iteration,
                    "outcome": outcome,
                    "latency_ms": latency,
                    "rss_kib": rss,
                    "power_w": "",
                    "bpu_percent": "",
                    "temperature_c": "",
                    "notes": trace.reason_code or "",
                }
            )
            iteration += 1
            if iteration % 50 == 0:
                emit(f"soak iteration {iteration} at {elapsed:.0f}s")
    finally:
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

    rss_head = _window([{"rss": value} for _, value in rss_samples], "rss", head=True)
    rss_tail = _window([{"rss": value} for _, value in rss_samples], "rss", head=False)
    drift_kib = (
        statistics.fmean(rss_tail) - statistics.fmean(rss_head)
        if rss_head and rss_tail
        else None
    )
    latency_head = latencies[: max(1, len(latencies) // 10)] if latencies else []
    latency_tail = latencies[-max(1, len(latencies) // 10) :] if latencies else []
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
            "overall_p95": percentile(latencies, 0.95),
            "overall_max": max(latencies) if latencies else None,
        },
        "memory_drift_kib": drift_kib,
        "memory_drift_ratio": (
            (drift_kib / statistics.fmean(rss_head)) if drift_kib is not None and rss_head else None
        ),
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
            "soak latency includes the per-iteration telemetry sampling used to "
            "detect drift; compare it with latency_raw.csv only as a trend, not "
            "as an absolute percentile"
        ),
    }
    return {"summary": summary, "rows": rows, "telemetry_rows": monitor}


def write_soak_files(run_dir, result: dict[str, Any]) -> dict[str, Any]:
    """Persist soak evidence under ``stability_logs/``."""
    monitor: BackgroundMonitor = result["telemetry_rows"]
    write_jsonl(run_dir.path("stability_logs", "soak.jsonl"), result["rows"])
    write_json(run_dir.path("stability_logs", "soak_summary.json"), result["summary"])
    write_csv(
        run_dir.path("stability_logs", "memory_during_soak.csv"),
        MEMORY_COLUMNS,
        monitor.memory_rows,
    )
    return result["summary"]


__all__ = ["run_soak", "write_soak_files", "RESULT_COLUMNS"]
