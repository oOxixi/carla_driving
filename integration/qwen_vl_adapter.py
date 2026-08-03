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
import math
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


_ACTION_BY_CODE = {
    "A": "START",
    "B": "STOP",
    "C": "SLOW_DOWN",
    "D": "SET_SPEED",
    "E": "EMERGENCY_STOP",
}


@dataclass(frozen=True, slots=True)
class QwenVLActionChoice:
    """One constrained model choice before deterministic Schema assembly."""

    code: str
    action: str
    confidence: float

    @classmethod
    def from_code(cls, code: str, confidence: float) -> "QwenVLActionChoice":
        normalized = str(code).strip().upper()
        try:
            action = _ACTION_BY_CODE[normalized]
        except KeyError as error:
            raise ValueError(f"unsupported Qwen action code: {normalized!r}") from error
        return cls(code=normalized, action=action, confidence=confidence)

    def __post_init__(self) -> None:
        code = str(self.code).strip().upper()
        action = str(self.action).strip().upper()
        if code not in _ACTION_BY_CODE:
            raise ValueError(f"unsupported Qwen action code: {code!r}")
        if action != _ACTION_BY_CODE[code]:
            raise ValueError(
                f"Qwen action code {code} must map to {_ACTION_BY_CODE[code]}"
            )
        if (
            type(self.confidence) not in (int, float)
            or isinstance(self.confidence, bool)
            or not math.isfinite(float(self.confidence))
            or not 0.0 <= float(self.confidence) <= 1.0
        ):
            raise ValueError("Qwen action confidence must be finite and in [0, 1]")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True, slots=True)
class QwenVLInferenceTrace:
    request_id: str
    started_ns: int
    completed_ns: int
    image_path: str | None
    raw_output: str
    decision: Mapping[str, Any] | None
    visual_preprocess: Mapping[str, Any] | None = None
    target_grounding: Mapping[str, Any] | None = None
    error: str | None = None

    @property
    def latency_ms(self) -> float:
        return (self.completed_ns - self.started_ns) / 1e6

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "started_ns": self.started_ns,
            "completed_ns": self.completed_ns,
            "latency_ms": self.latency_ms,
            "image_path": self.image_path,
            "raw_output": self.raw_output,
            "decision": None if self.decision is None else dict(self.decision),
            "visual_preprocess": (
                None
                if self.visual_preprocess is None
                else dict(self.visual_preprocess)
            ),
            "target_grounding": (
                None
                if self.target_grounding is None
                else dict(self.target_grounding)
            ),
            "error": self.error,
        }


