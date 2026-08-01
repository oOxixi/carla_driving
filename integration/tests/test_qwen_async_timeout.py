from __future__ import annotations

import time
from threading import Event

from integration.qwen_async import AsyncQwenDecisionBridge


def test_wall_clock_timeout_is_fail_closed_and_late_result_is_discarded() -> None:
    release = Event()

    def infer(_: object):
        release.wait(1.0)
        return {
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": False,
        }

    bridge = AsyncQwenDecisionBridge(infer, max_inference_s=0.02)
    try:
        bridge.submit(object(), now_s=1.0)
        time.sleep(0.04)
        timeout = bridge.latest(now_s=1.1)
        assert timeout is not None
        assert timeout.status == "TIMEOUT"
        assert timeout.runtime_command is None
        assert timeout.watchdog_alerts == ("QWEN_TIMEOUT",)

        release.set()
        time.sleep(0.02)
        still_timeout = bridge.latest(now_s=1.2)
        assert still_timeout is not None
        assert still_timeout.status == "TIMEOUT"
        assert still_timeout.runtime_command is None
    finally:
        release.set()
        bridge.close()
