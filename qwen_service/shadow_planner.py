"""Offline-only structured Qwen planning; intentionally no service infer() API.

The model owns semantic steps. Only transport IDs/timestamps are assembled by
code. This module never dispatches a command or silently repairs a bad plan.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from typing import Any, Mapping

from runtime.interface_registry import InterfaceRegistry
from runtime.plan_compiler import PlanCompiler
from runtime.plan_validator import PlanValidator
from .service import VllmQwenPlannerBackend, _planner_scene


ACTION_COMPLETIONS = {
    "KEEP_LANE": ("HOLD_FRAMES", "SPEED_REACHED"),
    "SET_SPEED": ("SPEED_REACHED",),
    "SLOW_DOWN": ("SPEED_BELOW", "SPEED_REACHED", "TARGET_PASSED"),
    "STOP": ("STOPPED", "SPEED_BELOW"), "YIELD": ("HOLD_FRAMES",),
    "FOLLOW": ("TARGET_GAP_REACHED", "HOLD_FRAMES"),
    "TURN_LEFT": ("JUNCTION_EXITED",), "TURN_RIGHT": ("JUNCTION_EXITED",),
    "CHANGE_LANE_LEFT": ("LANE_CENTERED",), "CHANGE_LANE_RIGHT": ("LANE_CENTERED",),
    "AVOID_OBSTACLE": ("TARGET_PASSED",), "RETURN_TO_LANE": ("LANE_CENTERED",),
    "PULL_OVER": ("STOPPED", "LANE_CENTERED"), "HOLD": ("HOLD_FRAMES", "STOPPED"),
}


def semantic_output_schema() -> dict[str, Any]:
    schema = json.loads((InterfaceRegistry().root / "maneuver_plan.schema.json").read_text(encoding="utf-8"))
    fields = ("steps", "replan_conditions", "confidence", "requires_confirmation", "reason_code")
    return {
        "type": "object", "additionalProperties": False,
        "required": list(fields),
        "properties": {name: schema["properties"][name] for name in fields},
        "$defs": schema["$defs"],
    }


def generation_schema(schema: Any) -> Any:
    """Older deployed grammar engines lack uniqueItems; post-validation does not.

    This is ONLY a transport grammar projection, never the acceptance schema.
    Do not drop semantic constraints from semantic_output_schema().
    """
    if isinstance(schema, dict):
        return {key: generation_schema(value) for key, value in schema.items() if key != "uniqueItems"}
    if isinstance(schema, list):
        return [generation_schema(value) for value in schema]
    return schema


def request_output_schema(request: Mapping[str, Any]) -> dict[str, Any]:
    """Constrain slots to measured input, not to a desired task answer."""
    schema = semantic_output_schema()
    target = schema["$defs"]["step"]["properties"]["target"]["properties"]
    target["target_id"]["enum"] = [None, *dict.fromkeys(t["target_id"] for t in request["targets"])]
    constraints = request["constraints"]
    limits = [13.8888888889]
    for name in ("speed_limit_mps", "max_target_speed_mps"):
        if constraints.get(name) is not None:
            limits.append(float(constraints[name]))
    target["target_speed_mps"]["maximum"] = min(limits)
    capabilities = request.get("scene_capabilities", {})
    lanes = capabilities.get("available_lanes", ["CURRENT"])
    target["target_lane"]["enum"] = [None, *dict.fromkeys([*lanes, "ROUTE_BRANCH"])]
    allowed = set(constraints["allowed_behaviors"])
    behaviors = schema["$defs"]["step"]["properties"]["behavior"]["enum"]
    schema["$defs"]["step"]["properties"]["behavior"]["enum"] = [
        b for b in behaviors if b == "HOLD" or b in allowed
        or b.removesuffix("_LEFT").removesuffix("_RIGHT") in allowed
    ]
    return schema


def flag_set_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """An unordered unique enum set becomes an object with optional true keys.

    Avoid unsupported uniqueItems without deleting or repairing duplicates after
    generation. This is a reversible representation, not a semantic rule engine.
    """
    result = copy.deepcopy(dict(schema))
    for field in (result["properties"]["replan_conditions"],
                  result["$defs"]["step"]["properties"]["preconditions"]):
        names = field["items"]["enum"]
        field.clear()
        field.update(type="object", additionalProperties=False,
                     properties={name: {"const": True} for name in names})
    return result


def decode_flag_sets(semantic: Mapping[str, Any]) -> dict[str, Any]:
    """Lossless set representation conversion, after strict wire validation."""
    result = copy.deepcopy(dict(semantic))
    result["replan_conditions"] = list(result["replan_conditions"])
    for step in result["steps"]:
        step["preconditions"] = list(step["preconditions"])
    return result


def action_completion_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Encode generic action/predicate compatibility, not task step order."""
    result = copy.deepcopy(dict(schema))
    step = result["$defs"]["step"]
    branches = []
    for behavior in step["properties"]["behavior"]["enum"]:
        branch = copy.deepcopy(step)
        branch["properties"]["behavior"] = {"const": behavior}
        branch["properties"]["completion"]["properties"]["type"]["enum"] = list(ACTION_COMPLETIONS[behavior])
        branches.append(branch)
    result["$defs"]["step"] = {"anyOf": branches}
    return result


