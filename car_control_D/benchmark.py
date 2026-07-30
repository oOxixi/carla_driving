"""Deterministic latency benchmark for D and the integrated control step."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import platform
from statistics import fmean
from time import perf_counter_ns
from typing import Callable

from car_control_A import RuntimeVehicleState
from car_control_A.routing import RouteReference
from car_control_B.pure_pursuit import PurePursuitController
from integration import ControlRuntime, PerceptionFrame

from .safety_supervisor import SafetySupervisor


def _percentile_ms(samples_ns: list[int], percentile: float) -> float:
    ordered = sorted(samples_ns)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index] / 1_000_000.0


def _summary(samples_ns: list[int]) -> dict[str, float | int]:
    return {
        "samples": len(samples_ns),
        "mean_ms": fmean(samples_ns) / 1_000_000.0,
        "p50_ms": _percentile_ms(samples_ns, 0.50),
        "p95_ms": _percentile_ms(samples_ns, 0.95),
        "p99_ms": _percentile_ms(samples_ns, 0.99),
        "max_ms": max(samples_ns) / 1_000_000.0,
    }


def _measure(operation: Callable[[int], object], *, iterations: int, warmup: int) -> list[int]:
    for index in range(warmup):
        operation(index)
    samples: list[int] = []
    for index in range(iterations):
        started = perf_counter_ns()
        operation(index)
        samples.append(perf_counter_ns() - started)
    return samples


def run_control_safety_benchmark(
    *,
    iterations: int = 10_000,
    warmup: int = 1_000,
    threshold_ms: float = 5.0,
) -> dict[str, object]:
    """Benchmark CARLA-independent hot paths and return machine-readable evidence."""
    if type(iterations) is not int or iterations <= 0:
        raise ValueError("iterations must be a positive integer")
    if type(warmup) is not int or warmup < 0:
        raise ValueError("warmup must be a non-negative integer")
    if type(threshold_ms) not in (int, float) or not math.isfinite(float(threshold_ms)) or threshold_ms <= 0:
        raise ValueError("threshold_ms must be a positive finite number")

    supervisor = SafetySupervisor()
    arbitration_cases = (
        (
            {"throttle": 0.3, "brake": 0.0, "steer": 0.1},
            {"speed_mps": 4.0, "front_distance_m": 30.0},
            {"ttc_s": 8.0},
        ),
        (
            {"throttle": 0.3, "brake": 0.0, "steer": 0.0},
            {"speed_mps": 6.0, "front_distance_m": 8.0},
            {"ttc_s": 1.0},
        ),
        (
            {"throttle": 0.0, "brake": 0.0, "steer": 0.0},
            {"speed_mps": 3.0, "traffic_light": "RED", "distance_to_stop_line_m": 5.0},
            {},
        ),
        (
            {"throttle": 0.3, "brake": 0.0, "steer": 0.8},
            {"speed_mps": 1.0, "route_deviation_m": 3.5},
            {},
        ),
        (
            {"throttle": 0.4, "brake": 0.4, "steer": 0.0},
            {"speed_mps": 2.0},
            {},
        ),
    )

    def arbitrate(index: int) -> object:
        control, state, risk = arbitration_cases[index % len(arbitration_cases)]
        return supervisor.arbitrate(control, state, risk=risk)

    route = RouteReference(((0.0, 0.0), (20.0, 0.0), (40.0, 0.0)), 0.0, 5.0)
    runtime = ControlRuntime(PurePursuitController())

    def integrated_step(index: int) -> object:
        frame = index + 1
        sim_time_s = frame * 0.05
        vehicle = RuntimeVehicleState(
            frame=frame,
            sim_time_s=sim_time_s,
            speed_mps=4.0,
            x_m=min(float(frame) * 0.2, 39.0),
            y_m=0.0,
            z_m=0.0,
            yaw_deg=0.0,
            lane_id="lane_1",
        )
        scene = PerceptionFrame(frame=frame, sim_time_s=sim_time_s)
        return runtime.step(vehicle, scene, route, dt_s=0.05)

    safety_result = _summary(_measure(arbitrate, iterations=iterations, warmup=warmup))
    integrated_result = _summary(_measure(integrated_step, iterations=iterations, warmup=warmup))
    passed = (
        float(safety_result["p95_ms"]) <= threshold_ms
        and float(integrated_result["p95_ms"]) <= threshold_ms
    )
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "control_safety_hot_path",
        "iterations_per_path": iterations,
        "warmup_iterations_per_path": warmup,
        "threshold_p95_ms": float(threshold_ms),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "results": {
            "safety_arbitration": safety_result,
            "integrated_control_step": integrated_result,
        },
        "acceptance": {
            "passed": passed,
            "rule": "both safety_arbitration.p95_ms and integrated_control_step.p95_ms <= threshold_p95_ms",
        },
    }


__all__ = ["run_control_safety_benchmark"]
