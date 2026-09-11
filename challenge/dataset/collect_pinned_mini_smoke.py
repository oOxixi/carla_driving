#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


DATASET_VERSION = "teacher_distill_v0.2_d1_pinned_smoke"
TEACHER_PROFILE = "b1-pinned-teacher-v1"

SCENARIOS = [
    "scenarios/smoke/S00_chain_start.json",
    "scenarios/smoke/S01_set_speed_20.json",
    "scenarios/acceptance_suite/basic/ACC_B05_emergency_stop.json",
    "scenarios/acceptance_suite/advanced/ACC_A01_lead_brake.json",
    "scenarios/acceptance_suite/advanced/ACC_A02_red_light_conflict.json",
    "scenarios/acceptance_suite/advanced/ACC_A03_pedestrian_crossing.json",
    "scenarios/acceptance_suite/advanced/ACC_A05_lane_change_left.json",
    "scenarios/acceptance_suite/challenge/ACC_C04_multi_target_binding.json",
]


def count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for x in path.read_text(encoding="utf-8").splitlines() if x.strip())


def health(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    print("TEACHER_STATUS=" + str(data.get("status")))
    print("TEACHER_MODEL=" + str(data.get("model_id")))
    print("TEACHER_MODE=" + str(data.get("qwen_mode")))
    print("PRODUCTION_READY=" + str(data.get("production_ready")))
    if data.get("status") != "READY":
        raise RuntimeError("Teacher status is not READY")
    if data.get("production_ready") is not True:
        raise RuntimeError("Teacher not production_ready")
    if data.get("model_id") != "Qwen/Qwen3.5-2B":
        raise RuntimeError("Unexpected Teacher model")
    if data.get("qwen_mode") != "planner_v2":
        raise RuntimeError("Unexpected qwen_mode")
    return data


def collect(repo: Path, logs: Path, dataset: Path) -> tuple[int, int]:
    input_logs = sorted(logs.glob("*.jsonl"))
    accepted = dataset / "pinned_smoke_valid.jsonl"
    rejected = dataset / "pinned_smoke_rejected.jsonl"

    if not input_logs:
        return 0, 0

    cmd = [
        sys.executable,
        "challenge/dataset/collector.py",
        "--repo-root",
        str(repo),
    ]
    for log in input_logs:
        cmd += ["--input-log", str(log)]
    cmd += [
        "--output",
        str(accepted),
        "--rejected-output",
        str(rejected),
        "--dataset-version",
        DATASET_VERSION,
    ]

    rc = subprocess.run(cmd, cwd=repo, check=False).returncode
    if rc != 0:
        raise RuntimeError("collector.py failed")
    return count_jsonl(accepted), count_jsonl(rejected)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--qwen-service-url", default="http://127.0.0.1:18004")
    p.add_argument(
        "--runner-python",
        default="/home/dcase_task2/miniconda3/envs/voice/bin/python",
        help="Python interpreter used for integration.carla_runner",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    repo = Path(__file__).resolve().parents[2]
    root = repo / "artifacts" / "b1_pinned_mini_smoke"
    logs = root / "logs"
    images = root / "qwen_images"
    dataset = root / "dataset"
    for d in (logs, images, dataset):
        d.mkdir(parents=True, exist_ok=True)

    teacher_health = health(args.qwen_service_url)

    runner_check = subprocess.run(
        [
            args.runner_python,
            "-c",
            (
                "import sys, carla; "
                "print('RUNNER_PYTHON=' + sys.executable); "
                "print('CARLA_IMPORT=PASS'); "
                "print('CARLA_MODULE=' + str(carla.__file__))"
            ),
        ],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )

    if runner_check.stdout:
        print(runner_check.stdout, end="")
    if runner_check.stderr:
        print(runner_check.stderr, end="", file=sys.stderr)

    if runner_check.returncode != 0:
        raise RuntimeError(
            "Configured --runner-python cannot import CARLA Python API"
        )

    pinned_manifest = repo / "challenge" / "teacher_pinned_manifest.json"
    if not pinned_manifest.is_file():
        raise RuntimeError("challenge/teacher_pinned_manifest.json not found")
    provenance = json.loads(pinned_manifest.read_text(encoding="utf-8"))
    if provenance.get("teacher_profile") != TEACHER_PROFILE:
        raise RuntimeError("Pinned Teacher profile mismatch")

    print("DATASET_VERSION=" + DATASET_VERSION)
    print("TEACHER_PROFILE=" + TEACHER_PROFILE)
    print("SCENARIOS=" + str(len(SCENARIOS)))

    for i, rel in enumerate(SCENARIOS, 1):
        scenario = repo / rel
        if not scenario.is_file():
            raise RuntimeError(f"Missing scenario: {rel}")
        data = json.loads(scenario.read_text(encoding="utf-8"))
        print(
            f"{i:02d} | {data.get('scenario_id')} | "
            f"commands={len(data.get('commands') or [])} | {rel}"
        )

    (root / "pinned_smoke_provenance.json").write_text(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "teacher_profile": TEACHER_PROFILE,
                "teacher_manifest": provenance,
                "teacher_health": teacher_health,
                "qwen_service_url": args.qwen_service_url,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    if args.dry_run:
        print("PINNED_MINI_SMOKE_DRY_RUN=PASS")
        return 0

    failed: list[str] = []
    for rel in SCENARIOS:
        cmd = [
            args.runner_python,
            "-m",
            "integration.carla_runner",
            "--host", "127.0.0.1",
            "--port", "2000",
            "--scenario-file", rel,
            "--qwen-service-url", args.qwen_service_url,
            "--qwen-mode", "planner_v2",
            "--qwen-timeout-ms", "5000",
            "--qwen-queue-size", "1",
            "--qwen-image-root", str(repo),
            "--qwen-image-prefix",
            "artifacts/b1_pinned_mini_smoke/qwen_images",
            "--log-dir", str(logs),
        ]
        print("=" * 72)
        print("RUN_SCENARIO=" + rel)
        rc = subprocess.run(cmd, cwd=repo, check=False).returncode
        if rc != 0:
            failed.append(rel)
            print("SCENARIO_PROCESS_FAILED=" + rel)

    accepted, rejected = collect(repo, logs, dataset)

    valid = dataset / "pinned_smoke_valid.jsonl"
    if valid.is_file():
        rc = subprocess.run(
            [
                sys.executable,
                "challenge/dataset/validate_dataset.py",
                str(valid),
            ],
            cwd=repo,
            check=False,
        ).returncode
        if rc != 0:
            raise RuntimeError("validate_dataset.py failed")

    summary = {
        "dataset_version": DATASET_VERSION,
        "teacher_profile": TEACHER_PROFILE,
        "scenario_count": len(SCENARIOS),
        "valid_samples": accepted,
        "rejected_records": rejected,
        "failed_scenario_processes": failed,
        "status": "PASS" if accepted > 0 and not failed else "REVIEW",
    }
    (root / "pinned_mini_smoke_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("VALID_SAMPLES=" + str(accepted))
    print("REJECTED_RECORDS=" + str(rejected))
    print("FAILED_SCENARIO_PROCESSES=" + str(len(failed)))
    for x in failed:
        print("FAILED_SCENARIO=" + x)
    print("SUMMARY=" + str(root / "pinned_mini_smoke_summary.json"))
    print("PINNED_MINI_SMOKE=" + summary["status"])
    return 0 if summary["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
