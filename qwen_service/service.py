"""Core B service with strict contracts, bounded concurrency and metrics."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
import base64
import io
import json
import math
from pathlib import Path
import statistics
from threading import BoundedSemaphore, Lock
import time
from typing import Any, Protocol

from integration.qwen_boundary import QwenInputContext
from integration.qwen_plan_adapter import (
    QwenPlanParseError,
    build_planner_v2_prompt,
    parse_maneuver_plan,
)
from integration.qwen_vl_adapter import StrictQwenVLAdapter, TransformersQwen25VLBackend
from runtime.interface_registry import InterfaceRegistry, InterfaceValidationError
from runtime.plan_validator import PlanValidationError, PlanValidator


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


class DecisionBackend(Protocol):
    model_id: str
    production_ready: bool

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def health(self) -> tuple[bool, str]: ...


class ServiceFailure(RuntimeError):
    def __init__(self, status_code: int, error_code: str, message: str, *, request_id: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "status": "ERROR",
            "error_code": self.error_code,
            "message": str(self),
            "request_id": self.request_id,
        }


@dataclass(frozen=True, slots=True)
class QwenServiceConfig:
    timeout_ms: float = 300.0
    max_concurrency: int = 1
    max_request_bytes: int = 262_144

    def __post_init__(self) -> None:
        if type(self.timeout_ms) not in (int, float) or isinstance(self.timeout_ms, bool) or not math.isfinite(float(self.timeout_ms)) or self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be finite and positive")
        for name in ("max_concurrency", "max_request_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")


class UnavailableBackend:
    model_id = "UNAVAILABLE"
    production_ready = False

    def __init__(self, reason: str = "no local Qwen checkpoint configured") -> None:
        self.reason = reason

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError(self.reason)

    def health(self) -> tuple[bool, str]:
        return False, self.reason


class DeterministicTestBackend:
    """Contract-test backend; never valid evidence for Qwen correctness/latency."""

    model_id = "DETERMINISTIC_TEST_BACKEND"
    production_ready = False

    def health(self) -> tuple[bool, str]:
        return True, "test backend ready (not a production Qwen model)"

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        now = time.monotonic_ns()
        constraints = request["constraints"]
        text = str(request["source_text"])
        targets = request["targets"]
        if constraints["must_stop"] or any(word in text for word in ("停车", "停止", "红灯")):
            intent = behavior = "STOP"
            target_id = None
            parameters: dict[str, float] = {}
            reason = "DETERMINISTIC_SAFETY_STOP"
        elif len(targets) == 1 and any(word in text for word in ("跟随", "前车", "车辆")):
            intent = behavior = "FOLLOW"
            target_id = targets[0]["target_id"]
            parameters = {"target_speed_mps": min(4.0, float(constraints.get("max_target_speed_mps") or 4.0)), "time_gap_s": 2.0}
            reason = "DETERMINISTIC_UNIQUE_TARGET"
        else:
            intent = behavior = "SLOW_DOWN"
            target_id = None
            parameters = {"target_speed_mps": min(2.0, float(constraints.get("max_target_speed_mps") or 2.0))}
            reason = "DETERMINISTIC_CONSERVATIVE"
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": intent,
            "target_id": target_id,
            "behavior": behavior,
            "parameters": parameters,
            "confidence": 1.0,
            "reason_code": reason,
            "created_at_ns": now,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": self.model_id,
        }


class DeterministicPlannerV2Backend:
    """Planner V2 contract stub; explicitly excluded from model evidence."""

    model_id = "DETERMINISTIC_PLANNER_V2_TEST_BACKEND"
    production_ready = False

    def health(self) -> tuple[bool, str]:
        return True, "planner v2 test backend ready (not a production Qwen model)"

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        text = str(request["source_text"])
        lower = text.lower()
        constraints = request["constraints"]
        capabilities = request.get("scene_capabilities", {})
        targets = request["targets"]
        maximum = float(constraints.get("max_target_speed_mps") or 4.0)
        cruise_speed = min(4.17, maximum)
        slow_speed = min(3.0, maximum)
        steps: list[dict[str, Any]] = []
        confirmation = False
        reason = "DETERMINISTIC_PLANNER_V2"

        if constraints["must_stop"]:
            steps.append(_planner_step(
                "s1", "STOP", speed=0.0,
                completion="STOPPED", completion_value=None,
                timeout_s=5.0, failure="SAFE_STOP",
            ))
            reason = "DETERMINISTIC_SAFETY_STOP"
        elif any(token in lower for token in ("右转", "turn right", "next right")):
            steps.extend((
                _planner_step("s1", "SLOW_DOWN", speed=slow_speed),
                _planner_step(
                    "s2", "TURN_RIGHT", speed=slow_speed, lane="ROUTE_BRANCH",
                    route_direction="RIGHT", preconditions=(
                        "PERCEPTION_FRESH", "ROUTE_AVAILABLE",
                        "INTERSECTION_AHEAD", "NO_EMERGENCY_RISK",
                    ), completion="JUNCTION_EXITED", completion_value=None,
                    timeout_s=30.0,
                ),
            ))
            if any(token in lower for token in ("公里", "km", "速度", "speed")):
                steps.append(_planner_step(
                    "s3", "SET_SPEED", speed=cruise_speed,
                    completion="SPEED_REACHED", completion_value=cruise_speed,
                ))
            reason = "DETERMINISTIC_TURN_RIGHT_SEQUENCE"
        elif any(token in lower for token in ("左转", "turn left", "next left")):
            steps.append(_planner_step(
                "s1", "TURN_LEFT", speed=slow_speed, lane="ROUTE_BRANCH",
                route_direction="LEFT", preconditions=(
                    "PERCEPTION_FRESH", "ROUTE_AVAILABLE",
                    "INTERSECTION_AHEAD", "NO_EMERGENCY_RISK",
                ), completion="JUNCTION_EXITED", completion_value=None,
                timeout_s=30.0,
            ))
            reason = "DETERMINISTIC_TURN_LEFT"
        elif any(token in lower for token in ("左变道", "向左变道", "left lane")):
            if capabilities.get("left_lane_exists") is True:
                steps.append(_planner_step(
                    "s1", "CHANGE_LANE_LEFT", speed=slow_speed,
                    lane="LEFT_ADJACENT", preconditions=(
                        "PERCEPTION_FRESH", "LEFT_LANE_EXISTS", "LEFT_GAP_SAFE",
                        "NO_EMERGENCY_RISK",
                    ), completion="LANE_CENTERED", completion_value=None,
                    timeout_s=12.0, failure="SAFE_STOP",
                ))
                if any(token in lower for token in ("公里", "km", "速度", "speed")):
                    steps.append(_planner_step(
                        "s2", "SET_SPEED", speed=cruise_speed,
                        completion="SPEED_REACHED", completion_value=cruise_speed,
                    ))
                    reason = "DETERMINISTIC_CHANGE_LANE_LEFT_SEQUENCE"
                else:
                    reason = "DETERMINISTIC_CHANGE_LANE_LEFT"
            else:
                steps.append(_planner_step(
                    "s1", "HOLD", speed=None, completion="HOLD_FRAMES",
                    completion_value=None, failure="CONFIRM",
                ))
                confirmation = True
                reason = "LEFT_LANE_UNVERIFIED"
        elif any(token in lower for token in ("跟随", "follow")) and len(targets) == 1:
            steps.append(_planner_step(
                "s1", "FOLLOW", speed=min(4.0, maximum),
                target_id=targets[0]["target_id"], time_gap_s=2.0,
                preconditions=("PERCEPTION_FRESH", "TARGET_VISIBLE", "NO_EMERGENCY_RISK"),
                completion="TARGET_GAP_REACHED", completion_value=2.0,
            ))
            reason = "DETERMINISTIC_UNIQUE_TARGET_FOLLOW"
        elif any(token in lower for token in ("绕过", "绕开", "避开", "avoid", "go around")):
            lane = (
                "LEFT_ADJACENT" if capabilities.get("left_lane_exists") is True
                else "RIGHT_ADJACENT" if capabilities.get("right_lane_exists") is True
                else None
            )
            if targets and lane is not None:
                side = "LEFT" if lane == "LEFT_ADJACENT" else "RIGHT"
                steps.extend((
                    _planner_step(
                        "s1", "AVOID_OBSTACLE", speed=slow_speed,
                        target_id=targets[0]["target_id"], lane=lane,
                        preconditions=(
                            "PERCEPTION_FRESH", "TARGET_VISIBLE",
                            f"{side}_LANE_EXISTS", f"{side}_GAP_SAFE",
                            "NO_EMERGENCY_RISK",
                        ),
                        completion="TARGET_PASSED", completion_value=None,
                        timeout_s=20.0,
                    ),
                    _planner_step(
                        "s2", "RETURN_TO_LANE", speed=slow_speed,
                        lane="CURRENT",
                        completion="LANE_CENTERED", completion_value=None,
                        timeout_s=20.0,
                    ),
                ))
                reason = "DETERMINISTIC_AVOID_AND_RETURN"
            else:
                steps.append(_planner_step(
                    "s1", "HOLD", speed=None, completion="HOLD_FRAMES",
                    completion_value=None, failure="CONFIRM",
                ))
                confirmation = True
                reason = "OBSTACLE_OR_ADJACENT_LANE_UNVERIFIED"
        else:
            steps.append(_planner_step(
                "s1", "HOLD", speed=None, completion="HOLD_FRAMES",
                completion_value=None, failure="CONFIRM",
            ))
            confirmation = True
            reason = "DETERMINISTIC_INSUFFICIENT_GROUNDING"
        now = time.monotonic_ns()
        return {
            "schema_version": "2.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "plan_id": "plan-" + str(request["request_id"]),
            "plan_type": "MANEUVER_SEQUENCE",
            "steps": steps,
            "replan_conditions": ["NEW_EMERGENCY_OBJECT", "PROGRESS_STALLED"],
            "confidence": 0.5 if confirmation else 1.0,
            "requires_confirmation": confirmation,
            "created_at_ns": now,
            "valid_until_ns": request["deadline_ns"],
            "reason_code": reason,
            "model_id": self.model_id,
        }


class LocalQwenPlannerBackend:
    """Real local Qwen2.5-VL generation backend for ManeuverPlan V2 JSON."""

    production_ready = True

    def __init__(
        self,
        model_path: str | Path,
        *,
        image_root: str | Path | None = None,
        max_new_tokens: int = 256,
        min_pixels: int = 64 * 28 * 28,
        max_pixels: int = 256 * 28 * 28,
    ) -> None:
        path = Path(model_path).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"local Qwen checkpoint not found: {path}")
        self.model_path = path
        self.image_root = None if image_root is None else Path(image_root).expanduser().resolve()
        self.model_id = path.name
        self.backend = TransformersQwen25VLBackend(
            path,
            max_new_tokens=max_new_tokens,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )

    def health(self) -> tuple[bool, str]:
        return True, f"local planner checkpoint loaded: {self.model_path}"

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        routing = request.get("routing")
        if not isinstance(routing, Mapping):
            raise ValueError("planner_v2 request is missing routing metadata")
        prompt = build_planner_v2_prompt(
            request, routing,
            scene_capabilities=request.get("scene_capabilities", {}),
        )
        return parse_maneuver_plan(self.backend.generate(
            prompt=prompt,
            image_path=self._resolve_image(request.get("rgb_ref")),
        ))

    def _resolve_image(self, value: Any) -> Path | None:
        if value is None:
            return None
        candidate = Path(str(value)).expanduser()
        if self.image_root is None:
            candidate = candidate.resolve()
        else:
            if candidate.is_absolute():
                raise ValueError("rgb_ref must be relative when image_root is configured")
            candidate = (self.image_root / candidate).resolve()
            try:
                candidate.relative_to(self.image_root)
            except ValueError as error:
                raise ValueError("rgb_ref escapes image_root") from error
        if not candidate.is_file():
            raise FileNotFoundError(f"Qwen RGB input not found: {candidate}")
        return candidate


class VllmQwenPlannerBackend:
    """Production Planner V2 adapter over an existing OpenAI-compatible vLLM."""

    production_ready = True
    _CHOICES = {
        "A": "KEEP_LANE", "B": "SET_SPEED", "C": "SLOW_DOWN", "D": "STOP",
        "E": "YIELD", "F": "FOLLOW", "G": "CHANGE_LANE_LEFT",
        "H": "CHANGE_LANE_RIGHT", "I": "TURN_LEFT", "J": "TURN_RIGHT",
        "K": "AVOID_OBSTACLE", "L": "RETURN_TO_LANE", "M": "PULL_OVER",
        "N": "HOLD",
    }

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        image_root: str | Path | None = None,
        api_key: str = "unused",
        timeout_s: float = 15.0,
        max_new_tokens: int = 256,
        image_max_side: int = 224,
        jpeg_quality: int = 75,
    ) -> None:
        if not base_url.strip() or not model.strip():
            raise ValueError("vLLM base URL and model must be non-empty")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("vLLM service backend requires the openai package") from error
        self._client = OpenAI(
            base_url=base_url.rstrip("/"), api_key=api_key,
            timeout=timeout_s, max_retries=0,
        )
        self.model_id = model
        self.image_root = None if image_root is None else Path(image_root).expanduser().resolve()
        # One constrained semantic token keeps the model inside the 150 ms
        # budget; strict ManeuverPlan JSON is assembled deterministically.
        self.max_new_tokens = 1
        if int(image_max_side) != 224:
            raise ValueError("planner_v2 fixes images at 224x224 (64 visual tokens)")
        self.image_max_side = 224
        self.jpeg_quality = int(jpeg_quality)

    def health(self) -> tuple[bool, str]:
        return True, f"vLLM planner endpoint configured: {self.model_id}"

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        choice_codes = self._choice_codes(request)
        prompt = self._choice_prompt(request, choice_codes=choice_codes)
        content: list[dict[str, Any]] = []
        image_path = self._resolve_image(request.get("rgb_ref"))
        if image_path is not None:
            content.append({
                "type": "image_url",
                "image_url": {"url": self._image_data_url(image_path)},
            })
        content.append({"type": "text", "text": prompt})
        response = self._client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": content}],
            temperature=0.0,
            max_tokens=self.max_new_tokens,
            extra_body={
                "structured_outputs": {"choice": choice_codes},
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError("vLLM returned no planner choices")
        raw = str(getattr(getattr(choices[0], "message", None), "content", "")).strip().upper()
        if raw not in self._CHOICES:
            raise ValueError(f"vLLM returned invalid constrained planner choice: {raw!r}")
        behavior = self._CHOICES[raw]
        routing = request.get("routing", {})
        if isinstance(routing, Mapping) and routing.get("disposition") == "CONFIRM_SAFE":
            behavior = "HOLD"
        constraints = request["constraints"]
        if constraints["must_stop"]:
            behavior = "STOP"
        allowed = set(constraints["allowed_behaviors"])
        normalized = behavior.removesuffix("_LEFT").removesuffix("_RIGHT")
        if behavior not in {"HOLD"} and behavior not in allowed and normalized not in allowed:
            raise ValueError(f"Qwen behavior {behavior} violates allowed_behaviors")
        steps = [self._step(request, behavior, index=1)]
        if behavior == "AVOID_OBSTACLE":
            steps.append(self._step(request, "RETURN_TO_LANE", index=2))
        return {
            "schema_version": "2.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "plan_id": f"plan-{request['request_id']}",
            "plan_type": "MANEUVER_SEQUENCE",
            "steps": steps,
            "replan_conditions": ["NEW_EMERGENCY_OBJECT", "ROUTE_DEVIATION"],
            "confidence": 0.90,
            "requires_confirmation": False,
            "created_at_ns": int(request["created_at_ns"]),
            "valid_until_ns": int(request["deadline_ns"]),
            "reason_code": f"QWEN_VLLM_CHOICE_{raw}_{behavior}",
            "model_id": self.model_id,
        }

    def _choice_codes(self, request: Mapping[str, Any]) -> list[str]:
        allowed = set(request["constraints"]["allowed_behaviors"])
        hint = request.get("command_hint", {})
        direction = (
            str(hint.get("direction", "")).upper()
            if isinstance(hint, Mapping) else ""
        )
        codes = [
            code
            for code, behavior in self._CHOICES.items()
            if behavior in allowed
            or behavior.removesuffix("_LEFT").removesuffix("_RIGHT") in allowed
        ]
        intent_codes = {
            "FOLLOW": {"D", "F"},
            "CHANGE_LANE": {"D", "G", "H"},
            "TURN": {"D", "I", "J"},
            "AVOID_OBSTACLE": {"D", "K"},
            "RETURN_TO_LANE": {"D", "L"},
            "PULL_OVER": {"D", "M"},
        }.get(str(hint.get("intent", "")).upper() if isinstance(hint, Mapping) else "")
        if intent_codes is not None:
            codes = [code for code in codes if code in intent_codes]
        if direction in {"LEFT", "RIGHT"}:
            opposite = "RIGHT" if direction == "LEFT" else "LEFT"
            codes = [
                code for code in codes
                if not self._CHOICES[code].endswith("_" + opposite)
            ]
        return codes or ["D"]

    def _choice_prompt(
        self,
        request: Mapping[str, Any],
        *,
        choice_codes: list[str] | None = None,
    ) -> str:
        source_text = str(request["source_text"])[:320]
        scene = request["scene_summary"]
        compact_scene = {
            key: scene[key]
            for key in ("traffic_light", "risk_level", "min_gap_m", "ttc_s")
            if key in scene
        }
        compact_targets = [
            {
                key: target[key]
                for key in ("target_id", "class", "distance_m", "relative_speed_mps", "relation")
                if key in target
            }
            for target in list(request.get("targets", ()))[:8]
            if isinstance(target, Mapping)
        ]
        lanes = request.get("scene_capabilities", {})
        compact_lanes = {
            key: lanes[key]
            for key in (
                "left_lane_exists", "right_lane_exists", "left_gap_safe",
                "right_gap_safe", "available_lanes", "return_direction",
            )
            if isinstance(lanes, Mapping) and key in lanes
        }
        compact = {
            "command": source_text,
            "command_hint": request.get("command_hint", {}),
            "visual_input": (
                "2x2 montage: front, left / right, rear"
                if "multiview" in str(request.get("rgb_ref", "")).lower()
                else "front camera"
            ),
            "scene": compact_scene,
            "targets": compact_targets,
            "constraints": request["constraints"],
            "lanes": compact_lanes,
            "route": request.get("routing", {}),
        }
        codes = list(self._CHOICES) if choice_codes is None else choice_codes
        legend = " ".join(f"{code}={self._CHOICES[code]}" for code in codes)
        return (
            "Choose exactly one safe high-level driving action code. "
            "Traffic rules and emergency safety override voice. No explanation.\n"
            + legend + "\nINPUT="
            + json.dumps(compact, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        )

    def _step(self, request: Mapping[str, Any], behavior: str, *, index: int) -> dict[str, Any]:
        hint = request.get("command_hint", {})
        capabilities = request.get("scene_capabilities", {})
        targets = request.get("targets", ())
        target_id = None
        if targets and behavior in {
            "FOLLOW", "AVOID_OBSTACLE", "YIELD", "SLOW_DOWN", "STOP",
        }:
            requested_target = (
                str(hint.get("target", "")).strip()
                if isinstance(hint, Mapping) else ""
            )
            preferred_relations = (
                {"center_ahead", "far_ahead"}
                if behavior == "FOLLOW"
                else {"center_ahead", "far_ahead", "occluded_ahead"}
            )
            candidates = [
                item for item in targets
                if str(item.get("relation", "")).lower() in preferred_relations
            ]
            explicitly_bound = [
                item for item in targets
                if requested_target and str(item.get("target_id", "")) == requested_target
            ]
            if explicitly_bound:
                candidates = explicitly_bound
            if behavior == "FOLLOW":
                typed_targets = [
                    item for item in candidates
                    if str(item.get("class", "")).lower() in {
                        "vehicle", "car", "truck", "bus", "cyclist",
                    }
                ]
                has_class_metadata = any(
                    str(item.get("class", "")).strip() for item in targets
                )
                candidates = typed_targets if has_class_metadata else candidates
            if candidates:
                target_id = candidates[0]["target_id"]
            elif behavior != "FOLLOW":
                target_id = targets[0]["target_id"]
        lane = "CURRENT"
        direction = None
        if behavior.endswith("_LEFT"):
            lane, direction = "LEFT_ADJACENT", "LEFT"
        elif behavior.endswith("_RIGHT"):
            lane, direction = "RIGHT_ADJACENT", "RIGHT"
        elif behavior.startswith("TURN_"):
            lane, direction = "ROUTE_BRANCH", behavior.rsplit("_", 1)[-1]
        elif behavior == "AVOID_OBSTACLE" and isinstance(hint, Mapping):
            hinted_direction = str(hint.get("direction", "")).upper()
            if hinted_direction in {"LEFT", "RIGHT"}:
                direction = hinted_direction
                lane = f"{hinted_direction}_ADJACENT"
        elif behavior == "PULL_OVER":
            lane = "SHOULDER"
        elif behavior == "RETURN_TO_LANE":
            lane = "CURRENT"
            direction = capabilities.get("return_direction")
        target_speed = hint.get("target_speed_mps") if isinstance(hint, Mapping) else None
        if behavior in {"STOP", "HOLD", "PULL_OVER"}:
            target_speed = 0.0
        elif behavior == "SLOW_DOWN":
            requested = math.inf if target_speed is None else float(target_speed)
            target_speed = min(
                requested,
                3.0,
                float(request["constraints"].get("max_target_speed_mps") or 3.0),
            )
        elif target_speed is None and behavior in {
            "KEEP_LANE", "FOLLOW", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT",
            "TURN_LEFT", "TURN_RIGHT", "AVOID_OBSTACLE", "RETURN_TO_LANE",
        }:
            target_speed = min(
                3.0,
                float(request["constraints"].get("max_target_speed_mps") or 3.0),
            )
        if type(target_speed) in (int, float) and not isinstance(target_speed, bool):
            maximum = request["constraints"].get("max_target_speed_mps")
            if type(maximum) in (int, float) and not isinstance(maximum, bool):
                target_speed = min(float(target_speed), float(maximum))
        completion_type = {
            "STOP": "STOPPED", "HOLD": "HOLD_FRAMES", "PULL_OVER": "STOPPED",
            "FOLLOW": "TARGET_GAP_REACHED", "AVOID_OBSTACLE": "TARGET_PASSED",
            "RETURN_TO_LANE": "LANE_CENTERED", "CHANGE_LANE_LEFT": "LANE_CENTERED",
            "CHANGE_LANE_RIGHT": "LANE_CENTERED", "TURN_LEFT": "JUNCTION_EXITED",
            "TURN_RIGHT": "JUNCTION_EXITED",
            "KEEP_LANE": "HOLD_FRAMES", "YIELD": "SPEED_BELOW",
        }.get(behavior, "SPEED_REACHED")
        timeout = 30.0 if behavior.startswith("TURN_") else 20.0 if behavior in {
            "AVOID_OBSTACLE", "RETURN_TO_LANE",
        } else 12.0 if behavior.startswith("CHANGE_LANE_") else 8.0
        completion_value = target_speed
        if completion_type == "TARGET_GAP_REACHED":
            completion_value = 2.0
        elif completion_type == "SPEED_BELOW":
            completion_value = target_speed if target_speed is not None else 2.0
        elif completion_type in {"HOLD_FRAMES", "LANE_CENTERED", "JUNCTION_EXITED", "TARGET_PASSED"}:
            completion_value = None
        return {
            "step_id": f"step-{index}",
            "behavior": behavior,
            "target": {
                "target_id": target_id,
                "target_lane": lane,
                "target_speed_mps": target_speed,
                "time_gap_s": 2.0 if behavior == "FOLLOW" else None,
                "route_direction": direction,
            },
            "preconditions": ["PERCEPTION_FRESH"],
            "completion": {
                "type": completion_type,
                "value": 0.2 if completion_type == "STOPPED" else completion_value,
                "lane": lane if completion_type == "LANE_CENTERED" else None,
                "hold_frames": 3,
            },
            "timeout_s": timeout,
            "on_failure": "SAFE_STOP",
        }

    def _resolve_image(self, value: Any) -> Path | None:
        if value is None:
            return None
        candidate = Path(str(value)).expanduser()
        if self.image_root is None:
            candidate = candidate.resolve()
        else:
            if candidate.is_absolute():
                raise ValueError("rgb_ref must be relative when image_root is configured")
            candidate = (self.image_root / candidate).resolve()
            candidate.relative_to(self.image_root)
        if not candidate.is_file():
            raise FileNotFoundError(f"Qwen RGB input not found: {candidate}")
        return candidate

    def _image_data_url(self, path: Path) -> str:
        try:
            from PIL import Image, ImageOps
        except ImportError as error:
            raise RuntimeError("vLLM image encoding requires Pillow") from error
        with Image.open(path) as image:
            if image.size == (self.image_max_side, self.image_max_side) and image.format == "JPEG":
                encoded = path.read_bytes()
                return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")
            image = ImageOps.pad(
                image.convert("RGB"),
                (self.image_max_side, self.image_max_side),
                method=Image.Resampling.LANCZOS,
                color=(0, 0, 0),
            )
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=self.jpeg_quality, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()


class LocalQwenBackend:
    """Adapter from the repository's real local Qwen2.5-VL implementation."""

    production_ready = True

    def __init__(
        self,
        model_path: str | Path,
        *,
        image_root: str | Path | None = None,
        max_new_tokens: int = 48,
        min_pixels: int = 64 * 28 * 28,
        max_pixels: int = 256 * 28 * 28,
    ) -> None:
        path = Path(model_path).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"local Qwen checkpoint not found: {path}")
        self.model_path = path
        self.model_id = path.name
        self.adapter = StrictQwenVLAdapter.from_local_checkpoint(
            path,
            image_root=image_root,
            max_new_tokens=max_new_tokens,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )

    def health(self) -> tuple[bool, str]:
        return True, f"local checkpoint loaded: {self.model_path}"

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        targets = [
            {
                "track_id": item["target_id"],
                "class": item["class"],
                "relation": item["relation"],
                "distance_m": item["distance_m"],
                "relative_speed_mps": item.get("relative_speed_mps"),
                "confidence": item["confidence"],
            }
            for item in request["targets"]
        ]
        context = QwenInputContext(
            request_id=request["request_id"],
            frame=request["scene_summary"]["frame_id"],
            sim_time_s=request["scene_summary"]["sim_time_s"],
            voice_command=request["source_text"],
            rgb_ref=request.get("rgb_ref"),
            scene_state=dict(request["scene_summary"]),
            perception={
                "traffic_light": request["scene_summary"]["traffic_light"],
                "detected_objects": targets,
            },
            safety_state=dict(request["constraints"]),
        )
        decision = self.adapter(context)
        return self._to_plan(request, decision)

    def _to_plan(self, request: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
        action = str(decision["action"]).upper()
        intent, behavior = {
            "START": ("KEEP_LANE", "KEEP_LANE"),
            "KEEP_LANE": ("KEEP_LANE", "KEEP_LANE"),
            "SET_SPEED": ("SET_SPEED", "SET_SPEED"),
            "SLOW_DOWN": ("SLOW_DOWN", "SLOW_DOWN"),
            "STOP": ("STOP", "STOP"),
            "EMERGENCY_STOP": ("STOP", "STOP"),
        }.get(action, ("REJECT", "HOLD"))
        parameters: dict[str, float] = {}
        if decision.get("target_speed_mps") is not None:
            parameters["target_speed_mps"] = float(decision["target_speed_mps"])
        elif action == "SLOW_DOWN":
            # The frozen strict Qwen boundary permits SLOW_DOWN without a
            # numeric speed.  D requires a concrete deterministic target, so B
            # supplies the documented conservative default rather than asking
            # the model for a low-level control value.
            maximum = request["constraints"].get("max_target_speed_mps")
            parameters["target_speed_mps"] = min(
                2.0, 2.0 if maximum is None else float(maximum),
            )
        now = time.monotonic_ns()
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": intent,
            "target_id": decision.get("target_track_id"),
            "behavior": behavior,
            "parameters": parameters,
            "confidence": decision["confidence"],
            "reason_code": "QWEN_VL_" + action,
            "created_at_ns": now,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": decision["requires_confirmation"],
            "model_id": self.model_id,
        }


