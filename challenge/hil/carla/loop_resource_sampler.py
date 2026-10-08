"""Sample host resource use while the Student loop runs.

The CPU half of "异构算力利用率" is measurable on the workstation: every second
this sampler records system CPU, and the CPU/RSS/threads of the two processes
that make up the loop (the CARLA runner and the Student decision service).
The BPU half needs the board or the vendor runtime, so it is only ever reported
as ``NOT_MEASURED`` here.

Usage::

    py -3.12 -m challenge.hil.carla.loop_resource_sampler \
        --duration-s 1800 --interval-s 1 --out <dir>

It writes ``resource_samples.jsonl`` (one row per tick) and
``resource_summary.json`` (drift, peaks, in-loop CPU share) next to each other.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


PROCESS_HINTS = (
    ("carla_runner", ("carla_runner",)),
    ("student_service", ("student_action_service",)),
)


def _match_processes() -> dict[str, list[psutil.Process]]:
    found: dict[str, list[psutil.Process]] = {name: [] for name, _ in PROCESS_HINTS}
    for process in psutil.process_iter(["pid", "cmdline", "name"]):
        try:
            cmdline = " ".join(process.info.get("cmdline") or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if not cmdline:
            continue
        for name, hints in PROCESS_HINTS:
            if any(hint in cmdline for hint in hints):
                found[name].append(process)
    return found


def sample(duration_s: float, interval_s: float, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "resource_samples.jsonl"
    psutil.cpu_percent(interval=None)
    handles: dict[int, psutil.Process] = {}
    cpu_state: dict[int, tuple[float, float]] = {}
    started = time.monotonic()
    rows: list[dict] = []
    with rows_path.open("w", encoding="utf-8") as stream:
        while time.monotonic() - started < duration_s:
            tick = time.monotonic()
            for process in _match_processes().values():
                for item in process:
                    handles.setdefault(item.pid, item)
            # ``py -3.12 -m tool`` spawns ``python.exe -m tool``: both match the
            # hint, and the launcher stub has a tiny RSS.  Keep the worker (the
            # matched process with the largest RSS) per hint instead of guessing
            # by parent/child direction, which previously dropped the worker.
            for _, hints in PROCESS_HINTS:
                candidates = []
                for pid, process in list(handles.items()):
                    try:
                        cmdline = " ".join(process.cmdline() or [])
                        if any(hint in cmdline for hint in hints):
                            candidates.append((process.memory_info().rss, pid))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        handles.pop(pid, None)
                if len(candidates) > 1:
                    candidates.sort(reverse=True)
                    for _, pid in candidates[1:]:
                        handles.pop(pid, None)
            row: dict = {
                "wall_time_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_s": round(tick - started, 3),
                "monotonic_ns": time.perf_counter_ns(),
                "system_cpu_percent": psutil.cpu_percent(interval=None),
                "system_cpu_count": psutil.cpu_count(),
            }
            for name, hints in PROCESS_HINTS:
                cpu = 0.0
                rss = 0.0
                threads = 0
                alive = 0
                measured = False
                for item in list(handles.values()):
                    try:
                        cmdline = " ".join(item.cmdline() or [])
                        if not any(hint in cmdline for hint in hints):
                            continue
                        # CPU from our own monotonic window: ``cpu_percent(None)``
                        # explodes when two ticks land close together on a
                        # loaded machine (documented as B3-TEL-001).
                        times = item.cpu_times()
                        total = float(times.user + times.system)
                        previous = cpu_state.get(item.pid)
                        cpu_state[item.pid] = (total, tick)
                        if previous is not None:
                            elapsed = tick - previous[1]
                            if elapsed >= 0.5 * interval_s:
                                cpu += 100.0 * (total - previous[0]) / elapsed
                                measured = True
                        rss += item.memory_info().rss / (1024 * 1024)
                        threads += item.num_threads()
                        alive += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        handles.pop(item.pid, None)
                        cpu_state.pop(item.pid, None)
                        continue
                row[f"{name}_processes"] = alive
                row[f"{name}_cpu_percent"] = round(cpu, 2) if measured else None
                row[f"{name}_rss_mib"] = round(rss, 2)
                row[f"{name}_threads"] = threads
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            rows.append(row)
            sleep_s = interval_s - (time.monotonic() - tick)
            if sleep_s > 0:
                time.sleep(sleep_s)

    def series(key: str) -> list[float]:
        return [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]

    def percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]

    def head_tail(key: str) -> tuple[float | None, float | None]:
        values = series(key)
        if len(values) < 10:
            return (values[0] if values else None, values[-1] if values else None)
        window = max(5, len(values) // 20)
        return (
            statistics.mean(values[:window]),
            statistics.mean(values[-window:]),
        )

    rss_series = series("student_service_rss_mib") + series("carla_runner_rss_mib")
    summary = {
        "samples": len(rows),
        "observed_duration_s": round(rows[-1]["elapsed_s"], 3) if rows else 0.0,
        "system_cpu_percent": {
            "mean": statistics.mean(series("system_cpu_percent")) if rows else None,
            "max": max(series("system_cpu_percent")) if rows else None,
        },
        "carla_runner_cpu_percent": {
            "mean": statistics.mean(series("carla_runner_cpu_percent")) if rows else None,
            "max": max(series("carla_runner_cpu_percent")) if rows else None,
            "p95": percentile(series("carla_runner_cpu_percent"), 0.95),
        },
        "student_service_cpu_percent": {
            "mean": statistics.mean(series("student_service_cpu_percent")) if rows else None,
            "max": max(series("student_service_cpu_percent")) if rows else None,
            "p95": percentile(series("student_service_cpu_percent"), 0.95),
        },
        "rss_mib": {
            "carla_runner_max": max(series("carla_runner_rss_mib"), default=None),
            "student_service_max": max(series("student_service_rss_mib"), default=None),
            "combined_drift_mib": (
                None if not rss_series else
                round(
                    (head_tail("student_service_rss_mib")[1] or 0.0)
                    + (head_tail("carla_runner_rss_mib")[1] or 0.0)
                    - (head_tail("student_service_rss_mib")[0] or 0.0)
                    - (head_tail("carla_runner_rss_mib")[0] or 0.0),
                    3,
                )
            ),
        },
        "bpu_utilization": "NOT_MEASURED",
        "note": (
            "CPU shares are per-process percentages (100 = one core). "
            "The official heterogeneous-utilization formula and the BPU half still "
            "belong to B2/A4; this file only supplies the CPU evidence."
        ),
    }
    (out_dir / "resource_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-s", type=float, default=1800.0)
    parser.add_argument("--interval-s", type=float, default=1.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    sample(args.duration_s, args.interval_s, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
