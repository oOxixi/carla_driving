"""Deterministic fixed-shape preprocessing for ModelRequest V1."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from typing import Any

import torch
from torch import Tensor

from .contract import BEHAVIORS, StudentShapeContract


_CLASS_INDEX = {
    "vehicle": 0,
    "pedestrian": 1,
    "cyclist": 2,
    "obstacle": 3,
    "unknown": 4,
}
_TRAFFIC_INDEX = {"RED": 0, "YELLOW": 1, "GREEN": 2, "UNKNOWN": 3}
_RISK_INDEX = {"LOW": 0, "CAUTION": 1, "HIGH": 2, "EMERGENCY": 3, "UNKNOWN": 4}
_INTENTS = (
    "KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "EMERGENCY_STOP", "YIELD",
    "FOLLOW", "TURN", "CHANGE_LANE", "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER",
)

POST_TURN_SPEED_INDEX = 63
_NUMBER = r"[0-9]{1,3}|[零〇一二两三四五六七八九十]{1,3}"
_SPEED = rf"(?:每小时\s*(?P<before>{_NUMBER})\s*(?:公里|千米)|(?P<after>{_NUMBER})\s*(?:(?:公里|千米)(?:每小时|/小时)|km\s*/\s*h))"
_POST_TURN_SPEED = re.compile(
    rf"(?:转(?:弯|向)?(?:完成|完)?(?:以)?后|转(?:弯)?\s*[,，、 ]*\s*(?:随后|然后|之后))"
    rf"\s*[,，、 ]*\s*(?:请)?(?:将(?:车)?速(?:度)?(?:设置为|设为|调到)|"
    rf"把(?:车)?速(?:度)?(?:设置为|设为|调到)|(?:保持|设速|定速)(?:为|到|在)?\s*){_SPEED}"
)


def explicit_post_turn_speed(request: Mapping[str, Any]) -> bool:
    from voice_group.nlu_b2.parser import _chinese_number_to_int

    hint = request.get("command_hint") or {}
    speed = hint.get("target_speed_mps")
    if hint.get("intent") != "TURN" or type(speed) not in (int, float) or not 0 < speed <= 50:
        return False
    text = unicodedata.normalize("NFKC", str(request.get("source_text", ""))).casefold()
    side = {"LEFT": "左", "RIGHT": "右"}.get(hint.get("direction"))
    if not side or f"{side}转" not in text or ("右转" if side == "左" else "左转") in text:
        return False
    if any(word in text for word in ("行人", "让行", "避让", "跟车", "不要", "别", "取消", "不再", "不保持", "最高", "上限", "不超过")):
        return False
    matches = list(_POST_TURN_SPEED.finditer(text))
    if len(matches) != 1 or text[matches[0].end():].strip(" 。！!，,；;"):
        return False
    number = matches[0]["before"] or matches[0]["after"]
    kph = int(number) if number.isascii() else _chinese_number_to_int(number)
    return kph is not None and abs(kph / 3.6 - speed) < 1e-4


@dataclass(frozen=True, slots=True)
class TensorizedRequest:
    rgb: Tensor
    text_tokens: Tensor
    targets: Tensor
    state: Tensor

    def as_tuple(self) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        return self.rgb, self.text_tokens, self.targets, self.state


class StudentPreprocessor:
    def __init__(self, contract: StudentShapeContract | None = None, *, post_turn_speed: bool = False) -> None:
        self.contract = contract or StudentShapeContract()
        self.post_turn_speed = post_turn_speed

    def __call__(self, request: Mapping[str, Any]) -> TensorizedRequest:
        return TensorizedRequest(
            rgb=self._rgb(request.get("rgb_ref")),
            text_tokens=self._text(str(request["source_text"])),
            targets=self._targets(request["targets"]),
            state=self._state(request),
        )

    def _rgb(self, reference: object) -> Tensor:
        shape = self.contract.input_shapes["rgb"]
        if not isinstance(reference, str) or not reference.strip():
            return torch.zeros(shape, dtype=torch.float32)
        path = Path(reference)
        if not path.is_file():
            return torch.zeros(shape, dtype=torch.float32)
        from PIL import Image

        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail(
                (self.contract.rgb_width, self.contract.rgb_height),
                Image.Resampling.BILINEAR,
            )
            # Letterbox instead of distorting camera geometry.  Padding uses
            # the ImageNet mean so it becomes approximately zero after the
            # normalization below.
            canvas = Image.new("RGB", (self.contract.rgb_width, self.contract.rgb_height), (123, 116, 104))
            canvas.paste(
                image,
                ((self.contract.rgb_width - image.width) // 2, (self.contract.rgb_height - image.height) // 2),
            )
            value = torch.tensor(bytearray(canvas.tobytes()), dtype=torch.uint8)
        value = value.reshape(self.contract.rgb_height, self.contract.rgb_width, 3)
        value = value.permute(2, 0, 1).unsqueeze(0).to(torch.float32).div_(255.0)
        mean = torch.tensor((0.485, 0.456, 0.406), dtype=torch.float32).reshape(1, 3, 1, 1)
        std = torch.tensor((0.229, 0.224, 0.225), dtype=torch.float32).reshape(1, 3, 1, 1)
        return (value - mean) / std

    def _text(self, text: str) -> Tensor:
        values = torch.zeros((1, self.contract.text_length), dtype=torch.float32)
        for index, character in enumerate(text[: self.contract.text_length]):
            values[0, index] = (ord(character) % 65535) / 65535.0
        return values

    def _targets(self, raw_targets: object) -> Tensor:
        values = torch.zeros(
            (1, self.contract.max_targets, self.contract.target_features),
            dtype=torch.float32,
        )
        if not isinstance(raw_targets, list):
            return values
        for index, target in enumerate(raw_targets[: self.contract.max_targets]):
            if not isinstance(target, Mapping):
                continue
            class_index = _CLASS_INDEX.get(str(target.get("class", "unknown")), 4)
            values[0, index, class_index] = 1.0
            values[0, index, 5] = min(float(target.get("distance_m", 0.0)), 200.0) / 200.0
            relative_speed = target.get("relative_speed_mps")
            if relative_speed is not None:
                values[0, index, 6] = max(-1.0, min(1.0, float(relative_speed) / 30.0))
            values[0, index, 7] = float(target.get("confidence", 0.0))
            relation = str(target.get("relation", "")).lower()
            relation_flags = (
                "left" in relation,
                "right" in relation,
                "center" in relation,
                "ahead" in relation or "front" in relation,
                "behind" in relation or "rear" in relation,
            )
            for relation_index, flag in enumerate(relation_flags):
                values[0, index, 8 + relation_index] = float(flag)
            values[0, index, 13] = float(not any(relation_flags))
        return values

    def _state(self, request: Mapping[str, Any]) -> Tensor:
        values = torch.zeros((1, self.contract.state_features), dtype=torch.float32)
        summary = request["scene_summary"]
        constraints = request["constraints"]
        capabilities = request.get("scene_capabilities") or {}
        values[0, _TRAFFIC_INDEX.get(str(summary["traffic_light"]), 3)] = 1.0
        values[0, 4 + _RISK_INDEX.get(str(summary["risk_level"]), 4)] = 1.0
        if summary.get("min_gap_m") is not None:
            values[0, 9] = min(float(summary["min_gap_m"]), 100.0) / 100.0
        if summary.get("ttc_s") is not None:
            values[0, 10] = min(float(summary["ttc_s"]), 20.0) / 20.0
        if constraints.get("speed_limit_mps") is not None:
            values[0, 11] = min(float(constraints["speed_limit_mps"]), 50.0) / 50.0
        if constraints.get("max_target_speed_mps") is not None:
            values[0, 12] = min(float(constraints["max_target_speed_mps"]), 50.0) / 50.0
        values[0, 13] = float(bool(constraints["must_stop"]))
        values[0, 14] = float(bool(capabilities.get("left_gap_safe", False)))
        values[0, 15] = float(bool(capabilities.get("right_gap_safe", False)))
        allowed = _expanded_allowed_behaviors(request)
        for behavior_index, behavior in enumerate(BEHAVIORS):
            values[0, 16 + behavior_index] = float(behavior in allowed)
        values[0, 30] = min(len(request["targets"]), self.contract.max_targets) / self.contract.max_targets
        values[0, 31] = float(bool(capabilities.get("route_available", False)))
        hint = request.get("command_hint") or {}
        intent = str(hint.get("intent", "")).upper()
        if intent in _INTENTS:
            values[0, 32 + _INTENTS.index(intent)] = 1.0
        target_speed = hint.get("target_speed_mps")
        if target_speed is not None:
            values[0, 44] = min(float(target_speed), 50.0) / 50.0
        direction = str(hint.get("direction") or "").upper()
        if direction in {"LEFT", "RIGHT", "STRAIGHT"}:
            values[0, 45 + ("LEFT", "RIGHT", "STRAIGHT").index(direction)] = 1.0
        values[0, 48] = float(bool(capabilities.get("left_lane_exists", False)))
        values[0, 49] = float(bool(capabilities.get("right_lane_exists", False)))
        values[0, 50] = float(bool(capabilities.get("intersection_ahead", False)))
        values[0, 51] = float(bool(capabilities.get("stop_line_clear", False)))
        routing = request.get("routing") or {}
        values[0, 52] = float(str(routing.get("disposition", "")) == "CONFIRM_SAFE")
        values[0, 53] = max(-1.0, min(1.0, float(routing.get("score", 0)) / 10.0))
        safe_wait = str(routing.get("safe_wait_behavior", ""))
        safe_wait_behaviors = ("KEEP_LANE_LIMITED", "SLOW_DOWN", "STOP", "EMERGENCY_STOP")
        if safe_wait in safe_wait_behaviors:
            values[0, 54 + safe_wait_behaviors.index(safe_wait)] = 1.0
        reasons = routing.get("reasons") or ()
        values[0, 58] = min(len(reasons), 8) / 8.0
        return_direction = str(capabilities.get("return_direction", ""))
        if return_direction in {"LEFT", "RIGHT"}:
            values[0, 59 + ("LEFT", "RIGHT").index(return_direction)] = 1.0
        values[0, 61] = float(
            capabilities.get("current_lane") is not None
            and capabilities.get("current_lane") == capabilities.get("original_lane")
        )
        values[0, 62] = min(len(capabilities.get("grounded_target_ids", ())), 8) / 8.0
        if self.post_turn_speed:
            values[0, POST_TURN_SPEED_INDEX] = float(explicit_post_turn_speed(request))
        return values


def _expanded_allowed_behaviors(request: Mapping[str, Any]) -> set[str]:
    constraints = request["constraints"]
    if bool(constraints["must_stop"]):
        return {"STOP"}
    direction = str((request.get("command_hint") or {}).get("direction") or "")
    allowed: set[str] = set()
    for behavior in constraints["allowed_behaviors"]:
        if behavior == "TURN":
            allowed.update(
                {"TURN_LEFT"} if direction == "LEFT" else
                {"TURN_RIGHT"} if direction == "RIGHT" else
                {"TURN_LEFT", "TURN_RIGHT"}
            )
        elif behavior == "CHANGE_LANE":
            allowed.update(
                {"CHANGE_LANE_LEFT"} if direction == "LEFT" else
                {"CHANGE_LANE_RIGHT"} if direction == "RIGHT" else
                {"CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT"}
            )
        else:
            allowed.add(str(behavior))
    return allowed or {"HOLD"}


__all__ = ["StudentPreprocessor", "TensorizedRequest", "_expanded_allowed_behaviors"]
