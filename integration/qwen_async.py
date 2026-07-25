"""Non-blocking boundary between slow Qwen inference and the CARLA loop."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math
from queue import Empty, Full, Queue
from threading import Lock, Thread
import time
from typing import Any

from car_control_A.high_level_command import HighLevelCommandAdapter
from .day22.command_adapter import build_high_level_command
from .qwen_boundary import fail_closed, validate_qwen_response


@dataclass(frozen=True)
class AsyncDecisionResult:
    sequence: int
    status: str
    submitted_sim_time_s: float
    age_s: float
    high_level_command: Mapping[str, Any] | None = None
    runtime_command: Mapping[str, Any] | None = None
    error: str | None = None

    @property
    def ready(self) -> bool:
        return self.status == "READY"

    @property
    def watchdog_alerts(self) -> tuple[str, ...]:
        """Return deterministic fail-closed alerts for every non-ready state."""
        if self.ready:
            return ()
        return fail_closed(
            self.status,
            self.error or f"Qwen decision status is {self.status}",
        ).watchdog_alerts


@dataclass(frozen=True)
class _Request:
    sequence: int
    context: Any
    submitted_sim_time_s: float


class AsyncQwenDecisionBridge:
    """
    Run one slow high-level inference function outside the control loop.

    The queue retains only the newest waiting request. A result is usable only
    while its simulation-time TTL is fresh. Errors and stale results never
    produce an executable command, so callers can fail closed.
    """

    def __init__(
        self,
        infer: Callable[[Any], Mapping[str, Any]],
        *,
        source_text: Callable[[Any], str] | None = None,
        ttl_s: float = 3.0,
        max_inference_s: float = 5.0,
    ) -> None:
        if not callable(infer):
            raise TypeError("infer must be callable")
        if type(ttl_s) not in (int, float) or ttl_s <= 0.0:
            raise ValueError("ttl_s must be positive")
        if (
            type(max_inference_s) not in (int, float)
            or isinstance(max_inference_s, bool)
            or not math.isfinite(float(max_inference_s))
            or max_inference_s <= 0.0
        ):
            raise ValueError("max_inference_s must be finite and positive")

        self._infer = infer
        self._source_text = source_text or (
            lambda context: str(getattr(context, "voice_command", ""))
        )
        self._ttl_s = float(ttl_s)
        self._max_inference_s = float(max_inference_s)
        self._queue: Queue[_Request | None] = Queue(maxsize=1)
        self._lock = Lock()
        self._latest_submitted = 0
        self._latest: AsyncDecisionResult | None = None
        self._latest_started_wall_s = 0.0
        self._closed = False
        self._thread = Thread(
            target=self._run,
            name="qwen-high-level-inference",
            daemon=True,
        )
        self._thread.start()

    def submit(self, context: Any, *, now_s: float) -> int:
        now = _sim_time(now_s)
        with self._lock:
            if self._closed:
                raise RuntimeError("Qwen decision bridge is closed")
            self._latest_submitted += 1
            request = _Request(self._latest_submitted, context, now)
            self._latest_started_wall_s = time.monotonic()
            self._latest = AsyncDecisionResult(
                sequence=request.sequence,
                status="PENDING",
                submitted_sim_time_s=now,
                age_s=0.0,
            )

        try:
            self._queue.put_nowait(request)
        except Full:
            try:
                self._queue.get_nowait()
            except Empty:
                pass
            self._queue.put_nowait(request)
        return request.sequence

    def latest(self, *, now_s: float) -> AsyncDecisionResult | None:
        now = _sim_time(now_s)
        with self._lock:
            result = self._latest
            if (
                result is not None
                and result.status == "PENDING"
                and time.monotonic() - self._latest_started_wall_s
                > self._max_inference_s
            ):
                result = AsyncDecisionResult(
                    sequence=result.sequence,
                    status="TIMEOUT",
                    submitted_sim_time_s=result.submitted_sim_time_s,
                    age_s=max(0.0, now - result.submitted_sim_time_s),
                    error="Qwen inference exceeded its wall-clock deadline",
                )
                self._latest = result
        if result is None:
            return None

        age = max(0.0, now - result.submitted_sim_time_s)
        if result.status == "READY" and age > self._ttl_s:
            return AsyncDecisionResult(
                sequence=result.sequence,
                status="STALE",
                submitted_sim_time_s=result.submitted_sim_time_s,
                age_s=age,
                error="Qwen decision exceeded its simulation-time TTL",
            )
        return AsyncDecisionResult(
            sequence=result.sequence,
            status=result.status,
            submitted_sim_time_s=result.submitted_sim_time_s,
            age_s=age,
            high_level_command=result.high_level_command,
            runtime_command=result.runtime_command,
            error=result.error,
        )

    def close(self, *, timeout_s: float = 1.0) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self._queue.put_nowait(None)
        except Full:
            try:
                self._queue.get_nowait()
            except Empty:
                pass
            self._queue.put_nowait(None)
        self._thread.join(timeout=max(0.0, float(timeout_s)))

    def __enter__(self) -> "AsyncQwenDecisionBridge":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _run(self) -> None:
        adapter = HighLevelCommandAdapter(default_ttl_s=self._ttl_s)
        while True:
            request = self._queue.get()
            if request is None:
                return
            try:
                raw_decision = self._infer(request.context)
                decision = validate_qwen_response(raw_decision)
                high_level = build_high_level_command(
                    decision,
                    self._source_text(request.context),
                    command_id=f"qwen_async_{request.sequence:08d}",
                )
                runtime = adapter.adapt(high_level)
                if runtime.get("status") != "valid":
                    raise ValueError("Qwen command failed A boundary validation")
                result = AsyncDecisionResult(
                    sequence=request.sequence,
                    status="READY",
                    submitted_sim_time_s=request.submitted_sim_time_s,
                    age_s=0.0,
                    high_level_command=high_level,
                    runtime_command=runtime,
                )
            except Exception as error:
                result = AsyncDecisionResult(
                    sequence=request.sequence,
                    status="ERROR",
                    submitted_sim_time_s=request.submitted_sim_time_s,
                    age_s=0.0,
                    error=f"{type(error).__name__}: {error}",
                )

            with self._lock:
                if (
                    request.sequence == self._latest_submitted
                    and self._latest is not None
                    and self._latest.status == "PENDING"
                ):
                    self._latest = result


def _sim_time(value: float) -> float:
    if type(value) not in (int, float):
        raise TypeError("now_s must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError("now_s must be finite and non-negative")
    return result


__all__ = ["AsyncDecisionResult", "AsyncQwenDecisionBridge"]
