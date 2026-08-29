"""A-owned fast/slow router with strict deadlines and bounded queues."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import math
from queue import Empty, Full, Queue
from threading import Lock, Thread
import time
from typing import Any
from uuid import uuid4

from .complexity_router import (
    CONFIRM_SAFE,
    FAST_LOCAL,
    ComplexityRouter,
    QwenRoutingDecision,
)
from .interface_registry import InterfaceRegistry, InterfaceValidationError
from .plan_compiler import CompiledManeuverPlan, PlanCompiler
from .plan_validator import PlanValidationError, PlanValidator


FAST_INTENTS = frozenset({
    "START", "STOP", "EMERGENCY_STOP", "SET_SPEED", "SLOW_DOWN", "KEEP_LANE",
})
PROPULSION_BEHAVIORS = frozenset({
    "KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "FOLLOW", "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT", "TURN_LEFT", "TURN_RIGHT", "PULL_OVER", "YIELD",
})
TERMINAL_STATUSES = frozenset({
    "SUCCEEDED", "FAILED", "REJECTED", "EXPIRED", "TIMED_OUT", "SAFETY_OVERRIDE",
})


@dataclass(frozen=True, slots=True)
class OrchestratorConfig:
    qwen_queue_size: int = 1
    sensor_queue_size: int = 4
    log_queue_size: int = 1024
    model_timeout_ms: float = 300.0
    minimum_confidence: float = 0.80
    max_speed_mps: float = 13.8888888889
    max_accel_mps2: float = 2.5
    max_decel_mps2: float = 5.0
    top_k_targets: int = 8
    qwen_mode: str = "atomic_v1"
    force_qwen_all_voice: bool = False
    allowed_slow_behaviors: tuple[str, ...] = (
        "KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "YIELD", "FOLLOW",
        "CHANGE_LANE", "TURN", "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER",
    )

    def __post_init__(self) -> None:
        for name in ("qwen_queue_size", "sensor_queue_size", "log_queue_size", "top_k_targets"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("model_timeout_ms", "max_speed_mps", "max_accel_mps2", "max_decel_mps2"):
            value = getattr(self, name)
            if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be in [0, 1]")
        if self.qwen_mode not in {"atomic_v1", "planner_v2"}:
            raise ValueError("qwen_mode must be 'atomic_v1' or 'planner_v2'")
        if type(self.force_qwen_all_voice) is not bool:
            raise TypeError("force_qwen_all_voice must be bool")
        allowed_values = {
            "KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "YIELD", "FOLLOW",
            "CHANGE_LANE", "TURN", "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER",
        }
        if (
            type(self.allowed_slow_behaviors) is not tuple
            or not self.allowed_slow_behaviors
            or len(set(self.allowed_slow_behaviors)) != len(self.allowed_slow_behaviors)
            or any(item not in allowed_values for item in self.allowed_slow_behaviors)
        ):
            raise ValueError("allowed_slow_behaviors must be a unique supported tuple")


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    qwen_depth: int
    sensor_depth: int
    log_depth: int
    qwen_overflow: int
    sensor_overflow: int
    log_overflow: int


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    disposition: str
    command_id: str
    control_command: Mapping[str, Any] | None = None
    model_request: Mapping[str, Any] | None = None
    decision_plan: Mapping[str, Any] | None = None
    feedback: Mapping[str, Any] | None = None
    reason_code: str = "NONE"
    queues: QueueSnapshot | None = None
    routing_score: int | None = None
    routing_reasons: tuple[str, ...] = ()
    routing_features: Mapping[str, Any] | None = None
    qwen_mode: str = "atomic_v1"
    safe_wait_behavior: str = "STOP"
    compiled_plan: Mapping[str, Any] | None = None
    model_completed_ns: int | None = None
    model_timing: Mapping[str, float] | None = None


@dataclass(frozen=True, slots=True)
class _SlowJob:
    request: dict[str, Any]
    perception: dict[str, Any]
    submitted_wall_ns: int
    routing: QwenRoutingDecision
    runtime_state: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _SlowResult:
    job: _SlowJob
    status: str
    completed_wall_ns: int
    plan: dict[str, Any] | None = None
    compiled: CompiledManeuverPlan | None = None
    error: str | None = None
    worker_started_wall_ns: int | None = None
    inference_completed_wall_ns: int | None = None


class PipelineOrchestrator:
    """Route commands while model inference stays on a private slow worker.

    ``infer`` is deliberately a callback boundary. It may be an HTTP Qwen
    client or a local adapter, but it executes only on the private slow worker.
    A missing callback keeps the fast path available and rejects slow requests.
    ``poll_slow`` is non-blocking by default; an explicit bounded wait is used
    only on a newly submitted acceptance command to measure the same-frame
    sensor-to-trajectory boundary.
    """

    def __init__(
        self,
        infer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        *,
        config: OrchestratorConfig | None = None,
        registry: InterfaceRegistry | None = None,
        complexity_router: ComplexityRouter | None = None,
        plan_validator: PlanValidator | None = None,
        plan_compiler: PlanCompiler | None = None,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self.config = config or OrchestratorConfig()
        self.registry = registry or InterfaceRegistry()
        self.complexity_router = complexity_router or ComplexityRouter(
            minimum_confidence=self.config.minimum_confidence,
        )
        self.plan_validator = plan_validator or PlanValidator(
            registry=self.registry,
            maximum_speed_mps=self.config.max_speed_mps,
            minimum_confidence=self.config.minimum_confidence,
            clock_ns=clock_ns,
        )
        self.plan_compiler = plan_compiler or PlanCompiler()
        self._clock_ns = clock_ns
        self._infer = infer
        self._qwen_queue: Queue[_SlowJob | None] = Queue(maxsize=self.config.qwen_queue_size)
        self._result_queue: Queue[_SlowResult] = Queue(
            maxsize=self.config.qwen_queue_size * 2 + 2,
        )
        self._sensor_queue: Queue[dict[str, Any]] = Queue(maxsize=self.config.sensor_queue_size)
        self._log_queue: Queue[dict[str, Any]] = Queue(maxsize=self.config.log_queue_size)
        self._lock = Lock()
        self._closed = False
        self._active_job: _SlowJob | None = None
        # Only active timed-out requests live here.  The worker removes the ID
        # when its late result arrives, so this cannot grow with completed work.
        self._revoked_request_ids: set[str] = set()
        self._overflow = {"qwen": 0, "sensor": 0, "log": 0}
        self._worker = Thread(target=self._run_slow_worker, name="qwen-slow-path", daemon=True)
        self._worker.start()

    def submit_command(
        self,
        command: Mapping[str, Any],
        perception: Mapping[str, Any],
        *,
        now_ns: int | None = None,
        rgb_ref: str | None = None,
        runtime_state: Mapping[str, Any] | None = None,
    ) -> OrchestrationResult:
        now = self._now(now_ns)
        try:
            canonical = self.registry.validate("driving_command", command)
            scene = self.registry.validate("perception_state", perception)
        except InterfaceValidationError as error:
            command_id = str(command.get("command_id", "invalid-command")) if isinstance(command, Mapping) else "invalid-command"
            return self._rejected(command_id, now, "INVALID_INTERFACE", str(error))
        command_id = canonical["command_id"]
        runtime_snapshot = dict(runtime_state or {})
        if canonical["deadline_ns"] <= canonical["received_at_ns"]:
            return self._rejected(command_id, now, "INVALID_DEADLINE", "deadline must follow receipt")
        if now >= canonical["deadline_ns"]:
            return self._feedback_result(command_id, now, "EXPIRED", "COMMAND_EXPIRED", "command deadline elapsed")

        routing = self.complexity_router.decide(canonical, scene, runtime_snapshot)
        self._publish_routing_event(command_id, scene, routing)
        emergency_reason = (
            self._perception_stop_reason(scene)
            or self._command_stop_reason(canonical)
            or self._blocked_maneuver_stop_reason(canonical, scene, runtime_snapshot)
        )
        intent = canonical["intent"]
        force_model = self.config.force_qwen_all_voice and intent != "EMERGENCY_STOP"
        if (
            emergency_reason is not None
            and intent not in {"STOP", "EMERGENCY_STOP"}
            and not force_model
        ):
            control = self._safety_stop(canonical, scene, now, emergency_reason)
            return OrchestrationResult(
                "FAST", command_id, control_command=control,
                feedback=self._feedback(
                    command_id, now, "SAFETY_OVERRIDE", "safety stop issued",
                    emergency_reason, safety_event_reason=emergency_reason,
                ),
                reason_code=emergency_reason, queues=self.queue_snapshot(),
                **self._routing_fields(routing),
            )

        if routing.disposition == FAST_LOCAL and not force_model:
            try:
                control = self._fast_control(canonical, scene, now)
            except (ValueError, InterfaceValidationError) as error:
                return self._rejected(command_id, now, "FAST_PATH_INVALID", str(error))
            return OrchestrationResult(
                "FAST", command_id, control_command=control,
                feedback=self._feedback(command_id, now, "RECEIVED", "fast command validated", None),
                reason_code=control["reason_code"], queues=self.queue_snapshot(),
                **self._routing_fields(routing),
            )

        if routing.disposition == CONFIRM_SAFE and not force_model:
            reason = routing.reasons[0] if routing.reasons else "CONFIRMATION_REQUIRED"
            return self._feedback_result(
                command_id, now, "REJECTED", reason,
                "command requires safe clarification and was not sent to Qwen",
                disposition="CONFIRM_SAFE", routing=routing,
            )

        request = self._model_request(
            canonical, scene, now, rgb_ref=rgb_ref,
            runtime_state=runtime_snapshot, routing=routing,
        )
        if self._infer is None:
            return self._feedback_result(
                command_id, now, "REJECTED", "QWEN_UNAVAILABLE",
                "complex command rejected because Qwen service is unavailable",
                model_request=request, routing=routing,
            )
        job = _SlowJob(request, scene, self._clock_ns(), routing, runtime_snapshot)
        evicted = self._enqueue_slow_job(job)
        if evicted is not None:
            self._put_latest(
                self._result_queue,
                _SlowResult(
                    evicted,
                    "OVERFLOW",
                    self._clock_ns(),
                    error="queued Qwen request was superseded by a newer request",
                ),
                "qwen",
                count_overflow=False,
            )
        return OrchestrationResult(
            "SLOW_PENDING", command_id, model_request=request,
            feedback=self._feedback(
                command_id, now, "RECEIVED", "slow request queued", None,
                safety_event_reason=emergency_reason,
            ),
            reason_code="QWEN_QUEUED", queues=self.queue_snapshot(),
            **self._routing_fields(routing),
        )

    def poll_slow(
        self,
        *,
        now_ns: int | None = None,
        wait_timeout_ms: float = 0.0,
    ) -> tuple[OrchestrationResult, ...]:
        if (
            type(wait_timeout_ms) not in (int, float)
            or isinstance(wait_timeout_ms, bool)
            or not math.isfinite(float(wait_timeout_ms))
            or wait_timeout_ms < 0
        ):
            raise ValueError("wait_timeout_ms must be finite and non-negative")
        completed_results: list[_SlowResult] = []
        if wait_timeout_ms > 0:
            try:
                completed_results.append(
                    self._result_queue.get(timeout=float(wait_timeout_ms) / 1000.0),
                )
            except Empty:
                pass
        now = self._now(now_ns)
        results: list[OrchestrationResult] = []
        active = self._active_snapshot()
        if active is not None:
            elapsed_ms = (self._clock_ns() - active.submitted_wall_ns) / 1e6
            if elapsed_ms > self.config.model_timeout_ms:
                timed_out = False
                with self._lock:
                    if self._active_job is active:
                        self._revoked_request_ids.add(active.request["request_id"])
                        self._active_job = None
                        timed_out = True
                if timed_out:
                    results.append(self._feedback_result(
                        active.request["command_id"], now, "TIMED_OUT", "QWEN_TIMEOUT",
                        "Qwen inference exceeded wall-clock deadline",
                        model_request=active.request, routing=active.routing,
                    ))
        while True:
            try:
                completed_results.append(self._result_queue.get_nowait())
            except Empty:
                break
        for completed in completed_results:
            consumed = self._consume_slow_result(completed)
            if consumed is not None:
                results.append(consumed)
        return tuple(results)

    def publish_perception(self, payload: Mapping[str, Any]) -> bool:
        scene = self.registry.validate("perception_state", payload)
        return self._put_latest(self._sensor_queue, scene, "sensor")

    def latest_perception(self) -> dict[str, Any] | None:
        latest: dict[str, Any] | None = None
        while True:
            try:
                latest = self._sensor_queue.get_nowait()
            except Empty:
                return latest

    def publish_log(self, record: Mapping[str, Any]) -> bool:
        try:
            canonical = json.loads(json.dumps(dict(record), allow_nan=False))
        except (TypeError, ValueError) as error:
            raise ValueError(f"log record must be strict JSON: {error}") from error
        return self._put_latest(self._log_queue, canonical, "log")

    def drain_logs(self, *, maximum: int | None = None) -> tuple[dict[str, Any], ...]:
        if maximum is not None and (type(maximum) is not int or maximum < 1):
            raise ValueError("maximum must be a positive integer or None")
        records: list[dict[str, Any]] = []
        while maximum is None or len(records) < maximum:
            try:
                records.append(self._log_queue.get_nowait())
            except Empty:
                break
        return tuple(records)

    def queue_snapshot(self) -> QueueSnapshot:
        with self._lock:
            overflow = dict(self._overflow)
        return QueueSnapshot(
            self._qwen_queue.qsize(), self._sensor_queue.qsize(), self._log_queue.qsize(),
            overflow["qwen"], overflow["sensor"], overflow["log"],
        )

    def close(self, *, timeout_s: float = 1.0) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._put_latest(self._qwen_queue, None, "qwen", count_overflow=False)
        self._worker.join(timeout=max(0.0, float(timeout_s)))

    def __enter__(self) -> "PipelineOrchestrator":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _run_slow_worker(self) -> None:
        while True:
            job = self._qwen_queue.get()
            if job is None:
                return
            with self._lock:
                if self._closed:
                    return
                self._active_job = job
            worker_started_wall_ns = self._clock_ns()
            inference_completed_wall_ns: int | None = None
            try:
                assert self._infer is not None
                raw = self._infer(job.request)
                inference_completed_wall_ns = self._clock_ns()
                if self.config.qwen_mode == "planner_v2":
                    validation_scene = {**job.perception, **job.runtime_state}
                    plan = self.plan_validator.validate(
                        raw,
                        scene=validation_scene,
                        expected_request_id=job.request["request_id"],
                        expected_command_id=job.request["command_id"],
                        now_ns=job.request["created_at_ns"],
                    )
                    compiled = self.plan_compiler.compile(plan, scene=validation_scene)
                else:
                    plan = self.registry.validate("decision_plan", raw)
                    compiled = None
                result = _SlowResult(
                    job, "READY", self._clock_ns(), plan=plan, compiled=compiled,
                    worker_started_wall_ns=worker_started_wall_ns,
                    inference_completed_wall_ns=inference_completed_wall_ns,
                )
            except (PlanValidationError, InterfaceValidationError) as error:
                inference_completed_wall_ns = inference_completed_wall_ns or self._clock_ns()
                result = _SlowResult(
                    job, "REJECTED", self._clock_ns(),
                    error=f"{type(error).__name__}: {error}",
                    worker_started_wall_ns=worker_started_wall_ns,
                    inference_completed_wall_ns=inference_completed_wall_ns,
                )
            except Exception as error:
                inference_completed_wall_ns = inference_completed_wall_ns or self._clock_ns()
                result = _SlowResult(
                    job, "ERROR", self._clock_ns(),
                    error=f"{type(error).__name__}: {error}",
                    worker_started_wall_ns=worker_started_wall_ns,
                    inference_completed_wall_ns=inference_completed_wall_ns,
                )
            with self._lock:
                still_active = self._active_job is job
                if still_active:
                    self._active_job = None
                closed = self._closed
            if closed:
                return
            # A timeout removes active authority.  The late result is queued so
            # poll_slow can retire its revocation marker without emitting a
            # second terminal status.
            self._put_latest(self._result_queue, result, "qwen", count_overflow=False)

    def _consume_slow_result(self, result: _SlowResult) -> OrchestrationResult | None:
        request = result.job.request
        command_id = request["command_id"]
        request_id = request["request_id"]
        # Requests may use a caller-supplied monotonic epoch (tests and remote
        # adapters do this).  Translate the measured worker duration onto that
        # epoch instead of comparing unrelated absolute clocks.
        created_ns = int(request["created_at_ns"])
        if abs(result.job.submitted_wall_ns - created_ns) <= 60_000_000_000:
            # Production path: same monotonic epoch.  Keep the absolute worker
            # completion time so image staging/queueing remains in E2E.
            decision_ns = result.completed_wall_ns
        else:
            # Synthetic callers can supply another monotonic epoch.
            decision_ns = created_ns + max(
                0, result.completed_wall_ns - result.job.submitted_wall_ns,
            )
        model_timing = self._model_timing(result, created_ns, decision_ns)
        with self._lock:
            if request_id in self._revoked_request_ids:
                self._revoked_request_ids.remove(request_id)
                return None
        if result.status == "OVERFLOW":
            return self._feedback_result(
                command_id, decision_ns, "REJECTED", "QUEUE_OVERFLOW",
                result.error or "queued Qwen request was superseded",
                model_request=request, routing=result.job.routing,
                model_completed_ns=decision_ns, model_timing=model_timing,
            )
        if result.status == "REJECTED":
            return self._feedback_result(
                command_id, decision_ns, "REJECTED", "QWEN_PLAN_REJECTED",
                result.error or "Qwen plan failed the runtime trust boundary",
                model_request=request, routing=result.job.routing,
                model_completed_ns=decision_ns, model_timing=model_timing,
            )
        if result.status != "READY" or result.plan is None:
            return self._feedback_result(
                command_id, decision_ns, "FAILED", "QWEN_ERROR",
                result.error or "Qwen inference failed", model_request=request,
                routing=result.job.routing, model_completed_ns=decision_ns,
                model_timing=model_timing,
            )
        plan = result.plan
        if decision_ns >= request["deadline_ns"] or decision_ns >= plan["valid_until_ns"]:
            return self._feedback_result(
                command_id, decision_ns, "EXPIRED", "QWEN_STALE",
                "Qwen decision arrived after its validity boundary", model_request=request,
                routing=result.job.routing, model_completed_ns=decision_ns,
                model_timing=model_timing,
            )
        if plan["request_id"] != request["request_id"] or plan["command_id"] != command_id:
            return self._feedback_result(
                command_id, decision_ns, "REJECTED", "QWEN_ID_MISMATCH",
                "Qwen request_id/command_id mismatch", model_request=request,
                routing=result.job.routing, model_completed_ns=decision_ns,
                model_timing=model_timing,
            )
        if float(plan["confidence"]) < self.config.minimum_confidence or plan.get("requires_confirmation"):
            return self._feedback_result(
                command_id, decision_ns, "REJECTED", "QWEN_LOW_CONFIDENCE",
                "Qwen plan requires confirmation or has low confidence", model_request=request,
                routing=result.job.routing, model_completed_ns=decision_ns,
                model_timing=model_timing,
            )
        target_id = plan.get("target_id")
        if self.config.qwen_mode == "planner_v2":
            target_ids = {
                step["target"].get("target_id")
                for step in plan["steps"]
                if step["target"].get("target_id") is not None
            }
            target_id = next(iter(target_ids), None)
        available = {item["track_id"] for item in result.job.perception["objects"]}
        if self.config.qwen_mode == "planner_v2":
            missing_targets = target_ids - available
        else:
            missing_targets = {target_id} - available if target_id is not None else set()
        if missing_targets:
            return self._feedback_result(
                command_id, decision_ns, "REJECTED", "QWEN_TARGET_NOT_FOUND",
                "Qwen target_id is absent from current PerceptionState", model_request=request,
                routing=result.job.routing, model_completed_ns=decision_ns,
                model_timing=model_timing,
            )
        if result.job.perception["stale"] or not result.job.perception["sync"]["within_tolerance"]:
            return self._feedback_result(
                command_id, decision_ns, "REJECTED", "PERCEPTION_STALE",
                "slow plan cannot execute on stale or unsynchronized perception",
                model_request=request, routing=result.job.routing,
                model_completed_ns=decision_ns, model_timing=model_timing,
            )
        try:
            if self.config.qwen_mode == "planner_v2":
                if result.compiled is None:
                    raise ValueError("planner_v2 result is missing compiled steps")
                control = self._compiled_plan_control(
                    plan, result.compiled, request, result.job.perception, decision_ns,
                )
            else:
                control = self._plan_control(plan, request, result.job.perception, decision_ns)
        except (ValueError, InterfaceValidationError, PlanValidationError) as error:
            return self._feedback_result(
                command_id, decision_ns, "REJECTED", "QWEN_PLAN_INFEASIBLE", str(error),
                model_request=request, routing=result.job.routing,
                model_completed_ns=decision_ns, model_timing=model_timing,
            )
        return OrchestrationResult(
            "SLOW_READY", command_id, control_command=control, model_request=request,
            decision_plan=plan,
            feedback=self._feedback(command_id, decision_ns, "EXECUTING", "validated Qwen plan dispatched", None),
            reason_code=control["reason_code"], queues=self.queue_snapshot(),
            compiled_plan=(None if result.compiled is None else result.compiled.to_dict()),
            model_completed_ns=decision_ns,
            model_timing=model_timing,
            **self._routing_fields(result.job.routing),
        )

    @staticmethod
    def _model_timing(
        result: _SlowResult,
        created_ns: int,
        decision_ns: int,
    ) -> dict[str, float]:
        """Split the slow path while avoiding comparisons across clock epochs."""
        submitted_ns = result.job.submitted_wall_ns
        worker_started_ns = result.worker_started_wall_ns or submitted_ns
        inference_completed_ns = (
            result.inference_completed_wall_ns or result.completed_wall_ns
        )
        timing = {
            "queue_wait_ms": max(0, worker_started_ns - submitted_ns) / 1e6,
            "infer_callback_ms": max(
                0, inference_completed_ns - worker_started_ns,
            ) / 1e6,
            "validate_compile_ms": max(
                0, result.completed_wall_ns - inference_completed_ns,
            ) / 1e6,
            "sensor_to_model_ms": max(0, decision_ns - created_ns) / 1e6,
        }
        if abs(submitted_ns - created_ns) <= 60_000_000_000:
            timing["sensor_to_submit_ms"] = max(0, submitted_ns - created_ns) / 1e6
        return timing

    def _fast_control(self, command: Mapping[str, Any], scene: Mapping[str, Any], now: int) -> dict[str, Any]:
        intent = command["intent"]
        behavior = {
            "START": "KEEP_LANE",
            "STOP": "STOP",
            "EMERGENCY_STOP": "EMERGENCY_STOP",
            "SET_SPEED": "SET_SPEED",
            "SLOW_DOWN": "SLOW_DOWN",
            "KEEP_LANE": "KEEP_LANE",
        }[intent]
        requested = command["parameters"].get("target_speed_mps")
        if requested is not None:
            requested = min(float(requested), self._scene_speed_limit(scene))
        return self.registry.validate("control_command", {
            "schema_version": "1.0",
            "command_id": command["command_id"],
            "path_type": "FAST",
            "behavior": behavior,
            "target": {"target_id": None, "target_speed_mps": requested, "time_gap_s": None},
            "limits": self._limits(scene),
            "issued_at_ns": now,
            "deadline_ns": command["deadline_ns"],
            "source": "DETERMINISTIC_FAST_PATH",
            "confidence": command["confidence"],
            "reason_code": f"FAST_{intent}",
        })

    def _plan_control(
        self,
        plan: Mapping[str, Any],
        request: Mapping[str, Any],
        scene: Mapping[str, Any],
        now: int,
    ) -> dict[str, Any]:
        behavior = str(plan["behavior"])
        allowed = set(request["constraints"]["allowed_behaviors"])
        normalized_for_constraint = behavior.removesuffix("_LEFT").removesuffix("_RIGHT")
        if normalized_for_constraint not in allowed and behavior not in allowed:
            raise ValueError(f"behavior {behavior} violates allowed_behaviors")
        if request["constraints"]["must_stop"] and behavior not in {"STOP", "HOLD"}:
            raise ValueError("must_stop constraint forbids propulsion plan")
        requested = plan["parameters"].get("target_speed_mps")
        if requested is not None:
            requested = min(float(requested), self._scene_speed_limit(scene))
        return self.registry.validate("control_command", {
            "schema_version": "1.0",
            "command_id": plan["command_id"],
            "path_type": "SLOW",
            "behavior": behavior,
            "target": {
                "target_id": plan.get("target_id"),
                "target_speed_mps": requested,
                "time_gap_s": plan["parameters"].get("time_gap_s"),
            },
            "limits": self._limits(scene),
            "issued_at_ns": now,
            "deadline_ns": min(request["deadline_ns"], plan["valid_until_ns"]),
            "source": "QWEN_DECISION_PLAN",
            "confidence": plan["confidence"],
            "reason_code": plan["reason_code"],
        })

    def _compiled_plan_control(
        self,
        plan: Mapping[str, Any],
        compiled: CompiledManeuverPlan,
        request: Mapping[str, Any],
        scene: Mapping[str, Any],
        now: int,
    ) -> dict[str, Any]:
        step = compiled.steps[0]
        behavior = step.behavior
        if behavior in {"WAIT_SAFE_GAP", "PASS_TARGET"}:
            behavior = "HOLD"
        allowed = set(request["constraints"]["allowed_behaviors"])
        normalized = behavior.removesuffix("_LEFT").removesuffix("_RIGHT")
        if behavior not in {"HOLD", "STOP"} and normalized not in allowed and behavior not in allowed:
            raise ValueError(f"compiled behavior {behavior} violates allowed_behaviors")
        target_speed = step.target.get("target_speed_mps")
        if target_speed is not None:
            target_speed = min(float(target_speed), self._scene_speed_limit(scene))
        time_gap = step.target.get("time_gap_s")
        return self.registry.validate("control_command", {
            "schema_version": "1.0",
            "command_id": plan["command_id"],
            "path_type": "SLOW",
            "behavior": behavior,
            "target": {
                "target_id": step.target.get("target_id"),
                "target_speed_mps": target_speed,
                "time_gap_s": time_gap,
            },
            "limits": self._limits(scene),
            "issued_at_ns": now,
            "deadline_ns": min(request["deadline_ns"], plan["valid_until_ns"]),
            "source": "QWEN_DECISION_PLAN",
            "confidence": plan["confidence"],
            "reason_code": f"{plan['reason_code']}:{step.step_id}",
        })

    def _model_request(
        self,
        command: Mapping[str, Any],
        scene: Mapping[str, Any],
        now: int,
        *,
        rgb_ref: str | None,
        runtime_state: Mapping[str, Any] | None = None,
        routing: QwenRoutingDecision | None = None,
    ) -> dict[str, Any]:
        objects = sorted(
            scene["objects"],
            key=lambda item: (float(item["distance_m"]), -float(item["confidence"]), item["track_id"]),
        )[: self.config.top_k_targets]
        targets = [
            {
                "target_id": item["track_id"],
                "class": item["class"],
                "distance_m": item["distance_m"],
                "relative_speed_mps": -float(item["velocity_mps"][0]),
                "confidence": item["confidence"],
                "relation": self._target_relation(item),
            }
            for item in objects
        ]
        must_stop = (
            self._perception_stop_reason(scene)
            or self._command_stop_reason(command)
            or self._blocked_maneuver_stop_reason(command, scene, runtime_state)
        ) is not None
        allowed = self._allowed_model_behaviors(command, routing, must_stop=must_stop)
        deadline = min(
            int(command["deadline_ns"]),
            now + int(self.config.model_timeout_ms * 1e6),
        )
        payload = {
            "schema_version": "1.0",
            "request_id": f"qwen-{uuid4().hex}",
            "command_id": command["command_id"],
            "created_at_ns": now,
            "deadline_ns": deadline,
            "source_text": command["source_text"],
            "command_hint": {
                "intent": command["intent"],
                "target_speed_mps": command["parameters"].get("target_speed_mps"),
                "direction": command["parameters"].get("direction"),
                "target": command["parameters"].get("target"),
            },
            "rgb_ref": rgb_ref,
            "scene_summary": {
                "frame_id": scene["frame_id"],
                "sim_time_s": scene["sim_time_s"],
                "traffic_light": scene["traffic_light"],
                "risk_level": scene["risk_level"],
                "min_gap_m": scene["min_gap_m"],
                "ttc_s": scene["ttc_s"],
            },
            "targets": targets,
            "constraints": {
                "speed_limit_mps": scene.get("speed_limit_mps"),
                "allowed_behaviors": allowed,
                "must_stop": must_stop,
                "max_target_speed_mps": self._scene_speed_limit(scene),
            },
        }
        if self.config.qwen_mode == "planner_v2":
            if routing is None:
                raise ValueError("planner_v2 model requests require routing metadata")
            confirmation_required = (
                command.get("requires_confirmation") is True
                or str(command.get("ambiguity", "NONE")) != "NONE"
            )
            if confirmation_required and not must_stop:
                payload["constraints"]["allowed_behaviors"] = ["STOP"]
            payload["routing"] = {
                "disposition": "CONFIRM_SAFE" if confirmation_required else routing.disposition,
                "score": routing.score,
                "reasons": list(routing.reasons),
                "safe_wait_behavior": routing.safe_wait_behavior,
            }
            capability_names = (
                "available_lanes", "left_lane_exists", "right_lane_exists",
                "left_gap_safe", "right_gap_safe", "route_available",
                "intersection_ahead", "stop_line_clear", "original_lane",
                "current_lane", "return_direction",
            )
            capabilities = {
                name: runtime_state[name]
                for name in capability_names
                if runtime_state is not None and name in runtime_state
            }
            payload["scene_capabilities"] = capabilities
        return self.registry.validate("model_request", payload)

    def _allowed_model_behaviors(
        self,
        command: Mapping[str, Any],
        routing: QwenRoutingDecision | None,
        *,
        must_stop: bool,
    ) -> list[str]:
        if must_stop:
            return ["STOP"]
        configured = list(self.config.allowed_slow_behaviors)
        if routing is None:
            return configured
        atomic_by_intent = {
            "START": {"KEEP_LANE", "SET_SPEED"},
            "KEEP_LANE": {"KEEP_LANE"},
            "SET_SPEED": {"SET_SPEED"},
            "SLOW_DOWN": {"SLOW_DOWN"},
        }
        intent = str(command.get("intent", "")).upper()
        maneuver_by_intent = {
            "FOLLOW": {"FOLLOW", "STOP"},
            "CHANGE_LANE": {"CHANGE_LANE", "STOP"},
            "TURN": {"TURN", "STOP"},
            "PULL_OVER": {"PULL_OVER", "STOP"},
            "AVOID_OBSTACLE": {
                "SLOW_DOWN", "AVOID_OBSTACLE", "CHANGE_LANE", "RETURN_TO_LANE", "STOP",
            },
        }
        if routing.features.requires_maneuver and intent in maneuver_by_intent:
            narrowed = [
                behavior for behavior in configured
                if behavior in maneuver_by_intent[intent]
            ]
            return narrowed or ["STOP"]
        if routing.features.requires_maneuver:
            return configured
        if (
            routing.features.atomic_action_count <= 1
            and not routing.features.has_sequence
            and not routing.features.has_condition
            and not routing.features.has_visual_reference
            and intent in atomic_by_intent
        ):
            narrowed = [
                behavior for behavior in configured
                if behavior in atomic_by_intent[intent]
            ]
            return narrowed or ["STOP"]
        non_maneuver_by_intent = {
            "START": {"KEEP_LANE", "SET_SPEED", "STOP"},
            "KEEP_LANE": {"KEEP_LANE", "SLOW_DOWN", "STOP"},
            "SET_SPEED": {"SET_SPEED", "SLOW_DOWN", "STOP"},
            "SLOW_DOWN": {"SLOW_DOWN", "STOP"},
            "YIELD": {"YIELD", "SLOW_DOWN", "STOP"},
        }
        permitted = non_maneuver_by_intent.get(intent)
        if permitted is None:
            return configured
        narrowed = [behavior for behavior in configured if behavior in permitted]
        return narrowed or ["STOP"]

    def _safety_stop(self, command: Mapping[str, Any], scene: Mapping[str, Any], now: int, reason: str) -> dict[str, Any]:
        return self.registry.validate("control_command", {
            "schema_version": "1.0",
            "command_id": command["command_id"],
            "path_type": "FAST",
            "behavior": "EMERGENCY_STOP" if scene["risk_level"] == "EMERGENCY" else "STOP",
            "target": {"target_id": None, "target_speed_mps": 0.0, "time_gap_s": None},
            "limits": self._limits(scene),
            "issued_at_ns": now,
            "deadline_ns": command["deadline_ns"],
            "source": "SAFETY_SYSTEM",
            "confidence": 1.0,
            "reason_code": reason,
        })

    def _limits(self, scene: Mapping[str, Any]) -> dict[str, float]:
        return {
            "max_speed_mps": self._scene_speed_limit(scene),
            "max_accel_mps2": self.config.max_accel_mps2,
            "max_decel_mps2": self.config.max_decel_mps2,
        }

    def _scene_speed_limit(self, scene: Mapping[str, Any]) -> float:
        value = scene.get("speed_limit_mps")
        return self.config.max_speed_mps if value is None else min(float(value), self.config.max_speed_mps)

    @staticmethod
    def _perception_stop_reason(scene: Mapping[str, Any]) -> str | None:
        if scene["stale"] or not scene["sync"]["within_tolerance"]:
            return "PERCEPTION_STALE"
        if not scene["modality_valid"]["vehicle_state"]:
            return "VEHICLE_STATE_INVALID"
        if scene["risk_level"] == "EMERGENCY":
            return "PERCEPTION_EMERGENCY"
        for item in scene.get("objects", ()):
            if not isinstance(item, Mapping):
                continue
            position = item.get("position_m")
            if not isinstance(position, (list, tuple)) or len(position) < 2:
                continue
            distance = item.get("distance_m")
            confidence = item.get("confidence", 0.0)
            velocity = item.get("velocity_mps")
            if type(distance) not in (int, float) or type(confidence) not in (int, float):
                continue
            stationary = (
                isinstance(velocity, (list, tuple))
                and len(velocity) >= 1
                and type(velocity[0]) in (int, float)
                and abs(float(velocity[0])) <= 0.3
            )
            if (
                float(position[0]) >= 0.0
                and abs(float(position[1])) <= 1.5
                and float(distance) <= 12.5
                and float(confidence) >= 0.5
                and stationary
            ):
                return "FRONT_OBJECT_STOP"
        if scene["traffic_light"] in {"RED", "YELLOW"} and scene.get("distance_to_stop_line_m") is not None:
            return "TRAFFIC_LIGHT_STOP"
        return None

    @staticmethod
    def _command_stop_reason(command: Mapping[str, Any]) -> str | None:
        source_text = str(command.get("source_text", "")).upper()
        if any(
            keyword in source_text
            for keyword in (
                "遮挡区域", "盲区", "OCCLUDED AREA", "BLIND SPOT", "BLIND-SPOT",
            )
        ):
            return "COMMAND_OCCLUSION_STOP"
        return None

    @staticmethod
    def _blocked_maneuver_stop_reason(
        command: Mapping[str, Any],
        scene: Mapping[str, Any],
        runtime_state: Mapping[str, Any] | None,
    ) -> str | None:
        source_text = str(command.get("source_text", "")).upper()
        if not any(
            keyword in source_text
            for keyword in ("绕过", "避让", "换道", "变道", "AVOID", "LANE CHANGE")
        ):
            return None
        state = dict(runtime_state or {})
        capability_keys = {
            "available_lanes", "left_lane_exists", "right_lane_exists",
            "left_gap_safe", "right_gap_safe",
        }
        if not capability_keys.intersection(state):
            return None
        front_obstacle = False
        for item in scene.get("objects", ()):
            if not isinstance(item, Mapping):
                continue
            position = item.get("position_m")
            distance = item.get("distance_m")
            confidence = item.get("confidence", 0.0)
            if (
                isinstance(position, (list, tuple))
                and len(position) >= 2
                and type(distance) in (int, float)
                and type(confidence) in (int, float)
                and 0.0 <= float(position[0])
                and abs(float(position[1])) <= 1.8
                and float(distance) <= 30.0
                and float(confidence) >= 0.5
            ):
                front_obstacle = True
                break
        if not front_obstacle:
            return None
        available = set(state.get("available_lanes") or ())
        left_safe = bool(state.get("left_lane_exists")) and bool(state.get("left_gap_safe"))
        right_safe = bool(state.get("right_lane_exists")) and bool(state.get("right_gap_safe"))
        if available:
            left_safe = left_safe and "LEFT_ADJACENT" in available
            right_safe = right_safe and "RIGHT_ADJACENT" in available
        return None if left_safe or right_safe else "NO_SAFE_ADJACENT_LANE"

    @staticmethod
    def _target_relation(item: Mapping[str, Any]) -> str:
        x, y, _z = (float(value) for value in item["position_m"])
        longitudinal = "ahead" if x >= 0.0 else "behind"
        lateral = "left" if y > 1.5 else "right" if y < -1.5 else "center"
        return f"{lateral}_{longitudinal}"

    def _feedback_result(
        self,
        command_id: str,
        now: int,
        status: str,
        reason: str,
        detail: str,
        *,
        model_request: Mapping[str, Any] | None = None,
        disposition: str = "REJECTED",
        routing: QwenRoutingDecision | None = None,
        model_completed_ns: int | None = None,
        model_timing: Mapping[str, float] | None = None,
    ) -> OrchestrationResult:
        return OrchestrationResult(
            disposition, command_id, model_request=model_request,
            feedback=self._feedback(command_id, now, status, detail, reason),
            reason_code=reason, queues=self.queue_snapshot(),
            model_completed_ns=model_completed_ns,
            model_timing=model_timing,
            **({} if routing is None else self._routing_fields(routing)),
        )

    def _rejected(self, command_id: str, now: int, reason: str, detail: str) -> OrchestrationResult:
        return self._feedback_result(command_id, now, "REJECTED", reason, detail)

    def _routing_fields(self, routing: QwenRoutingDecision) -> dict[str, Any]:
        return {
            "routing_score": routing.score,
            "routing_reasons": routing.reasons,
            "routing_features": routing.features.to_dict(),
            "qwen_mode": self.config.qwen_mode,
            "safe_wait_behavior": routing.safe_wait_behavior,
        }

    def _publish_routing_event(
        self,
        command_id: str,
        scene: Mapping[str, Any],
        routing: QwenRoutingDecision,
    ) -> None:
        self.publish_log({
            "record_type": "qwen_routing_event",
            "command_id": command_id,
            "plan_id": None,
            "frame_id": scene["frame_id"],
            "sim_time_s": scene["sim_time_s"],
            "route": routing.disposition,
            "routing_score": routing.score,
            "reason_codes": list(routing.reasons),
            "qwen_call_index": 0,
            "safe_wait_behavior": routing.safe_wait_behavior,
            "qwen_mode": self.config.qwen_mode,
            "routing_features": routing.features.to_dict(),
        })

    def _feedback(
        self,
        command_id: str,
        now: int,
        status: str,
        detail: str,
        reason: str | None,
        *,
        safety_event_reason: str | None = None,
    ) -> dict[str, Any]:
        safety_event = None
        if safety_event_reason is not None:
            stopped = {"throttle": 0.0, "brake": 1.0, "steer": 0.0}
            safety_event = {
                "reason_code": safety_event_reason,
                "raw_control": dict(stopped),
                "final_control": dict(stopped),
            }
        return self.registry.validate("execution_feedback", {
            "schema_version": "1.0",
            "command_id": command_id,
            "status": status,
            "action_summary": detail,
            "emitted_at_ns": now,
            "t_action_apply_ns": None,
            "latency_ms": None,
            "safety_event": safety_event,
            "terminal_reason": reason if status in TERMINAL_STATUSES else None,
        })

    def _active_snapshot(self) -> _SlowJob | None:
        with self._lock:
            return self._active_job

    def _enqueue_slow_job(self, job: _SlowJob) -> _SlowJob | None:
        """Enqueue newest work and return any explicitly evicted request."""
        with self._lock:
            if self._closed:
                raise RuntimeError("orchestrator is closed")
        while True:
            try:
                self._qwen_queue.put_nowait(job)
                return None
            except Full:
                try:
                    evicted = self._qwen_queue.get_nowait()
                except Empty:
                    continue
                if evicted is None:
                    # close() owns the sentinel.  Restore it and reject work
                    # racing with shutdown instead of reviving the worker.
                    self._qwen_queue.put_nowait(None)
                    raise RuntimeError("orchestrator is closed")
                with self._lock:
                    self._overflow["qwen"] += 1
                self._qwen_queue.put_nowait(job)
                return evicted

    def _now(self, value: int | None) -> int:
        now = self._clock_ns() if value is None else value
        if type(now) is not int or now < 0:
            raise ValueError("now_ns must be a non-negative integer")
        return now

    def _put_latest(
        self,
        queue: Queue[Any],
        value: Any,
        queue_name: str,
        *,
        count_overflow: bool = True,
    ) -> bool:
        with self._lock:
            if self._closed and value is not None:
                raise RuntimeError("orchestrator is closed")
        overflowed = False
        try:
            queue.put_nowait(value)
        except Full:
            overflowed = True
            try:
                queue.get_nowait()
            except Empty:
                pass
            queue.put_nowait(value)
            if count_overflow:
                with self._lock:
                    self._overflow[queue_name] += 1
        return not overflowed


__all__ = [
    "FAST_INTENTS",
    "OrchestratorConfig",
    "OrchestrationResult",
    "PipelineOrchestrator",
    "QueueSnapshot",
]
