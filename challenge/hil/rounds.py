"""Repeat a frozen configuration several times and keep every raw sample."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Callable, Sequence

from .replay import ReplayCase, run_replay
from .runtime_adapter import PlannerRuntime
from .samplers import BackgroundMonitor, TelemetrySpec
from .stages import LatencyCollector


@dataclass(slots=True)
class RoundResult:
    round_index: int
    case_count: int
    ready: int
    structural_pass: int
    started_at_utc: str
    duration_s: float
    telemetry: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round_index,
            "case_count": self.case_count,
            "ready": self.ready,
            "structural_pass": self.structural_pass,
            "started_at_utc": self.started_at_utc,
            "duration_s": self.duration_s,
            "telemetry": self.telemetry,
            "error": self.error,
        }


@dataclass(slots=True)
class RunResult:
    collector: LatencyCollector = field(default_factory=LatencyCollector)
    replay_rows: list[dict[str, Any]] = field(default_factory=list)
    plan_rows: list[dict[str, Any]] = field(default_factory=list)
    rounds: list[RoundResult] = field(default_factory=list)
    memory_rows: list[dict[str, Any]] = field(default_factory=list)
    power_rows: list[dict[str, Any]] = field(default_factory=list)
    utilization_rows: list[dict[str, Any]] = field(default_factory=list)
    telemetry_errors: list[str] = field(default_factory=list)
    warmup_traces: int = 0

    def summary(self) -> dict[str, Any]:
        measured = [
            trace
            for trace in self.collector.traces()
            if trace.phase == "measured"
        ]
        return {
            "rounds": len(self.rounds),
            "measured_traces": len(measured),
            "warmup_traces": self.warmup_traces,
            "replay_rows": len(self.replay_rows),
            "duration_s": sum(item.duration_s for item in self.rounds),
            "per_round": [item.to_dict() for item in self.rounds],
        }


def run_rounds(
    runtime: PlannerRuntime,
    cases: Sequence[ReplayCase],
    *,
    run_id: str,
    rounds: int = 3,
    warmup: int = 5,
    telemetry: TelemetrySpec | None = None,
    progress: Callable[[str], None] | None = None,
) -> RunResult:
    """Warm up once, then run `rounds` identical measurement windows."""
    if rounds < 1:
        raise ValueError("rounds must be >= 1")
    result = RunResult()

    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    # Warmup is deliberately outside the measured windows: the first call
    # includes session/allocator setup that no reviewer wants in a P95.
    warmup_count = min(warmup, len(cases))
    for case in cases[:warmup_count]:
        _, trace = runtime.infer(
            case.request, case_id=case.case_id, round_index=0, phase="warmup"
        )
        result.collector.add(trace)
        result.warmup_traces += 1
    emit(f"warmup done: {result.warmup_traces} samples")

    for round_index in range(1, rounds + 1):
        monitor = BackgroundMonitor(telemetry, run_id=run_id, round_index=round_index)
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        monitor.start()
        error: str | None = None
        ready = 0
        structural_pass = 0
        case_count = 0
        try:
            replay = run_replay(
                runtime, cases, run_id=run_id, round_index=round_index
            )
        except Exception as failure:  # pragma: no cover - defensive
            error = f"{type(failure).__name__}: {failure}"
            replay = None
        finally:
            monitor.stop()
        if replay is not None:
            result.replay_rows.extend(replay.rows)
            result.plan_rows.extend(replay.plans)
            for trace in replay.traces:
                result.collector.add(trace)
            ready = int(replay.summary.get("ready") or 0)
            structural_pass = int(replay.summary.get("structural_pass") or 0)
            case_count = int(replay.summary.get("case_count") or 0)
        result.memory_rows.extend(monitor.memory_rows)
        result.power_rows.extend(monitor.power_rows)
        result.utilization_rows.extend(monitor.utilization_rows)
        result.telemetry_errors.extend(monitor.errors)
        result.rounds.append(
            RoundResult(
                round_index=round_index,
                case_count=case_count,
                ready=ready,
                structural_pass=structural_pass,
                started_at_utc=started_at,
                duration_s=time.monotonic() - started,
                telemetry=monitor.summary(),
                error=error,
            )
        )
        emit(
            f"round {round_index}/{rounds}: cases={case_count} ready={ready} "
            f"structural_pass={structural_pass}"
        )
    return result


__all__ = ["RunResult", "RoundResult", "run_rounds"]
