"""Strict Qwen Planner V2 prompt, JSON parser, validation and compilation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from typing import Any

from runtime.complexity_router import QwenRoutingDecision
from runtime.plan_compiler import CompiledManeuverPlan, PlanCompiler
from runtime.plan_validator import PlanValidator


PLANNER_V2_SYSTEM_PROMPT = """\
You are a high-level autonomous-driving maneuver planner. Return exactly one
JSON object matching ManeuverPlan schema_version 2.0. Do not use Markdown.

Safety contract:
- Use only these behaviors: KEEP_LANE, SET_SPEED, SLOW_DOWN, STOP, YIELD,
  FOLLOW, TURN_LEFT, TURN_RIGHT, CHANGE_LANE_LEFT, CHANGE_LANE_RIGHT,
  AVOID_OBSTACLE, RETURN_TO_LANE, PULL_OVER, HOLD.
- Return 1 to 4 semantic steps. Every step must contain target,
  preconditions, completion, timeout_s, and on_failure.
- Copy request_id, command_id, and visible target IDs exactly from input.
- Never invent a target ID or a lane. If grounding is uncertain, set
  requires_confirmation=true and prefer HOLD/STOP.
- Traffic lights, must_stop, emergency risk, and speed limits override the
  user's requested progress.
- Never output throttle, brake, steer, steering angle, wheel angle, torque,
  raw waypoints, code, or a CARLA actor handle.
- Completion is deterministic sensor state, never another model opinion.
- Allow at least 30 seconds for a turn, 12 seconds for an ordinary lane
  change, and 20 seconds for each avoidance/return step; shorter deadlines
  are not reliable for topology-safe urban execution.
"""


class QwenPlanParseError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlannerV2Result:
    raw_summary: str
    plan: Mapping[str, Any]
    compiled: CompiledManeuverPlan


def build_planner_v2_prompt(
    request: Mapping[str, Any],
    routing: QwenRoutingDecision | Mapping[str, Any],
    *,
    scene_capabilities: Mapping[str, Any] | None = None,
) -> str:
    if not isinstance(request, Mapping):
        raise TypeError("request must be a mapping")
    if isinstance(routing, QwenRoutingDecision):
        route_payload = {
            "disposition": routing.disposition,
            "score": routing.score,
            "reasons": list(routing.reasons),
            "safe_wait_behavior": routing.safe_wait_behavior,
            "features": routing.features.to_dict(),
        }
    elif isinstance(routing, Mapping):
        route_payload = dict(routing)
    else:
        raise TypeError("routing must be QwenRoutingDecision or mapping")
    payload = {
        "task": "produce_maneuver_plan_v2",
        "request": dict(request),
        "routing": route_payload,
        "scene_capabilities": dict(scene_capabilities or {}),
        "output_contract": {
            "schema_version": "2.0",
            "plan_type": "MANEUVER_SEQUENCE",
            "maximum_steps": 4,
            "strict_json_only": True,
        },
    }
    return PLANNER_V2_SYSTEM_PROMPT + "\nINPUT_JSON:\n" + json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )


def parse_maneuver_plan(raw: str | bytes | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        # Round-trip detaches backend-owned mutation and rejects non-JSON data.
        try:
            return json.loads(json.dumps(dict(raw), ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError) as error:
            raise QwenPlanParseError(f"MODEL_OUTPUT_NOT_STRICT_JSON: {error}") from error
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise QwenPlanParseError("MODEL_OUTPUT_NOT_UTF8") from error
    if not isinstance(raw, str):
        raise QwenPlanParseError("MODEL_OUTPUT_MUST_BE_JSON_OBJECT")
    text = raw.strip()
    if not text or text.startswith("```") or not (text.startswith("{") and text.endswith("}")):
        raise QwenPlanParseError("MODEL_OUTPUT_MUST_BE_BARE_JSON_OBJECT")
    decoder = json.JSONDecoder()
    try:
        payload, end = decoder.raw_decode(text)
    except json.JSONDecodeError as error:
        raise QwenPlanParseError(f"MODEL_OUTPUT_INVALID_JSON: {error.msg}") from error
    if text[end:].strip():
        raise QwenPlanParseError("MODEL_OUTPUT_HAS_TRAILING_CONTENT")
    if not isinstance(payload, dict):
        raise QwenPlanParseError("MODEL_OUTPUT_MUST_BE_JSON_OBJECT")
    return payload


class QwenPlannerV2Adapter:
    """Turn one backend JSON response into a validated, compiled plan."""

    def __init__(
        self,
        generate: Callable[[str, str | None], str | bytes | Mapping[str, Any]],
        *,
        validator: PlanValidator | None = None,
        compiler: PlanCompiler | None = None,
    ) -> None:
        if not callable(generate):
            raise TypeError("generate must be callable")
        self.generate = generate
        self.validator = validator or PlanValidator()
        self.compiler = compiler or PlanCompiler()
        self.last_raw_summary: str | None = None
        self.last_error: str | None = None

    def infer(
        self,
        request: Mapping[str, Any],
        *,
        routing: QwenRoutingDecision | Mapping[str, Any],
        scene: Mapping[str, Any],
    ) -> PlannerV2Result:
        prompt = build_planner_v2_prompt(request, routing, scene_capabilities=scene)
        try:
            raw = self.generate(prompt, request.get("rgb_ref"))
            self.last_raw_summary = _summary(raw)
            parsed = parse_maneuver_plan(raw)
            plan = self.validator.validate(
                parsed,
                scene=scene,
                expected_request_id=str(request["request_id"]),
                expected_command_id=str(request["command_id"]),
                now_ns=int(request["created_at_ns"]),
            )
            compiled = self.compiler.compile(plan, scene=scene)
        except Exception as error:
            self.last_error = f"{type(error).__name__}: {error}"
            raise
        self.last_error = None
        return PlannerV2Result(self.last_raw_summary, plan, compiled)


def _summary(raw: Any) -> str:
    if isinstance(raw, Mapping):
        text = json.dumps(dict(raw), ensure_ascii=False, sort_keys=True, allow_nan=False)
    elif isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = str(raw)
    text = " ".join(text.split())
    return text if len(text) <= 512 else text[:509] + "..."


__all__ = [
    "PLANNER_V2_SYSTEM_PROMPT",
    "PlannerV2Result",
    "QwenPlanParseError",
    "QwenPlannerV2Adapter",
    "build_planner_v2_prompt",
    "parse_maneuver_plan",
]
