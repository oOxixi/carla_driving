#!/usr/bin/env python3
"""Run all 84 current acceptance scenarios once on the prepared A800 host."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from urllib.request import urlopen

PROJECT_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_IMPORT_ROOT))

from qwen_service.client import QwenServiceClient


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": statistics.fmean(values) if values else None,
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def read_rows(log_dir: Path) -> tuple[list[dict], str | None]:
    logs = sorted(log_dir.glob("*.jsonl"), key=lambda path: path.stat().st_mtime)
    if not logs:
        return [], None
    rows = [
        json.loads(line) for line in logs[-1].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return rows, str(logs[-1])


def parse_run(log_dir: Path, console: str) -> dict[str, object]:
    rows, run_log = read_rows(log_dir)
    complete = [row for row in rows if row.get("record_type") == "run_complete"]
    summary = complete[-1].get("summary", {}) if complete else {}
    sensor_to_control_ms: list[float] = []
    sensor_to_trajectory_ms: list[float] = []
    for row in rows:
        timing = row.get("latency")
        if isinstance(timing, dict) and isinstance(timing.get("sensor_to_control_ms"), (int, float)):
            sensor_to_control_ms.append(float(timing["sensor_to_control_ms"]))
        if row.get("record_type") == "qwen_trajectory":
            latency = row.get("latency")
            if isinstance(latency, dict) and isinstance(
                latency.get("sensor_to_trajectory_ms"), (int, float),
            ):
                sensor_to_trajectory_ms.append(float(latency["sensor_to_trajectory_ms"]))
    extension_rows = []
    qwen_rows = []
    for line in console.splitlines():
        if '"record_type": "scenario_extension_acceptance"' in line:
            bucket = extension_rows
        elif '"record_type": "qwen_scenario_acceptance"' in line:
            bucket = qwen_rows
        else:
            continue
        try:
            bucket.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    extension = extension_rows[-1] if extension_rows else None
    qwen = qwen_rows[-1] if qwen_rows else None
    alignment_checks: list[dict[str, object]] = []
    if qwen is not None and isinstance(qwen.get("checks"), dict):
        alignment_checks.append({
            "key": "expected_behaviors",
            "passed": qwen["checks"].get("behaviors") is True,
        })
    if extension is not None:
        for check in extension.get("checks", []):
            if check.get("key") in {
                "expected_target_actor_id", "pedestrian_trigger_actor_id",
                "target_binding_correct", "allowed_qwen_actions",
                "oracle_expected_behaviors", "oracle_expected_target_actor_id",
            }:
                alignment_checks.append({
                    "key": check["key"], "passed": check.get("status") == "PASS",
                })
    alignment_passed = (
        None if not alignment_checks
        else all(check["passed"] is True for check in alignment_checks)
    )
    return {
        "status": summary.get("status", "NO_RUN_COMPLETE"),
        "score": summary.get("score", {}).get("final_score"),
        "failed_keys": summary.get("acceptance", {}).get("failed_keys", []),
        "extension_passed": None if extension is None else extension.get("passed"),
        "extension_failed_keys": [] if extension is None else extension.get("failed_keys", []),
        "qwen_contract_passed": None if qwen is None else qwen.get("passed"),
        "qwen_contract_failures": [] if qwen is None else qwen.get("failures", []),
        "alignment_checks": alignment_checks,
        "alignment_passed": alignment_passed,
        "sensor_ready_to_control_ms": distribution(sensor_to_control_ms),
        "official_sensor_to_trajectory_ms": distribution(sensor_to_trajectory_ms),
        "run_log": run_log,
    }


def fetch_json(url: str) -> dict[str, object] | None:
    try:
        with urlopen(url, timeout=3.0) as response:
            value = json.loads(response.read())
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def completed_scenario_ids(roots: list[Path], valid_ids: set[str]) -> set[str]:
    """Return suite IDs that already own a readable terminal summary."""
    completed: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.summary.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            scenario_id = payload.get("scenario_id")
            if scenario_id in valid_ids and payload.get("status") in {"SUCCEEDED", "FAILED"}:
                completed.add(str(scenario_id))
    return completed


def warm_qwen_service(
    *, project: Path, base_url: str, count: int,
) -> dict[str, float | int | None]:
    if count < 0:
        raise ValueError("warmup count must be non-negative")
    if count == 0:
        return distribution([])
    image_root = project / "artifacts" / "acceptance84" / "warmup_frames"
    image_root.mkdir(parents=True, exist_ok=True)
    profiles = (
        ("keep the current lane", "KEEP_LANE", None, ("KEEP_LANE",)),
        ("set speed to twenty kilometres per hour", "SET_SPEED", None, ("SET_SPEED",)),
        ("slow down", "SLOW_DOWN", None, ("SLOW_DOWN",)),
        ("stop", "STOP", None, ("STOP",)),
        ("keep lane, slow or stop if unsafe", "KEEP_LANE", None, ("KEEP_LANE", "SLOW_DOWN", "STOP")),
        ("follow the vehicle directly ahead", "FOLLOW", None, ("FOLLOW",)),
        ("avoid the obstacle on the left", "AVOID_OBSTACLE", "LEFT", ("AVOID_OBSTACLE",)),
        ("avoid the obstacle on the right", "AVOID_OBSTACLE", "RIGHT", ("AVOID_OBSTACLE",)),
        ("change lane left", "CHANGE_LANE", "LEFT", ("CHANGE_LANE",)),
        ("change lane right", "CHANGE_LANE", "RIGHT", ("CHANGE_LANE",)),
        ("turn left", "TURN", "LEFT", ("TURN",)),
        ("turn right", "TURN", "RIGHT", ("TURN",)),
        ("pull over safely", "PULL_OVER", "RIGHT", ("PULL_OVER",)),
        ("return to the original lane", "RETURN_TO_LANE", "LEFT", ("RETURN_TO_LANE",)),
    )
    # The first visual request can compile the multimodal CUDA graph.  Warm-up
    # must be allowed to finish that one-time work; the CARLA orchestrator still
    # enforces the official 300 ms decision deadline during measured scenarios.
    client = QwenServiceClient(base_url, timeout_s=30.0)
    latencies: list[float] = []
    for index in range(count):
        source_text, intent, direction, allowed = profiles[index % len(profiles)]
        image = image_root / f"warmup_{index:02d}_224.ppm"
        if not image.is_file():
            color = (
                (48 + index * 17) % 256,
                (64 + index * 29) % 256,
                (80 + index * 43) % 256,
            )
            image.write_bytes(b"P6\n224 224\n255\n" + bytes(color) * (224 * 224))
        rgb_ref = image.relative_to(project).as_posix()
        now = time.monotonic_ns()
        request = {
            "schema_version": "1.0", "request_id": f"warmup-{index}-{now}",
            "command_id": f"warmup-{index}", "created_at_ns": now,
            # Warm-up owns no vehicle control and may trigger one-time CUDA
            # compilation.  Measured CARLA requests retain their 300 ms limit.
            "deadline_ns": now + 30_000_000_000, "source_text": "保持当前车道安全行驶",
            "command_hint": {
                "intent": intent,
                "target_speed_mps": 5.56 if intent not in {"STOP", "SLOW_DOWN"} else None,
                "direction": direction,
                "target": "target_front" if intent == "FOLLOW" else None,
            },
            "rgb_ref": rgb_ref,
            "routing": {"disposition": "QWEN_PLAN", "score": 3,
                        "reasons": ["WARMUP"], "safe_wait_behavior": "SLOW_DOWN"},
            "scene_capabilities": {
                "available_lanes": [
                    "CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT", "SHOULDER",
                ],
                "left_lane_exists": True, "right_lane_exists": True,
                "left_gap_safe": True, "right_gap_safe": True,
                "route_available": True, "intersection_ahead": True,
                "return_direction": direction,
            },
            "scene_summary": {"frame_id": index, "sim_time_s": index * 0.05,
                              "traffic_light": "GREEN", "risk_level": "LOW",
                              "min_gap_m": None, "ttc_s": None},
            "targets": [{
                "target_id": "target_front", "class": "vehicle", "distance_m": 20.0,
                "relative_speed_mps": 0.0, "confidence": 1.0,
                "relation": "center_ahead",
            }],
            "constraints": {"speed_limit_mps": 8.33,
                            "allowed_behaviors": list(allowed),
                            "must_stop": intent == "STOP", "max_target_speed_mps": 8.33},
        }
        request["source_text"] = source_text
        if direction is None:
            request["scene_capabilities"].pop("return_direction", None)
        started = time.perf_counter_ns()
        client.infer(request)
        latencies.append((time.perf_counter_ns() - started) / 1e6)
    return distribution(latencies)


def write_report(path: Path, metadata: dict[str, object], records: list[dict[str, object]]) -> None:
    succeeded = sum(record.get("status") == "SUCCEEDED" for record in records)
    latency_values = [
        float(value)
        for record in records
        for value in record.get("raw_sensor_to_control_ms", [])
    ]
    official_latency_values = [
        float(value)
        for record in records
        for value in record.get("raw_sensor_to_trajectory_ms", [])
    ]
    alignment_samples = [
        record.get("alignment_passed") for record in records
        if record.get("alignment_passed") is not None
    ]
    alignment_correct = sum(value is True for value in alignment_samples)
    report = {
        **metadata,
        "scenario_count_finished": len(records),
        "scenario_succeeded": succeeded,
        "scenario_accuracy_percent": 100.0 * succeeded / len(records) if records else None,
        "sensor_ready_to_control_ms": distribution(latency_values),
        "official_sensor_to_trajectory_ms": distribution(official_latency_values),
        "official_first_50_sensor_to_trajectory_ms": distribution(
            official_latency_values[:50]
        ),
        "multimodal_semantic_alignment": {
            "unit": "scenario",
            "count": len(alignment_samples),
            "correct": alignment_correct,
            "accuracy_percent": (
                100.0 * alignment_correct / len(alignment_samples)
                if alignment_samples else None
            ),
        },
        "wall_time_s_total": sum(float(record["wall_time_s"]) for record in records),
        "records": records,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def should_stop_after_record(status: object, *, fail_fast: bool) -> bool:
    return bool(fail_fast and str(status) != "SUCCEEDED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qwen-service-url", default="http://127.0.0.1:8765")
    parser.add_argument("--carla-host", default="127.0.0.1")
    parser.add_argument("--carla-port", type=int, default=2000)
    parser.add_argument("--warmup-requests", type=int, default=20)
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="stop after writing the first non-SUCCEEDED scenario result",
    )
    parser.add_argument(
        "--skip-summary-root", action="append", type=Path, default=[],
        help="skip scenarios that already have a terminal *.summary.json below this root",
    )
    parser.add_argument(
        "--exclude-scenario-id", action="append", default=[],
        help="exclude a scenario from a diagnostic/resume run without marking it complete",
    )
    parser.add_argument(
        "--suite-revision",
        default="4238023+server-carla-perception-e2e",
        help="deployment revision used when the server copy has no .git directory",
    )
    args = parser.parse_args()

    project = args.project.resolve()
    suite = project / "scenarios" / "acceptance_suite"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    matrix = json.loads((suite / "matrix.json").read_text(encoding="utf-8"))
    all_scenarios = [
        item for item in matrix["scenarios"]
        if item["runtime_support"]["status"] == "current"
    ]
    if len(all_scenarios) != 84 or matrix["counts"].get("extension_required") != 0:
        raise RuntimeError("one-shot total run requires exactly 84 current scenarios and zero extensions")
    seen = completed_scenario_ids(
        [path.resolve() for path in args.skip_summary_root],
        {item["scenario_id"] for item in all_scenarios},
    )
    excluded = set(args.exclude_scenario_id)
    scenarios = [
        item for item in all_scenarios
        if item["scenario_id"] not in seen and item["scenario_id"] not in excluded
    ]
    health = fetch_json(args.qwen_service_url.rstrip("/") + "/health")
    if not health or health.get("production_ready") is not True:
        raise RuntimeError(f"production Qwen service is not ready: {health}")

    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        revision = args.suite_revision
    metadata: dict[str, object] = {
        "schema_version": "1.0",
        "suite_revision": revision,
        "hardware": "NVIDIA A800-SXM4-80GB",
        "cuda": "13.2",
        "selection": "unseen scenarios from 84/84 matrix runtime_support.status=current",
        "matrix_scenario_count": 84,
        "skipped_existing_scenario_count": len(seen),
        "skipped_existing_scenario_ids": sorted(seen),
        "scenario_count_expected": len(scenarios),
        "qwen_service_health_start": health,
        "qwen_visual_warmup": warm_qwen_service(
            project=project, base_url=args.qwen_service_url,
            count=args.warmup_requests,
        ),
        "official_measurement_window": "first 50 successful sensor-to-trajectory samples",
    }
    records: list[dict[str, object]] = []
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(project), "QWEN_API_KEY": "unused"})
    total = len(scenarios)
    for index, item in enumerate(scenarios, 1):
        scenario_id = item["scenario_id"]
        root = output / "scenarios" / scenario_id
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        command = [
            str(args.python), "-m", "integration.carla_runner",
            "--host", args.carla_host, "--port", str(args.carla_port),
            "--scenario-file", str(suite / item["path"]),
            "--perception-mode", "sensors", "--scenario-facts-mode", "perception",
            "--sensor-profile", "low", "--realtime",
            "--qwen-service-url", args.qwen_service_url,
            "--qwen-mode", "planner_v2", "--qwen-timeout-ms", "300",
            "--qwen-queue-size", "8", "--qwen-image-root", str(project),
            "--qwen-image-prefix", f"artifacts/acceptance84/qwen_images/{scenario_id}",
            "--sensor-warmup-frames", "20", "--sensor-timeout-s", "1.0",
            "--print-every", "500", "--log-dir", str(log_dir),
        ]
        print(f"[{index:02d}/{total:02d}] START {scenario_id}", flush=True)
        started = time.perf_counter()
        scenario_data = json.loads((suite / item["path"]).read_text(encoding="utf-8"))
        timeout_s = max(300.0, float(scenario_data["runtime"]["duration_s"]) + 300.0)
        try:
            completed = subprocess.run(
                command, cwd=project, env=env, text=True,
                capture_output=True, timeout=timeout_s, check=False,
            )
            returncode = completed.returncode
            console = completed.stdout + completed.stderr
            error = None
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            console = (exc.stdout or "") + (exc.stderr or "")
            error = f"TIMEOUT_{timeout_s:.0f}S"
        wall_time_s = time.perf_counter() - started
        (root / "console.log").write_text(
            f"returncode={returncode}\n{console}", encoding="utf-8",
        )
        parsed = parse_run(log_dir, console)
        rows, _ = read_rows(log_dir)
        raw_latency = [
            float(row["latency"]["sensor_to_control_ms"])
            for row in rows
            if isinstance(row.get("latency"), dict)
            and isinstance(row["latency"].get("sensor_to_control_ms"), (int, float))
        ]
        raw_official_latency = [
            float(row["latency"]["sensor_to_trajectory_ms"])
            for row in rows
            if row.get("record_type") == "qwen_trajectory"
            and isinstance(row.get("latency"), dict)
            and isinstance(row["latency"].get("sensor_to_trajectory_ms"), (int, float))
        ]
        if error:
            parsed["status"] = error
        record = {
            "index": index, "scenario_id": scenario_id, "path": item["path"],
            "official_level": item["official_level"], "returncode": returncode,
            "wall_time_s": wall_time_s, **parsed,
            "raw_sensor_to_control_ms": raw_latency,
            "raw_sensor_to_trajectory_ms": raw_official_latency,
        }
        records.append(record)
        write_report(output / "scenario_results.json", metadata, records)
        print(
            f"[{index:02d}/{total:02d}] END {scenario_id} status={record['status']} "
            f"wall={wall_time_s:.1f}s",
            flush=True,
        )
        if should_stop_after_record(record["status"], fail_fast=args.fail_fast):
            metadata["stopped_early"] = True
            metadata["stopped_after_scenario_id"] = scenario_id
            break

    metadata["qwen_service_metrics_end"] = fetch_json(
        args.qwen_service_url.rstrip("/") + "/metrics"
    )
    write_report(output / "scenario_results.json", metadata, records)
    print(f"REPORT {output / 'scenario_results.json'}", flush=True)
    return 1 if metadata.get("stopped_early") is True else 0


if __name__ == "__main__":
    raise SystemExit(main())
