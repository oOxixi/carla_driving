from __future__ import annotations

from tools.evaluate_voice_audio import (
    _edit_distance,
    _latency_stats,
    _normalize_transcript,
    _synthetic_noise_audio,
    _summarize,
)

import numpy as np
import pytest
import soundfile as sf


def test_transcript_metrics_are_deterministic() -> None:
    assert _normalize_transcript("速度设为 30 公里。") == "速度设为30公里"
    assert _edit_distance("靠边停车", "考边停车") == 1
    assert _latency_stats([1.0, 2.0, 3.0]) == {
        "count": 3,
        "mean_ms": 2.0,
        "p95_ms": 2.9,
        "p99_ms": 2.98,
        "max_ms": 3.0,
    }


def test_summary_uses_all_samples_as_accuracy_denominator() -> None:
    records = [
        {
            "inference_ok": True,
            "reference_chars": 4,
            "edit_distance": 0,
            "asr_exact": True,
            "intent_ok": True,
            "slots_ok": True,
            "asr_verification": None,
            "latency": {"asr_ms": 2, "nlu_ms": 1, "total_ms": 3},
        },
        {"inference_ok": False},
    ]
    summary = _summarize(records)
    assert summary["inference_success"] == 1
    assert summary["intent_accuracy"] == 0.5
    assert summary["slot_accuracy"] == 0.5


def test_synthetic_noise_is_deterministic_and_matches_requested_snr(tmp_path) -> None:
    sample_rate = 16000
    seconds = np.arange(sample_rate, dtype=np.float32) / sample_rate
    clean = (0.1 * np.sin(2 * np.pi * 440 * seconds)).astype(np.float32)
    path = tmp_path / "tone.wav"
    sf.write(path, clean, sample_rate, subtype="FLOAT")

    first = _synthetic_noise_audio(path, 10.0, np.random.default_rng(7))
    second = _synthetic_noise_audio(path, 10.0, np.random.default_rng(7))
    assert np.array_equal(first, second)

    actual_noise = first - clean
    measured_snr = 20.0 * np.log10(
        np.sqrt(np.mean(clean**2)) / np.sqrt(np.mean(actual_noise**2))
    )
    assert measured_snr == pytest.approx(10.0, abs=0.15)