def _planner_step(
    step_id: str,
    behavior: str,
    *,
    speed: float | None,
    target_id: str | None = None,
    lane: str | None = "CURRENT",
    time_gap_s: float | None = None,
    route_direction: str | None = None,
    preconditions: tuple[str, ...] = ("PERCEPTION_FRESH", "NO_EMERGENCY_RISK"),
    completion: str = "SPEED_BELOW",
    completion_value: float | None = 3.3,
    timeout_s: float = 5.0,
    failure: str = "SAFE_STOP",
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "behavior": behavior,
        "target": {
            "target_id": target_id,
            "target_lane": lane,
            "target_speed_mps": speed,
            "time_gap_s": time_gap_s,
            "route_direction": route_direction,
        },
        "preconditions": list(preconditions),
        "completion": {
            "type": completion,
            "value": completion_value,
            "lane": lane if completion == "LANE_CENTERED" else None,
            "hold_frames": 5,
        },
        "timeout_s": timeout_s,
        "on_failure": failure,
    }


class QwenDecisionService:
    def __init__(
        self,
        backend: DecisionBackend,
        *,
        config: QwenServiceConfig | None = None,
        registry: InterfaceRegistry | None = None,
        qwen_mode: str = "atomic_v1",
        clock_ns: Any = time.monotonic_ns,
    ) -> None:
        if not callable(getattr(backend, "infer", None)) or not callable(getattr(backend, "health", None)):
            raise TypeError("backend must provide infer() and health()")
        self.backend = backend
        if qwen_mode not in {"atomic_v1", "planner_v2"}:
            raise ValueError("qwen_mode must be 'atomic_v1' or 'planner_v2'")
        self.qwen_mode = qwen_mode
        self.config = config or QwenServiceConfig()
        self.registry = registry or InterfaceRegistry()
        self.plan_validator = PlanValidator(
            registry=self.registry,
            clock_ns=clock_ns,
        )
        self._clock_ns = clock_ns
        self._slots = BoundedSemaphore(self.config.max_concurrency)
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_concurrency,
            thread_name_prefix="qwen-infer",
        )
        self._lock = Lock()
        self._active = 0
        self._counts = {
            "requests": 0,
            "success": 0,
            "invalid": 0,
            "expired": 0,
            "busy": 0,
            "timeouts": 0,
            "backend_errors": 0,
        }
        self._latencies_ms: list[float] = []

    def infer(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request_id = str(payload.get("request_id", "")) if isinstance(payload, Mapping) else None
        with self._lock:
            self._counts["requests"] += 1
        try:
            request = self.registry.validate("model_request", payload)
        except InterfaceValidationError as error:
            self._increment("invalid")
            raise ServiceFailure(400, "INVALID_REQUEST", str(error), request_id=request_id) from error
        request_id = request["request_id"]
        now = self._clock_ns()
        if request["deadline_ns"] <= request["created_at_ns"]:
            self._increment("invalid")
            raise ServiceFailure(400, "INVALID_DEADLINE", "deadline must follow creation", request_id=request_id)
        if now >= request["deadline_ns"]:
            self._increment("expired")
            raise ServiceFailure(408, "REQUEST_EXPIRED", "request deadline elapsed", request_id=request_id)
        healthy, reason = self.backend.health()
        if not healthy:
            self._increment("backend_errors")
            raise ServiceFailure(503, "MODEL_UNAVAILABLE", reason, request_id=request_id)
        if not self._slots.acquire(blocking=False):
            self._increment("busy")
            raise ServiceFailure(429, "CONCURRENCY_LIMIT", "Qwen service is busy", request_id=request_id)

        with self._lock:
            self._active += 1
        started = time.perf_counter_ns()
        future = self._executor.submit(self.backend.infer, request)
        future.add_done_callback(self._release_slot)
        deadline_ms = (request["deadline_ns"] - now) / 1e6
        timeout_s = min(float(self.config.timeout_ms), deadline_ms) / 1000.0
        try:
            raw = future.result(timeout=timeout_s)
        except FutureTimeout as error:
            self._increment("timeouts")
            raise ServiceFailure(504, "MODEL_TIMEOUT", "Qwen inference exceeded deadline", request_id=request_id) from error
        except (QwenPlanParseError, PlanValidationError) as error:
            self._increment("invalid")
            code = error.reason_code if isinstance(error, PlanValidationError) else "INVALID_MODEL_OUTPUT"
            raise ServiceFailure(502, code, str(error), request_id=request_id) from error
        except Exception as error:
            self._increment("backend_errors")
            raise ServiceFailure(500, "MODEL_ERROR", f"{type(error).__name__}: {error}", request_id=request_id) from error
        elapsed_ms = (time.perf_counter_ns() - started) / 1e6
        validation_now = self._clock_ns()
        try:
            if self.qwen_mode == "planner_v2":
                plan = self.plan_validator.validate(
                    raw,
                    scene=_planner_scene(request),
                    expected_request_id=request_id,
                    expected_command_id=request["command_id"],
                    now_ns=validation_now,
                    allow_confirmation=True,
                )
            else:
                plan = self.registry.validate("decision_plan", raw)
        except (InterfaceValidationError, PlanValidationError) as error:
            self._increment("invalid")
            code = error.reason_code if isinstance(error, PlanValidationError) else "INVALID_MODEL_OUTPUT"
            raise ServiceFailure(502, code, str(error), request_id=request_id) from error
        if plan["request_id"] != request_id or plan["command_id"] != request["command_id"]:
            self._increment("invalid")
            raise ServiceFailure(502, "MODEL_ID_MISMATCH", "model output IDs do not match request", request_id=request_id)
        if plan["valid_until_ns"] > request["deadline_ns"] or plan["created_at_ns"] >= plan["valid_until_ns"]:
            self._increment("invalid")
            raise ServiceFailure(502, "INVALID_MODEL_VALIDITY", "model output validity exceeds request", request_id=request_id)
        if any(name in plan for name in ("throttle", "brake", "steer")):
            self._increment("invalid")
            raise ServiceFailure(502, "LOW_LEVEL_OUTPUT_FORBIDDEN", "model output contains vehicle control", request_id=request_id)
        with self._lock:
            self._counts["success"] += 1
            self._latencies_ms.append(elapsed_ms)
        return plan

    def health(self) -> dict[str, Any]:
        healthy, reason = self.backend.health()
        with self._lock:
            active = self._active
        return {
            "schema_version": "1.0",
            "status": "READY" if healthy else "DEGRADED",
            "model_id": self.backend.model_id,
            "production_ready": bool(self.backend.production_ready and healthy),
            "reason": reason,
            "active_requests": active,
            "max_concurrency": self.config.max_concurrency,
            "timeout_ms": self.config.timeout_ms,
            "qwen_mode": self.qwen_mode,
            "gpu": _gpu_metrics(),
        }

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            counts = dict(self._counts)
            active = self._active
            values = list(self._latencies_ms)
        return {
            "schema_version": "1.0",
            "model_id": self.backend.model_id,
            "production_ready": bool(self.backend.production_ready),
            "qwen_mode": self.qwen_mode,
            "active_requests": active,
            "max_concurrency": self.config.max_concurrency,
            "counts": counts,
            "latency_ms": {
                "count": len(values),
                "mean": statistics.fmean(values) if values else None,
                "p95": _percentile(values, 0.95),
                "p99": _percentile(values, 0.99),
                "max": max(values) if values else None,
            },
            "gpu": _gpu_metrics(),
        }

    def close(self, *, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _release_slot(self, _future: Future[Any]) -> None:
        with self._lock:
            self._active -= 1
        self._slots.release()

    def _increment(self, name: str) -> None:
        with self._lock:
            self._counts[name] += 1


def _gpu_metrics() -> dict[str, Any]:
    try:
        import torch
        if not torch.cuda.is_available():
            return {"available": False, "reason": "torch.cuda.is_available() is false"}
        device = torch.cuda.current_device()
        free, total = torch.cuda.mem_get_info(device)
        return {
            "available": True,
            "device_index": device,
            "device_name": torch.cuda.get_device_name(device),
            "memory_allocated_bytes": int(torch.cuda.memory_allocated(device)),
            "memory_reserved_bytes": int(torch.cuda.memory_reserved(device)),
            "memory_free_bytes": int(free),
            "memory_total_bytes": int(total),
        }
    except Exception as error:  # pragma: no cover - driver dependent
        return {"available": False, "reason": f"{type(error).__name__}: {error}"}


def _planner_scene(request: Mapping[str, Any]) -> dict[str, Any]:
    summary = request["scene_summary"]
    capabilities = request.get("scene_capabilities", {})
    return {
        "objects": [
            {"track_id": target["target_id"]}
            for target in request["targets"]
        ],
        "traffic_light": summary["traffic_light"],
        "distance_to_stop_line_m": (
            1.0 if request["constraints"]["must_stop"]
            and summary["traffic_light"] in {"RED", "YELLOW"} else None
        ),
        "risk_level": summary["risk_level"],
        "speed_limit_mps": request["constraints"].get("speed_limit_mps"),
        "must_stop": request["constraints"]["must_stop"],
        "stale": False,
        "sync": {"within_tolerance": True},
        **(dict(capabilities) if isinstance(capabilities, Mapping) else {}),
    }


__all__ = [
    "DecisionBackend",
    "DeterministicPlannerV2Backend",
    "DeterministicTestBackend",
    "LocalQwenBackend",
    "LocalQwenPlannerBackend",
    "QwenDecisionService",
    "QwenServiceConfig",
    "ServiceFailure",
    "UnavailableBackend",
    "VllmQwenPlannerBackend",
]
