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
            }:
                alignment_checks.append({
                    "key": check["key"], "passed": check.get("status") == "PASS",
                })
    alignment_passed = (
        bool(alignment_checks)
        and all(check["passed"] is True for check in alignment_checks)
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


def warm_qwen_service(
    *, project: Path, base_url: str, count: int,
) -> dict[str, float | int | None]:
    if count < 0:
        raise ValueError("warmup count must be non-negative")
    if count == 0:
        return distribution([])
    image = project / "artifacts" / "acceptance84" / "warmup_224.ppm"
    image.parent.mkdir(parents=True, exist_ok=True)
    if not image.is_file():
        image.write_bytes(b"P6\n224 224\n255\n" + bytes((48, 64, 80)) * (224 * 224))
    rgb_ref = image.relative_to(project).as_posix()
    client = QwenServiceClient(base_url, timeout_s=1.0)
    latencies: list[float] = []
    for index in range(count):
        now = time.monotonic_ns()
        request = {
            "schema_version": "1.0", "request_id": f"warmup-{index}-{now}",
            "command_id": f"warmup-{index}", "created_at_ns": now,
            "deadline_ns": now + 300_000_000, "source_text": "保持当前车道安全行驶",
            "command_hint": {"intent": "KEEP_LANE", "target_speed_mps": None,
                             "direction": None, "target": None},
            "rgb_ref": rgb_ref,
            "routing": {"disposition": "QWEN_PLAN", "score": 3,
                        "reasons": ["WARMUP"], "safe_wait_behavior": "SLOW_DOWN"},
            "scene_capabilities": {"available_lanes": ["CURRENT"],
                                   "route_available": True},
            "scene_summary": {"frame_id": index, "sim_time_s": index * 0.05,
                              "traffic_light": "GREEN", "risk_level": "LOW",
                              "min_gap_m": None, "ttc_s": None},
            "targets": [],
            "constraints": {"speed_limit_mps": 8.33,
                            "allowed_behaviors": ["KEEP_LANE", "SLOW_DOWN", "STOP"],
                            "must_stop": False, "max_target_speed_mps": 8.33},
        }
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
    scenarios = [
        item for item in matrix["scenarios"]
        if item["runtime_support"]["status"] == "current"
    ]
    if len(scenarios) != 84 or matrix["counts"].get("extension_required") != 0:
        raise RuntimeError("one-shot total run requires exactly 84 current scenarios and zero extensions")
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
        "selection": "84/84 matrix runtime_support.status=current",
        "scenario_count_expected": 84,
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
        print(f"[{index:02d}/84] START {scenario_id}", flush=True)
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
            f"[{index:02d}/84] END {scenario_id} status={record['status']} "
            f"wall={wall_time_s:.1f}s",
            flush=True,
        )

    metadata["qwen_service_metrics_end"] = fetch_json(
        args.qwen_service_url.rstrip("/") + "/metrics"
    )
    write_report(output / "scenario_results.json", metadata, records)
    print(f"REPORT {output / 'scenario_results.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
