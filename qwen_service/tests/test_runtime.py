from __future__ import annotations

from threading import Event

import pytest

from qwen_service.runtime import (
    InferenceTimeoutError,
    QwenServiceRuntime,
    ServiceBusyError,
)


def _payload(request_id: str = "req-001") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "frame": 12,
        "sim_time_s": 0.6,
        "voice_command": "减速",
        "rgb_ref": None,
        "scene_state": {"traffic_light": "GREEN"},
        "perception": {"detected_objects": []},
        "safety_state": {"recommended_action": "SLOW_DOWN"},
    }


class _ReadyAdapter:
    def infer(self, _context: object) -> dict[str, object]:
        return {
            "action": "SLOW_DOWN",
            "confidence": 0.95,
            "requires_confirmation": False,
            "reason_zh": "前方风险",
        }


def test_successful_inference_updates_runtime_metrics() -> None:
    runtime = QwenServiceRuntime(
        _ReadyAdapter(),
        model_name="test-qwen",
        gpu_stats=lambda: {"available": False},
    )
    try:
        response = runtime.infer(_payload())
        metrics = runtime.metrics()
    finally:
        runtime.close()

    assert response["status"] == "READY"
    assert response["request_id"] == "req-001"
    assert response["decision"]["action"] == "SLOW_DOWN"
    assert metrics["requests"] == {
        "total": 1,
        "succeeded": 1,
        "failed": 0,
        "timed_out": 0,
        "busy_rejected": 0,
    }
    assert metrics["latency_ms"]["count"] == 1
    assert metrics["gpu"] == {"available": False}


class _BlockingAdapter:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    def infer(self, _context: object) -> dict[str, object]:
        self.started.set()
        if not self.release.wait(timeout=2.0):
            raise RuntimeError("test did not release inference")
        return {
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": False,
        }


def test_timeout_keeps_gpu_slot_bounded_until_inference_really_finishes() -> None:
    adapter = _BlockingAdapter()
    runtime = QwenServiceRuntime(
        adapter,
        model_name="test-qwen",
        max_concurrency=1,
        timeout_s=0.01,
        gpu_stats=lambda: {"available": False},
    )
    try:
        with pytest.raises(InferenceTimeoutError):
            runtime.infer(_payload("req-timeout"))
        assert adapter.started.is_set()

        with pytest.raises(ServiceBusyError):
            runtime.infer(_payload("req-busy"))

        metrics = runtime.metrics()
        assert metrics["requests"]["timed_out"] == 1
        assert metrics["requests"]["busy_rejected"] == 1
        assert metrics["in_flight"] == 1
    finally:
        adapter.release.set()
        runtime.close()
