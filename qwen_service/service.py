"""Core B service with strict contracts, bounded concurrency and metrics."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
import math
from pathlib import Path
import statistics
from threading import BoundedSemaphore, Lock
import time
from typing import Any, Protocol

from integration.qwen_boundary import QwenInputContext
from integration.qwen_vl_adapter import StrictQwenVLAdapter
from runtime.interface_registry import InterfaceRegistry, InterfaceValidationError


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


class DecisionBackend(Protocol):
    model_id: str
    production_ready: bool

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def health(self) -> tuple[bool, str]: ...


class ServiceFailure(RuntimeError):
    def __init__(self, status_code: int, error_code: str, message: str, *, request_id: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "status": "ERROR",
            "error_code": self.error_code,
            "message": str(self),
            "request_id": self.request_id,
        }


@dataclass(frozen=True, slots=True)
class QwenServiceConfig:
    timeout_ms: float = 300.0
    max_concurrency: int = 1
    max_request_bytes: int = 262_144

    def __post_init__(self) -> None:
        if type(self.timeout_ms) not in (int, float) or isinstance(self.timeout_ms, bool) or not math.isfinite(float(self.timeout_ms)) or self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be finite and positive")
        for name in ("max_concurrency", "max_request_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")


class UnavailableBackend:
    model_id = "UNAVAILABLE"
    production_ready = False

    def __init__(self, reason: str = "no local Qwen checkpoint configured") -> None:
        self.reason = reason

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError(self.reason)

    def health(self) -> tuple[bool, str]:
        return False, self.reason


class DeterministicTestBackend:
    """Contract-test backend; never valid evidence for Qwen correctness/latency."""

    model_id = "DETERMINISTIC_TEST_BACKEND"
    production_ready = False

    def health(self) -> tuple[bool, str]:
        return True, "test backend ready (not a production Qwen model)"

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        now = time.monotonic_ns()
        constraints = request["constraints"]
        text = str(request["source_text"])
        targets = request["targets"]
        if constraints["must_stop"] or any(word in text for word in ("停车", "停止", "红灯")):
            intent = behavior = "STOP"
            target_id = None
            parameters: dict[str, float] = {}
            reason = "DETERMINISTIC_SAFETY_STOP"
        elif len(targets) == 1 and any(word in text for word in ("跟随", "前车", "车辆")):
            intent = behavior = "FOLLOW"
            target_id = targets[0]["target_id"]
            parameters = {"target_speed_mps": min(4.0, float(constraints.get("max_target_speed_mps") or 4.0)), "time_gap_s": 2.0}
            reason = "DETERMINISTIC_UNIQUE_TARGET"
        else:
            intent = behavior = "SLOW_DOWN"
            target_id = None
            parameters = {"target_speed_mps": min(2.0, float(constraints.get("max_target_speed_mps") or 2.0))}
            reason = "DETERMINISTIC_CONSERVATIVE"
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": intent,
            "target_id": target_id,
            "behavior": behavior,
            "parameters": parameters,
            "confidence": 1.0,
            "reason_code": reason,
            "created_at_ns": now,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": self.model_id,
        }


class LocalQwenBackend:
    """Adapter from the repository's real local Qwen2.5-VL implementation."""

    production_ready = True

    def __init__(
        self,
        model_path: str | Path,
        *,
        image_root: str | Path | None = None,
        max_new_tokens: int = 48,
        min_pixels: int = 64 * 28 * 28,
        max_pixels: int = 256 * 28 * 28,
    ) -> None:
        path = Path(model_path).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"local Qwen checkpoint not found: {path}")
        self.model_path = path
        self.model_id = path.name
        self.adapter = StrictQwenVLAdapter.from_local_checkpoint(
            path,
            image_root=image_root,
            max_new_tokens=max_new_tokens,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )

    def health(self) -> tuple[bool, str]:
        return True, f"local checkpoint loaded: {self.model_path}"

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        targets = [
            {
                "track_id": item["target_id"],
                "class": item["class"],
                "relation": item["relation"],
                "distance_m": item["distance_m"],
                "relative_speed_mps": item.get("relative_speed_mps"),
                "confidence": item["confidence"],
            }
            for item in request["targets"]
        ]
        context = QwenInputContext(
            request_id=request["request_id"],
            frame=request["scene_summary"]["frame_id"],
            sim_time_s=request["scene_summary"]["sim_time_s"],
            voice_command=request["source_text"],
            rgb_ref=request.get("rgb_ref"),
            scene_state=dict(request["scene_summary"]),
            perception={
                "traffic_light": request["scene_summary"]["traffic_light"],
                "detected_objects": targets,
            },
            safety_state=dict(request["constraints"]),
        )
        decision = self.adapter(context)
        return self._to_plan(request, decision)

    def _to_plan(self, request: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
        action = str(decision["action"]).upper()
        intent, behavior = {
            "START": ("KEEP_LANE", "KEEP_LANE"),
            "KEEP_LANE": ("KEEP_LANE", "KEEP_LANE"),
            "SET_SPEED": ("SET_SPEED", "SET_SPEED"),
            "SLOW_DOWN": ("SLOW_DOWN", "SLOW_DOWN"),
            "STOP": ("STOP", "STOP"),
            "EMERGENCY_STOP": ("STOP", "STOP"),
        }.get(action, ("REJECT", "HOLD"))
        parameters: dict[str, float] = {}
        if decision.get("target_speed_mps") is not None:
            parameters["target_speed_mps"] = float(decision["target_speed_mps"])
        elif action == "SLOW_DOWN":
            # The frozen strict Qwen boundary permits SLOW_DOWN without a
            # numeric speed.  D requires a concrete deterministic target, so B
            # supplies the documented conservative default rather than asking
            # the model for a low-level control value.
            maximum = request["constraints"].get("max_target_speed_mps")
            parameters["target_speed_mps"] = min(
                2.0, 2.0 if maximum is None else float(maximum),
            )
        now = time.monotonic_ns()
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": intent,
            "target_id": decision.get("target_track_id"),
            "behavior": behavior,
            "parameters": parameters,
            "confidence": decision["confidence"],
            "reason_code": "QWEN_VL_" + action,
            "created_at_ns": now,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": decision["requires_confirmation"],
            "model_id": self.model_id,
        }


