"""Rule-based B2 parser for vehicle voice commands.

The module accepts B1 output, extracts executable slots, validates safety
constraints, and returns a unified JSON-like dict for the CARLA control side.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable


SUPPORTED_INTENTS = {
    "SET_SPEED",
    "CHANGE_LANE",
    "PULL_OVER",
    "STOP",
    "EMERGENCY_STOP",
    "AVOID_OBSTACLE",
    "KEEP_LANE",
    "FOLLOW_ROUTE",
    "TURN",
    "SLOW_DOWN",
    "SPEED_UP",
}


@dataclass(frozen=True)
class ParserConfig:
    """Runtime limits agreed with the vehicle-control side."""

    min_speed_kmh: int = 0
    max_speed_kmh: int = 80
    low_confidence_threshold: float = 0.60
    default_pull_over_side: str = "RIGHT"


@dataclass
class ParseContext:
    request_id: Any | None
    original_text: str
    normalized_text: str
    intent: str
    intent_confidence: float
    asr_confidence: float | None = None
    b1_status: str | None = None
    route: str = "fast"
    reason: str | None = None
    b1_latency_ms: float | None = None
    slots: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)

    def error(self, code: str, message: str) -> None:
        self.errors.append({"code": code, "message": message})

    def warning(self, code: str, message: str) -> None:
        self.warnings.append({"code": code, "message": message})


class CommandParser:
    """Extract slots, validate them, and package executable commands."""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()
        self._handlers: dict[str, Callable[[ParseContext], None]] = {
            "SET_SPEED": self._handle_set_speed,
            "CHANGE_LANE": self._handle_change_lane,
            "PULL_OVER": self._handle_pull_over,
            "STOP": self._handle_stop,
            "EMERGENCY_STOP": self._handle_stop,
            "AVOID_OBSTACLE": self._handle_avoid_obstacle,
            "KEEP_LANE": self._handle_keep_lane,
            "FOLLOW_ROUTE": self._handle_follow_route,
            "TURN": self._handle_turn,
            "SLOW_DOWN": self._handle_relative_speed,
            "SPEED_UP": self._handle_relative_speed,
        }

    def parse(self, b1_result: dict[str, Any]) -> dict[str, Any]:
        """Parse B1 output into the final JSON command consumed by D."""

        start = time.perf_counter()
        ctx = self._build_context(b1_result)

        blocking_error = self._blocking_b1_error(ctx)
        if blocking_error:
            ctx.error(*blocking_error)
        elif ctx.intent not in SUPPORTED_INTENTS:
            ctx.error("UNKNOWN_INTENT", f"不支持的意图: {ctx.intent or '<empty>'}")
        else:
            self._handlers[ctx.intent](ctx)
            self._validate_common_safety(ctx)

        if ctx.intent_confidence < self.config.low_confidence_threshold:
            ctx.warning(
                "LOW_CONFIDENCE",
                f"B1 意图置信度 {ctx.intent_confidence:.2f} 低于阈值 {self.config.low_confidence_threshold:.2f}",
            )

        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        return {
            "request_id": ctx.request_id,
            "intent": ctx.intent,
            "slots": ctx.slots,
            "intent_confidence": ctx.intent_confidence,
            "asr_confidence": ctx.asr_confidence,
            "status": self._status(ctx),
            "route": ctx.route,
            "reason": ctx.reason,
            "latency_ms": latency_ms,
            "b1_latency_ms": ctx.b1_latency_ms,
            "original_text": ctx.original_text,
            "normalized_text": ctx.normalized_text,
            "errors": ctx.errors,
            "warnings": ctx.warnings,
        }

    def _build_context(self, b1_result: dict[str, Any]) -> ParseContext:
        request_id = b1_result.get("request_id")
        original_text = str(b1_result.get("original_text", "") or "")
        normalized_text = str(
            b1_result.get("normalized_text", b1_result.get("text", "")) or ""
        )
        intent = str(b1_result.get("intent", "") or "").strip().upper()
        intent_confidence = _safe_float(
            b1_result.get("intent_confidence", 1.0),
            default=1.0,
        )
        b1_status = _optional_lower(b1_result.get("status"))
        route = _optional_lower(b1_result.get("route")) or "fast"
        reason = b1_result.get("reason")
        return ParseContext(
            request_id=request_id,
            original_text=original_text,
            normalized_text=_normalize_text(normalized_text),
            intent=intent,
            intent_confidence=intent_confidence,
            asr_confidence=_optional_float(b1_result.get("asr_confidence")),
            b1_status=b1_status,
            route=route,
            reason=str(reason) if reason is not None else None,
            b1_latency_ms=_optional_float(b1_result.get("b1_latency_ms")),
        )

    @staticmethod
    def _blocking_b1_error(ctx: ParseContext) -> tuple[str, str] | None:
        if ctx.b1_status == "needs_slow_path":
            ctx.route = "slow"
            return ("NEEDS_SLOW_PATH", "B1 标记为慢路径处理，B2 不生成快路径可执行指令")
        if ctx.b1_status == "unknown":
            return ("B1_UNKNOWN", "B1 未能识别为可执行车控指令")
        if ctx.b1_status and ctx.b1_status != "valid":
            return ("B1_INVALID_STATUS", f"B1 状态不允许执行: {ctx.b1_status}")
        if ctx.intent == "UNKNOWN":
            return ("UNKNOWN_INTENT", "B1 意图为 UNKNOWN，禁止生成可执行指令")
        return None

    def _handle_set_speed(self, ctx: ParseContext) -> None:
        speed = _extract_speed(ctx.normalized_text)
        if speed is None:
            ctx.error("MISSING_SLOT", "SET_SPEED 缺少 speed 槽位")
            return
        ctx.slots["speed"] = speed
        ctx.slots["unit"] = "km/h"

    def _handle_change_lane(self, ctx: ParseContext) -> None:
        direction = _extract_direction(ctx.normalized_text)
        if direction == "CONFLICT":
            ctx.error("CONFLICT_SLOT", "同时出现左/右方向，无法安全变道")
            return
        if direction not in {"LEFT", "RIGHT"}:
            ctx.error("MISSING_SLOT", "CHANGE_LANE 缺少 direction 槽位")
            return
        ctx.slots["direction"] = direction

    def _handle_pull_over(self, ctx: ParseContext) -> None:
        direction = _extract_direction(ctx.normalized_text)
        if direction == "CONFLICT":
            ctx.error("CONFLICT_SLOT", "靠边停车方向冲突")
            return
        ctx.slots["side"] = (
            direction if direction in {"LEFT", "RIGHT"} else self.config.default_pull_over_side
        )
        if direction not in {"LEFT", "RIGHT"}:
            ctx.warning("INFERRED_SLOT", "未给出靠边方向，默认靠右停车")
        ctx.slots["stop"] = True

    def _handle_stop(self, ctx: ParseContext) -> None:
        ctx.slots["brake"] = "FULL" if ctx.intent == "EMERGENCY_STOP" else "NORMAL"

    def _handle_avoid_obstacle(self, ctx: ParseContext) -> None:
        direction = _extract_direction(ctx.normalized_text)
        if direction == "CONFLICT":
            ctx.error("CONFLICT_SLOT", "绕障方向冲突")
            return
        if direction in {"LEFT", "RIGHT"}:
            ctx.slots["direction"] = direction
        else:
            ctx.slots["direction"] = "AUTO"
            ctx.warning("INFERRED_SLOT", "未给出绕障方向，交由决策模块自动选择")
        ctx.slots["target"] = _extract_obstacle_target(ctx.normalized_text)

    def _handle_keep_lane(self, ctx: ParseContext) -> None:
        ctx.slots["mode"] = "KEEP_CURRENT_LANE"

    def _handle_follow_route(self, ctx: ParseContext) -> None:
        target = _extract_target(ctx.normalized_text)
        if target:
            ctx.slots["target"] = target
        else:
            ctx.slots["mode"] = "FOLLOW_CURRENT_ROUTE"
            ctx.warning("INFERRED_SLOT", "未给出目标点，默认继续当前路线")

    def _handle_turn(self, ctx: ParseContext) -> None:
        direction = _extract_direction(ctx.normalized_text)
        if direction == "CONFLICT":
            ctx.error("CONFLICT_SLOT", "转向方向冲突")
            return
        if direction not in {"LEFT", "RIGHT", "STRAIGHT"}:
            ctx.error("MISSING_SLOT", "TURN 缺少 direction 槽位")
            return
        ctx.slots["direction"] = direction

    def _handle_relative_speed(self, ctx: ParseContext) -> None:
        speed = _extract_speed(ctx.normalized_text)
        if speed is not None:
            ctx.slots["speed"] = speed
            ctx.slots["unit"] = "km/h"
            ctx.slots["mode"] = "TARGET"
        else:
            ctx.slots["mode"] = "RELATIVE"
            ctx.slots["action"] = "DECELERATE" if ctx.intent == "SLOW_DOWN" else "ACCELERATE"
            ctx.warning("MISSING_OPTIONAL_SLOT", "未给出目标速度，输出相对速度动作")

    def _validate_common_safety(self, ctx: ParseContext) -> None:
        speed = ctx.slots.get("speed")
        if speed is not None:
            if not isinstance(speed, int):
                ctx.error("INVALID_SLOT", "speed 必须是整数 km/h")
            elif speed < self.config.min_speed_kmh:
                ctx.error("INVALID_SLOT", f"speed 不能小于 {self.config.min_speed_kmh} km/h")
            elif speed > self.config.max_speed_kmh:
                ctx.error("UNSAFE_SLOT", f"speed {speed} km/h 超过安全上限 {self.config.max_speed_kmh} km/h")

        direction = ctx.slots.get("direction") or ctx.slots.get("side")
        if direction is not None and direction not in {"LEFT", "RIGHT", "STRAIGHT", "AUTO"}:
            ctx.error("INVALID_SLOT", f"非法方向: {direction}")

    @staticmethod
    def _status(ctx: ParseContext) -> str:
        if not ctx.errors:
            return "valid"
        priority = (
            ("NEEDS_SLOW_PATH", "needs_slow_path"),
            ("B1_UNKNOWN", "unknown"),
            ("UNKNOWN_INTENT", "unknown_intent"),
            ("CONFLICT_SLOT", "conflict"),
            ("MISSING_SLOT", "missing_slot"),
            ("UNSAFE_SLOT", "unsafe"),
            ("INVALID_SLOT", "invalid_slot"),
            ("B1_INVALID_STATUS", "invalid"),
        )
        codes = {item["code"] for item in ctx.errors}
        for code, status in priority:
            if code in codes:
                return status
        return "invalid"


def parse_command(b1_result: dict[str, Any], config: ParserConfig | None = None) -> dict[str, Any]:
    """Convenience function for callers that do not need a parser instance."""

    return CommandParser(config).parse(b1_result)


def _normalize_text(text: str) -> str:
    table = str.maketrans(
        "０１２３４５６７８９，。！？；：　",
        "0123456789,.!?;: ",
    )
    normalized = text.translate(table)
    normalized = normalized.upper().replace("公里每小时", "KM/H")
    normalized = normalized.replace("公里/小时", "KM/H").replace("千米每小时", "KM/H")
    normalized = normalized.replace("千米/小时", "KM/H").replace("码", "KM/H")
    return re.sub(r"\s+", "", normalized)


def _extract_direction(text: str) -> str | None:
    has_left = any(word in text for word in ("左", "LEFT", "左侧", "左边"))
    has_right = any(word in text for word in ("右", "RIGHT", "右侧", "右边"))
    has_straight = any(word in text for word in ("直行", "向前", "前进", "STRAIGHT"))
    if has_left and has_right:
        return "CONFLICT"
    if has_left:
        return "LEFT"
    if has_right:
        return "RIGHT"
    if has_straight:
        return "STRAIGHT"
    return None


def _extract_speed(text: str) -> int | None:
    arabic = re.search(r"(?<!\d)(\d{1,3})(?:KM/H|公里|千米|迈)?", text)
    if arabic:
        return int(arabic.group(1))

    chinese_match = re.search(r"([零〇一二两三四五六七八九十百]{1,6})(?:KM/H|公里|千米|迈)?", text)
    if chinese_match:
        return _chinese_number_to_int(chinese_match.group(1))
    return None


def _extract_obstacle_target(text: str) -> str:
    if "行人" in text:
        return "PEDESTRIAN"
    if "车辆" in text or "车" in text:
        return "VEHICLE"
    if "障碍" in text or "障碍物" in text:
        return "OBSTACLE"
    return "FRONT_OBSTACLE"


def _extract_target(text: str) -> str | None:
    match = re.search(r"(?:去|到|前往|开到)([\u4e00-\u9fa5A-Z0-9_-]{2,20})", text)
    if not match:
        return None
    target = match.group(1)
    stop_words = ("路线", "那里", "前面")
    if target in stop_words:
        return None
    return target


def _chinese_number_to_int(value: str) -> int | None:
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if not value:
        return None
    if "百" in value:
        left, _, right = value.partition("百")
        hundreds = digits.get(left, 1 if left == "" else None)
        if hundreds is None:
            return None
        tail = _chinese_number_to_int(right) if right else 0
        return hundreds * 100 + (tail or 0)
    if "十" in value:
        left, _, right = value.partition("十")
        tens = digits.get(left, 1 if left == "" else None)
        ones = digits.get(right, 0 if right == "" else None)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    result = 0
    for char in value:
        if char not in digits:
            return None
        result = result * 10 + digits[char]
    return result


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_lower(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None
