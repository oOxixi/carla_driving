"""Run the dynamic-frame Qwen3-VL latency gate or a fixed-image diagnostic."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time
from typing import Any

from integration.qwen_boundary import QwenInputContext
from integration.qwen_profiles import resolve_qwen_profile
from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend
from integration.qwen_vl_adapter import StrictQwenVLAdapter


_OFFICIAL_WARMUPS = 5
_OFFICIAL_MEASUREMENTS = 10


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


def _dynamic_frame_paths(directory: Path) -> list[Path]:
    root = directory.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("--dynamic-frames-dir must be a directory")
    frames = sorted(path.resolve() for path in root.iterdir() if path.is_file())
    required = _OFFICIAL_WARMUPS + _OFFICIAL_MEASUREMENTS
    if len(frames) < required:
        raise ValueError(f"official gate requires at least {required} dynamic frames")
    selected = frames[:required]
    if len(set(selected)) != required:
        raise ValueError("official gate frames must use distinct files")
    digests = [_file_sha256(path) for path in selected]
    if len(set(digests)) != required:
        raise ValueError("official gate frames must have distinct content")
    return selected


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("QWEN_BASE_URL"))
    parser.add_argument("--profile", default="qwen3vl-2b-int4")
    input_mode = parser.add_mutually_exclusive_group(required=True)
    input_mode.add_argument("--dynamic-frames-dir", type=Path)
    input_mode.add_argument("--fixed-image-diagnostic", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold-ms", type=float, default=300.0)
    parser.add_argument("--timeout-s", type=float, default=2.0)
    args = parser.parse_args()
    try:
        profile = resolve_qwen_profile(args.profile)
    except ValueError as error:
        parser.error(str(error))
    base_url = args.base_url or f"http://127.0.0.1:{profile.port}/v1"

    if args.dynamic_frames_dir is not None:
        try:
            frames = _dynamic_frame_paths(args.dynamic_frames_dir)
        except ValueError as error:
            parser.error(str(error))
        image_root = args.dynamic_frames_dir.expanduser().resolve()
        dataset_kind = "official_dynamic_frame_latency_gate"
        diagnostic = False
    else:
        image = args.fixed_image_diagnostic.expanduser().resolve()
        if not image.is_file():
            parser.error(f"--fixed-image-diagnostic does not exist: {image}")
        frames = [image] * (_OFFICIAL_WARMUPS + _OFFICIAL_MEASUREMENTS)
        image_root = image.parent
        dataset_kind = "fixed_image_hot_latency_diagnostic"
        diagnostic = True
    backend = OpenAICompatibleQwenVLBackend(
        base_url=base_url,
        profile=profile,
        api_key=os.environ.get("QWEN_API_KEY", "unused"),
        timeout_s=args.timeout_s,
    )
    adapter = StrictQwenVLAdapter(backend, image_root=image_root)
    latencies_ms: list[float] = []
    failure: dict[str, str] | None = None
    try:
        for index, image in enumerate(frames[:_OFFICIAL_WARMUPS]):
            image_ref = str(image.relative_to(image_root))
            adapter.infer(_context(image_ref, index))
            print(f"warmup {index + 1}/{_OFFICIAL_WARMUPS}: ready", flush=True)
        for index, image in enumerate(frames[_OFFICIAL_WARMUPS:]):
            started_ns = time.perf_counter_ns()
            image_ref = str(image.relative_to(image_root))
            adapter.infer(_context(image_ref, _OFFICIAL_WARMUPS + index))
            elapsed_ms = (time.perf_counter_ns() - started_ns) / 1e6
            latencies_ms.append(elapsed_ms)
            print(
                f"measure {index + 1}/{_OFFICIAL_MEASUREMENTS}: {elapsed_ms:.3f} ms",
                flush=True,
            )
    except Exception as error:
        failure = {"type": type(error).__name__, "message": str(error)}
    finally:
        backend.close()

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_kind": dataset_kind,
        "profile": profile.name,
        "model": profile.model,
        "model_revision": profile.revision,
        "image_max_side": profile.image_max_side,
        "visual_tokens": profile.visual_tokens,
        "base_url": base_url,
        "warmups": _OFFICIAL_WARMUPS,
        "measurements_requested": _OFFICIAL_MEASUREMENTS,
        "gpu": _gpu_snapshot(),
    }
    if diagnostic:
        report["fixed_image"] = str(frames[0])
    else:
        report["dynamic_frames_dir"] = str(image_root)
        report["dynamic_frame_count"] = len(frames)
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
    if diagnostic:
        report.update({
            "latency_diagnostic": gate,
            "status": "DIAGNOSTIC",
            "run_correctness_next": False,
        })
    else:
        report.update({"latency_ms": gate, "status": gate["status"]})
    _write_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if diagnostic else latency_gate_exit_code(gate)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["latency_gate_exit_code", "summarize_latency_gate"]
