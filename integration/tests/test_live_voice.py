import numpy as np
import pytest

from integration.live_voice import EnergyVadSegmenter, LiveVoiceConfig


def _frame(amplitude: float, config: LiveVoiceConfig) -> bytes:
    values = np.full(
        config.samples_per_frame,
        round(amplitude * 32767),
        dtype="<i2",
    )
    return values.tobytes()


def test_energy_vad_emits_one_utterance_after_trailing_silence() -> None:
    config = LiveVoiceConfig(
        pre_roll_ms=40,
        end_silence_ms=60,
        min_voice_ms=40,
        trigger_frames=2,
    )
    vad = EnergyVadSegmenter(config)
    output = None
    for amplitude in [0.0005] * 5 + [0.02] * 6 + [0.0005] * 3:
        output = vad.feed(_frame(amplitude, config)) or output
    assert output is not None
    assert len(output) >= config.bytes_per_frame * 8


def test_energy_vad_ignores_short_noise_spike() -> None:
    config = LiveVoiceConfig(
        pre_roll_ms=40,
        end_silence_ms=60,
        min_voice_ms=80,
        trigger_frames=2,
    )
    vad = EnergyVadSegmenter(config)
    outputs = [
        vad.feed(_frame(amplitude, config))
        for amplitude in [0.0005] * 4 + [0.02] * 2 + [0.0005] * 4
    ]
    assert all(output is None for output in outputs)


def test_energy_vad_rejects_wrong_frame_size() -> None:
    with pytest.raises(ValueError, match="expected"):
        EnergyVadSegmenter().feed(b"short")


def test_live_voice_config_validates_thresholds() -> None:
    with pytest.raises(ValueError):
        LiveVoiceConfig(noise_ratio=1.0)
