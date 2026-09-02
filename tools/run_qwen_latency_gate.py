"""Run only the Qwen-VL latency gate; never starts a correctness suite."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time
from typing import Any

from integration.qwen_boundary import QwenInputContext
from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend
from integration.qwen_vl_adapter import StrictQwenVLAdapter


DEFAULT_QWEN_MODEL = "h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4"
DEFAULT_QWEN_REVISION = "unverified-local-snapshot"


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize_latency_gate(
    latencies_ms: list[float],
    *,
    threshold_ms: float,
) -> dict[str, object]:
    if not latencies_ms:
        raise ValueError("latencies_ms must not be empty")
    if (
        type(threshold_ms) not in (int, float)
        or isinstance(threshold_ms, bool)
        or not math.isfinite(float(threshold_ms))
        or float(threshold_ms) <= 0.0
    ):
        raise ValueError("threshold_ms must be finite and positive")
    values = [float(value) for value in latencies_ms]
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("latencies_ms must contain finite non-negative values")
    p95_ms = _percentile(values, 0.95)
    passed = p95_ms <= float(threshold_ms)
    return {
        "count": len(values),
        "mean_ms": statistics.fmean(values),
        "p50_ms": _percentile(values, 0.50),
        "p95_ms": p95_ms,
        "max_ms": max(values),
        "threshold_ms": float(threshold_ms),
        "status": "PASS" if passed else "EARLY_STOP",
        "run_correctness_next": passed,
    }


def latency_gate_exit_code(report: Mapping[str, object]) -> int:
    status = report.get("status")
    if status == "PASS":
        return 0
    if status == "EARLY_STOP":
        return 2
    raise ValueError(f"unsupported latency gate status: {status!r}")


def _context(image_name: str, index: int) -> QwenInputContext:
    return QwenInputContext(
        request_id=f"qwen3vl-latency-{index:03d}",
        frame=index,
        sim_time_s=index * 0.05,
        voice_command="前方道路安全时设置速度为每秒五米",
        rgb_ref=image_name,
        scene_state={"speed_mps": 2.0, "behavior_state": "LANE_FOLLOW"},
        perception={
            "traffic_light": "GREEN",
            "visual_valid": True,
            "detected_objects": [],
        },
        safety_state={
            "minimum_ttc_s": 8.0,
            "recommended_action": "KEEP_SPEED",
        },
    )


def _gpu_snapshot() -> dict[str, object]:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,compute_cap,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError):
        return {"available": False}
    first = completed.stdout.strip().splitlines()[0].split(",")
    if len(first) != 4:
        return {"available": False, "raw": completed.stdout.strip()}
    return {
        "available": True,
        "name": first[0].strip(),
        "compute_capability": first[1].strip(),
        "memory_mib": float(first[2].strip()),
        "driver_version": first[3].strip(),
    }


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get(
        "QWEN_BASE_URL", "http://127.0.0.1:8002/v1"
    ))
    parser.add_argument(
        "--model", default=os.environ.get("QWEN_MODEL", DEFAULT_QWEN_MODEL)
    )
    parser.add_argument("--model-revision", default=DEFAULT_QWEN_REVISION)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--measurements", type=int, default=10)
    parser.add_argument("--threshold-ms", type=float, default=300.0)
    parser.add_argument("--timeout-s", type=float, default=2.0)
    parser.add_argument(
        "--inference-gpu-name",
        help="GPU on the inference server when --base-url is remote.",
    )
    parser.add_argument(
        "--inference-gpu-memory-mib",
        type=float,
        help="Total memory of the remote inference GPU.",
    )
    parser.add_argument(
        "--inference-gpu-source",
        default="operator-supplied remote nvidia-smi snapshot",
    )
    args = parser.parse_args()
    if args.warmups < 1 or args.measurements < 1:
        parser.error("--warmups and --measurements must be positive")

    image = args.image.expanduser().resolve()
    if not image.is_file():
        parser.error(f"--image does not exist: {image}")
    backend = OpenAICompatibleQwenVLBackend(
        base_url=args.base_url,
        api_key=os.environ.get("QWEN_API_KEY", "unused"),
        model=args.model,
        timeout_s=args.timeout_s,
    )
    adapter = StrictQwenVLAdapter(backend, image_root=image.parent)
    latencies_ms: list[float] = []
    failure: dict[str, str] | None = None
    try:
        for index in range(args.warmups):
            adapter.infer(_context(image.name, index))
            print(f"warmup {index + 1}/{args.warmups}: ready", flush=True)
        for index in range(args.measurements):
            started_ns = time.perf_counter_ns()
            adapter.infer(_context(image.name, args.warmups + index))
            elapsed_ms = (time.perf_counter_ns() - started_ns) / 1e6
            latencies_ms.append(elapsed_ms)
            print(
                f"measure {index + 1}/{args.measurements}: {elapsed_ms:.3f} ms",
                flush=True,
            )
    except Exception as error:
        failure = {"type": type(error).__name__, "message": str(error)}
    finally:
        backend.close()

    client_gpu = _gpu_snapshot()
    inference_gpu = (
        {
            "available": True,
            "name": args.inference_gpu_name,
            "memory_mib": args.inference_gpu_memory_mib,
            "source": args.inference_gpu_source,
        }
        if args.inference_gpu_name
        else {**client_gpu, "source": "local client nvidia-smi snapshot"}
    )
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_kind": "latency_gate_only_no_correctness",
        "model": args.model,
        "model_revision": args.model_revision,
        "base_url": args.base_url,
        "image": str(image),
        "warmups": args.warmups,
        "measurements_requested": args.measurements,
        "gpu": inference_gpu,
        "client_gpu": client_gpu,
    }
    if failure is not None:
        report.update({
            "status": "ERROR",
            "error": failure,
            "run_correctness_next": False,
            "latencies_ms": latencies_ms,
        })
        _write_report(args.output, report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        return 1

    gate = summarize_latency_gate(latencies_ms, threshold_ms=args.threshold_ms)
    report.update({"latency_ms": gate, "status": gate["status"]})
    _write_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return latency_gate_exit_code(gate)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["latency_gate_exit_code", "summarize_latency_gate"]
