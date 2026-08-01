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
import re
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
    visual_preprocess: Mapping[str, Any] | None = None
    target_grounding: Mapping[str, Any] | None = None

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
        max_new_tokens: int = 64,
        device_map: str = "auto",
        torch_dtype: str = "auto",
        min_pixels: int = 64 * 28 * 28,
        max_pixels: int = 256 * 28 * 28,
        crop_top_ratio: float = 0.04,
        crop_bottom_ratio: float = 0.08,
    ) -> "StrictQwenVLAdapter":
        """Load a real local Qwen2.5-VL checkpoint without network fallback."""
        backend = TransformersQwen25VLBackend(
            model_path,
            max_new_tokens=max_new_tokens,
            device_map=device_map,
            torch_dtype=torch_dtype,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
            crop_top_ratio=crop_top_ratio,
            crop_bottom_ratio=crop_bottom_ratio,
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
        _validate_target_reference(decision, context)
        decision, target_grounding = _ground_explicit_target(
            decision, context
        )
        trace = QwenVLInferenceTrace(
            request_id=context.request_id,
            started_ns=started_ns,
            completed_ns=completed_ns,
            image_path=None if image_path is None else str(image_path),
            raw_output=raw,
            decision=dict(decision),
            visual_preprocess=getattr(
                self._backend, "last_visual_metadata", None,
            ),
            target_grounding=target_grounding,
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
        "\n目标关联可选字段：target_track_id。它只能精确复制"
        "perception.detected_objects中真实存在的track_id，禁止编造。"
        "\n如果用户命令包含“正前方、左侧、右侧、相邻车道、较近、较远、跟随”等"
        "目标描述，并且detected_objects中存在唯一匹配项，target_track_id不是可选项，"
        "必须输出；不得用target_speed_mps、reason_zh或decision_source代替它。"
        "\n示例：命令要求跟随右侧相邻车道车辆，匹配对象track_id为vehicle_right_01，"
        "则输出必须包含\"target_track_id\":\"vehicle_right_01\"。"
        "\n该规则同样适用于行人、骑行者、被遮挡目标、较近/较远目标以及“避让”动作。"
        "只要命令描述与detected_objects中的一个对象唯一匹配，就必须先复制其track_id，"
        "再决定action；无论action是SLOW_DOWN还是STOP都不得漏掉。"
        "\n唯一目标响应模板："
        "{\"action\":\"SLOW_DOWN\",\"confidence\":1.0,"
        "\"requires_confirmation\":false,\"target_track_id\":\"从输入精确复制的ID\"}。"
        "\naction只能是START、STOP、SLOW_DOWN、SET_SPEED、EMERGENCY_STOP。"
        "\nSET_SPEED必须包含target_speed_mps；其他无关字段禁止出现。"
        "\nconfidence范围0到1；requires_confirmation和visual_valid必须是JSON布尔值。"
        "\n禁止字段：throttle, brake, steer, steering_angle, wheel_angle。"
        "\n推荐设置decision_source为QWEN_VL。"
        "\n\n确定性决策规则："
        "\n1. 公里每小时必须除以3.6转换为米每秒，例如18km/h=5m/s，"
        "20km/h=5.56m/s，30km/h=8.33m/s。"
        "\n2. 明确的停车、紧急停车及因红灯/TTC危险产生的安全停车不需要确认，"
        "requires_confirmation=false。"
        "\n3. 只有目标不明确、多个目标、视觉无效或输入置信度不足时才要求确认。"
        "\n4. 红灯或safety_state推荐STOP时输出STOP；TTC不大于2秒或推荐"
        "EMERGENCY_STOP时输出EMERGENCY_STOP。安全规则覆盖用户继续行驶指令。"
        "\n5. STOP、START、EMERGENCY_STOP绝不能包含target_speed_mps；"
        "SET_SPEED必须包含该字段。"
        "\n6. 用户指令明确指向某个检测目标时必须输出对应target_track_id；"
        "目标不唯一时不得猜测，应要求确认且省略target_track_id。"
        "\n\n输入：\n"
        + json.dumps(input_payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )


def _validate_target_reference(
    decision: Mapping[str, Any],
    context: QwenInputContext,
) -> None:
    target = decision.get("target_track_id")
    if target is None:
        return
    objects = context.perception.get("detected_objects", [])
    if not isinstance(objects, list):
        raise ValueError("perception.detected_objects must be a list")
    available = {
        str(item.get("track_id"))
        for item in objects
        if isinstance(item, Mapping) and item.get("track_id") is not None
    }
    if target not in available:
        raise ValueError(
            f"Qwen target_track_id is not present in perception: {target!r}"
        )


def _explicit_target_candidates(
    context: QwenInputContext,
) -> list[Mapping[str, Any]] | None:
    """Resolve only high-confidence Chinese target descriptions."""
    command = context.voice_command
    expected_class: str | None = None
    if "行人" in command:
        expected_class = "pedestrian"
    elif "车辆" in command or "前车" in command:
        expected_class = "vehicle"
    if expected_class is None:
        return None

    relation_check: Any = None
    distance_match = re.search(
        r"距离约(?P<distance>\d+(?:\.\d+)?)米",
        command,
    )
    if distance_match is not None:
        requested_distance = float(distance_match.group("distance"))
        relation_check = lambda relation, item=None: True
    elif "左侧相邻车道" in command:
        relation_check = lambda relation: "left_adjacent" in relation
    elif "右侧相邻车道" in command:
        relation_check = lambda relation: "right_adjacent" in relation
    elif "被前车部分遮挡" in command or "部分遮挡" in command:
        relation_check = lambda relation: "occluded" in relation
    elif "较远" in command:
        relation_check = lambda relation: relation.startswith("far_ahead")
    elif "正前方" in command:
        relation_check = lambda relation: relation == "center_ahead"
    if relation_check is None:
        return None

    objects = context.perception.get("detected_objects", [])
    if not isinstance(objects, list):
        raise ValueError("perception.detected_objects must be a list")
    candidates = [
        item
        for item in objects
        if (
            isinstance(item, Mapping)
            and str(item.get("class", "")).lower() == expected_class
            and not (
                type(item.get("confidence")) in (int, float)
                and float(item["confidence"]) < 0.5
            )
        )
    ]
    if distance_match is not None:
        return [
            item
            for item in candidates
            if (
                type(item.get("distance_m")) in (int, float)
                and abs(float(item["distance_m"]) - requested_distance) <= 2.0
            )
        ]
    return [
        item for item in candidates
        if relation_check(str(item.get("relation", "")).lower())
    ]


def _ground_explicit_target(
    decision: Mapping[str, Any],
    context: QwenInputContext,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Fuse Qwen action with a unique deterministic semantic target."""
    candidates = _explicit_target_candidates(context)
    if candidates is None:
        return dict(decision), None
    target = decision.get("target_track_id")
    candidate_ids = {
        str(item["track_id"])
        for item in candidates
        if item.get("track_id") is not None
    }
    if not candidate_ids:
        if (
            target is not None
            or decision["action"] not in {"STOP", "EMERGENCY_STOP"}
            or not decision["requires_confirmation"]
        ):
            raise ValueError(
                "explicit voice target is absent; decision must fail closed "
                "with STOP and requires_confirmation=true"
            )
        return dict(decision), {
            "status": "ABSENT_FAIL_CLOSED",
            "candidate_track_ids": [],
            "qwen_target_track_id": target,
        }
    if len(candidate_ids) == 1:
        expected = next(iter(candidate_ids))
        grounded = dict(decision)
        grounded["target_track_id"] = expected
        return grounded, {
            "status": (
                "MATCHED" if target == expected else "CORRECTED_UNIQUE"
            ),
            "candidate_track_ids": [expected],
            "qwen_target_track_id": target,
            "grounded_target_track_id": expected,
        }
    if target is not None or not decision["requires_confirmation"]:
        raise ValueError(
            "explicit voice target is ambiguous; target must be omitted and "
            "requires_confirmation=true"
        )
    return dict(decision), {
        "status": "AMBIGUOUS_CONFIRMATION",
        "candidate_track_ids": sorted(candidate_ids),
        "qwen_target_track_id": target,
    }


class TransformersQwen25VLBackend:
    """Lazy optional-dependency backend for a local Qwen2.5-VL checkpoint."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        max_new_tokens: int = 64,
        device_map: str = "auto",
        torch_dtype: str = "auto",
        min_pixels: int = 64 * 28 * 28,
        max_pixels: int = 256 * 28 * 28,
        crop_top_ratio: float = 0.04,
        crop_bottom_ratio: float = 0.08,
    ) -> None:
        checkpoint = Path(model_path).expanduser().resolve()
        if not checkpoint.is_dir():
            raise FileNotFoundError(f"Qwen checkpoint directory not found: {checkpoint}")
        if type(max_new_tokens) is not int or max_new_tokens < 1:
            raise ValueError("max_new_tokens must be a positive integer")
        if type(min_pixels) is not int or min_pixels < 28 * 28:
            raise ValueError("min_pixels must be an integer of at least 784")
        if type(max_pixels) is not int or max_pixels < min_pixels:
            raise ValueError("max_pixels must be an integer >= min_pixels")
        for name, value in (
            ("crop_top_ratio", crop_top_ratio),
            ("crop_bottom_ratio", crop_bottom_ratio),
        ):
            if (
                type(value) not in (int, float)
                or isinstance(value, bool)
                or not 0.0 <= float(value) < 0.5
            ):
                raise ValueError(f"{name} must be in [0, 0.5)")
        if float(crop_top_ratio) + float(crop_bottom_ratio) >= 0.5:
            raise ValueError("combined vertical crop must retain at least half the image")
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
        self._crop_top_ratio = float(crop_top_ratio)
        self._crop_bottom_ratio = float(crop_bottom_ratio)
        self.last_visual_metadata: dict[str, Any] | None = None
        self._processor = AutoProcessor.from_pretrained(
            str(checkpoint),
            trust_remote_code=True,
            local_files_only=True,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
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
        self.last_visual_metadata = None
        if image_inputs:
            cropped_images = []
            metadata = []
            for image in image_inputs:
                cropped, item_metadata = crop_road_roi(
                    image,
                    top_ratio=self._crop_top_ratio,
                    bottom_ratio=self._crop_bottom_ratio,
                )
                cropped_images.append(cropped)
                metadata.append(item_metadata)
            image_inputs = cropped_images
            self.last_visual_metadata = {
                "strategy": "vertical_road_roi",
                "top_ratio": self._crop_top_ratio,
                "bottom_ratio": self._crop_bottom_ratio,
                "images": metadata,
                "max_new_tokens": self._max_new_tokens,
            }
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


def crop_road_roi(
    image: Any,
    *,
    top_ratio: float = 0.04,
    bottom_ratio: float = 0.08,
) -> tuple[Any, dict[str, Any]]:
    """Remove low-value sky/hood bands without changing horizontal geometry."""
    for name, value in (
        ("top_ratio", top_ratio),
        ("bottom_ratio", bottom_ratio),
    ):
        if (
            type(value) not in (int, float)
            or isinstance(value, bool)
            or not 0.0 <= float(value) < 0.5
        ):
            raise ValueError(f"{name} must be in [0, 0.5)")
    if float(top_ratio) + float(bottom_ratio) >= 0.5:
        raise ValueError("combined vertical crop must retain at least half the image")
    if not hasattr(image, "size") or not callable(getattr(image, "crop", None)):
        raise TypeError("image must provide Pillow-compatible size and crop")
    width, height = image.size
    if type(width) is not int or type(height) is not int or width < 1 or height < 2:
        raise ValueError("image dimensions must be positive integers")
    top = int(round(height * float(top_ratio)))
    bottom = height - int(round(height * float(bottom_ratio)))
    if bottom <= top:
        raise ValueError("crop ratios produced an empty image")
    cropped = image.crop((0, top, width, bottom))
    return cropped, {
        "original_size": [width, height],
        "crop_box_xyxy": [0, top, width, bottom],
        "cropped_size": [cropped.size[0], cropped.size[1]],
        "retained_pixel_ratio": round(
            (cropped.size[0] * cropped.size[1]) / (width * height),
            6,
        ),
    }


__all__ = [
    "QwenVLGenerationBackend",
    "QwenVLInferenceTrace",
    "StrictQwenVLAdapter",
    "TransformersQwen25VLBackend",
    "build_strict_qwen_prompt",
    "crop_road_roi",
]