class StrictQwenVLAdapter:
    """Callable adapter suitable for ``AsyncQwenDecisionBridge``."""

    def __init__(
        self,
        backend: QwenVLGenerationBackend,
        *,
        image_root: str | Path | None = None,
    ) -> None:
        if not callable(getattr(backend, "generate", None)) and not callable(
            getattr(backend, "generate_action", None)
        ):
            raise TypeError(
                "backend must provide generate(...) or generate_action(...)"
            )
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
        max_new_tokens: int = 48,
        device_map: str = "auto",
        torch_dtype: str = "auto",
        awq_backend: str = "auto",
        min_pixels: int = 64 * 28 * 28,
        max_pixels: int = 64 * 28 * 28,
        crop_top_ratio: float = 0.04,
        crop_bottom_ratio: float = 0.08,
    ) -> "StrictQwenVLAdapter":
        """Load a real local Qwen2.5-VL checkpoint without network fallback."""
        backend = TransformersQwen25VLBackend(
            model_path,
            max_new_tokens=max_new_tokens,
            device_map=device_map,
            torch_dtype=torch_dtype,
            awq_backend=awq_backend,
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
        generate_action = getattr(self._backend, "generate_action", None)
        prompt = (
            build_action_choice_prompt(context)
            if callable(generate_action)
            else build_strict_qwen_prompt(context)
        )
        started_ns = time.monotonic_ns()
        raw = ""
        decision: dict[str, Any] | None = None
        target_grounding: Mapping[str, Any] | None = None
        trace_error: str | None = None
        try:
            if callable(generate_action):
                choice = generate_action(
                    prompt=prompt,
                    image_path=image_path,
                    context=context,
                )
                if not isinstance(choice, QwenVLActionChoice):
                    raise TypeError(
                        "Qwen action backend must return QwenVLActionChoice"
                    )
                raw = choice.code
                decision = validate_qwen_response(
                    assemble_action_choice(choice, context)
                )
            else:
                raw = self._backend.generate(prompt=prompt, image_path=image_path)
                if type(raw) is not str or not raw.strip():
                    raise ValueError("Qwen backend returned an empty non-text response")
                decision = validate_qwen_response(raw)
            _validate_target_reference(decision, context)
            decision, target_grounding = _ground_explicit_target(
                decision, context
            )
            return decision
        except Exception as error:
            trace_error = f"{type(error).__name__}: {error}"
            raise
        finally:
            trace = QwenVLInferenceTrace(
                request_id=context.request_id,
                started_ns=started_ns,
                completed_ns=time.monotonic_ns(),
                image_path=None if image_path is None else str(image_path),
                raw_output=raw if type(raw) is str else repr(raw),
                decision=None if decision is None else dict(decision),
                visual_preprocess=getattr(
                    self._backend, "last_visual_metadata", None,
                ),
                target_grounding=target_grounding,
                error=trace_error,
            )
            with self._trace_lock:
                self._last_trace = trace

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
        "你是自动驾驶高层决策模块；安全规则覆盖用户命令。"
        "只输出一个JSON对象；禁止```、Markdown、解释或底层控制。"
        "严格仿此单行格式: "
        '{"action":"SLOW_DOWN","confidence":0.9,"requires_confirmation":false}。'
        "非规则必需时省略所有可选字段。"
        "\n必填: action,confidence,requires_confirmation；可选: "
        "target_speed_mps,target_track_id,reason_zh,decision_source,visual_valid。"
        "\naction只能是START、STOP、SLOW_DOWN、SET_SPEED、EMERGENCY_STOP；"
        "confidence为0到1，布尔值必须是JSON布尔值。"
        "\n禁止字段: throttle, brake, steer, steering_angle, wheel_angle。"
        "\n规则: 速度从km/h除以3.6，如20km/h=5.56m/s。"
        "明确的停车、紧急停车、红灯或安全停车无需确认。"
        "TTC不大于2秒或建议EMERGENCY_STOP时紧急停车；安全规则覆盖用户继续行驶。"
        "STOP、START、EMERGENCY_STOP绝不能包含target_speed_mps；"
        "SET_SPEED必须包含target_speed_mps。"
        "target_track_id只能复制detected_objects中真实ID，禁止编造。"
        "明确唯一目标时必须输出；行人、骑行者、被遮挡目标同样适用，"
        "无论action是SLOW_DOWN还是STOP都不得漏掉。"
        "目标缺失、不唯一、视觉无效或置信度不足时省略ID并要求确认或安全停车。"
        "\n输入:\n"
        + json.dumps(input_payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )


def build_action_choice_prompt(context: QwenInputContext) -> str:
    """Build the compact five-way classification prompt used by Qwen3-VL."""
    payload = {
        "voice": context.voice_command,
        "vehicle": dict(context.scene_state),
        "perception": dict(context.perception),
        "safety": dict(context.safety_state),
    }
    return (
        "融合图像与四模态状态，只输出一个代码，禁止解释或底层控制。"
        "A=START；B=STOP；C=SLOW_DOWN；D=SET_SPEED；E=EMERGENCY_STOP。"
        "优先级:安全规则>明确语音动作>普通视觉线索；普通车辆本身不是停车风险。"
        "红灯或安全模块要求停车选B；TTC不大于2秒或紧急危险选E；"
        "明确跟随或避让且无停车风险必须选C；明确设置速度选D；"
        "只有确认安全的启动或继续才选A。"
        "输入:"
        + json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )


def assemble_action_choice(
    choice: QwenVLActionChoice,
    context: QwenInputContext,
    *,
    confidence_threshold: float = 0.60,
) -> dict[str, Any]:
    """Turn one model class into the existing strict high-level decision."""
    if not isinstance(choice, QwenVLActionChoice):
        raise TypeError("choice must be QwenVLActionChoice")
    if not isinstance(context, QwenInputContext):
        raise TypeError("context must be QwenInputContext")
    if not 0.0 <= float(confidence_threshold) <= 1.0:
        raise ValueError("confidence_threshold must be in [0, 1]")

    visual_valid = context.perception.get("visual_valid")
    override = _deterministic_safety_action(context)
    if override is not None:
        action, confidence = override
        decision = _base_choice_decision(
            action,
            confidence=confidence,
            requires_confirmation=False,
            source="SAFETY_RULE",
            visual_valid=visual_valid,
        )
        return decision

    if choice.confidence < confidence_threshold:
        return _base_choice_decision(
            "STOP",
            confidence=choice.confidence,
            requires_confirmation=True,
            source="QWEN35_LOW_CONFIDENCE",
            visual_valid=visual_valid,
        )

    if visual_valid is False:
        return _base_choice_decision(
            "STOP",
            confidence=choice.confidence,
            requires_confirmation=True,
            source="QWEN35_VISUAL_INVALID",
            visual_valid=False,
        )

    candidates = _explicit_target_candidates(context)
    if candidates is not None:
        candidate_ids = {
            str(item["track_id"])
            for item in candidates
            if item.get("track_id") is not None
        }
        if len(candidate_ids) != 1:
            return _base_choice_decision(
                "STOP",
                confidence=choice.confidence,
                requires_confirmation=True,
                source="TARGET_GROUNDING",
                visual_valid=visual_valid,
            )

    decision = _base_choice_decision(
        choice.action,
        confidence=choice.confidence,
        requires_confirmation=False,
        source="QWEN35_CHOICE",
        visual_valid=visual_valid,
    )
    if choice.action == "SET_SPEED":
        target_speed_mps = _voice_target_speed_mps(context.voice_command)
        if target_speed_mps is None or target_speed_mps > 50.0:
            return _base_choice_decision(
                "STOP",
                confidence=choice.confidence,
                requires_confirmation=True,
                source="QWEN35_SPEED_UNRESOLVED",
                visual_valid=visual_valid,
            )
        decision["target_speed_mps"] = target_speed_mps
    return decision


def _base_choice_decision(
    action: str,
    *,
    confidence: float,
    requires_confirmation: bool,
    source: str,
    visual_valid: object,
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "action": action,
        "confidence": float(confidence),
        "requires_confirmation": requires_confirmation,
        "decision_source": source,
    }
    if type(visual_valid) is bool:
        decision["visual_valid"] = visual_valid
    return decision


def _deterministic_safety_action(
    context: QwenInputContext,
) -> tuple[str, float] | None:
    safety = context.safety_state
    perception = context.perception
    recommended = str(safety.get("recommended_action") or "").strip().upper()
    ttc = safety.get("minimum_ttc_s", safety.get("ttc_s"))
    collision = safety.get("collision") is True or perception.get("collision") is True
    if collision or recommended in {"EMERGENCY_STOP", "EMERGENCY_BRAKE"} or (
        type(ttc) in (int, float)
        and not isinstance(ttc, bool)
        and math.isfinite(float(ttc))
        and float(ttc) <= 2.0
    ):
        return "EMERGENCY_STOP", 0.99

    traffic_light = str(
        perception.get("traffic_light", context.scene_state.get("traffic_light", ""))
    ).strip().upper()
    if (
        traffic_light == "RED"
        or safety.get("red_light_violation") is True
        or recommended in {"STOP", "FULL_BRAKE"}
    ):
        return "STOP", 0.99
    if recommended == "SLOW_DOWN":
        return "SLOW_DOWN", 0.95
    return None


_VOICE_SPEED_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>公里每小时|千米每小时|km/?h|kph|米每秒|m/s|mps)",
    flags=re.IGNORECASE,
)
_CHINESE_SPEED_PREFIX_RE = re.compile(
    r"每秒(?P<value>[零〇一二两三四五六七八九十]+)米"
)
_CHINESE_SPEED_SUFFIX_RE = re.compile(
    r"(?P<value>[零〇一二两三四五六七八九十]+)"
    r"(?P<unit>公里每小时|千米每小时|米每秒)"
)


