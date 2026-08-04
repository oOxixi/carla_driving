from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

import tools.run_qwen_latency_gate as latency_gate_module
from integration.qwen_vl_adapter import QwenVLActionChoice
from tools.run_qwen_latency_gate import (
    latency_gate_exit_code,
    summarize_latency_gate,
)


def test_latency_gate_reports_interpolated_p95_and_early_stop() -> None:
    report = summarize_latency_gate(
        [100.0, 200.0, 300.0, 400.0, 500.0],
        threshold_ms=300.0,
    )

    assert report == {
        "count": 5,
        "mean_ms": 300.0,
        "p50_ms": 300.0,
        "p95_ms": pytest.approx(480.0),
        "max_ms": 500.0,
        "threshold_ms": 300.0,
        "status": "EARLY_STOP",
        "run_correctness_next": False,
    }
    assert latency_gate_exit_code(report) == 2


def test_latency_gate_allows_correctness_only_after_latency_passes() -> None:
    report = summarize_latency_gate(
        [210.0, 220.0, 230.0, 240.0, 250.0],
        threshold_ms=300.0,
    )

    assert report["p95_ms"] == pytest.approx(248.0)
    assert report["status"] == "PASS"
    assert report["run_correctness_next"] is True
    assert latency_gate_exit_code(report) == 0


def test_latency_gate_resolves_default_profile_for_model_and_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = tmp_path / "scene.png"
    image.write_bytes(b"not-decoded-by-fake")
    output = tmp_path / "latency.json"
    captured: dict[str, object] = {}

    class FakeBackend:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)
            self.prompt_style = kwargs["profile"].prompt_style  # type: ignore[index,union-attr]

        def generate_action(self, **_: object) -> QwenVLActionChoice:
            return QwenVLActionChoice("A", "START", 0.99)

        def close(self) -> None:
            pass

    monkeypatch.setattr(latency_gate_module, "OpenAICompatibleQwenVLBackend", FakeBackend)
    monkeypatch.setattr(latency_gate_module, "_gpu_snapshot", lambda: {"available": False})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_latency_gate.py",
            "--image",
            str(image),
            "--output",
            str(output),
            "--warmups",
            "1",
            "--measurements",
            "1",
        ],
    )

    assert latency_gate_module.main() == 0

    profile = captured["profile"]
    assert profile.name == "qwen3vl-2b-int4"  # type: ignore[union-attr]
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["model"] == "h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4"
    assert report["model_revision"] == "f91db2369bd00e7ec20bf09b6a0080cdb26aefa5"
    assert report["image_max_side"] == 256
