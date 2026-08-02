"""Continuous PulseAudio microphone input for the CARLA voice runner.

Audio capture and ASR run on worker threads so CARLA's synchronous control
loop never waits for a microphone read or model inference.  The main thread
polls completed command envelopes and remains the only owner of vehicle state.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import queue
import subprocess
import threading
import time
from typing import Any

import numpy as np


@dataclass(frozen=True)
class LiveVoiceConfig:
    source: str = "@DEFAULT_SOURCE@"
    sample_rate: int = 16_000
    frame_ms: int = 20
    pre_roll_ms: int = 300
    end_silence_ms: int = 700
    max_utterance_s: float = 7.0
    min_voice_ms: int = 160
    min_rms: float = 0.003
    noise_ratio: float = 3.0
    trigger_frames: int = 3

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("microphone source must be non-empty")
        if self.sample_rate <= 0 or self.frame_ms <= 0:
            raise ValueError("sample rate and frame size must be positive")
        if 1000 % self.frame_ms:
            raise ValueError("frame_ms must divide one second")
        if self.pre_roll_ms < 0 or self.end_silence_ms <= 0:
            raise ValueError("pre-roll must be non-negative and end silence positive")
        if self.max_utterance_s <= 0.0 or self.min_voice_ms <= 0:
            raise ValueError("utterance durations must be positive")
        if self.min_rms <= 0.0 or self.noise_ratio <= 1.0:
            raise ValueError("VAD thresholds must be positive")
        if self.trigger_frames < 1:
            raise ValueError("trigger_frames must be positive")

    @property
    def samples_per_frame(self) -> int:
        return self.sample_rate * self.frame_ms // 1000

    @property
    def bytes_per_frame(self) -> int:
        return self.samples_per_frame * 2


class EnergyVadSegmenter:
    """Adaptive energy VAD for short push-free driving commands."""

    def __init__(self, config: LiveVoiceConfig | None = None) -> None:
        self.config = config or LiveVoiceConfig()
        frames_per_second = 1000 // self.config.frame_ms
        self._pre_roll: deque[bytes] = deque(
            maxlen=max(1, self.config.pre_roll_ms // self.config.frame_ms)
        )
        self._noise_rms: deque[float] = deque(maxlen=frames_per_second * 3)
        self._end_silence_frames = max(
            1, self.config.end_silence_ms // self.config.frame_ms
        )
        self._max_frames = max(
            1, int(self.config.max_utterance_s * frames_per_second)
        )
        self._min_voice_frames = max(
            1, self.config.min_voice_ms // self.config.frame_ms
        )
        self._active = False
        self._active_threshold = self.config.min_rms
        self._frames: list[bytes] = []
        self._trigger_run = 0
        self._silence_run = 0
        self._voiced_frames = 0

    @staticmethod
    def _rms(frame: bytes) -> float:
        samples = np.frombuffer(frame, dtype="<i2").astype(np.float32)
        if samples.size == 0:
            return 0.0
        samples /= 32768.0
        return float(np.sqrt(np.mean(samples * samples)))

    def _threshold(self) -> float:
        if not self._noise_rms:
            return self.config.min_rms
        return max(
            self.config.min_rms,
            float(np.median(np.asarray(self._noise_rms)))
            * self.config.noise_ratio,
        )

    def feed(self, frame: bytes) -> bytes | None:
        if len(frame) != self.config.bytes_per_frame:
            raise ValueError(
                f"expected {self.config.bytes_per_frame} PCM bytes, got {len(frame)}"
            )
        rms = self._rms(frame)
        if not self._active:
            threshold = self._threshold()
            self._pre_roll.append(frame)
            if rms >= threshold:
                self._trigger_run += 1
            else:
                self._trigger_run = 0
                self._noise_rms.append(rms)
            if self._trigger_run < self.config.trigger_frames:
                return None
            self._active = True
            self._active_threshold = threshold
            self._frames = list(self._pre_roll)
            self._voiced_frames = self.config.trigger_frames
            self._silence_run = 0
            return None

        self._frames.append(frame)
        if rms >= self._active_threshold:
            self._voiced_frames += 1
            self._silence_run = 0
        else:
            self._silence_run += 1
        ended = self._silence_run >= self._end_silence_frames
        reached_limit = len(self._frames) >= self._max_frames
        if not (ended or reached_limit):
            return None
        utterance = b"".join(self._frames) if self._voiced_frames >= self._min_voice_frames else None
        self._reset_after_utterance()
        return utterance

    def flush(self) -> bytes | None:
        if not self._active or self._voiced_frames < self._min_voice_frames:
            self._reset_after_utterance()
            return None
        utterance = b"".join(self._frames)
        self._reset_after_utterance()
        return utterance

    def _reset_after_utterance(self) -> None:
        self._active = False
        self._frames = []
        self._trigger_run = 0
        self._silence_run = 0
        self._voiced_frames = 0
        self._pre_roll.clear()


@dataclass(frozen=True)
class LiveVoiceResult:
    command: dict[str, Any] | None
    duration_s: float
    error: str | None = None


class LiveVoiceSource:
    """Capture, segment, and recognize microphone commands asynchronously."""

    def __init__(self, config: LiveVoiceConfig | None = None) -> None:
        self.config = config or LiveVoiceConfig()
        self._segments: queue.Queue[tuple[bytes, int] | None] = queue.Queue(maxsize=4)
        self._results: queue.Queue[LiveVoiceResult] = queue.Queue()
        self._stop = threading.Event()
        self._capture_thread: threading.Thread | None = None
        self._asr_thread: threading.Thread | None = None
        self._process: subprocess.Popen[bytes] | None = None

    def preload(self) -> dict[str, object]:
        from voice_group.pipeline import preload_voice_models

        return preload_voice_models()

    def start(self) -> None:
        if self._capture_thread is not None:
            raise RuntimeError("live microphone is already running")
        command = [
            "parec",
            "--record",
            f"--device={self.config.source}",
            f"--rate={self.config.sample_rate}",
            "--format=s16le",
            "--channels=1",
            "--raw",
            "--client-name=carla-live-voice",
        ]
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self._capture_thread = threading.Thread(
            target=self._capture_loop, name="live-voice-capture", daemon=True
        )
        self._asr_thread = threading.Thread(
            target=self._recognition_loop, name="live-voice-asr", daemon=True
        )
        self._capture_thread.start()
        self._asr_thread.start()

    def poll(self) -> tuple[LiveVoiceResult, ...]:
        results: list[LiveVoiceResult] = []
        while True:
            try:
                results.append(self._results.get_nowait())
            except queue.Empty:
                return tuple(results)

    def stop(self) -> None:
        self._stop.set()
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        try:
            self._segments.put_nowait(None)
        except queue.Full:
            pass
        for thread in (self._capture_thread, self._asr_thread):
            if thread is not None:
                thread.join(timeout=3.0)

    def _capture_loop(self) -> None:
        process = self._process
        assert process is not None and process.stdout is not None
        segmenter = EnergyVadSegmenter(self.config)
        frame_bytes = self.config.bytes_per_frame
        pending = bytearray()
        try:
            while not self._stop.is_set():
                chunk = process.stdout.read(frame_bytes - len(pending))
                if not chunk:
                    if process.poll() is not None:
                        break
                    continue
                pending.extend(chunk)
                if len(pending) < frame_bytes:
                    continue
                frame = bytes(pending)
                pending.clear()
                utterance = segmenter.feed(frame)
                if utterance is not None:
                    duration_s = len(utterance) / 2 / self.config.sample_rate
                    started_ns = time.monotonic_ns() - int(duration_s * 1e9)
                    try:
                        self._segments.put((utterance, started_ns), timeout=0.1)
                    except queue.Full:
                        self._results.put(LiveVoiceResult(
                            None, duration_s, "recognition queue full; utterance dropped"
                        ))
        except Exception as error:
            self._results.put(LiveVoiceResult(
                None, 0.0, f"microphone capture failed: {type(error).__name__}: {error}"
            ))
        finally:
            utterance = segmenter.flush()
            if utterance is not None and not self._stop.is_set():
                started_ns = time.monotonic_ns() - int(
                    len(utterance) / 2 / self.config.sample_rate * 1e9
                )
                try:
                    self._segments.put_nowait((utterance, started_ns))
                except queue.Full:
                    pass

    def _recognition_loop(self) -> None:
        from voice_group.pipeline import audio_to_command

        while not self._stop.is_set():
            try:
                item = self._segments.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                return
            pcm, started_ns = item
            duration_s = len(pcm) / 2 / self.config.sample_rate
            try:
                audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
                command = audio_to_command(audio, t_audio_start_ns=started_ns)
                self._results.put(LiveVoiceResult(dict(command), duration_s))
            except Exception as error:
                self._results.put(LiveVoiceResult(
                    None,
                    duration_s,
                    f"voice recognition failed: {type(error).__name__}: {error}",
                ))


__all__ = [
    "EnergyVadSegmenter",
    "LiveVoiceConfig",
    "LiveVoiceResult",
    "LiveVoiceSource",
]
