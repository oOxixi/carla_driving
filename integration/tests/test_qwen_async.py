from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event

from car_control_A.high_level_command import HighLevelCommandAdapter
from integration.qwen_async import AsyncQwenDecisionBridge


@dataclass(frozen=True)
class Context:
    voice_command: str


def _wait_until_ready(
    bridge: AsyncQwenDecisionBridge,
    *,
    now_s: float,
    timeout_s: float = 1.0,
):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = bridge.latest(now_s=now_s)
        if result is not None and result.status != "PENDING":
            return result
        time.sleep(0.001)
    raise AssertionError("async Qwen result did not finish")


def test_model_requested_confirmation_is_preserved() -> None:
    envelope = HighLevelCommandAdapter().adapt({
        "schema_version": "1.0",
        "command_id": "confirm-1",
        "action": "STOP",
        "confidence": 0.4,
        "requires_confirmation": True,
    })

    assert envelope["confirm_required"] is True
    assert envelope["ambiguity_type"] == "MODEL_CONFIRMATION_REQUIRED"


def test_submit_is_non_blocking_and_returns_runtime_command() -> None:
    release = Event()

    def infer(_: Context):
        release.wait(1.0)
        return {
            "action": "SET_SPEED",
            "target_speed_mps": 4.0,
            "confidence": 0.9,
            "requires_confirmation": False,
        }

    with AsyncQwenDecisionBridge(
        infer,
        ttl_s=2.0,
        command_ttl_s=25.0,
    ) as bridge:
        started = time.monotonic()
        sequence = bridge.submit(Context("设置速度"), now_s=10.0)
        elapsed = time.monotonic() - started

        assert elapsed < 0.1
        assert bridge.latest(now_s=10.0).status == "PENDING"

        release.set()
        result = _wait_until_ready(bridge, now_s=10.2)
        assert result.sequence == sequence
        assert result.ready
        assert result.runtime_command["intent"] == "SET_SPEED"
        assert result.runtime_command["parameters"]["speed"] == 4.0
        assert result.runtime_command["valid_duration_s"] == 25.0


def test_expired_result_is_stale_and_not_executable() -> None:
    with AsyncQwenDecisionBridge(
        lambda _: {
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": False,
        },
        ttl_s=1.0,
    ) as bridge:
        bridge.submit(Context("停车"), now_s=2.0)
        assert _wait_until_ready(bridge, now_s=2.1).ready

        stale = bridge.latest(now_s=3.1)
        assert stale.status == "STALE"
        assert stale.runtime_command is None


def test_inference_error_has_no_executable_command() -> None:
    def fail(_: Context):
        raise RuntimeError("model unavailable")

    with AsyncQwenDecisionBridge(fail) as bridge:
        bridge.submit(Context("继续"), now_s=1.0)
        result = _wait_until_ready(bridge, now_s=1.1)
        assert result.status == "ERROR"
        assert result.runtime_command is None
        assert "model unavailable" in result.error