class QwenDecisionService:
    def __init__(
        self,
        backend: DecisionBackend,
        *,
        config: QwenServiceConfig | None = None,
        registry: InterfaceRegistry | None = None,
        clock_ns: Any = time.monotonic_ns,
    ) -> None:
        if not callable(getattr(backend, "infer", None)) or not callable(getattr(backend, "health", None)):
            raise TypeError("backend must provide infer() and health()")
        self.backend = backend
        self.config = config or QwenServiceConfig()
        self.registry = registry or InterfaceRegistry()
        self._clock_ns = clock_ns
        self._slots = BoundedSemaphore(self.config.max_concurrency)
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_concurrency,
            thread_name_prefix="qwen-infer",
        )
        self._lock = Lock()
        self._active = 0
        self._counts = {
            "requests": 0,
            "success": 0,
            "invalid": 0,
            "expired": 0,
            "busy": 0,
            "timeouts": 0,
            "backend_errors": 0,
        }
        self._latencies_ms: list[float] = []

    def infer(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request_id = str(payload.get("request_id", "")) if isinstance(payload, Mapping) else None
        with self._lock:
            self._counts["requests"] += 1
        try:
            request = self.registry.validate("model_request", payload)
        except InterfaceValidationError as error:
            self._increment("invalid")
            raise ServiceFailure(400, "INVALID_REQUEST", str(error), request_id=request_id) from error
        request_id = request["request_id"]
        now = self._clock_ns()
        if request["deadline_ns"] <= request["created_at_ns"]:
            self._increment("invalid")
            raise ServiceFailure(400, "INVALID_DEADLINE", "deadline must follow creation", request_id=request_id)
        if now >= request["deadline_ns"]:
            self._increment("expired")
            raise ServiceFailure(408, "REQUEST_EXPIRED", "request deadline elapsed", request_id=request_id)
        healthy, reason = self.backend.health()
        if not healthy:
            self._increment("backend_errors")
            raise ServiceFailure(503, "MODEL_UNAVAILABLE", reason, request_id=request_id)
        if not self._slots.acquire(blocking=False):
            self._increment("busy")
            raise ServiceFailure(429, "CONCURRENCY_LIMIT", "Qwen service is busy", request_id=request_id)

        with self._lock:
            self._active += 1
        started = time.perf_counter_ns()
        future = self._executor.submit(self.backend.infer, request)
        future.add_done_callback(self._release_slot)
        deadline_ms = (request["deadline_ns"] - now) / 1e6
        timeout_s = min(float(self.config.timeout_ms), deadline_ms) / 1000.0
        try:
            raw = future.result(timeout=timeout_s)
        except FutureTimeout as error:
            self._increment("timeouts")
            raise ServiceFailure(504, "MODEL_TIMEOUT", "Qwen inference exceeded deadline", request_id=request_id) from error
        except Exception as error:
            self._increment("backend_errors")
            raise ServiceFailure(500, "MODEL_ERROR", f"{type(error).__name__}: {error}", request_id=request_id) from error
        elapsed_ms = (time.perf_counter_ns() - started) / 1e6
        try:
            plan = self.registry.validate("decision_plan", raw)
        except InterfaceValidationError as error:
            self._increment("invalid")
            raise ServiceFailure(502, "INVALID_MODEL_OUTPUT", str(error), request_id=request_id) from error
        if plan["request_id"] != request_id or plan["command_id"] != request["command_id"]:
            self._increment("invalid")
            raise ServiceFailure(502, "MODEL_ID_MISMATCH", "model output IDs do not match request", request_id=request_id)
        if plan["valid_until_ns"] > request["deadline_ns"] or plan["created_at_ns"] >= plan["valid_until_ns"]:
            self._increment("invalid")
            raise ServiceFailure(502, "INVALID_MODEL_VALIDITY", "model output validity exceeds request", request_id=request_id)
        if any(name in plan for name in ("throttle", "brake", "steer")):
            self._increment("invalid")
            raise ServiceFailure(502, "LOW_LEVEL_OUTPUT_FORBIDDEN", "model output contains vehicle control", request_id=request_id)
        with self._lock:
            self._counts["success"] += 1
            self._latencies_ms.append(elapsed_ms)
        return plan

    def health(self) -> dict[str, Any]:
        healthy, reason = self.backend.health()
        with self._lock:
            active = self._active
        return {
            "schema_version": "1.0",
            "status": "READY" if healthy else "DEGRADED",
            "model_id": self.backend.model_id,
            "production_ready": bool(self.backend.production_ready and healthy),
            "reason": reason,
            "active_requests": active,
            "max_concurrency": self.config.max_concurrency,
            "timeout_ms": self.config.timeout_ms,
            "gpu": _gpu_metrics(),
        }

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            counts = dict(self._counts)
            active = self._active
            values = list(self._latencies_ms)
        return {
            "schema_version": "1.0",
            "model_id": self.backend.model_id,
            "production_ready": bool(self.backend.production_ready),
            "active_requests": active,
            "max_concurrency": self.config.max_concurrency,
            "counts": counts,
            "latency_ms": {
                "count": len(values),
                "mean": statistics.fmean(values) if values else None,
                "p95": _percentile(values, 0.95),
                "p99": _percentile(values, 0.99),
                "max": max(values) if values else None,
            },
            "gpu": _gpu_metrics(),
        }

    def close(self, *, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _release_slot(self, _future: Future[Any]) -> None:
        with self._lock:
            self._active -= 1
        self._slots.release()

    def _increment(self, name: str) -> None:
        with self._lock:
            self._counts[name] += 1


def _gpu_metrics() -> dict[str, Any]:
    try:
        import torch
        if not torch.cuda.is_available():
            return {"available": False, "reason": "torch.cuda.is_available() is false"}
        device = torch.cuda.current_device()
        free, total = torch.cuda.mem_get_info(device)
        return {
            "available": True,
            "device_index": device,
            "device_name": torch.cuda.get_device_name(device),
            "memory_allocated_bytes": int(torch.cuda.memory_allocated(device)),
            "memory_reserved_bytes": int(torch.cuda.memory_reserved(device)),
            "memory_free_bytes": int(free),
            "memory_total_bytes": int(total),
        }
    except Exception as error:  # pragma: no cover - driver dependent
        return {"available": False, "reason": f"{type(error).__name__}: {error}"}


__all__ = [
    "DecisionBackend",
    "DeterministicTestBackend",
    "LocalQwenBackend",
    "QwenDecisionService",
    "QwenServiceConfig",
    "ServiceFailure",
    "UnavailableBackend",
]
