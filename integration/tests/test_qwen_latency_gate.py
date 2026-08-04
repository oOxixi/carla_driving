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
    frames = tmp_path / "frames"
    frames.mkdir()
    frame_paths = []
    for index in range(15):
        frame = frames / f"frame-{index:02d}.png"
        frame.write_bytes(f"distinct-frame-{index}".encode("ascii"))
        frame_paths.append(frame.resolve())
    output = tmp_path / "latency.json"
    captured: dict[str, object] = {}

    class FakeBackend:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)
            captured["image_paths"] = []
            self.prompt_style = kwargs["profile"].prompt_style  # type: ignore[index,union-attr]

        def generate_action(self, **kwargs: object) -> QwenVLActionChoice:
            captured["image_paths"].append(kwargs["image_path"])  # type: ignore[index,union-attr]
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
            "--dynamic-frames-dir",
            str(frames),
            "--output",
            str(output),
        ],
    )

    assert latency_gate_module.main() == 0

    profile = captured["profile"]
    assert profile.name == "qwen3vl-2b-int4"  # type: ignore[union-attr]
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["model"] == "h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4"
    assert report["model_revision"] == "f91db2369bd00e7ec20bf09b6a0080cdb26aefa5"
    assert report["image_max_side"] == 256
    assert report["dataset_kind"] == "official_dynamic_frame_latency_gate"
    assert report["warmups"] == 5
    assert report["measurements_requested"] == 10
    assert captured["image_paths"] == frame_paths


@pytest.mark.parametrize("frame_count", [1, 15])
def test_official_gate_rejects_single_or_repeated_frame_content(
    frame_count: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(frame_count):
        (frames / f"frame-{index:02d}.png").write_bytes(b"same-content")
    output = tmp_path / "latency.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_latency_gate.py",
            "--dynamic-frames-dir",
            str(frames),
            "--output",
            str(output),
        ],
    )

    with pytest.raises(SystemExit, match="2"):
        latency_gate_module.main()


def test_fixed_image_mode_is_a_diagnostic_not_an_official_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = tmp_path / "scene.png"
    image.write_bytes(b"fixed-image")
    output = tmp_path / "diagnostic.json"

    class FakeBackend:
        prompt_style = "compact-v2"

        def __init__(self, **_: object) -> None:
            pass

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
            "--fixed-image-diagnostic",
            str(image),
            "--output",
            str(output),
        ],
    )

    assert latency_gate_module.main() == 0

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["dataset_kind"] == "fixed_image_hot_latency_diagnostic"
    assert report["status"] == "DIAGNOSTIC"
    assert report["run_correctness_next"] is False
