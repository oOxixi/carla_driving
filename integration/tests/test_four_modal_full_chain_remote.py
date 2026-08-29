from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
from integration.qwen_vl_adapter import QwenVLActionChoice
from tools.run_four_modal_full_chain import main


def test_remote_run_excludes_warmups_and_records_staged_dynamic_samples(
    tmp_path: Path, monkeypatch
) -> None:
    """Dropping timing boundaries or reusing one frame must fail this test."""
    audio = tmp_path / "command.mp3"
    audio.write_bytes(b"not decoded: fake ASR is injected")
    frames = []
    for index in range(10):
        frame = tmp_path / f"frame-{index}.png"
        frame.write_bytes(f"frame {index}".encode())
        frames.append(frame)
    latency_manifest = tmp_path / "latency.json"
    latency_manifest.write_text(
        json.dumps({
            "samples": [
                {
                    "audio_ref": str(audio),
                        "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
                    "frame_ref": str(frame),
                        "frame_sha256": hashlib.sha256(frame.read_bytes()).hexdigest(),
                    "expected_intent": "STOP",
                }
                for index, frame in enumerate(frames)
            ]
        }),
        encoding="utf-8",
    )
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        json.dumps({
            "case_id": "fake-case",
            "category": "baseline",
            "split": "test",
            "rgb_ref": str(frames[0]),
            "expected_transcript": "stop",
            "scene_state": {
                "ego_speed_mps": 0.0,
                "modalities": {"voice": "v", "rgb": "r", "lidar": "l", "ego_state": "e"},
            },
            "perception": {"lidar_summary": {"valid": True, "raw_sha256": "b" * 64}},
            "safety_state": {"recommended_action": "KEEP_SPEED"},
            "expected": {"actions": ["STOP"], "requires_confirmation": False},
        }) + "\n",
        encoding="utf-8",
    )
    asr_manifest = tmp_path / "asr.json"
    asr_manifest.write_text("[]", encoding="utf-8")
    output = tmp_path / "result.json"

    class FakeOpenAICompatibleBackend:
        response_body = {
            "choices": [{
                "message": {"content": "B"},
                "logprobs": {"content": [{"token": "B", "logprob": -0.01}]},
            }]
        }

        def __init__(self, *, profile, **_kwargs) -> None:
            self.profile = profile
            self.prompt_style = profile.prompt_style
            self.last_visual_metadata = None

        def generate_action(self, **_kwargs) -> QwenVLActionChoice:
            choice = self.response_body["choices"][0]
            assert choice["logprobs"]["content"] == [{"token": "B", "logprob": -0.01}]
            return QwenVLActionChoice.from_code(choice["message"]["content"], 0.99)

        def close(self) -> None:
            pass

    monkeypatch.setattr("tools.run_four_modal_full_chain.preload_voice_models", lambda: {})
    def slow_parse_audio(*_args, t_audio_start_ns: int, **_kwargs):
        return {
            "source_text": "stop",
            "intent": "STOP",
            "status": "valid",
            "confirm_required": False,
            "t_asr_end_ns": t_audio_start_ns + 1_000_000,
            "t_intent_end_ns": t_audio_start_ns + 61_000_000,
        }

    monkeypatch.setattr(
        "tools.run_four_modal_full_chain.audio_to_command", slow_parse_audio
    )
    monkeypatch.setattr(
        "tools.run_four_modal_full_chain.OpenAICompatibleQwenVLBackend",
        FakeOpenAICompatibleBackend,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_four_modal_full_chain.py",
            "--qwen-base-url", "http://fake.invalid/v1",
            "--asr-manifest", str(asr_manifest),
            "--multimodal-cases", str(cases),
            "--latency-manifest", str(latency_manifest),
            "--warmup", "5", "--measured", "10",
            "--output", str(output),
        ],
    )

    assert main() == 3
    report = json.loads(output.read_text(encoding="utf-8"))
    raw = [json.loads(line) for line in (output.parent / "raw_timings.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(raw) == 15
    assert sum(row["phase"] == "warmup" for row in raw) == 5
    measured = [row for row in raw if row["phase"] == "measured"]
    assert len(measured) == 10
    assert len({row["frame_sha256"] for row in measured}) == 10
    assert set(measured[0]["stage_timing"]) == {
        "asr_ms", "instruction_parse_ms", "asr_nlu_ms", "sensor_fusion_ready_ms",
        "qwen_service_ms", "post_qwen_control_ms", "end_to_end_ms",
    }
    parse_values = sorted(row["stage_timing"]["instruction_parse_ms"] for row in measured)
    assert report["latency"]["instruction_parse_ms"] == {
        "count": 10,
        "mean": sum(parse_values) / 10,
        "p50": parse_values[4],
        "p95": parse_values[9],
        "p99": parse_values[9],
        "max": parse_values[9],
    }
    assert report["latency"]["end_to_end_ms"]["count"] == 10
    assert report["instruction_parse_gate"]["passes"] is False
    assert report["accuracy"]["asr"]["case_count"] == 0
    assert report["accuracy"]["multimodal"]["case_count"] == 1
    assert report["official_verdict"]["status"] == "INCOMPLETE"


@pytest.mark.parametrize(("warmup", "measured"), [(0, 1), (5, 10)])
def test_low_latency_diagnostic_never_advances_official_gates(
    warmup: int, measured: int, tmp_path: Path, monkeypatch
) -> None:
    asr_manifest = tmp_path / "asr.json"
    cases = tmp_path / "cases.jsonl"
    latency_manifest = tmp_path / "latency.json"
    for path, text in ((asr_manifest, "[]"), (cases, "{}\n"), (latency_manifest, "{}")):
        path.write_text(text, encoding="utf-8")
    output = tmp_path / "diagnostic.json"
    sample = {
        "audio_ref": "fake.mp3",
        "audio_sha256": "a" * 64,
        "frame_ref": "fake.png",
        "frame_sha256": "b" * 64,
        "expected_intent": "STOP",
        "frame_path": tmp_path / "fake.png",
    }
    sample["frame_path"].write_bytes(b"fake")
    stage_timing = {
        "asr_ms": 1.0,
        "instruction_parse_ms": 1.0,
        "asr_nlu_ms": 2.0,
        "sensor_fusion_ready_ms": 1.0,
        "qwen_service_ms": 1.0,
        "post_qwen_control_ms": 1.0,
        "end_to_end_ms": 6.0,
    }
    monkeypatch.setattr(
        "tools.run_four_modal_full_chain._load_latency_samples",
        lambda _path: [sample] * 10,
    )
    monkeypatch.setattr(
        "tools.run_four_modal_full_chain._load_jsonl",
        lambda _path: [{"rgb_ref": str(sample["frame_path"])}],
    )
    monkeypatch.setattr(
        "tools.run_four_modal_full_chain._make_qwen",
        lambda _args: (object(), None, {}),
    )
    monkeypatch.setattr("tools.run_four_modal_full_chain.preload_voice_models", lambda: {})
    monkeypatch.setattr(
        "tools.run_four_modal_full_chain._run_one",
        lambda sample, _case, _qwen, index, phase: {
            "phase": phase,
                "sample_index": index,
                "status": "READY",
                "stage_timing": stage_timing,
                **{key: value for key, value in sample.items() if key != "frame_path"},
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_four_modal_full_chain.py",
            "--qwen-base-url", "http://fake.invalid/v1",
            "--asr-manifest", str(asr_manifest),
            "--multimodal-cases", str(cases),
            "--latency-manifest", str(latency_manifest),
            "--warmup", str(warmup),
            "--measured", str(measured),
            "--diagnostic",
            "--output", str(output),
        ],
    )

    assert main() == 0

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["official_mode"] is False
    assert report["official_gates"] is None
    assert report["official_verdict"] is None
    assert report["diagnostic_gate"] == {
        "status": "DIAGNOSTIC",
        "reason": "diagnostic_non_official",
        "run_accuracy": False,
        "run_stability": False,
    }
