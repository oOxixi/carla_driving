from __future__ import annotations

import pytest

from integration.qwen_fault_injection import ScenarioQwenFaultInjector


def test_timeout_fault_delays_before_calling_real_client():
    events = []

    def infer(request):
        events.append(("infer", request["request_id"]))
        return {"ok": True}

    injector = ScenarioQwenFaultInjector(
        infer,
        {"type": "TIMEOUT", "delay_ms": 6000},
        sleeper=lambda seconds: events.append(("sleep", seconds)),
    )

    assert injector({"request_id": "request-1"}) == {"ok": True}
    assert events == [("sleep", 6.0), ("infer", "request-1")]


def test_low_level_fault_corrupts_copy_at_runtime_boundary():
    original = {"schema_version": "2.0", "steps": [{"behavior": "TURN_RIGHT"}]}
    injector = ScenarioQwenFaultInjector(
        lambda _request: original,
        {"type": "LOW_LEVEL_FIELD", "field": "steer", "value": 0.8},
    )

    result = injector({})

    assert result["steps"][0]["steer"] == 0.8
    assert result is not original
    assert original == {"schema_version": "2.0", "steps": [{"behavior": "TURN_RIGHT"}]}


@pytest.mark.parametrize(
    "fault",
    [
        {"type": "UNKNOWN"},
        {"type": "TIMEOUT", "delay_ms": 0},
        {"type": "LOW_LEVEL_FIELD", "field": "target_speed", "value": 1.0},
        {"type": "LOW_LEVEL_FIELD", "field": "steer", "value": "left"},
    ],
)
def test_invalid_fault_contract_is_rejected(fault):
    with pytest.raises((TypeError, ValueError)):
        ScenarioQwenFaultInjector(lambda request: request, fault)
