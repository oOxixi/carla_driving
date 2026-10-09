"""Clean a ``resource_samples.jsonl`` file written by the loop sampler.

The first version of the sampler used ``psutil.Process.cpu_percent(None)`` and
could land two ticks on top of each other when the machine was loaded, which
inflates the per-process CPU share exactly like B3-TEL-001.  This analyser drops
those collapsed windows (dt < 0.5 s) and reports mean / p95 / max over the
remaining samples, so the quoted numbers are defensible.

Usage::

    py -3.12 -m challenge.hil.carla.analyse_resource_samples --samples <jsonl> --out <json>
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

CPU_KEYS = (
    "system_cpu_percent",
    "carla_runner_cpu_percent",
    "student_service_cpu_percent",
)
RSS_KEYS = ("carla_runner_rss_mib", "student_service_rss_mib")


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]


def analyse(path: Path, *, minimum_window_s: float = 0.5) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    kept: list[dict] = []
    dropped = 0
    previous_ns: int | None = None
    for row in rows:
        stamp = row.get("monotonic_ns")
        if stamp is None:
            stamp = int(float(row.get("elapsed_s") or 0.0) * 1e9)
        if previous_ns is not None and (stamp - previous_ns) < minimum_window_s * 1e9:
            dropped += 1
            continue
        previous_ns = stamp
        kept.append(row)

    def stats(key: str) -> dict:
        values = [float(row[key]) for row in kept if isinstance(row.get(key), (int, float))]
        return {
            "n": len(values),
            "mean": (sum(values) / len(values)) if values else None,
            "p95": _percentile(values, 0.95),
            "max": max(values) if values else None,
        }

    rss_first = next(
        (row for row in kept if all(isinstance(row.get(k), (int, float)) for k in RSS_KEYS)),
        None,
    )
    rss_last = next(
        (row for row in reversed(kept) if all(isinstance(row.get(k), (int, float)) for k in RSS_KEYS)),
        None,
    )
    drift = None
    if rss_first and rss_last:
        drift = round(
            sum(float(rss_last[k]) for k in RSS_KEYS) - sum(float(rss_first[k]) for k in RSS_KEYS), 3
        )
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(path),
        "samples_total": len(rows),
        "samples_used": len(kept),
        "samples_dropped_collapsed_window": dropped,
        "observed_duration_s": (
            round((int(kept[-1].get("monotonic_ns") or 0) - int(kept[0].get("monotonic_ns") or 0)) / 1e9, 3)
            if len(kept) > 1 and kept[0].get("monotonic_ns") else
            (round(float(kept[-1].get("elapsed_s") or 0.0) - float(kept[0].get("elapsed_s") or 0.0), 3) if kept else 0.0)
        ),
        "cpu_percent": {key: stats(key) for key in CPU_KEYS},
        "rss_mib": {
            **{key: stats(key) for key in RSS_KEYS},
            "combined_drift_mib": drift,
        },
        "bpu_utilization": "NOT_MEASURED",
        "note": (
            "per-process CPU percentages (100 = one core); collapsed sampling windows dropped. "
            "The official heterogeneous-utilization formula and the BPU half belong to B2/A4."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--minimum-window-s", type=float, default=0.5)
    args = parser.parse_args()
    report = analyse(Path(args.samples), minimum_window_s=args.minimum_window_s)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
