#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


DATASET_VERSION = "teacher_distill_v0.1_smoke"

# ---------------------------------------------------------------------
# B1 Smoke v0.1 curated scenario set.
#
# Goals:
# - cover NORMAL / COMPLEX / SAFETY_CRITICAL
# - include basic control, pedestrian, red light, lead vehicle,
#   obstacle avoidance, lane change, detour, multi-target and weather
# - avoid Frozen/Official evaluation scenes
# - avoid intentionally invalid/failure-only scenarios in valid Smoke
#
# Intentionally excluded from valid-Smoke acquisition:
# - ACC_C02_ambiguous_instruction
# - ACC_C03_illegal_instruction
# - ACC_C05_perception_failure
# - CX05_sensor_dropout_route_recovery
#
# Those can later be used as rejected/hard-negative governance cases.
# ---------------------------------------------------------------------

SMOKE_SCENARIOS = [
    # Existing/basic smoke
    "scenarios/smoke/S00_chain_start.json",
    "scenarios/smoke/S01_set_speed_20.json",
    "scenarios/smoke/S02_slow_down.json",
    "scenarios/smoke/S03_stop.json",
    "scenarios/smoke/S04_emergency_stop.json",

    # Basic acceptance
    "scenarios/acceptance_suite/basic/ACC_B01_start_keep_lane.json",
    "scenarios/acceptance_suite/basic/ACC_B02_set_speed_20.json",
    "scenarios/acceptance_suite/basic/ACC_B03_slow_to_10.json",
    "scenarios/acceptance_suite/basic/ACC_B04_normal_stop.json",
    "scenarios/acceptance_suite/basic/ACC_B05_emergency_stop.json",
    "scenarios/acceptance_suite/basic/ACC_B06_offset_recovery.json",

    # Advanced acceptance
    "scenarios/acceptance_suite/advanced/ACC_A01_lead_brake.json",
    "scenarios/acceptance_suite/advanced/ACC_A02_red_light_conflict.json",
    "scenarios/acceptance_suite/advanced/ACC_A03_pedestrian_crossing.json",
    "scenarios/acceptance_suite/advanced/ACC_A04_static_obstacle_stop.json",
    "scenarios/acceptance_suite/advanced/ACC_A05_lane_change_left.json",
    "scenarios/acceptance_suite/advanced/ACC_A06_obstacle_detour_return.json",

    # Supplemental diversity
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A01_lead_brake_15m.json",
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A04_red_light_close_stop_line.json",
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A07_pedestrian_right_to_left.json",
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A10_static_vehicle_center.json",
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A13_lane_change_right.json",
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A16_detour_right_static_vehicle.json",
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A17_detour_left_construction.json",
    "scenarios/acceptance_suite/supplemental/advanced/SUP_A18_detour_return_original_lane.json",

    # Complex
    "scenarios/acceptance_suite/complex/CX01_urban_intersection_conflict.json",
    "scenarios/acceptance_suite/complex/CX02_multi_vehicle_target_follow_brake.json",
    "scenarios/acceptance_suite/complex/CX03_construction_bicycle_detour.json",
    "scenarios/acceptance_suite/complex/CX04_heavy_rain_ambiguous_multi_target.json",

    # Challenge but expected to produce valid Teacher plans
    "scenarios/acceptance_suite/challenge/ACC_C01_heavy_rain_fog.json",
    "scenarios/acceptance_suite/challenge/ACC_C04_multi_target_binding.json",
]


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return value if isinstance(value, dict) else None


def count_jsonl_rows(path: Path) -> int:
    if not path.is_file():
        return 0

    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if not path.is_file():
        return rows

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            value = json.loads(line)

            if isinstance(value, dict):
                rows.append(value)

    return rows


def validate_teacher(service_url: str) -> None:
    url = service_url.rstrip("/") + "/health"

    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.loads(response.read())

    print(f"TEACHER_STATUS={data.get('status')}")
    print(f"TEACHER_MODEL={data.get('model_id')}")
    print(f"TEACHER_MODE={data.get('qwen_mode')}")
    print(f"PRODUCTION_READY={data.get('production_ready')}")

    if data.get("status") != "READY":
        raise RuntimeError("Teacher service is not READY")

    if data.get("production_ready") is not True:
        raise RuntimeError("Teacher service is not production_ready")

    if data.get("model_id") != "Qwen/Qwen3.5-2B":
        raise RuntimeError(
            "Unexpected Teacher model: "
            + str(data.get("model_id"))
        )

    if data.get("qwen_mode") != "planner_v2":
        raise RuntimeError(
            "Unexpected Teacher mode: "
            + str(data.get("qwen_mode"))
        )


