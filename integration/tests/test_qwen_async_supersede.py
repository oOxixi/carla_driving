from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event

from integration.qwen_async import AsyncQwenDecisionBridge


@dataclass(frozen=True)
class Context:
    voice_command: str


def test_superseded_slow_result_cannot_replace_newer_request() -> None:
    first_started = Event()
    release_first = Event()

    def infer(context: Context):
        if context.voice_command == "first":
            first_started.set()
            release_first.wait(1.0)
            speed = 1.0
        else:
            speed = 5.0
        return {
            "action": "SET_SPEED",
            "target_speed_mps": speed,
            "confidence": 0.9,
            "requires_confirmation": False,
        }

    with AsyncQwenDecisionBridge(infer) as bridge:
        first = bridge.submit(Context("first"), now_s=1.0)
        assert first_started.wait(1.0)
        second = bridge.submit(Context("second"), now_s=1.1)
        assert second > first
        release_first.set()

        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            result = bridge.latest(now_s=1.2)
            if result is not None and result.status != "PENDING":
                break
            time.sleep(0.001)
        else:
            raise AssertionError("newest async decision did not finish")

        assert result.sequence == second
        assert result.runtime_command["parameters"]["speed"] == 5.0
