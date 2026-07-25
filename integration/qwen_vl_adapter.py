"""Production boundary between a local Qwen2.5-VL checkpoint and CARLA.

The model is deliberately kept outside the control loop.  This adapter only
turns one :class:`QwenInputContext` into a strictly validated high-level
decision.  ``AsyncQwenDecisionBridge`` owns timeout/stale handling and the
deterministic D safety layer remains the only producer of final controls.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from threading import Lock
import time
from typing import Any, Protocol

from .qwen_boundary import QwenInputContext, validate_qwen_response


class QwenVLGenerationBackend(Protocol):
    """Minimal generation interface used by the strict adapter and tests."""

    def generate(self, *, prompt: str, image_path: Path | None) -> str:
        ...


@dataclass(frozen=True, slots=True)
class QwenVLInferenceTrace:
    request_id: str
    started_ns: int
    completed_ns: int
    image_path: str | None
    raw_output: str
    decision: Mapping[str, Any]

    @property
    def latency_ms(self) -> float:
        return (self.completed_ns - self.started_ns) / 1e6


class StrictQwenVLAdapter:
    """Callable adapter suitable for ``AsyncQwenDecisionBridge``."""

    def __init__(
        self,
        backend: QwenVLGenerationBackend,
        *,
        image_root: str | Path | None = None,
    ) -> None:
        if not callable(getattr(backend, "generate", None)):
            raise TypeError("backend must provide generate(prompt=..., image_path=...)")
        self._backend = backend
        self._image_root = (
            Path(image_root).expanduser().resolve() if image_root is not None else None
        )
        self._trace_lock = Lock()
        self._last_trace: QwenVLInferenceTrace | None = None

    @classmethod
    def from_local_checkpoint(
        cls,
        model_path: str | Path,
        *,
        image_root: str | Path | None = None,
        max_new_tokens: int = 192,
        device_map: str = "auto",
        torch_dtype: str = "auto",
    ) -> "StrictQwenVLAdapter":
        """Load a real local Qwen2.5-VL checkpoint without network fallback."""
        backend = TransformersQwen25VLBackend(
            model_path,
            max_new_tokens=max_new_tokens,
            device_map=device_map,
            torch_dtype=torch_dtype,
        )
        return cls(backend, image_root=image_root)

    @property
    def last_trace(self) -> QwenVLInferenceTrace | None:
        with self._trace_lock:
            return self._last_trace

    def infer(self, context: QwenInputContext) -> dict[str, Any]:
        if not isinstance(context, QwenInputContext):
            raise TypeError("context must be QwenInputContext")
        image_path = self._resolve_image(context.rgb_ref)
        prompt = build_strict_qwen_prompt(context)
        started_ns = time.monotonic_ns()
        raw = self._backend.generate(prompt=prompt, image_path=image_path)
        completed_ns = time.monotonic_ns()
        if type(raw) is not str or not raw.strip():
            raise ValueError("Qwen backend returned an empty non-text response")
        decision = validate_qwen_response(raw)
        trace = QwenVLInferenceTrace(
            request_id=context.request_id,
            started_ns=started_ns,
            completed_ns=completed_ns,
            image_path=None if image_path is None else str(image_path),
            raw_output=raw,
            decision=dict(decision),
        )
        with self._trace_lock:
            self._last_trace = trace
        return decision

    def __call__(self, context: QwenInputContext) -> dict[str, Any]:
        return self.infer(context)

    def _resolve_image(self, rgb_ref: str | None) -> Path | None:
        if rgb_ref is None:
            return None
        candidate = Path(rgb_ref).expanduser()
        if self._image_root is not None:
            if candidate.is_absolute():
                raise ValueError("rgb_ref must be relative when image_root is configured")
            candidate = (self._image_root / candidate).resolve()
            try:
                candidate.relative_to(self._image_root)
            except ValueError as error:
                raise ValueError("rgb_ref escapes image_root") from error
        else:
            candidate = candidate.resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Qwen RGB input not found: {candidate}")
        return candidate


def build_strict_qwen_prompt(context: QwenInputContext) -> str:
    """Build a deterministic prompt whose output matches the frozen boundary."""
    input_payload = context.to_payload()
    return (
        "你是自动驾驶系统的高层多模态决策模块。"
        "你不能输出油门、刹车、方向盘或任何底层控制量。"
        "安全状态和交通规则的优先级高于用户命令。"
        "目标不存在、目标不唯一、输入置信度不足时必须要求确认或安全停车。"
        "\n\n只输出一个JSON对象，不要Markdown、解释或额外文字。"
        "\n必填字段：action, confidence, requires_confirmation。"
        "\n可选字段：target_speed_mps, reason_zh, decision_source, visual_valid。"
        "\naction只能是START、STOP、SLOW_DOWN、SET_SPEED、EMERGENCY_STOP。"
        "\nSET_SPEED必须包含target_speed_mps；其他无关字段禁止出现。"
        "\nconfidence范围0到1；requires_confirmation和visual_valid必须是JSON布尔值。"
        "\n禁止字段：throttle, brake, steer, steering_angle, wheel_angle。"
        "\n推荐设置decision_source为QWEN_VL。"
        "\n\n输入：\n"
        + json.dumps(input_payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )


class TransformersQwen25VLBackend:
    """Lazy optional-dependency backend for a local Qwen2.5-VL checkpoint."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        max_new_tokens: int = 192,
        device_map: str = "auto",
        torch_dtype: str = "auto",
    ) -> None:
        checkpoint = Path(model_path).expanduser().resolve()
        if not checkpoint.is_dir():
            raise FileNotFoundError(f"Qwen checkpoint directory not found: {checkpoint}")
        if type(max_new_tokens) is not int or max_new_tokens < 1:
            raise ValueError("max_new_tokens must be a positive integer")
        try:
            import torch
            from qwen_vl_utils import process_vision_info
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        except ImportError as error:
            raise RuntimeError(
                "Qwen runtime requires torch, transformers, pillow and qwen-vl-utils"
            ) from error

        self._torch = torch
        self._process_vision_info = process_vision_info
        self._max_new_tokens = max_new_tokens
        self._processor = AutoProcessor.from_pretrained(
            str(checkpoint),
            trust_remote_code=True,
            local_files_only=True,
        )
        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            str(checkpoint),
            torch_dtype=torch_dtype,
            device_map=device_map,
            trust_remote_code=True,
            local_files_only=True,
        ).eval()

    def generate(self, *, prompt: str, image_path: Path | None) -> str:
        content: list[dict[str, Any]] = []
        if image_path is not None:
            content.append({"type": "image", "image": str(image_path)})
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        chat_text = self._processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        image_inputs, video_inputs = self._process_vision_info(messages)
        processor_args: dict[str, Any] = {
            "text": [chat_text],
            "padding": True,
            "return_tensors": "pt",
        }
        if image_inputs:
            processor_args["images"] = image_inputs
        if video_inputs:
            processor_args["videos"] = video_inputs
        inputs = self._processor(**processor_args)
        device = next(self._model.parameters()).device
        inputs = inputs.to(device)
        with self._torch.inference_mode():
            generated = self._model.generate(
                **inputs,
                max_new_tokens=self._max_new_tokens,
                do_sample=False,
                use_cache=True,
            )
        trimmed = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(inputs.input_ids, generated)
        ]
        decoded = self._processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        if not decoded:
            raise RuntimeError("Qwen returned no decoded output")
        return decoded[0].strip()


__all__ = [
    "QwenVLGenerationBackend",
    "QwenVLInferenceTrace",
    "StrictQwenVLAdapter",
    "TransformersQwen25VLBackend",
    "build_strict_qwen_prompt",
]
