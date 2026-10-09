"""Run the acceptance suite with the distilled Student as the CARLA decision module.

Every scenario is executed through the repository runner with
``--qwen-service-url <student service> --qwen-mode planner_v2``, so the plan the
vehicle executes is the Student's own ManeuverPlan V2; the deterministic safety
chain, the FSM and the controllers are unchanged.  The driver collects the two
acceptance records per run and aggregates them per difficulty group, which is
the closest measurable proxy for "场景任务完成率" while the official 1000-frame
benchmark is unavailable.

Usage::

    py -3.12 -m challenge.hil.carla.run_student_loop_suite \
        --service-url http://127.0.0.1:8100 --out D:\\nana\\oe\\work\\student_loop\\suite.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GROUPS = ("basic", "advanced", "challenge")


def _records(stdout: str) -> list[dict]:
    records: list[dict] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "record_type" in payload:
            records.append(payload)
    return records


def run_scenario(
    scenario: Path,
    *,
    repo: Path,
    service_url: str,
    image_root: Path,
    run_dir: Path,
    timeout_s: float,
    extra_args: list[str] | None = None,
) -> dict:
    log_dir = run_dir / scenario.stem / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "integration.carla_runner",
        "--scenario-file", str(scenario),
        "--host", "127.0.0.1", "--port", "2000",
        "--realtime",
        "--perception-mode", "sensors",
        "--qwen-service-url", service_url,
        "--qwen-mode", "planner_v2",
        "--qwen-image-root", str(image_root),
        "--qwen-timeout-ms", "500",
        "--timeout-s", str(timeout_s),
        "--log-dir", str(log_dir),
        "--print-every", "1000000",
    ] + list(extra_args or [])
    completed = subprocess.run(command, cwd=repo, text=True, capture_output=True)
    records = _records(completed.stdout or "")
    acceptance = next(
        (item for item in reversed(records) if item.get("record_type") == "scenario_acceptance"),
        None,
    )
    extension = next(
        (item for item in reversed(records)
         if item.get("record_type") == "scenario_extension_acceptance"),
        None,
    )
    return {
        "scenario": scenario.stem,
        "group": scenario.parent.name,
        "returncode": completed.returncode,
        "status": (acceptance or {}).get("status", "NO_RECORD"),
        "score": (acceptance or {}).get("score"),
        "failed_keys": (acceptance or {}).get("failed_keys"),
        "extension_passed": (extension or {}).get("passed"),
        "extension_failed_keys": (extension or {}).get("failed_keys"),
        "qwen_behaviors": ((extension or {}).get("evidence") or {}).get("qwen_behaviors"),
        "qwen_outcomes": ((extension or {}).get("evidence") or {}).get("qwen_outcomes"),
        "collision_seen": ((extension or {}).get("evidence") or {}).get("collision_seen"),
        "max_route_deviation_m": ((extension or {}).get("evidence") or {}).get(
            "max_route_deviation_m"
        ),
        "final_speed_mps": ((extension or {}).get("evidence") or {}).get("final_speed_mps"),
        "stderr_tail": (completed.stderr or "")[-800:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--service-url", default="http://127.0.0.1:8100")
    parser.add_argument("--image-root", default="")
    parser.add_argument("--groups", default=",".join(GROUPS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-root", default="")
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--repeats-per-scenario", type=int, default=1)
    parser.add_argument(
        "--extra-args", default="",
        help="verbatim extra args for integration.carla_runner (e.g. --perception-mode world)",
    )
    parser.add_argument("--resume", action="store_true", help="skip rows already recorded")
    parser.add_argument("--tag", default="", help="label stored with every row")
    parser.add_argument(
        "--only", default="",
        help="comma-separated scenario stems to run (default: every scenario in --groups)",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    groups = [item.strip() for item in args.groups.split(",") if item.strip()]
    run_root = Path(args.run_root) if args.run_root else Path(args.out).with_suffix("")
    run_root.mkdir(parents=True, exist_ok=True)
    scenarios: list[Path] = []
    for group in groups:
        scenarios.extend(sorted((repo / "scenarios" / "acceptance_suite" / group).glob("*.json")))
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        scenarios = [item for item in scenarios if item.stem in wanted]
    if not scenarios:
        raise SystemExit("no scenarios found")

    report: dict = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "service_url": args.service_url,
        "qwen_mode": "planner_v2",
        "tag": args.tag,
        "extra_args": args.extra_args,
        "repeats_per_scenario": args.repeats_per_scenario,
        "scenarios": [],
    }
    if args.resume and Path(args.out).is_file():
        existing = json.loads(Path(args.out).read_text(encoding="utf-8"))
        report["scenarios"] = existing.get("scenarios", [])
    done = {
        (row.get("scenario"), row.get("run_index", 1))
        for row in report["scenarios"]
    }
    extra = [item for item in args.extra_args.split() if item]
    for scenario in scenarios:
        for index in range(1, args.repeats_per_scenario + 1):
            if args.resume and (scenario.stem, index) in done:
                print(f"SKIP {scenario.parent.name}/{scenario.stem} run {index}", flush=True)
                continue
            print(f"RUN {scenario.parent.name}/{scenario.stem} run {index}", flush=True)
            record = run_scenario(
                scenario,
                repo=repo,
                service_url=args.service_url,
                image_root=Path(args.image_root) if args.image_root else run_root / "images",
                run_dir=run_root / f"run_{index}",
                timeout_s=args.timeout_s,
                extra_args=extra,
            )
            record["run_index"] = index
            report["scenarios"].append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
            Path(args.out).write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8",
            )

    summary: dict[str, dict] = {}
    for group in groups:
        rows = [row for row in report["scenarios"] if row["group"] == group]
        # The repository runner reports SUCCEEDED/FAILED for scenario_acceptance.
        passed = [row for row in rows if row["status"] == "SUCCEEDED"]
        summary[group] = {
            "runs": len(rows),
            "passed": len(passed),
            "completion_rate": (len(passed) / len(rows)) if rows else None,
            "failed_keys": sorted({
                key for row in rows for key in (row.get("failed_keys") or [])
            }),
        }
    total_rows = report["scenarios"]
    passed_rows = [row for row in total_rows if row["status"] == "SUCCEEDED"]
    report["summary"] = {
        "per_group": summary,
        "overall": {
            "runs": len(total_rows),
            "passed": len(passed_rows),
            "completion_rate": (len(passed_rows) / len(total_rows)) if total_rows else None,
        },
        "criterion": (
            "scenario_acceptance.status == SUCCEEDED (the repository runner's own verdict; "
            "scenario_extension_acceptance is recorded separately)"
        ),
    }
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
