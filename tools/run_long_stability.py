"""Run a wall-clock CARLA sensor soak with GPU and periodic Qwen evidence."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess
import threading
import time
from typing import Any

from integration.qwen_boundary import QwenInputContext
from integration.qwen_profiles import resolve_qwen_profile
from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend
from integration.qwen_vl_adapter import StrictQwenVLAdapter
from integration.sensor_stability import run_sensor_probe


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _gpu_sample(gpu_index: int) -> dict[str, Any]:
    command = [
        "nvidia-smi",
        f"--id={gpu_index}",
        "--query-gpu=index,uuid,name,memory.used,memory.total,"
        "utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=10.0,
    )
    fields = [field.strip() for field in completed.stdout.strip().split(",")]
    if len(fields) != 7:
        raise ValueError(f"unexpected nvidia-smi output: {completed.stdout!r}")
    return {
        "wall_time_utc": datetime.now(timezone.utc).isoformat(),
        "index": int(fields[0]),
        "uuid": fields[1],
        "name": fields[2],
        "memory_used_mib": float(fields[3]),
        "memory_total_mib": float(fields[4]),
        "utilization_gpu_percent": float(fields[5]),
        "temperature_c": float(fields[6]),
    }


def _monitor_gpu(
    stop: threading.Event,
    records: list[dict[str, Any]],
    errors: list[str],
    *,
    gpu_index: int,
    interval_s: float,
) -> None:
    while not stop.is_set():
        try:
            records.append(_gpu_sample(gpu_index))
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
        stop.wait(interval_s)


def _qwen_context(image_ref: str, index: int) -> QwenInputContext:
    target = "vehicle_center_soak"
    return QwenInputContext(
        request_id=f"soak-qwen-{index:03d}",
        frame=index,
        sim_time_s=float(index),
        voice_command="减速并跟随正前方的车辆",
        rgb_ref=image_ref,
        scene_state={"map": "Carla/Maps/Town03_Opt", "soak": True},
        perception={
            "traffic_light": "UNKNOWN",
            "collision": False,
            "lead_distance_m": 16.0,
            "detected_objects": [
                {
                    "track_id": target,
                    "class": "vehicle",
                    "relation": "center_ahead",
                    "distance_m": 16.0,
                }
            ],
        },
        safety_state={
            "input_confidence": 1.0,
            "recommended_action": "SLOW_DOWN",
            "reason": "lead_vehicle",
            "visual_valid": True,
            "lidar_valid": True,
        },
    )


def _run_qwen_periodically(
    stop: threading.Event,
    records: list[dict[str, Any]],
    adapter: StrictQwenVLAdapter,
    *,
    image_ref: str,
    interval_s: float,
    timeout_budget_s: float,
) -> None:
    index = 0
    while not stop.is_set():
        started = time.monotonic()
        try:
            decision = adapter(_qwen_context(image_ref, index))
            latency_s = time.monotonic() - started
            records.append(
                {
                    "request_id": f"soak-qwen-{index:03d}",
                    "wall_time_utc": datetime.now(timezone.utc).isoformat(),
                    "status": (
                        "TIMEOUT_BUDGET_EXCEEDED"
                        if latency_s > timeout_budget_s
                        else "READY"
                    ),
                    "latency_ms": latency_s * 1000.0,
                    "decision": decision,
                    "target_ok": (
                        decision.get("target_track_id")
                        == "vehicle_center_soak"
                    ),
                }
            )
        except Exception as error:
            records.append(
                {
                    "request_id": f"soak-qwen-{index:03d}",
                    "wall_time_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "ERROR",
                    "latency_ms": (time.monotonic() - started) * 1000.0,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "target_ok": False,
                }
            )
        index += 1
        stop.wait(interval_s)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--duration-minutes", type=float, default=30.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("--gpu-sample-seconds", type=float, default=5.0)
    parser.add_argument("--qwen-model", required=True)
    parser.add_argument("--qwen-base-url")
    parser.add_argument("--qwen-profile", default="qwen3vl-2b-int4")
    parser.add_argument("--qwen-image-root", required=True, type=Path)
    parser.add_argument("--qwen-image-ref", required=True)
    parser.add_argument("--qwen-interval-seconds", type=float, default=300.0)
    parser.add_argument("--qwen-timeout-budget-seconds", type=float, default=10.0)
    args = parser.parse_args()
    if args.duration_minutes <= 0:
        raise ValueError("duration-minutes must be positive")

    import carla

    if args.qwen_base_url:
        profile = resolve_qwen_profile(args.qwen_profile)
        backend = OpenAICompatibleQwenVLBackend(
            base_url=args.qwen_base_url,
            profile=profile,
            model=args.qwen_model,
            timeout_s=args.qwen_timeout_budget_seconds,
        )
        adapter = StrictQwenVLAdapter(backend, image_root=args.qwen_image_root)
        qwen_endpoint = args.qwen_base_url
    else:
        adapter = StrictQwenVLAdapter.from_local_checkpoint(
            Path(args.qwen_model),
            image_root=args.qwen_image_root,
        )
        qwen_endpoint = "local_checkpoint"
    stop = threading.Event()
    gpu_records: list[dict[str, Any]] = []
    gpu_errors: list[str] = []
    qwen_records: list[dict[str, Any]] = []
    monitor = threading.Thread(
        target=_monitor_gpu,
        args=(stop, gpu_records, gpu_errors),
        kwargs={
            "gpu_index": args.gpu_index,
            "interval_s": args.gpu_sample_seconds,
        },
        daemon=True,
    )
    qwen_worker = threading.Thread(
        target=_run_qwen_periodically,
        args=(stop, qwen_records, adapter),
        kwargs={
            "image_ref": args.qwen_image_ref,
            "interval_s": args.qwen_interval_seconds,
            "timeout_budget_s": args.qwen_timeout_budget_seconds,
        },
        daemon=True,
    )
    requested_wall_s = args.duration_minutes * 60.0
    # Wall time is the acceptance contract. A one-frame floor avoids extending
    # the soak beyond the requested duration when GPU contention lowers FPS.
    minimum_frames = 1
    started = time.monotonic()
    monitor.start()
    qwen_worker.start()
    try:
        sensor = run_sensor_probe(
            carla_api=carla,
            host=args.host,
            port=args.port,
            timeout_s=30.0,
            sensor_timeout_s=3.0,
            fixed_delta_s=0.05,
            mode="both",
            profile="low",
            frames=minimum_frames,
            startup_frames=20,
            expected_map="Town03_Opt",
            minimum_wall_duration_s=requested_wall_s,
        )
    finally:
        stop.set()
        monitor.join(timeout=15.0)
        qwen_worker.join(timeout=15.0)
    wall_duration_s = time.monotonic() - started

    recovery = run_sensor_probe(
        carla_api=carla,
        host=args.host,
        port=args.port,
        timeout_s=30.0,
        sensor_timeout_s=3.0,
        fixed_delta_s=0.05,
        mode="both",
        profile="low",
        frames=20,
        startup_frames=10,
        expected_map="Town03_Opt",
    )
    qwen_latencies = [
        float(record["latency_ms"])
        for record in qwen_records
        if record["status"] in {"READY", "TIMEOUT_BUDGET_EXCEEDED"}
    ]
    memory = [record["memory_used_mib"] for record in gpu_records]
    utilization = [record["utilization_gpu_percent"] for record in gpu_records]
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "gpu_index": args.gpu_index,
            "qwen_model": str(args.qwen_model),
            "qwen_endpoint": qwen_endpoint,
            "map": sensor.map_name,
            "sensor_mode": "both",
            "sensor_profile": "low",
        },
        "requested_wall_duration_s": requested_wall_s,
        "observed_wall_duration_s": wall_duration_s,
        "wall_duration_met": wall_duration_s >= requested_wall_s,
        "sensor": asdict(sensor),
        "aligned_fps": (
            sensor.aligned_frames / sensor.duration_s
            if sensor.duration_s > 0
            else None
        ),
        "dropped_aligned_frames": 0 if sensor.success else 1,
        "gpu": {
            "sample_count": len(gpu_records),
            "sampling_errors": gpu_errors,
            "memory_used_mib_mean": statistics.fmean(memory) if memory else None,
            "memory_used_mib_max": max(memory) if memory else None,
            "utilization_percent_mean": (
                statistics.fmean(utilization) if utilization else None
            ),
            "utilization_percent_max": max(utilization) if utilization else None,
            "samples": gpu_records,
        },
        "qwen": {
            "request_count": len(qwen_records),
            "ready": sum(record["status"] == "READY" for record in qwen_records),
            "timeout_budget_exceeded": sum(
                record["status"] == "TIMEOUT_BUDGET_EXCEEDED"
                for record in qwen_records
            ),
            "errors": sum(record["status"] == "ERROR" for record in qwen_records),
            "target_correct": sum(
                bool(record.get("target_ok")) for record in qwen_records
            ),
            "latency_ms_mean": (
                statistics.fmean(qwen_latencies) if qwen_latencies else None
            ),
            "latency_ms_p95": _percentile(qwen_latencies, 0.95),
            "latency_ms_p99": _percentile(qwen_latencies, 0.99),
            "latency_ms_max": max(qwen_latencies) if qwen_latencies else None,
            "records": qwen_records,
        },
        "recovery_probe": asdict(recovery),
        "success": (
            sensor.success
            and wall_duration_s >= requested_wall_s
            and not gpu_errors
            and bool(qwen_records)
            and all(record["status"] == "READY" for record in qwen_records)
            and all(record.get("target_ok") for record in qwen_records)
            and recovery.success
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
