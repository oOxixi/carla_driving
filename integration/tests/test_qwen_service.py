from __future__ import annotations

import copy
import json
from pathlib import Path
import threading
import time

import pytest

from qwen_service import (
    DeterministicTestBackend,
    QwenDecisionService,
    QwenServiceConfig,
    ServiceFailure,
    UnavailableBackend,
)


ROOT = Path(__file__).resolve().parents[2]


def _request() -> dict:
    payload = json.loads((ROOT / "interfaces" / "examples" / "model_request.json").read_text(encoding="utf-8"))
    now = time.monotonic_ns()
    payload["created_at_ns"] = now
    payload["deadline_ns"] = now + 1_000_000_000
    return payload


def test_service_returns_strict_high_level_plan_and_metrics() -> None:
    service = QwenDecisionService(DeterministicTestBackend())
    try:
        result = service.infer(_request())
        assert result["behavior"] == "FOLLOW"
        assert result["target_id"] == "vehicle-right-01"
        assert not {"throttle", "brake", "steer"}.intersection(result)
        metrics = service.metrics()
        assert metrics["counts"]["success"] == 1
        assert metrics["latency_ms"]["count"] == 1
        assert service.health()["production_ready"] is False
    finally:
        service.close()


def test_service_rejects_expired_and_unknown_fields() -> None:
    service = QwenDecisionService(DeterministicTestBackend())
    try:
        expired = _request()
        expired["created_at_ns"] = 1
        expired["deadline_ns"] = 2
        with pytest.raises(ServiceFailure) as caught:
            service.infer(expired)
        assert caught.value.error_code == "REQUEST_EXPIRED"
        unknown = _request()
        unknown["unexpected"] = True
        with pytest.raises(ServiceFailure) as caught:
            service.infer(unknown)
        assert caught.value.error_code == "INVALID_REQUEST"
    finally:
        service.close()


def test_service_unavailable_is_explicit_503() -> None:
    service = QwenDecisionService(UnavailableBackend("weights absent"))
    try:
        with pytest.raises(ServiceFailure) as caught:
            service.infer(_request())
        assert caught.value.status_code == 503
        assert caught.value.error_code == "MODEL_UNAVAILABLE"
        assert service.health()["status"] == "DEGRADED"
    finally:
        service.close()


def test_service_enforces_timeout_and_keeps_capacity_bounded() -> None:
    release = threading.Event()

    class SlowBackend(DeterministicTestBackend):
        production_ready = True

        def infer(self, request):
            release.wait(1.0)
            return super().infer(request)

    service = QwenDecisionService(
        SlowBackend(), config=QwenServiceConfig(timeout_ms=5.0, max_concurrency=1),
    )
    try:
        with pytest.raises(ServiceFailure) as timeout:
            service.infer(_request())
        assert timeout.value.error_code == "MODEL_TIMEOUT"
        with pytest.raises(ServiceFailure) as busy:
            service.infer(_request())
        assert busy.value.error_code == "CONCURRENCY_LIMIT"
    finally:
        release.set()
        service.close(wait=True)


def test_service_rejects_model_id_mismatch() -> None:
    class WrongBackend(DeterministicTestBackend):
        def infer(self, request):
            plan = dict(super().infer(request))
            plan["command_id"] = "wrong"
            return plan

    service = QwenDecisionService(WrongBackend())
    try:
        with pytest.raises(ServiceFailure) as caught:
            service.infer(_request())
        assert caught.value.error_code == "MODEL_ID_MISMATCH"
    finally:
        service.close()
