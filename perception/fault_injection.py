"""Deterministic sensor and observation fault injection with explicit invalidity."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import random
from typing import Iterable

import numpy as np

from .fusion_tracker import Observation
from .sensor_adapter import Modality, SensorRecorder, SensorReplayer, SensorSample


SENSOR_FAULTS = frozenset({
    "camera_blackout", "radar_dropout", "lidar_missing", "sensor_latency", "radar_noise",
})
OBSERVATION_FAULTS = frozenset({"false_positive", "missed_detection"})


def inject_sensor_fault(
    sample: SensorSample,
    fault: str,
    *,
    latency_ms: float = 250.0,
    noise_std_m: float = 1.0,
    seed: int = 0,
) -> SensorSample:
    if fault not in SENSOR_FAULTS:
        raise ValueError(f"unsupported sensor fault: {fault}")
    if fault == "camera_blackout" and sample.modality is Modality.RGB:
        payload = np.zeros_like(sample.payload) if isinstance(sample.payload, np.ndarray) else None
        return sample.invalidated("RGB_BLACKOUT", payload=payload)
    if fault == "radar_dropout" and sample.modality is Modality.RADAR:
        return sample.invalidated("RADAR_DROPOUT", payload=None)
    if fault == "lidar_missing" and sample.modality is Modality.LIDAR:
        return sample.invalidated("LIDAR_MISSING", payload=None)
    if fault == "sensor_latency":
        if latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        return replace(sample, captured_at_ns=sample.captured_at_ns + int(latency_ms * 1e6))
    if fault == "radar_noise" and sample.modality is Modality.RADAR:
        rng = np.random.default_rng(seed)
        payload = np.asarray(sample.payload, dtype=float)
        return replace(sample, payload=payload + rng.normal(0.0, noise_std_m, size=payload.shape), error_code="RADAR_NOISE_INJECTED")
    return sample


def inject_observation_fault(
    observations: Iterable[Observation],
    fault: str,
    *,
    seed: int = 0,
) -> tuple[Observation, ...]:
    if fault not in OBSERVATION_FAULTS:
        raise ValueError(f"unsupported observation fault: {fault}")
    values = list(observations)
    if fault == "missed_detection":
        return tuple(item for item in values if item.source is not Modality.RGB)
    random.Random(seed).shuffle(values)
    values.append(Observation(
        Modality.RGB, "unknown", (8.0, 6.0, 0.0), (0.0, 0.0, 0.0),
        0.31, source_id=f"false-{seed}", bbox_xyxy_norm=(0.01, 0.4, 0.05, 0.5),
    ))
    return tuple(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fault", required=True, choices=sorted(SENSOR_FAULTS))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--latency-ms", type=float, default=250.0)
    parser.add_argument("--noise-std-m", type=float, default=1.0)
    args = parser.parse_args()
    counts = {"input": 0, "affected": 0}
    with SensorRecorder(args.output) as recorder:
        for sample in SensorReplayer(args.input):
            counts["input"] += 1
            injected = inject_sensor_fault(
                sample, args.fault, seed=args.seed,
                latency_ms=args.latency_ms, noise_std_m=args.noise_std_m,
            )
            counts["affected"] += int(injected != sample)
            recorder.record(injected)
    report = {
        "schema_version": "1.0",
        "fault": args.fault,
        "seed": args.seed,
        "input": str(args.input),
        "output": str(args.output),
        "counts": counts,
        "degradation_contract": "affected modality is invalid or explicitly marked; never fabricated as normal",
    }
    report_path = args.output.with_suffix(args.output.suffix + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
