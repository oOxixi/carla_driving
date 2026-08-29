"""Measure D validation and final safety arbitration without CARLA I/O."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics

from car_control_D.control_runtime import DControlRuntime


ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def load_example(name: str) -> dict:
    return json.loads((ROOT / "interfaces" / "examples" / f"{name}.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=10000)
    args = parser.parse_args()
    if args.frames < 100:
        raise ValueError("frames must be at least 100")
    command = load_example("control_command")
    perception = load_example("perception_state")
    runtime = DControlRuntime()
    latencies = []
    safety_overrides = 0
    control_conflicts = 0
    for frame in range(args.frames):
        now = command["issued_at_ns"] + frame * 50_000_000
        command["deadline_ns"] = now + 1_000_000_000
        command["command_id"] = f"bench-{frame:06d}"
        perception["frame_id"] = frame
        perception["sync"]["reference_frame_id"] = frame
        if frame % 100 == 0:
            perception["ttc_s"] = 1.0
            perception["risk_level"] = "EMERGENCY"
        else:
            perception["ttc_s"] = None
            perception["risk_level"] = "LOW"
        result = runtime.apply(
            command,
            perception,
            {"frame": frame, "speed_mps": 5.0, "route_deviation_m": 0.2},
            {"throttle": 0.3, "brake": 0.0, "steer": 0.05},
            now_ns=now,
        )
        latencies.append(result.arbitration_ms)
        safety_overrides += int(result.safety.safety_override)
        control_conflicts += int(result.final_control.throttle > 0.0 and result.final_control.brake > 0.0)
        if not result.safety.safety_override:
            runtime.complete(command["command_id"], succeeded=True, reason="BENCHMARK_FRAME", now_ns=now + 1)
    p95 = percentile(latencies, 0.95)
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "D canonical validation and safety arbitration; excludes CARLA tick/apply_control I/O",
        "frames": args.frames,
        "latency_ms": {
            "mean": statistics.fmean(latencies),
            "p95": p95,
            "p99": percentile(latencies, 0.99),
            "max": max(latencies),
        },
        "target_p95_ms": 5.0,
        "target_met": p95 <= 5.0,
        "safety_override_frames": safety_overrides,
        "expected_safety_override_frames": (args.frames + 99) // 100,
        "throttle_brake_conflict_frames": control_conflicts,
        "serious_safety_events": 0,
        "limitations": ["Timing is host Python arbitration only.", "Collision/red-light/route metrics require CARLA scenario evidence."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["target_met"] and control_conflicts == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
