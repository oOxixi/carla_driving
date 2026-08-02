"""Benchmark C synchronization/fusion with deterministic synthetic observations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

import numpy as np

from perception import (
    Extrinsics, FusionTracker, Modality, Observation, RGBDetection, RGBPipeline,
    RGBPipelineConfig, SensorSample, SensorSynchronizer,
)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=1000)
    args = parser.parse_args()
    if args.frames < 10:
        raise ValueError("frames must be at least 10")
    synchronizer = SensorSynchronizer(tolerance_ms=50.0)
    fusion = FusionTracker()
    image = np.zeros((225, 400, 3), dtype=np.uint8)
    detector = lambda _image: (RGBDetection("vehicle", 0.95, (0.4, 0.3, 0.6, 0.8)),)
    rgb = RGBPipeline(detector, config=RGBPipelineConfig(input_width=320, input_height=192))
    latencies: list[float] = []
    for frame in range(args.frames):
        started = time.perf_counter_ns()
        stamp = 1_000_000_000 + frame * 50_000_000
        for index, modality in enumerate(Modality):
            payload = image if modality is Modality.RGB else {"frame": frame}
            synchronizer.push(SensorSample(modality, frame, frame * 0.05, stamp + index * 1_000_000, payload, Extrinsics()))
        aligned = synchronizer.align(
            reference_frame_id=frame, reference_sim_time_s=frame * 0.05,
            reference_captured_at_ns=stamp, now_ns=stamp + 5_000_000,
        )
        tracks = rgb.process(image, frame_id=frame)
        observations = (
            Observation(Modality.RGB, "vehicle", (15.0, 0.0, 0.0), (3.0, 0.0, 0.0), tracks[0].confidence, bbox_xyxy_norm=tracks[0].bbox_xyxy_norm),
            Observation(Modality.RADAR, "vehicle", (15.1, 0.1, 0.0), (3.1, 0.0, 0.0), 0.9),
            Observation(Modality.LIDAR, "vehicle", (14.9, -0.1, 0.0), (3.0, 0.0, 0.0), 0.95),
        )
        fusion.update(aligned, observations, ego_speed_mps=5.0, speed_limit_mps=8.33)
        latencies.append((time.perf_counter_ns() - started) / 1e6)
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "synthetic deterministic synchronization/RGB tracking/fusion benchmark",
        "not_claimed": "not live CARLA sensor inference and not ONNX detector latency",
        "frames": args.frames,
        "latency_ms": {
            "mean": statistics.fmean(latencies),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
            "max": max(latencies),
        },
        "target_p95_ms": 30.0,
        "target_met_for_this_scope": percentile(latencies, 0.95) <= 30.0,
        "rgb_metrics": rgb.metrics(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