def collect_dataset(
    repo_root: Path,
    log_dir: Path,
    dataset_dir: Path,
) -> tuple[int, int]:
    logs = sorted(log_dir.glob("*.jsonl"))

    if not logs:
        return 0, 0

    valid_path = dataset_dir / "smoke_valid.jsonl"
    rejected_path = dataset_dir / "smoke_rejected.jsonl"

    cmd = [
        sys.executable,
        "challenge/dataset/collector.py",
        "--repo-root",
        str(repo_root),
    ]

    for log in logs:
        cmd.extend(
            [
                "--input-log",
                str(log),
            ]
        )

    cmd.extend(
        [
            "--output",
            str(valid_path),
            "--rejected-output",
            str(rejected_path),
            "--dataset-version",
            DATASET_VERSION,
        ]
    )

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError("collector.py failed")

    return (
        count_jsonl_rows(valid_path),
        count_jsonl_rows(rejected_path),
    )


def existing_valid_scenarios(
    dataset_dir: Path,
) -> set[str]:
    valid_path = dataset_dir / "smoke_valid.jsonl"

    result: set[str] = set()

    for sample in read_jsonl(valid_path):
        metadata = sample.get("metadata")

        if not isinstance(metadata, dict):
            continue

        scenario_id = metadata.get("scenario_id")

        if isinstance(scenario_id, str):
            result.add(scenario_id)

    return result


def run_scenario(
    repo_root: Path,
    scenario_path: str,
    service_url: str,
    log_dir: Path,
) -> int:
    cmd = [
        sys.executable,
        "-m",
        "integration.carla_runner",
        "--host",
        "127.0.0.1",
        "--port",
        "2000",
        "--scenario-file",
        scenario_path,
        "--qwen-service-url",
        service_url,
        "--qwen-mode",
        "planner_v2",
        "--qwen-timeout-ms",
        "5000",
        "--qwen-queue-size",
        "1",
        "--qwen-image-root",
        str(repo_root),
        "--qwen-image-prefix",
        "artifacts/b1_teacher_smoke/qwen_images",
        "--log-dir",
        str(log_dir),
    ]

    print()
    print("=" * 72)
    print(f"RUN_SCENARIO={scenario_path}")
    print("=" * 72)

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        check=False,
    )

    return result.returncode


def validate_dataset(
    repo_root: Path,
    dataset_dir: Path,
) -> None:
    valid_path = dataset_dir / "smoke_valid.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            "challenge/dataset/validate_dataset.py",
            str(valid_path),
        ],
        cwd=repo_root,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError("validate_dataset.py failed")


