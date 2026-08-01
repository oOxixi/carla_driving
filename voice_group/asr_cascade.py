"""Conditional faster-whisper verification for safety-critical voice commands."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import Any

import numpy as np


RISKY_INTENTS = frozenset(
    {
        "SET_SPEED",
        "CHANGE_LANE",
        "PULL_OVER",
        "AVOID_OBSTACLE",
        "TURN",
        "SLOW_DOWN",
        "SPEED_UP",
    }
)
_NUMBER = re.compile(r"\d")
_TRUTHY = frozenset({"1", "true", "yes", "on"})
_DLL_DIRECTORY_HANDLES: list[Any] = []


def _add_nvidia_dll_directories() -> None:
    """Expose pip-installed NVIDIA runtime DLLs to CTranslate2 on Windows."""
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return
    site_packages = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    directories: list[str] = []
    for component in ("cublas", "cudnn"):
        directory = site_packages / component / "bin"
        if directory.is_dir():
            directories.append(str(directory))
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))
    if directories:
        os.environ["PATH"] = os.pathsep.join(
            [*directories, os.environ.get("PATH", "")]
        )


@dataclass(frozen=True)
class CascadeConfig:
    enabled: bool = True
    model_size: str = "small"
    device: str = "cuda"
    compute_type: str = "int8_float16"
    minimum_calibrated_confidence: float = 0.90
    calibration_path: Path = (
        Path(__file__).resolve().parent
        / "models"
        / "faster_whisper_small_confidence.json"
    )

    @classmethod
    def from_environment(cls) -> "CascadeConfig":
        enabled = os.getenv("VOICE_CASCADE_ENABLED", "1").strip().lower() in _TRUTHY
        return cls(
            enabled=enabled,
            model_size=os.getenv("VOICE_CASCADE_MODEL", "small"),
            device=os.getenv("VOICE_CASCADE_DEVICE", "cuda"),
            compute_type=os.getenv(
                "VOICE_CASCADE_COMPUTE_TYPE",
                "int8_float16",
            ),
            minimum_calibrated_confidence=float(
                os.getenv("VOICE_CASCADE_MIN_CONFIDENCE", "0.90")
            ),
            calibration_path=Path(
                os.getenv(
                    "VOICE_CASCADE_CALIBRATION",
                    str(cls.calibration_path),
                )
            ),
        )


class ConfidenceCalibrator:
    """Apply a stored Platt calibration without inventing a fallback score."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.metadata: dict[str, Any] | None = None
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("method") != "platt_logit":
                raise ValueError(f"unsupported confidence calibration: {path}")
            self.metadata = payload

    def transform(self, raw_probability: float | None) -> float | None:
        if raw_probability is None or self.metadata is None:
            return None
        probability = min(max(float(raw_probability), 1e-6), 1.0 - 1e-6)
        logit = math.log(probability / (1.0 - probability))
        value = (
            float(self.metadata["intercept"])
            + float(self.metadata["slope"]) * logit
        )
        return round(1.0 / (1.0 + math.exp(-max(min(value, 30.0), -30.0))), 6)


class FasterWhisperVerifier:
    """Lazy faster-whisper adapter; model loading occurs only on first trigger."""

    def __init__(self, config: CascadeConfig | None = None) -> None:
        self.config = config or CascadeConfig.from_environment()
        self._model = None
        self._warmed = False
        self._calibrator = ConfidenceCalibrator(self.config.calibration_path)

    def _get_model(self):
        if self._model is None:
            _add_nvidia_dll_directories()
            try:
                from faster_whisper import WhisperModel
            except ImportError as error:
                raise RuntimeError(
                    "faster-whisper is not installed; install voice_group requirements"
                ) from error
            self._model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
        return self._model

    def warmup(self) -> None:
        if self._warmed:
            return
        model = self._get_model()
        segments, _ = model.transcribe(
            np.zeros(16000, dtype=np.float32),
            language="zh",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            condition_on_previous_text=False,
            word_timestamps=False,
            vad_filter=False,
        )
        list(segments)
        # Warm the VAD path separately; otherwise the first real command pays
        # its one-time ONNX initialization cost.
        vad_segments, _ = model.transcribe(
            np.zeros(16000, dtype=np.float32),
            language="zh",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            condition_on_previous_text=False,
            word_timestamps=False,
            vad_filter=True,
        )
        list(vad_segments)
        self._warmed = True

    def transcribe(self, audio: Any) -> dict[str, Any]:
        started = time.monotonic_ns()
        segments, info = self._get_model().transcribe(
            audio,
            language="zh",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            condition_on_previous_text=False,
            word_timestamps=True,
            vad_filter=True,
        )
        realized = list(segments)
        text = "".join(segment.text for segment in realized).strip()
        from opencc import OpenCC

        text = OpenCC("t2s").convert(text)
        word_probabilities = [
            float(word.probability)
            for segment in realized
            for word in (segment.words or [])
            if word.probability is not None
        ]
        raw_probability = (
            sum(word_probabilities) / len(word_probabilities)
            if word_probabilities
            else None
        )
        segment_logprobs = [
            float(segment.avg_logprob)
            for segment in realized
            if segment.avg_logprob is not None
        ]
        return {
            "text": text,
            "raw_word_probability": (
                round(raw_probability, 6)
                if raw_probability is not None
                else None
            ),
            "calibrated_confidence": self._calibrator.transform(raw_probability),
            "calibration_available": self._calibrator.metadata is not None,
            "avg_logprob": (
                round(sum(segment_logprobs) / len(segment_logprobs), 6)
                if segment_logprobs
                else None
            ),
            "no_speech_probability": getattr(info, "no_speech_prob", None),
            "latency_ms": round((time.monotonic_ns() - started) / 1e6, 1),
            "model": self.config.model_size,
            "device": self.config.device,
            "compute_type": self.config.compute_type,
        }