def validate_action_completions(semantic: Mapping[str, Any]) -> None:
    for index, step in enumerate(semantic["steps"]):
        if step["completion"]["type"] not in ACTION_COMPLETIONS[step["behavior"]]:
            raise ValueError(f"steps[{index}] {step['behavior']} cannot complete with {step['completion']['type']}")


def shadow_model_input(request: Mapping[str, Any]) -> dict[str, Any]:
    """Remove NLU answers, not hard safety facts. Never mutate the source.

    Upstream allowed_behaviors mixes semantic policy with capability constraints;
    do NOT widen it without that distinction being made upstream first.
    """
    payload = copy.deepcopy(dict(request))
    payload.pop("command_hint", None)
    payload.pop("routing", None)
    capabilities = payload.get("scene_capabilities", {})
    # Scenario-owned actor names/groups are execution evidence, not RGB evidence.
    capabilities.pop("grounded_target_ids", None)
    capabilities.pop("completion_target_groups", None)
    return payload


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate model JSON key: {key}")
        result[key] = value
    return result


class StructuredShadowPlanner:
    """Transport composition prevents accidental use as a DecisionBackend."""

    def __init__(self, transport: VllmQwenPlannerBackend, *, max_tokens: int = 2048,
                 wire_format: str = "full_json") -> None:
        if type(max_tokens) is not int or not 256 <= max_tokens <= 8192:
            raise ValueError("shadow max_tokens must be an integer in [256, 8192]")
        self.transport = transport
        self.max_tokens = max_tokens
        if wire_format not in {"full_json", "flag_sets_v1"}:
            raise ValueError("wire_format must be full_json or flag_sets_v1")
        self.wire_format = wire_format

    def generate(self, request: Mapping[str, Any], *, vision: str = "original") -> dict[str, Any]:
        if vision not in {"original", "no_rgb"}:
            raise ValueError("vision must be original or no_rgb")
        original = InterfaceRegistry().validate("model_request", request)
        payload = shadow_model_input(original)
        payload.pop("rgb_ref", None)
        schema = request_output_schema(payload)
        wire_base = flag_set_schema(schema) if self.wire_format == "flag_sets_v1" else schema
        wire_schema = action_completion_schema(wire_base)
        prompt = (
            "Produce a high-level driving task plan from the original instruction and observations. "
            "Return ONLY JSON matching the supplied schema, with 1 to 4 semantic steps. "
            "Infer the order, targets and conditional completion from the instruction; do not omit "
            "yielding, return or resumption when requested. Use existing target IDs only. "
            "Images are context, NOT proof that an opaque target ID corresponds to a visual object. "
            "If target grounding or the instruction is uncertain, request confirmation and HOLD/STOP. "
            "Obey constraints.allowed_behaviors (LEFT/RIGHT variants of TURN/CHANGE_LANE are permitted). "
            "HOLD is available for confirmation. Obey must_stop, red lights and speed limits; "
            "do not plan later propulsion through a currently mandatory stop. "
            "Use observable completion predicates, never throttle, brake, steer or waypoints. "
            "Explicitly requested speeds/directions must be respected within safety constraints. "
            "Input distances/speeds are metres and metres per second. "
            "Use only available lanes; missing safety facts are unknown, not safe. "
            "Model confidence is uncalibrated self-report, not a probability of safe execution.\nINPUT="
            + json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        )
        if self.wire_format == "flag_sets_v1":
            prompt = (
                "Wire representation: preconditions and replan_conditions are OBJECT SETS, "
                'for example {"PERCEPTION_FRESH":true}, not arrays. '
                "Include a key only when required; values must be true. Empty set is {}. "
                "This changes representation only; do not omit task steps.\n"
            ) + prompt
        content: list[dict[str, Any]] = []
        encoded_sha = None
        if vision == "original":
            image_path = self.transport._resolve_image(original.get("rgb_ref"))
            if image_path is None:
                raise ValueError("original vision requires an existing rgb_ref; no silent text-only fallback")
            image_url = self.transport._image_data_url(image_path)
            encoded_sha = hashlib.sha256(base64.b64decode(image_url.split(",", 1)[1])).hexdigest()
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        content.append({"type": "text", "text": prompt})
        response = self.transport._client.chat.completions.create(
            model=self.transport.model_id, messages=[{"role": "user", "content": content}],
            temperature=0.0, max_tokens=self.max_tokens,
            extra_body={"structured_outputs": {"json": generation_schema(wire_schema)},
                        "chat_template_kwargs": {"enable_thinking": False}},
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise ValueError("shadow model returned no choices")
        choice = choices[0]
        raw = getattr(getattr(choice, "message", None), "content", None)
        report: dict[str, Any] = {
            "scope": "OFFLINE_SHADOW_NOT_EXECUTABLE_NOT_GATE",
            "request_id": original["request_id"], "command_id": original["command_id"],
            "model_id": self.transport.model_id, "vision": vision,
            "image_sent": encoded_sha is not None, "encoded_image_sha256": encoded_sha,
            "upstream_allowed_behaviors": original["constraints"]["allowed_behaviors"],
            "constraint_policy": "PRESERVE_UPSTREAM_NO_NLU_HINT",
            "raw_model_response": raw, "finish_reason": getattr(choice, "finish_reason", None),
            "validation": "REJECTED", "semantic_step_source": "MODEL_JSON",
            "validation_layers": {"wire_schema": False, "semantic_schema": False,
                                  "action_completion": False, "plan_validator": False, "compiler": False},
            "wire_format": self.wire_format,
            "task_accuracy": "NOT_MEASURED",
            "visual_grounding": "UNVERIFIED_NO_IMAGE_TRACK_ASSOCIATION_IN_MODEL_REQUEST_V1",
            "generic_range_targets_only": bool(payload["targets"]) and all(
                t["class"] in {"obstacle", "unknown"} for t in payload["targets"]
            ),
            "wire_schema_sha256": hashlib.sha256(json.dumps(wire_schema, sort_keys=True).encode()).hexdigest(),
            "model_input_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
        import jsonschema
        try:
            if report["finish_reason"] != "stop":
                raise ValueError("shadow generation incomplete or finish reason unavailable")
            if not isinstance(raw, str):
                raise ValueError("shadow content must be a JSON string")
            semantic = json.loads(raw, object_pairs_hook=_unique_object)
            # Report actionable slot errors before an anyOf wrapper obscures them.
            wire_errors = list(jsonschema.Draft202012Validator(wire_base).iter_errors(semantic))
            if not wire_errors:
                wire_errors = list(jsonschema.Draft202012Validator(wire_schema).iter_errors(semantic))
            if wire_errors:
                report["contract_errors"] = [
                    {"path": ".".join(map(str, e.absolute_path)), "message": e.message}
                    for e in wire_errors[:32]
                ]
                report["contract_error_count"] = len(wire_errors)
                raise wire_errors[0]
            report["validation_layers"]["wire_schema"] = True
            if self.wire_format == "flag_sets_v1":
                semantic = decode_flag_sets(semantic)
            jsonschema.Draft202012Validator(schema).validate(semantic)
            report["validation_layers"]["semantic_schema"] = True
            validate_action_completions(semantic)
            report["validation_layers"]["action_completion"] = True
            # Transport metadata only: never overwrite semantic fields or append steps.
            plan = {
                **semantic, "schema_version": "2.0", "request_id": original["request_id"],
                "command_id": original["command_id"], "plan_id": f"shadow-{original['request_id'][:121]}",
                "plan_type": "MANEUVER_SEQUENCE", "created_at_ns": original["created_at_ns"],
                "valid_until_ns": original["deadline_ns"], "model_id": self.transport.model_id,
            }
            report["model_plan"] = plan
            allowed = set(original["constraints"]["allowed_behaviors"])
            for step in plan["steps"]:
                behavior = step["behavior"]
                normalized = behavior.removesuffix("_LEFT").removesuffix("_RIGHT")
                if behavior != "HOLD" and behavior not in allowed and normalized not in allowed:
                    raise ValueError(f"model behavior not allowed by upstream constraint: {behavior}")
            # Replay clocks belong to the captured run, not this machine's uptime.
            # Only validate at capture time; this does NOT authorize current execution.
            scene = _planner_scene(payload)
            validated = PlanValidator().validate(
                plan, scene=scene, expected_request_id=original["request_id"],
                expected_command_id=original["command_id"], now_ns=original["created_at_ns"],
                allow_confirmation=True,
            )
            report["validation_layers"]["plan_validator"] = True
            report["compiled_preview"] = PlanCompiler().compile(validated, scene=scene).to_dict()
            report["validation_layers"]["compiler"] = True
            report["validation"] = "CONTRACT_PASS_ONLY"
        except (ValueError, TypeError, jsonschema.ValidationError) as error:
            report["rejection_reason"] = str(error)
            report["rejection_type"] = type(error).__name__
        return report
