"""Aggregate what the Student-in-the-loop CARLA runs already recorded.

The repository runner writes one ``*.summary.json`` and one per-frame
``*.jsonl`` per scenario.  Those two files already contain everything B3 owns
for the scoring items that do not need a board:

* end-to-end latency inside the closed loop (perception -> control / trajectory,
  plus the model decision) -- the voice front end is not part of B3;
* semantic-action alignment (the scenario's own ``oracle_expected_behaviors``
  and related acceptance checks);
* driving-comfort proxies (longitudinal acceleration, jerk, lateral
  acceleration, steer rate) computed from the fixed-delta frame log;
* safety counters (collisions, red-light violations, route deviations,
  safety-override episodes).

Usage::

    py -3.12 -m challenge.hil.carla.summarise_student_loop \
        --runs <run_root> --out <json>
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LATENCY_KEYS = (
    "decision_avg_ms", "decision_p95_ms", "decision_p99_ms", "decision_max_ms",
    "sensor_to_control_avg_ms", "sensor_to_control_p95_ms", "sensor_to_control_p99_ms",
    "sensor_to_control_max_ms",
    "sensor_to_trajectory_avg_ms", "sensor_to_trajectory_p95_ms",
    "sensor_to_trajectory_max_ms",
    "qwen_model_avg_ms", "qwen_model_p95_ms",
    "perception_acquire_avg_ms", "pipeline_active_avg_ms", "simulator_tick_avg_ms",
)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _frame_metrics(path: Path) -> dict[str, Any]:
    """Comfort + latency derived from the per-frame evidence log."""
    frames: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("record_type") == "frame":
            frames.append(record)
    if len(frames) < 3:
        return {"frames": len(frames), "available": False}
    times = [float(item.get("sim_time_s") or 0.0) for item in frames]
    speeds = [float(item.get("speed_mps") or 0.0) for item in frames]
    yaws = [
        math.radians(float((item.get("vehicle") or {}).get("yaw_deg") or 0.0))
        for item in frames
    ]
    steers = [
        float((item.get("final_control") or {}).get("steer") or 0.0) for item in frames
    ]
    cross_track = [
        abs(float((item.get("lateral") or {}).get("cross_track_error_m") or 0.0))
        for item in frames
    ]
    latency_keys = (
        "sensor_to_control_ms", "sensor_to_decision_ms", "decision_ms",
        "perception_acquire_ms", "pipeline_active_ms", "simulator_tick_ms",
    )
    latencies: dict[str, list[float]] = {key: [] for key in latency_keys}
    for item in frames:
        block = item.get("latency") or {}
        for key in latency_keys:
            value = block.get(key)
            if isinstance(value, (int, float)):
                latencies[key].append(float(value))
    long_accel: list[float] = []
    jerk: list[float] = []
    lateral_accel: list[float] = []
    steer_rate: list[float] = []
    for index in range(1, len(frames)):
        dt = times[index] - times[index - 1]
        if dt <= 0:
            continue
        accel = (speeds[index] - speeds[index - 1]) / dt
        long_accel.append(accel)
        if len(long_accel) >= 2:
            jerk.append((long_accel[-1] - long_accel[-2]) / dt)
        delta_yaw = (yaws[index] - yaws[index - 1] + math.pi) % (2 * math.pi) - math.pi
        lateral_accel.append(speeds[index] * (delta_yaw / dt))
        steer_rate.append((steers[index] - steers[index - 1]) / dt)
    peak_speed = max(speeds)
    return {
        "available": True,
        "frames": len(frames),
        "max_speed_mps": peak_speed,
        "max_speed_kph": peak_speed * 3.6,
        "mean_speed_mps": sum(speeds) / len(speeds),
        "max_abs_long_accel_mps2": max((abs(value) for value in long_accel), default=None),
        "p95_abs_long_accel_mps2": _percentile([abs(v) for v in long_accel], 0.95),
        "max_abs_jerk_mps3": max((abs(value) for value in jerk), default=None),
        "p95_abs_jerk_mps3": _percentile([abs(v) for v in jerk], 0.95),
        "max_abs_lateral_accel_mps2": max((abs(value) for value in lateral_accel), default=None),
        "p95_abs_lateral_accel_mps2": _percentile([abs(v) for v in lateral_accel], 0.95),
        "max_abs_steer_rate_per_s": max((abs(value) for value in steer_rate), default=None),
        "max_abs_cross_track_error_m": max(cross_track, default=None),
        "latency_ms": {
            key: {
                "n": len(values),
                "mean": (sum(values) / len(values)) if values else None,
                "p95": _percentile(values, 0.95),
                "max": max(values) if values else None,
            } for key, values in latencies.items()
        },
        "_latency_samples": latencies,
    }


def summarise(runs_root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_root": str(runs_root),
        "scenarios": [],
    }
    for summary_path in sorted(runs_root.glob("*/logs/*.summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        frame_paths = sorted(summary_path.parent.glob("*.jsonl"))
        frames = _frame_metrics(frame_paths[0]) if frame_paths else {"available": False}
        samples = frames.pop("_latency_samples", {}) if frames.get("available") else {}
        for key, values in (samples or {}).items():
            report.setdefault("_samples", {}).setdefault(key, []).extend(values)
        latency = summary.get("latency") or {}
        acceptance = summary.get("acceptance") or {}
        metrics = acceptance.get("metrics") or {}
        extension = metrics.get("extension_acceptance") or {}
        extension_checks = {
            str(item.get("key")): item
            for item in (extension.get("checks") or [])
            if isinstance(item, dict)
        }
        checks = {
            str(item.get("key")): item.get("status")
            for item in (acceptance.get("checks") or [])
            if isinstance(item, dict)
        }
        report["scenarios"].append({
            "scenario": summary.get("scenario_id"),
            "difficulty": summary.get("difficulty"),
            "status": summary.get("status"),
            "score": summary.get("score"),
            "completion": summary.get("completion"),
            "failed_keys": acceptance.get("failed_keys"),
            "oracle_expected_behaviors": checks.get("oracle_expected_behaviors"),
            "latency": {key: latency.get(key) for key in LATENCY_KEYS if key in latency},
            "extension": {
                "passed": extension.get("passed"),
                "failed_keys": extension.get("failed_keys"),
                "oracle": extension_checks.get("oracle_expected_behaviors"),
                "checks": {
                    key: item.get("status") for key, item in extension_checks.items()
                },
            },
            "behaviors": (extension.get("evidence") or {}).get("qwen_behaviors"),
            "safety": {
                "collision_count": summary.get("collision_count"),
                "red_light_violation_count": summary.get("red_light_violation_count"),
                "route_deviation_count": summary.get("route_deviation_count"),
                "serious_route_deviation": summary.get("serious_route_deviation"),
                "safety_override_episodes": summary.get("safety_override_episodes"),
                "safety_override_frames": summary.get("safety_override_frames"),
                "min_ttc_s": summary.get("min_ttc_s"),
                "min_gap_m": summary.get("min_gap_m"),
            },
            "frame_metrics": frames,
        })
    return report


def _aggregate(report: dict[str, Any]) -> dict[str, Any]:
    rows = report["scenarios"]
    pooled = report.get("_samples") or {}

    def pooled_latency(key: str) -> dict[str, Any]:
        values = pooled.get(key) or []
        return {
            "n": len(values),
            "mean": (sum(values) / len(values)) if values else None,
            "p50": _percentile(values, 0.50),
            "p95": _percentile(values, 0.95),
            "p99": _percentile(values, 0.99),
            "max": max(values) if values else None,
        }
    def frame_values(key: str, *, aggregate_key: str | None = None) -> list[float]:
        """Pool the per-frame statistic across runs (weight = run, not frame)."""
        out: list[float] = []
        for row in rows:
            metrics = row.get("frame_metrics") or {}
            if not metrics.get("available"):
                continue
            block = metrics.get("latency_ms") if aggregate_key == "latency" else metrics
            value = (block or {}).get(key)
            if isinstance(value, dict):
                value = value.get("p95")
            if isinstance(value, (int, float)):
                out.append(float(value))
        return out

    def run_values(key: str) -> list[float]:
        return [
            float((row.get("latency") or {})[key])
            for row in rows
            if isinstance((row.get("latency") or {}).get(key), (int, float))
        ]

    groups = sorted({row.get("difficulty") for row in rows if row.get("difficulty")})
    completion: dict[str, float] = {}
    for group in groups:
        group_rows = [row for row in rows if row.get("difficulty") == group]
        passed = [row for row in group_rows if row.get("status") == "SUCCEEDED"]
        completion[group] = (len(passed) / len(group_rows)) if group_rows else 0.0
    weights = {"basic": 0.30, "advanced": 0.40, "challenge": 0.30}
    weighted_completion = sum(
        weights.get(group, 0.0) * rate for group, rate in completion.items()
    )
    return {
        "scenarios": len(rows),
        "per_group": {
            group: {
                "runs": sum(1 for row in rows if row.get("difficulty") == group),
                "passed": sum(
                    1 for row in rows
                    if row.get("difficulty") == group and row.get("status") == "SUCCEEDED"
                ),
                "completion_rate": completion.get(group),
            } for group in groups
        },
        "scoring_proxy": {
            "weighted_completion_rate": weighted_completion,
            "weights": weights,
            "task_completion_score_out_of_15": round(weighted_completion * 15.0, 4),
            "formula": "基础分 = (基础完成率×30% + 进阶×40% + 挑战×30%) × 15（细则第四部分（一））",
            "caveat": "自建 18 场景、单 seed，不是官方 1000 帧基准；仅作口径演算",
        },
        "latency_ms": {
            **{
                key: {
                    "n": len(run_values(key)),
                    "mean": (sum(run_values(key)) / len(run_values(key))) if run_values(key) else None,
                    "p95_of_run_p95": _percentile(run_values(key), 0.95),
                    "max_of_run_max": max(run_values(key)) if run_values(key) else None,
                } for key in (
                    "decision_avg_ms", "decision_p95_ms",
                    "sensor_to_control_avg_ms", "sensor_to_control_p95_ms",
                    "sensor_to_trajectory_avg_ms", "sensor_to_trajectory_p95_ms",
                )
            },
            "per_frame_sensor_to_control_ms": {
                **pooled_latency("sensor_to_control_ms"),
                "source": "pooled over every frame of the 18 runs",
            },
            "per_frame_sensor_to_decision_ms": pooled_latency("sensor_to_decision_ms"),
            "per_frame_decision_ms": pooled_latency("decision_ms"),
            "per_frame_perception_acquire_ms": pooled_latency("perception_acquire_ms"),
            "per_frame_simulator_tick_ms": pooled_latency("simulator_tick_ms"),
        },
        "oracle_alignment": {
            "checked": sum(
                1 for row in rows if (row.get("extension") or {}).get("oracle") is not None
            ),
            "passed": sum(
                1 for row in rows
                if ((row.get("extension") or {}).get("oracle") or {}).get("status") == "PASS"
            ),
            "failed_scenarios": [
                row["scenario"] for row in rows
                if ((row.get("extension") or {}).get("oracle") or {}).get("status") == "FAIL"
            ],
        },
        "extension_acceptance": {
            "passed": sum(1 for row in rows if (row.get("extension") or {}).get("passed")),
            "runs": len(rows),
            "failed_keys": sorted({
                key for row in rows
                for key in ((row.get("extension") or {}).get("failed_keys") or [])
            }),
        },
        "safety": {
            "collisions": sum(int(row["safety"].get("collision_count") or 0) for row in rows),
            "red_light_violations": sum(
                int(row["safety"].get("red_light_violation_count") or 0) for row in rows
            ),
            "route_deviations": sum(
                int(row["safety"].get("route_deviation_count") or 0) for row in rows
            ),
            "serious_route_deviations": sum(
                1 for row in rows if row["safety"].get("serious_route_deviation")
            ),
            "safety_override_frames": sum(
                int(row["safety"].get("safety_override_frames") or 0) for row in rows
            ),
        },
        "comfort": {
            key: {
                "n": len(frame_values(key)),
                "max": max(frame_values(key)) if frame_values(key) else None,
                "p95_across_runs": _percentile(frame_values(key), 0.95),
                "mean": (sum(frame_values(key)) / len(frame_values(key))) if frame_values(key) else None,
            } for key in (
                "max_abs_long_accel_mps2", "max_abs_jerk_mps3",
                "p95_abs_long_accel_mps2", "p95_abs_jerk_mps3",
                "max_abs_lateral_accel_mps2", "max_abs_steer_rate_per_s",
                "max_abs_cross_track_error_m",
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", required=True, help="run root holding <scenario>/logs/")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = summarise(Path(args.runs))
    report["aggregate"] = _aggregate(report)
    report.pop("_samples", None)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["aggregate"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
