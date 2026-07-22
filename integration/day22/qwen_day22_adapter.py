from __future__ import annotations

import json
import re
from typing import Any, Callable, Mapping

from .day22_context import Day22Context
from .qwen_prompt_v2 import ALLOWED_ACTIONS, build_day22_prompt
from .safety_adapter import normalize_safety_state


FORBIDDEN_FIELDS = frozenset({
    "throttle",
    "brake",
    "steer",
    "steering_angle",
    "wheel_angle",
})


def _short_reason(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback

    text = text.replace("\n", " ").strip()
    return text[:20]


def _make_decision(
    action: str,
    *,
    confidence: float,
    reason_zh: str,
    requires_confirmation: bool = False,
    target_speed_mps: float | None = None,
    decision_source: str = "SAFETY_RULE",
) -> dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported action: {action}")

    result: dict[str, Any] = {
        "action": action,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "requires_confirmation": bool(requires_confirmation),
        "reason_zh": _short_reason(reason_zh, "安全决策"),
        "decision_source": decision_source,
    }

    if target_speed_mps is not None:
        speed = max(0.0, float(target_speed_mps))
        result["target_speed_mps"] = speed

    return result


def _extract_json(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise TypeError("Qwen output must be a string")

    blocks = re.findall(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        raw,
        flags=re.I | re.S,
    )

    candidates = blocks + [raw]

    decoder = json.JSONDecoder()

    for candidate in candidates:
        start = candidate.find("{")
        if start < 0:
            continue

        try:
            obj, _ = decoder.raw_decode(candidate[start:])
        except json.JSONDecodeError:
            continue

        if isinstance(obj, dict):
            return obj

    raise ValueError("no valid JSON object found")


def _sanitize_qwen_decision(raw: str) -> dict[str, Any]:
    data = _extract_json(raw)

    forbidden = FORBIDDEN_FIELDS.intersection(data.keys())
    if forbidden:
        raise ValueError(
            "Qwen emitted forbidden low-level fields: "
            + ",".join(sorted(forbidden))
        )

    action = str(data.get("action", "")).strip().upper()
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"invalid Qwen action: {action}")

    speed = data.get("target_speed_mps")
    if speed is not None:
        speed = float(speed)

    return _make_decision(
        action,
        confidence=float(data.get("confidence", 0.0)),
        reason_zh=data.get("reason_zh", "Qwen高层判断"),
        requires_confirmation=bool(
            data.get("requires_confirmation", False)
        ),
        target_speed_mps=speed,
        decision_source="QWEN",
    )


class Day22QwenAdapter:
    """
    Day22稳定高层决策入口。

    model_infer:
        可选函数，签名为 model_infer(prompt: str) -> str。
        提供时执行真实Qwen输出解析；未提供时使用确定性基线。

    不论是否调用真实Qwen，最终都经过安全规则覆盖。
    """

    def __init__(
        self,
        model_infer: Callable[[str], str] | None = None,
        *,
        low_confidence_threshold: float = 0.60,
        pedestrian_confidence_threshold: float = 0.60,
        emergency_ttc_s: float = 1.50,
        caution_ttc_s: float = 2.50,
        emergency_distance_m: float = 5.0,
        caution_distance_m: float = 10.0,
        red_stop_line_guard_m: float = 8.0,
        slow_speed_mps: float = 3.0,
        rain_speed_mps: float = 5.0,
    ) -> None:
        self.model_infer = model_infer
        self.low_confidence_threshold = float(low_confidence_threshold)
        self.pedestrian_confidence_threshold = float(
            pedestrian_confidence_threshold
        )
        self.emergency_ttc_s = float(emergency_ttc_s)
        self.caution_ttc_s = float(caution_ttc_s)
        self.emergency_distance_m = float(emergency_distance_m)
        self.caution_distance_m = float(caution_distance_m)
        self.red_stop_line_guard_m = float(red_stop_line_guard_m)
        self.slow_speed_mps = float(slow_speed_mps)
        self.rain_speed_mps = float(rain_speed_mps)

    def build_prompt(self, context: Day22Context) -> str:
        safety = normalize_safety_state(context.safety_state)

        return build_day22_prompt(
            voice_command=context.voice_command,
            perception=context.perception,
            safety_state=safety,
            scene_state=context.scene_state,
        )

    def infer(self, context: Day22Context) -> dict[str, Any]:
        safety = normalize_safety_state(context.safety_state)

        qwen_decision: dict[str, Any] | None = None

        if self.model_infer is not None:
            try:
                raw = self.model_infer(self.build_prompt(context))
                qwen_decision = _sanitize_qwen_decision(raw)
            except Exception:
                qwen_decision = _make_decision(
                    "STOP",
                    confidence=0.0,
                    requires_confirmation=True,
                    reason_zh="Qwen输出异常",
                    decision_source="QWEN_FAIL_SAFE",
                )

        return self._apply_safety_policy(
            context=context,
            safety=safety,
            qwen_decision=qwen_decision,
        )

    def _apply_safety_policy(
        self,
        *,
        context: Day22Context,
        safety: Mapping[str, Any],
        qwen_decision: dict[str, Any] | None,
    ) -> dict[str, Any]:
        recommended = safety["recommended_action"]

        if recommended in {"FULL_BRAKE", "EMERGENCY_BRAKE"}:
            action = (
                "EMERGENCY_STOP"
                if recommended == "EMERGENCY_BRAKE"
                else "STOP"
            )
            return _make_decision(
                action,
                confidence=0.99,
                reason_zh="安全模块要求停车",
            )

        if safety["lidar_valid"] is False:
            return _make_decision(
                "STOP",
                confidence=0.99,
                reason_zh="LiDAR无效安全停车",
                requires_confirmation=True,
            )

        ttc = safety["ttc_s"]
        if ttc is not None and ttc <= self.emergency_ttc_s:
            return _make_decision(
                "EMERGENCY_STOP",
                confidence=0.99,
                reason_zh="TTC风险过高",
            )

        stop_line = safety["distance_to_stop_line_m"]
        if safety["traffic_light"] == "RED":
            if (
                stop_line is None
                or stop_line <= self.red_stop_line_guard_m
            ):
                return _make_decision(
                    "STOP",
                    confidence=0.98,
                    reason_zh="红灯安全约束优先",
                )

            return _make_decision(
                "SLOW_DOWN",
                confidence=0.95,
                reason_zh="接近红灯提前减速",
                target_speed_mps=self.slow_speed_mps,
            )

        object_class = safety["object_class"]
        object_confidence = safety["object_confidence"]
        visual_valid = safety["visual_valid"]

        reliable_visual = (
            visual_valid is not False
            and object_confidence >= self.pedestrian_confidence_threshold
        )

        if (
            object_class in {"PEDESTRIAN", "PERSON"}
            and reliable_visual
        ):
            return _make_decision(
                "STOP",
                confidence=0.98,
                reason_zh="检测到可靠行人风险",
            )

        distance = safety["front_distance_m"]

        if distance is not None and distance <= self.emergency_distance_m:
            return _make_decision(
                "STOP",
                confidence=0.98,
                reason_zh="前方距离过近",
            )

        if ttc is not None and ttc <= self.caution_ttc_s:
            return _make_decision(
                "SLOW_DOWN",
                confidence=0.95,
                reason_zh="TTC进入警戒范围",
                target_speed_mps=self.slow_speed_mps,
            )

        if distance is not None and distance <= self.caution_distance_m:
            return _make_decision(
                "SLOW_DOWN",
                confidence=0.90,
                reason_zh="前方距离不足",
                target_speed_mps=self.slow_speed_mps,
            )

        confidence = safety["input_confidence"]
        if confidence < self.low_confidence_threshold:
            return _make_decision(
                "STOP",
                confidence=confidence,
                reason_zh="安全输入置信度不足",
                requires_confirmation=True,
            )

        if (
            safety["visual_valid"] is False
            and safety["lidar_valid"] is not True
        ):
            return _make_decision(
                "STOP",
                confidence=0.50,
                reason_zh="感知状态不可用",
                requires_confirmation=True,
            )

        if safety["weather"] in {"rain", "heavy_rain"}:
            return _make_decision(
                "SET_SPEED",
                confidence=0.85,
                reason_zh="雨天降低速度",
                target_speed_mps=self.rain_speed_mps,
            )

        if qwen_decision is not None:
            return self._ground_safe_scene_qwen_decision(
                context=context,
                safety=safety,
                qwen_decision=qwen_decision,
            )

        return _make_decision(
            "START",
            confidence=0.90,
            reason_zh="安全状态正常",
            decision_source="DETERMINISTIC_BASELINE",
        )

    def _ground_safe_scene_qwen_decision(
        self,
        *,
        context: Day22Context,
        safety: Mapping[str, Any],
        qwen_decision: dict[str, Any],
    ) -> dict[str, Any]:
        """
        处理没有触发任何确定性风险规则的安全场景。

        原则：
        - 明确的用户停车/减速命令可以执行；
        - Qwen仅凭图片或语言生成、但结构化状态不支持的危险判断，
          不能直接改变车辆高层目标；
        - 视觉危险必须先进入perception/safety_state统一接口，
          不能绕过结构化感知接口。
        """

        action = str(qwen_decision.get("action", "")).upper()
        voice = str(context.voice_command).strip()

        stop_words = (
            "停车",
            "停下",
            "停止",
            "别走",
            "不要走",
            "紧急停车",
        )

        slow_words = (
            "减速",
            "慢一点",
            "开慢",
            "降低速度",
        )

        if action == "START":
            return qwen_decision

        if (
            action in {"STOP", "EMERGENCY_STOP"}
            and any(word in voice for word in stop_words)
        ):
            return qwen_decision

        if (
            action in {"SLOW_DOWN", "SET_SPEED"}
            and any(word in voice for word in slow_words)
        ):
            return qwen_decision

        return _make_decision(
            "START",
            confidence=0.90,
            reason_zh="结构化状态无风险",
            decision_source="QWEN_UNGROUNDED_REJECTED",
        )
