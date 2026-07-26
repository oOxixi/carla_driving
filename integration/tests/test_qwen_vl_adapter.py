from __future__ import annotations

import json
from pathlib import Path

import pytest

from integration.qwen_boundary import QwenInputContext
from integration.qwen_vl_adapter import StrictQwenVLAdapter, build_strict_qwen_prompt


class FakeBackend:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[str, Path | None]] = []

    def generate(self, *, prompt: str, image_path: Path | None) -> str:
        self.calls.append((prompt, image_path))
        return self.response  # type: ignore[return-value]


def _context(rgb_ref: str | None = None) -> QwenInputContext:
    return QwenInputContext(
        request_id="req-7",
        frame=7,
        sim_time_s=0.35,
        voice_command="继续走，但前面是红灯",
        rgb_ref=rgb_ref,
        scene_state={"traffic_light": "RED"},
        perception={"visual_valid": True},
        safety_state={"risk_level": "HIGH"},
    )


def test_adapter_resolves_image_and_returns_only_validated_high_level_json(
    tmp_path: Path,
) -> None:
    image = tmp_path / "rgb" / "000007.jpg"
    image.parent.mkdir()
    image.write_bytes(b"not-decoded-by-fake")
    backend = FakeBackend(json.dumps({
        "action": "STOP",
        "confidence": 0.98,
        "requires_confirmation": False,
        "reason_zh": "红灯停车",
        "decision_source": "QWEN_VL",
        "visual_valid": True,
    }))
    adapter = StrictQwenVLAdapter(backend, image_root=tmp_path)

    decision = adapter(_context("rgb/000007.jpg"))

    assert decision["action"] == "STOP"
    assert backend.calls[0][1] == image.resolve()
    assert "禁止字段" in backend.calls[0][0]
    assert adapter.last_trace is not None
    assert adapter.last_trace.request_id == "req-7"
    assert adapter.last_trace.latency_ms >= 0.0


@pytest.mark.parametrize(
    "response",
    [
        "```json\n{\"action\":\"STOP\"}\n```",
        json.dumps({
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": False,
            "brake": 1.0,
        }),
        "",
    ],
)
def test_adapter_rejects_prose_low_level_controls_and_empty_output(
    response: str,
) -> None:
    adapter = StrictQwenVLAdapter(FakeBackend(response))
    with pytest.raises((TypeError, ValueError)):
        adapter(_context())
    assert adapter.last_trace is not None
    assert adapter.last_trace.decision is None
    assert adapter.last_trace.error is not None
    assert adapter.last_trace.raw_output == response


def test_adapter_rejects_image_reference_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.jpg"
    outside.write_bytes(b"x")
    adapter = StrictQwenVLAdapter(FakeBackend("{}"), image_root=tmp_path)

    with pytest.raises(ValueError, match="escapes image_root"):
        adapter(_context("../outside.jpg"))


def test_prompt_serializes_frozen_context_and_never_requests_controls() -> None:
    prompt = build_strict_qwen_prompt(_context())
    assert '"request_id": "req-7"' in prompt
    assert '"traffic_light": "RED"' in prompt
    assert "throttle, brake, steer" in prompt
    assert "action只能是" in prompt