def build_manifest(
    repo_root: Path,
    dataset_dir: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "challenge/dataset/build_manifest.py",
            "--accepted",
            str(dataset_dir / "smoke_valid.jsonl"),
            "--rejected",
            str(dataset_dir / "smoke_rejected.jsonl"),
            "--output",
            str(dataset_dir / "dataset_manifest_v0.json"),
            "--dataset-version",
            DATASET_VERSION,
        ],
        cwd=repo_root,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError("build_manifest.py failed")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--target-valid",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--qwen-service-url",
        default="http://127.0.0.1:18003",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    args = parser.parse_args()

    if not 20 <= args.target_valid <= 50:
        raise SystemExit(
            "--target-valid must be between 20 and 50"
        )

    repo_root = Path(__file__).resolve().parents[2]

    log_dir = (
        repo_root
        / "artifacts"
        / "b1_teacher_smoke"
        / "logs"
    )

    dataset_dir = (
        repo_root
        / "artifacts"
        / "b1_teacher_smoke"
        / "dataset"
    )

    image_dir = (
        repo_root
        / "artifacts"
        / "b1_teacher_smoke"
        / "qwen_images"
    )

    log_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    print(f"REPO_ROOT={repo_root}")
    print(f"TARGET_VALID={args.target_valid}")
    print(f"QWEN_SERVICE={args.qwen_service_url}")

    print()
    print("Checking Teacher service...")

    validate_teacher(args.qwen_service_url)

    print("TEACHER_HEALTH=PASS")

    print()
    print("===== CURATED SMOKE PLAN =====")

    valid_scenarios = []

    for index, relative_path in enumerate(
        SMOKE_SCENARIOS,
        start=1,
    ):
        path = repo_root / relative_path

        if not path.is_file():
            raise RuntimeError(
                f"Scenario not found: {relative_path}"
            )

        data = load_json(path)

        if data is None:
            raise RuntimeError(
                f"Invalid scenario JSON: {relative_path}"
            )

        scenario_id = data.get("scenario_id")
        commands = data.get("commands") or []

        print(
            f"{index:02d}. "
            f"{relative_path} | "
            f"id={scenario_id} | "
            f"map={data.get('map')} | "
            f"seed={data.get('seed')} | "
            f"commands={len(commands)}"
        )

        valid_scenarios.append(relative_path)

    if args.dry_run:
        print()
        print(
            f"CURATED_SCENARIOS={len(valid_scenarios)}"
        )
        print("DRY_RUN=PASS")
        return

    accepted, rejected = collect_dataset(
        repo_root,
        log_dir,
        dataset_dir,
    )

    already_valid = existing_valid_scenarios(
        dataset_dir
    )

    print()
    print(f"INITIAL_ACCEPTED={accepted}")
    print(f"INITIAL_REJECTED={rejected}")
    print(
        "EXISTING_VALID_SCENARIOS="
        + str(len(already_valid))
    )

    attempted = 0
    skipped_existing = 0
    failed_processes: list[str] = []

    for relative_path in valid_scenarios:
        if accepted >= args.target_valid:
            break

        data = load_json(
            repo_root / relative_path
        ) or {}

        scenario_id = data.get("scenario_id")

        if (
            isinstance(scenario_id, str)
            and scenario_id in already_valid
        ):
            print()
            print(
                "SKIP_ALREADY_VALID="
                + scenario_id
            )

            skipped_existing += 1
            continue

        attempted += 1

        returncode = run_scenario(
            repo_root=repo_root,
            scenario_path=relative_path,
            service_url=args.qwen_service_url,
            log_dir=log_dir,
        )

        if returncode != 0:
            failed_processes.append(
                relative_path
            )

            print(
                "SCENARIO_PROCESS_FAILED="
                + relative_path
            )

        accepted, rejected = collect_dataset(
            repo_root,
            log_dir,
            dataset_dir,
        )

        already_valid = existing_valid_scenarios(
            dataset_dir
        )

        print()
        print(f"CURRENT_ACCEPTED={accepted}")
        print(f"CURRENT_REJECTED={rejected}")
        print(f"TARGET_VALID={args.target_valid}")

        time.sleep(0.5)

    print()
    print("=" * 72)
    print("FINAL DATASET VALIDATION")
    print("=" * 72)

    validate_dataset(
        repo_root,
        dataset_dir,
    )

    build_manifest(
        repo_root,
        dataset_dir,
    )

    accepted, rejected = collect_dataset(
        repo_root,
        log_dir,
        dataset_dir,
    )

    print()
    print("=" * 72)
    print("B1 SMOKE SUMMARY")
    print("=" * 72)

    print(f"ATTEMPTED_SCENARIOS={attempted}")
    print(
        f"SKIPPED_EXISTING_SCENARIOS={skipped_existing}"
    )
    print(f"VALID_TEACHER_SAMPLES={accepted}")
    print(f"REJECTED_RECORDS={rejected}")
    print(
        "FAILED_SCENARIO_PROCESSES="
        + str(len(failed_processes))
    )

    for item in failed_processes:
        print(
            "FAILED_SCENARIO="
            + item
        )

    print(
        "VALID_DATASET="
        + str(
            dataset_dir / "smoke_valid.jsonl"
        )
    )

    print(
        "REJECTED_DATASET="
        + str(
            dataset_dir / "smoke_rejected.jsonl"
        )
    )

    print(
        "MANIFEST="
        + str(
            dataset_dir
            / "dataset_manifest_v0.json"
        )
    )

    if accepted >= args.target_valid:
        print("SMOKE_TARGET_REACHED=true")
    else:
        print("SMOKE_TARGET_REACHED=false")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
