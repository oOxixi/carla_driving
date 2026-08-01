"""Repeat real-sensor CARLA scenarios across deterministic evidence seeds."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any


def _latest_summary(directory: Path) -> Path | None:
    summaries = sorted(directory.glob("*.summary.json"), key=lambda path: path.stat().st_mtime)
    return summaries[-1] if summaries else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", required=True, type=Path)
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--repeats-per-seed", type=int, default=4)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--carla-pythonpath", type=Path)
    parser.add_argument("--timeout-s", type=float, default=90.0)
    args = parser.parse_args()
    seeds = [int(value) for value in args.seeds.split(",")]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if args.carla_pythonpath:
        env["PYTHONPATH"] = os.pathsep.join(
            [str(args.carla_pythonpath), env.get("PYTHONPATH", "")]
        )

    records: list[dict[str, Any]] = []
    for scenario in args.scenario:
        for seed in seeds:
            for repeat in range(args.repeats_per_seed):
                run_dir = args.output_dir / scenario.stem / f"seed_{seed}" / f"run_{repeat + 1:02d}"
                run_dir.mkdir(parents=True, exist_ok=True)
                command = [
                    sys.executable, "-m", "integration.carla_runner",
                    "--scenario-file", str(scenario),
                    "--seed", str(seed),
                    "--perception-mode", "sensors",
                    "--sensor-profile", "low",
                    "--sensor-timeout-s", "10",
                    "--sensor-warmup-frames", "15",
                    "--log-dir", str(run_dir),
                    "--print-every", "1000000",
                ]
                print(
                    f"RUN scenario={scenario.stem} seed={seed} repeat={repeat + 1}",
                    flush=True,
                )
                try:
                    result = subprocess.run(
                        command,
                        cwd=Path(__file__).resolve().parents[1],
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=args.timeout_s,
                        check=False,
                    )
                    (run_dir / "console.log").write_text(
                        result.stdout + "\nSTDERR\n" + result.stderr,
                        encoding="utf-8",
                    )
                    summary_path = _latest_summary(run_dir)
                    summary = (
                        json.loads(summary_path.read_text(encoding="utf-8"))
                        if summary_path is not None
                        else {}
                    )
                    record = {
                        "scenario": scenario.stem,
                        "seed": seed,
                        "repeat": repeat + 1,
                        "returncode": result.returncode,
                        "status": summary.get("status", "NO_SUMMARY"),
                        "summary": None if summary_path is None else str(summary_path),
                        "score": (summary.get("score") or {}).get("final_score"),
                        "collision_count": summary.get("collision_count"),
                        "red_light_violation_count": summary.get("red_light_violation_count"),
                        "min_gap_m": summary.get("min_gap_m"),
                        "sensor_to_control_avg_ms": (
                            summary.get("latency") or {}
                        ).get("sensor_to_control_avg_ms"),
                        "sensor_to_control_max_ms": (
                            summary.get("latency") or {}
                        ).get("sensor_to_control_max_ms"),
                    }
                except subprocess.TimeoutExpired as error:
                    (run_dir / "console.log").write_text(
                        (error.stdout or "") + "\nTIMEOUT\n" + (error.stderr or ""),
                        encoding="utf-8",
                    )
                    record = {
                        "scenario": scenario.stem,
                        "seed": seed,
                        "repeat": repeat + 1,
                        "returncode": None,
                        "status": "TIMEOUT",
                        "summary": None,
                    }
                records.append(record)
                print(json.dumps(record, ensure_ascii=False), flush=True)

    per_scenario: dict[str, dict[str, Any]] = {}
    for scenario in args.scenario:
        selected = [record for record in records if record["scenario"] == scenario.stem]
        latencies = [
            float(record["sensor_to_control_avg_ms"])
            for record in selected
            if record.get("sensor_to_control_avg_ms") is not None
        ]
        per_scenario[scenario.stem] = {
            "runs": len(selected),
            "seeds": sorted({record["seed"] for record in selected}),
            "succeeded": sum(record["status"] == "SUCCEEDED" for record in selected),
            "success_rate": (
                sum(record["status"] == "SUCCEEDED" for record in selected) / len(selected)
            ),
            "collisions": sum(record.get("collision_count") or 0 for record in selected),
            "red_light_violations": sum(
                record.get("red_light_violation_count") or 0 for record in selected
            ),
            "minimum_gap_m": min(
                (record["min_gap_m"] for record in selected if record.get("min_gap_m") is not None),
                default=None,
            ),
            "mean_run_sensor_to_control_avg_ms": (
                statistics.fmean(latencies) if latencies else None
            ),
            "max_sensor_to_control_ms": max(
                (
                    record["sensor_to_control_max_ms"]
                    for record in selected
                    if record.get("sensor_to_control_max_ms") is not None
                ),
                default=None,
            ),
        }
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": seeds,
        "repeats_per_seed": args.repeats_per_seed,
        "per_scenario": per_scenario,
        "records": records,
    }
    report_path = args.output_dir / "scenario_matrix_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"report": str(report_path), "per_scenario": per_scenario}, ensure_ascii=False))
    return 0 if all(item["success_rate"] == 1.0 for item in per_scenario.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
