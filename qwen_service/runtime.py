"""Bounded execution and observable metrics for Qwen inference."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
import math
from threading import BoundedSemaphore, Lock
import time
from typing import Any

from integration.qwen_boundary import (
    QWEN_BOUNDARY_SCHEMA_VERSION,
    QwenInputContext,
    validate_qwen_response,
)


class ServiceBusyError(RuntimeError):
    """Raised when every bounded model worker is occupied."""


class InferenceTimeoutError(RuntimeError):
    """Raised when a request exceeds its wall-clock inference deadline."""


class ModelInferenceError(RuntimeError):
    """Raised when the model or strict output boundary rejects a request."""


class QwenServiceRuntime:
    """Keep one loaded model behind a bounded, fail-closed request boundary."""

    def __init__(
        self,
        adapter: object,
        *,
        model_name: str,
        max_concurrency: int = 1,
        timeout_s: float = 5.0,
        metrics_window: int = 1000,
        gpu_stats: Callable[[], Mapping[str, Any]] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        infer = getattr(adapter, "infer", None)
        if not callable(infer):
            raise TypeError("adapter must provide infer(context)")
        if type(model_name) is not str or not model_name.strip():
            raise ValueError("model_name must be a non-empty string")
        if type(max_concurrency) is not int or max_concurrency < 1:
            raise ValueError("max_concurrency must be a positive integer")
        if (
            type(timeout_s) not in (int, float)
            or isinstance(timeout_s, bool)
            or not math.isfinite(float(timeout_s))
            or float(timeout_s) <= 0.0
        ):
            raise ValueError("timeout_s must be finite and positive")
        if type(metrics_window) is not int or metrics_window < 1:
            raise ValueError("metrics_window must be a positive integer")

        self._adapter = adapter
        self._infer: Callable[[QwenInputContext], object] = infer
        self._model_name = model_name.strip()
        self._max_concurrency = max_concurrency
        self._timeout_s = float(timeout_s)
        self._gpu_stats = gpu_stats or _torch_gpu_stats
        self._clock = clock
        self._started_s = clock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrency,
            thread_name_prefix="qwen-service-infer",
        )
        self._slots = BoundedSemaphore(max_concurrency)
        self._lock = Lock()
        self._closed = False
        self._in_flight = 0
        self._requests_total = 0
        self._succeeded = 0
        self._failed = 0
        self._timed_out = 0
        self._busy_rejected = 0
        self._latencies_ms: deque[float] = deque(maxlen=metrics_window)

    def health(self) -> dict[str, object]:
        with self._lock:
            return {
                "schema_version": "1.0",
                "status": "UNAVAILABLE" if self._closed else "READY",
                "model": self._model_name,
                "max_concurrency": self._max_concurrency,
                "in_flight": self._in_flight,
            }

    def infer(self, payload: Mapping[str, object]) -> dict[str, object]:
        context = _parse_context(payload)
        with self._lock:
            if self._closed:
                raise RuntimeError("Qwen service runtime is closed")
            self._requests_total += 1
        if not self._slots.acquire(blocking=False):
            with self._lock:
                self._busy_rejected += 1
            raise ServiceBusyError("all Qwen inference slots are occupied")
        with self._lock:
            self._in_flight += 1

        started_s = self._clock()
        future = self._executor.submit(self._infer, context)
        try:
            raw_decision = future.result(timeout=self._timeout_s)
            decision = validate_qwen_response(raw_decision)
        except FutureTimeoutError as error:
            elapsed_ms = (self._clock() - started_s) * 1000.0
            self._record("timed_out", elapsed_ms)
            future.add_done_callback(self._release_slot)
            raise InferenceTimeoutError(
                f"Qwen inference exceeded {self._timeout_s:.3f}s"
            ) from error
        except Exception as error:
            elapsed_ms = (self._clock() - started_s) * 1000.0
            self._record("failed", elapsed_ms)
            self._release_slot(future)
            raise ModelInferenceError(f"{type(error).__name__}: {error}") from error

        elapsed_ms = (self._clock() - started_s) * 1000.0
        self._record("succeeded", elapsed_ms)
        self._release_slot(future)
        return {
            "schema_version": "1.0",
            "status": "READY",
            "request_id": context.request_id,
            "model": self._model_name,
            "latency_ms": round(elapsed_ms, 6),
            "decision": decision,
        }

    def metrics(self) -> dict[str, object]:
        with self._lock:
            latencies = list(self._latencies_ms)
            completed = self._succeeded + self._failed + self._timed_out
            uptime_s = max(0.0, self._clock() - self._started_s)
            report: dict[str, object] = {
                "schema_version": "1.0",
                "model": self._model_name,
                "requests": {
                    "total": self._requests_total,
                    "succeeded": self._succeeded,
                    "failed": self._failed,
                    "timed_out": self._timed_out,
                    "busy_rejected": self._busy_rejected,
                },
                "in_flight": self._in_flight,
                "max_concurrency": self._max_concurrency,
                "uptime_s": round(uptime_s, 6),
                "throughput_rps": (
                    round(completed / uptime_s, 6) if uptime_s > 0.0 else 0.0
                ),
                "latency_ms": _latency_summary(latencies),
            }
        try:
            report["gpu"] = dict(self._gpu_stats())
        except Exception as error:
            report["gpu"] = {
                "available": False,
                "error": f"{type(error).__name__}: {error}",
            }
        return report

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=True)
        close = getattr(self._adapter, "close", None)
        if callable(close):
            close()

    def _record(self, outcome: str, elapsed_ms: float) -> None:
        with self._lock:
            if outcome == "succeeded":
                self._succeeded += 1
            elif outcome == "failed":
                self._failed += 1
            elif outcome == "timed_out":
                self._timed_out += 1
            else:
                raise ValueError(f"unsupported outcome: {outcome}")
            self._latencies_ms.append(max(0.0, elapsed_ms))

    def _release_slot(self, _future: Future[object]) -> None:
        with self._lock:
            self._in_flight -= 1
        self._slots.release()


def _parse_context(payload: Mapping[str, object]) -> QwenInputContext:
    if not isinstance(payload, Mapping):
        raise TypeError("request body must be a JSON object")
    required = {
        "schema_version",
        "request_id",
        "frame",
        "sim_time_s",
        "voice_command",
        "rgb_ref",
        "scene_state",
        "perception",
        "safety_state",
    }
    fields = set(payload)
    if fields != required:
        raise ValueError(
            f"request fields mismatch; missing={sorted(required - fields)}, "
            f"unknown={sorted(fields - required)}"
        )
    if payload["schema_version"] != QWEN_BOUNDARY_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be {QWEN_BOUNDARY_SCHEMA_VERSION}"
        )
    return QwenInputContext(
        request_id=payload["request_id"],  # type: ignore[arg-type]
        frame=payload["frame"],  # type: ignore[arg-type]
        sim_time_s=payload["sim_time_s"],  # type: ignore[arg-type]
        voice_command=payload["voice_command"],  # type: ignore[arg-type]
        rgb_ref=payload["rgb_ref"],  # type: ignore[arg-type]
        scene_state=payload["scene_state"],  # type: ignore[arg-type]
        perception=payload["perception"],  # type: ignore[arg-type]
        safety_state=payload["safety_state"],  # type: ignore[arg-type]
    )


def _latency_summary(values: list[float]) -> dict[str, object]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "mean": round(sum(ordered) / len(ordered), 6),
        "p95": round(_percentile(ordered, 0.95), 6),
        "p99": round(_percentile(ordered, 0.99), 6),
        "max": round(ordered[-1], 6),
    }


def _percentile(ordered: list[float], quantile: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _torch_gpu_stats() -> dict[str, object]:
    try:
        import torch
    except ImportError:
        return {"available": False}
    if not torch.cuda.is_available():
        return {"available": False}
    bytes_per_mb = 1024 * 1024
    device = torch.cuda.current_device()
    return {
        "available": True,
        "device": torch.cuda.get_device_name(device),
        "memory_allocated_mb": round(
            torch.cuda.memory_allocated(device) / bytes_per_mb, 3
        ),
        "memory_reserved_mb": round(
            torch.cuda.memory_reserved(device) / bytes_per_mb, 3
        ),
        "peak_memory_allocated_mb": round(
            torch.cuda.max_memory_allocated(device) / bytes_per_mb, 3
        ),
    }


__all__ = [
    "InferenceTimeoutError",
    "ModelInferenceError",
    "QwenServiceRuntime",
    "ServiceBusyError",
]