def _voice_target_speed_mps(command: str) -> float | None:
    normalized = re.sub(r"\s+", "", command)
    match = _VOICE_SPEED_RE.search(normalized)
    if match is not None:
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        return value / 3.6 if unit in {
            "公里每小时", "千米每小时", "km/h", "kmh", "kph",
        } else value

    prefix = _CHINESE_SPEED_PREFIX_RE.search(normalized)
    if prefix is not None:
        return _chinese_number_below_100(prefix.group("value"))
    suffix = _CHINESE_SPEED_SUFFIX_RE.search(normalized)
    if suffix is None:
        return None
    value = _chinese_number_below_100(suffix.group("value"))
    return value / 3.6 if suffix.group("unit") in {
        "公里每小时", "千米每小时",
    } else value


def _chinese_number_below_100(text: str) -> float:
    digits = {
        "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3,
        "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    }
    if "十" not in text:
        if len(text) != 1 or text not in digits:
            raise ValueError(f"unsupported Chinese speed number: {text!r}")
        return float(digits[text])
    tens, ones = text.split("十", 1)
    if len(tens) > 1 or len(ones) > 1:
        raise ValueError(f"unsupported Chinese speed number: {text!r}")
    tens_value = 1 if not tens else digits[tens]
    ones_value = 0 if not ones else digits[ones]
    return float(tens_value * 10 + ones_value)


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
    nearest_requested = False
    distance_match = re.search(
        r"距离约(?P<distance>\d+(?:\.\d+)?)米",
        command,
    )
    if distance_match is not None:
        requested_distance = float(distance_match.group("distance"))
        relation_check = lambda relation, item=None: True
    elif "最近" in command or "较近" in command:
        nearest_requested = True
        relation_check = lambda relation: True
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
    if nearest_requested:
        with_distance = [
            item
            for item in candidates
            if (
                type(item.get("distance_m")) in (int, float)
                and not isinstance(item.get("distance_m"), bool)
                and math.isfinite(float(item["distance_m"]))
            )
        ]
        if not with_distance:
            return candidates if len(candidates) == 1 else []
        nearest_distance = min(float(item["distance_m"]) for item in with_distance)
        return [
            item
            for item in with_distance
            if abs(float(item["distance_m"]) - nearest_distance) <= 0.25
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
        max_new_tokens: int = 48,
        device_map: str = "auto",
        torch_dtype: str = "auto",
        awq_backend: str = "auto",
        min_pixels: int = 64 * 28 * 28,
        max_pixels: int = 64 * 28 * 28,
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
        if awq_backend not in {"auto", "torch_awq", "gemm", "gemm_triton"}:
            raise ValueError(
                "awq_backend must be auto/torch_awq/gemm/gemm_triton"
            )
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
            from transformers import (
                AutoConfig,
                AutoProcessor,
                Qwen2_5_VLForConditionalGeneration,
            )
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
        model_load_args: dict[str, Any] = {}
        model_config = AutoConfig.from_pretrained(
            str(checkpoint),
            trust_remote_code=True,
            local_files_only=True,
        )
        quantization = getattr(model_config, "quantization_config", None)
        if isinstance(quantization, Mapping) and quantization.get(
            "quant_method"
        ) == "awq":
            awq_config = dict(quantization)
            skipped_modules = list(
                awq_config.get("modules_to_not_convert") or []
            )
            # Qwen's older checkpoint names the visual tower ``visual`` while
            # Transformers 5.x exposes it as ``model.visual``.  Keep both so
            # full-precision vision weights are never treated as packed AWQ.
            if "visual" in skipped_modules and "model.visual" not in skipped_modules:
                skipped_modules.append("model.visual")
            awq_config["modules_to_not_convert"] = skipped_modules
            if awq_backend != "auto":
                awq_config["backend"] = awq_backend
            model_config.quantization_config = awq_config
        elif awq_backend != "auto":
            raise ValueError("awq_backend override requires an AWQ checkpoint")
        model_load_args["config"] = model_config
        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            str(checkpoint),
            torch_dtype=torch_dtype,
            device_map=device_map,
            trust_remote_code=True,
            local_files_only=True,
            **model_load_args,
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
    "QwenVLActionChoice",
    "QwenVLGenerationBackend",
    "QwenVLInferenceTrace",
    "StrictQwenVLAdapter",
    "TransformersQwen25VLBackend",
    "assemble_action_choice",
    "build_action_choice_prompt",
    "build_strict_qwen_prompt",
    "crop_road_roi",
]
