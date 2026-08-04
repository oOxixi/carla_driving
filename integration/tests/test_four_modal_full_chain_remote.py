from __future__ import annotations

import json
import hashlib
from pathlib import Path

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
    monkeypatch.setattr(
        "tools.run_four_modal_full_chain.audio_to_command",
        lambda *_args, **_kwargs: {"source_text": "stop", "intent": "STOP", "status": "valid", "confirm_required": False},
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

    assert main() == 0
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
    assert report["accuracy"]["asr"]["case_count"] == 0
    assert report["accuracy"]["multimodal"]["case_count"] == 1