def needs_verification(command: dict[str, Any]) -> bool:
    """Verify commands where a second model can change a control decision.

    UNKNOWN commands are already rejected by the primary parser, while STOP
    commands must take the fast safe path. Running Whisper for either class
    adds latency without improving the control decision.
    """
    intent = str(command.get("intent", "")).upper()
    return (
        intent in RISKY_INTENTS
        or bool(_NUMBER.search(str(command.get("source_text", ""))))
        or (command.get("status") != "valid" and intent != "UNKNOWN")
    )


def semantic_signature(command: dict[str, Any]) -> tuple[Any, ...]:
    """Return only fields whose disagreement can change vehicle behaviour.

    Free-form target wording is deliberately excluded. For obstacle avoidance,
    for example, ``障碍物`` versus the homophone ``帐碍物`` must not block an
    otherwise identical left/right manoeuvre.
    """
    intent = str(command.get("intent", "")).upper()
    parameters = command.get("parameters", {})
    if intent == "SET_SPEED":
        return intent, parameters.get("speed"), parameters.get("unit")
    if intent in {"CHANGE_LANE", "TURN", "AVOID_OBSTACLE"}:
        return intent, parameters.get("direction")
    if intent == "PULL_OVER":
        return intent, parameters.get("side")
    if intent in {"SLOW_DOWN", "SPEED_UP"}:
        return (
            intent,
            parameters.get("speed"),
            parameters.get("unit"),
            parameters.get("action"),
        )
    return (intent,)


def apply_verification(
    primary: dict[str, Any],
    verification: dict[str, Any],
    secondary: dict[str, Any],
    *,
    minimum_confidence: float,
) -> dict[str, Any]:
    """Attach audit data and gate execution when the two semantics disagree."""
    output = dict(primary)
    audit = {
        **verification,
        "intent": secondary.get("intent"),
        "parameters": secondary.get("parameters", {}),
        "status": secondary.get("status"),
        "semantic_agreement": (
            semantic_signature(primary) == semantic_signature(secondary)
        ),
    }
    output["asr_verification"] = audit
    calibrated = verification.get("calibrated_confidence")
    if calibrated is not None:
        # This score belongs to the verifier, not SenseVoice. Keep the two
        # provenance domains separate so a weak verifier score cannot turn a
        # correct primary command into a low-confidence command.
        output["verification_confidence"] = calibrated

    warning: dict[str, str] | None = None
    safe_stop = str(primary.get("intent", "")).upper() in {
        "STOP",
        "EMERGENCY_STOP",
    }
    confident_disagreement = (
        not audit["semantic_agreement"]
        and calibrated is not None
        and calibrated >= minimum_confidence
        and not safe_stop
    )
    if confident_disagreement:
        warning = {
            "code": "ASR_MODEL_DISAGREEMENT",
            "message": "SenseVoice 与 faster-whisper 的车控语义不一致，必须确认",
        }
    elif not audit["semantic_agreement"]:
        warning = {
            "code": "ASR_UNCERTAIN_DISAGREEMENT",
            "message": "复核语义不一致但分数不足，不覆盖高准确率主模型",
        }
    elif calibrated is None:
        warning = {
            "code": "UNCALIBRATED_VERIFIER",
            "message": "复核模型尚无有效校准文件；语义一致但保留未校准标记",
        }

    if warning is not None:
        output["warnings"] = [*output.get("warnings", []), warning]
        if warning["code"] == "ASR_MODEL_DISAGREEMENT":
            output["confirm_required"] = True
            output["ambiguity_type"] = warning["code"]
    return output


def mark_verifier_unavailable(
    command: dict[str, Any],
    error: Exception,
) -> dict[str, Any]:
    """Fail into the confirmation gate rather than silently bypass verification."""
    output = dict(command)
    output["confirm_required"] = True
    output["ambiguity_type"] = "ASR_VERIFIER_UNAVAILABLE"
    output["warnings"] = [
        *output.get("warnings", []),
        {
            "code": "ASR_VERIFIER_UNAVAILABLE",
            "message": f"ASR 复核不可用，必须确认: {type(error).__name__}",
        },
    ]
    output["asr_verification"] = {
        "available": False,
        "error": f"{type(error).__name__}: {error}",
    }
    return output
