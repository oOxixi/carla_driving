"""Decode Student tensors into a strict, grounded ManeuverPlan V2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any

import torch
from torch import Tensor

from challenge.student.contract import (
    BEHAVIORS,
    COMPLETION_TYPES,
    ON_FAILURE,
    OUTPUT_NAMES,
    REPLAN_CONDITIONS,
    TARGET_LANES,
)
from challenge.student.preprocess import _expanded_allowed_behaviors


_IMPLICIT_CURRENT_BEHAVIORS = frozenset({
    "FOLLOW",
    "HOLD",
    "KEEP_LANE",
    "SET_SPEED",
    "SLOW_DOWN",
    "STOP",
    "YIELD",
})
_POINTER_GROUNDED_BEHAVIORS = frozenset({
    "FOLLOW",
    "AVOID_OBSTACLE",
    "SLOW_DOWN",
})


class StudentPlanAdapter:
    def __init__(self, *, model_id: str = "student-v0-r3-fp32") -> None:
        self.model_id = model_id

    def decode(
        self,
        request: Mapping[str, Any],
        outputs: Mapping[str, Tensor],
    ) -> dict[str, Any]:
        missing = [name for name in OUTPUT_NAMES if name not in outputs]
        extra = sorted(set(outputs).difference(OUTPUT_NAMES))
        if missing or extra:
            raise ValueError(
                f"Student V0 output dict mismatch: missing={missing}, extra={extra}"
            )
        (
            plan_length_logits,
            behavior_logits,
            target_pointer_logits,
            target_lane_logits,
            target_speed_mps,
            completion_logits,
            failure_logits,
            confidence_value,
            confirmation_logits,
            replan_logits,
        ) = (outputs[name] for name in OUTPUT_NAMES)
        maximum_steps = int(behavior_logits.shape[1])
        plan_length = int(plan_length_logits[0].argmax().item()) + 1
        plan_length = max(1, min(plan_length, maximum_steps))
        feasible = _feasible_behaviors(request, _expanded_allowed_behaviors(request))
        forced_confirmation = not feasible
        allowed = feasible or {"HOLD"}
        must_stop = bool(request["constraints"]["must_stop"])
        if must_stop:
            plan_length = 1

        steps: list[dict[str, Any]] = []
        for index in range(plan_length):
            behavior = "STOP" if must_stop else _best_allowed(
                behavior_logits[0, index], BEHAVIORS, allowed,
            )
            pointer_scores = target_pointer_logits[0, index]
            if behavior in {"FOLLOW", "AVOID_OBSTACLE"} and request["targets"]:
                pointer = int(pointer_scores[: min(len(request["targets"]), 8)].argmax().item())
            else:
                pointer = int(pointer_scores.argmax().item())
            target = request["targets"][pointer] if pointer < len(request["targets"]) else None
            if behavior in {"FOLLOW", "AVOID_OBSTACLE"} and target is None:
                behavior = "KEEP_LANE" if "KEEP_LANE" in allowed else "STOP"
            lane = TARGET_LANES[int(target_lane_logits[0, index].argmax().item())]
            speed = _bounded_speed(float(target_speed_mps[0, index].item()), request)
            completion = COMPLETION_TYPES[int(completion_logits[0, index].argmax().item())]
            completion = _compatible_completion(behavior, completion)
            on_failure = ON_FAILURE[int(failure_logits[0, index].argmax().item())]
            steps.append(_step(
                index=index,
                behavior=behavior,
                target=target,
                predicted_lane=lane,
                speed=speed,
                completion=completion,
                on_failure=on_failure,
                request=request,
            ))
            if behavior in {"STOP", "HOLD", "PULL_OVER"}:
                break

        confidence = max(0.0, min(1.0, float(confidence_value[0, 0].item())))
        confirmation = bool(
            forced_confirmation
            or confirmation_logits[0, 0].item() >= 0.0
            or confidence < 0.80
        )
        replan_conditions = [
            name for name, logit in zip(REPLAN_CONDITIONS, replan_logits[0])
            if float(logit.item()) >= 0.0
        ][:8]
        created_at_ns = int(request["created_at_ns"])
        valid_until_ns = int(request["deadline_ns"])
        if valid_until_ns <= created_at_ns:
            valid_until_ns = created_at_ns + 1
        return {
            "schema_version": "2.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "plan_id": _plan_id(str(request["request_id"])),
            "plan_type": "MANEUVER_SEQUENCE",
            "steps": steps,
            "replan_conditions": replan_conditions,
            "confidence": confidence,
            "requires_confirmation": confirmation,
            "created_at_ns": created_at_ns,
            "valid_until_ns": valid_until_ns,
            "reason_code": "STUDENT_V0_STRUCTURED",
            "model_id": self.model_id,
        }


def _best_allowed(logits: Tensor, names: Sequence[str], allowed: set[str]) -> str:
    ranked = torch.argsort(logits, descending=True).tolist()
    for index in ranked:
        if names[index] in allowed:
            return names[index]
    return "HOLD"


def _feasible_behaviors(request: Mapping[str, Any], allowed: set[str]) -> set[str]:
    feasible = set(allowed)
    capabilities = request.get("scene_capabilities") or {}
    if not request["targets"]:
        feasible.difference_update(("FOLLOW", "AVOID_OBSTACLE"))
    if not bool(capabilities.get("left_lane_exists", False)) or not bool(
        capabilities.get("left_gap_safe", False)
    ):
        feasible.discard("CHANGE_LANE_LEFT")
    if not bool(capabilities.get("right_lane_exists", False)) or not bool(
        capabilities.get("right_gap_safe", False)
    ):
        feasible.discard("CHANGE_LANE_RIGHT")
    if not bool(capabilities.get("route_available", False)):
        feasible.difference_update(("TURN_LEFT", "TURN_RIGHT", "RETURN_TO_LANE"))
    explicit_turn = _explicit_route_turn(request)
    if explicit_turn is not None:
        for behavior in ("TURN_LEFT", "TURN_RIGHT"):
            if behavior != explicit_turn:
                feasible.discard(behavior)
    elif not bool(capabilities.get("intersection_ahead", False)):
        feasible.difference_update(("TURN_LEFT", "TURN_RIGHT"))
    if _available_avoid_lane("NONE", request) is None:
        feasible.discard("AVOID_OBSTACLE")
    available_lanes = {
        str(item).upper() for item in capabilities.get("available_lanes", ())
    }
    if "SHOULDER" not in available_lanes:
        feasible.discard("PULL_OVER")
    return feasible


def _explicit_route_turn(request: Mapping[str, Any]) -> str | None:
    """Return the exact routed turn explicitly requested by the command.

    A route-backed voice command can legitimately be issued before the next
    junction enters the perception horizon.  Keeping the matching turn in the
    decode mask lets the FSM receive the intended maneuver early; the emitted
    ``INTERSECTION_AHEAD`` precondition still prevents execution until the
    junction is observable.  This exception is deliberately unavailable for
    ambiguous text, missing route context, or a directionless TURN command.
    """
    capabilities = request.get("scene_capabilities") or {}
    if not bool(capabilities.get("route_available", False)):
        return None
    hint = request.get("command_hint") or {}
    intent = str(hint.get("intent", "")).strip().upper()
    if intent in {"TURN_LEFT", "TURN_RIGHT"}:
        return intent
    if intent != "TURN":
        return None
    direction = str(hint.get("direction", "")).strip().upper()
    if direction in {"LEFT", "RIGHT"}:
        return f"TURN_{direction}"
    return None


def _plan_id(request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:12]
    return f"student-{request_id[:80]}-{digest}"


def _bounded_speed(predicted: float, request: Mapping[str, Any]) -> float:
    limits = [50.0]
    constraints = request["constraints"]
    for key in ("speed_limit_mps", "max_target_speed_mps"):
        value = constraints.get(key)
        if value is not None:
            limits.append(float(value))
    return max(0.0, min(predicted, *limits))


def _compatible_completion(behavior: str, predicted: str) -> str:
    required = {
        "TURN_LEFT": "JUNCTION_EXITED",
        "TURN_RIGHT": "JUNCTION_EXITED",
        "CHANGE_LANE_LEFT": "LANE_CENTERED",
        "CHANGE_LANE_RIGHT": "LANE_CENTERED",
        "STOP": "STOPPED",
        "FOLLOW": "TARGET_GAP_REACHED",
        "YIELD": "HOLD_FRAMES",
        "PULL_OVER": "STOPPED",
        "KEEP_LANE": "HOLD_FRAMES",
        "HOLD": "HOLD_FRAMES",
        "AVOID_OBSTACLE": "TARGET_PASSED",
    }
    if behavior in required:
        return required[behavior]
    if behavior == "SET_SPEED":
        return "SPEED_REACHED"
    if behavior == "SLOW_DOWN":
        return "SPEED_BELOW"
    if behavior == "RETURN_TO_LANE":
        return "LANE_CENTERED"
    return predicted


def _step(
    *,
    index: int,
    behavior: str,
    target: Mapping[str, Any] | None,
    predicted_lane: str,
    speed: float,
    completion: str,
    on_failure: str,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    lane: str | None = (
        "CURRENT" if behavior in _IMPLICIT_CURRENT_BEHAVIORS else None
    )
    preconditions = ["PERCEPTION_FRESH"]
    if behavior not in {"STOP", "HOLD", "YIELD"}:
        preconditions.append("NO_EMERGENCY_RISK")
    if behavior == "CHANGE_LANE_LEFT":
        lane = "LEFT_ADJACENT"
        preconditions.extend(("LEFT_LANE_EXISTS", "LEFT_GAP_SAFE"))
    elif behavior == "CHANGE_LANE_RIGHT":
        lane = "RIGHT_ADJACENT"
        preconditions.extend(("RIGHT_LANE_EXISTS", "RIGHT_GAP_SAFE"))
    elif behavior in {"TURN_LEFT", "TURN_RIGHT"}:
        lane = "ROUTE_BRANCH"
        preconditions.extend(("ROUTE_AVAILABLE", "INTERSECTION_AHEAD"))
    elif behavior == "RETURN_TO_LANE":
        lane = "CURRENT"
        preconditions.append("ROUTE_AVAILABLE")
    elif behavior == "AVOID_OBSTACLE":
        lane = _available_avoid_lane(predicted_lane, request)
        preconditions.append("TARGET_VISIBLE")
    elif behavior == "FOLLOW":
        preconditions.append("TARGET_VISIBLE")

    if behavior == "PULL_OVER":
        lane = "SHOULDER" if predicted_lane == "SHOULDER" else None

    target_id = (
        target["target_id"]
        if target is not None and behavior in _POINTER_GROUNDED_BEHAVIORS
        else None
    )
    target_speed = speed if behavior in {"SET_SPEED", "SLOW_DOWN", "FOLLOW"} else None
    completion_value: float | None = None
    completion_lane: str | None = None
    if completion in {"SPEED_BELOW", "SPEED_REACHED"}:
        completion_value = speed
    elif completion == "TARGET_GAP_REACHED":
        completion_value = 5.0
    elif completion == "LANE_CENTERED":
        completion_lane = lane or "CURRENT"
    timeout = 30.0 if behavior.startswith("TURN_") else 20.0 if behavior in {
        "AVOID_OBSTACLE", "RETURN_TO_LANE",
    } else 12.0 if behavior.startswith("CHANGE_LANE_") else 10.0
    return {
        "step_id": f"step-{index + 1}",
        "behavior": behavior,
        "target": {
            "target_id": target_id,
            "target_lane": lane,
            "target_speed_mps": target_speed,
            "time_gap_s": 2.0 if behavior == "FOLLOW" else None,
            "route_direction": (
                "LEFT" if behavior == "TURN_LEFT" else
                "RIGHT" if behavior == "TURN_RIGHT" else None
            ),
        },
        "preconditions": preconditions,
        "completion": {
            "type": completion,
            "value": completion_value,
            "lane": completion_lane,
            "hold_frames": 3,
        },
        "timeout_s": timeout,
        "on_failure": on_failure,
    }


def _available_avoid_lane(
    predicted_lane: str,
    request: Mapping[str, Any],
) -> str | None:
    """Ground an avoidance lane in the lanes reported by perception.

    Prefer the model head, but never publish an adjacent lane that is known to
    be absent.  The plan compiler adds the corresponding live gap gate, so an
    existing but temporarily unsafe lane is waited for rather than entered.
    """
    capabilities = request.get("scene_capabilities") or {}
    declared = capabilities.get("available_lanes")
    available = (
        {str(item).upper() for item in declared}
        if isinstance(declared, Sequence) and not isinstance(declared, (str, bytes))
        else None
    )

    candidates: list[str] = []
    if predicted_lane in {"LEFT_ADJACENT", "RIGHT_ADJACENT"}:
        candidates.append(predicted_lane)
    candidates.extend(
        lane for lane in ("LEFT_ADJACENT", "RIGHT_ADJACENT")
        if lane not in candidates
    )
    for lane in candidates:
        side = "left" if lane == "LEFT_ADJACENT" else "right"
        if not bool(capabilities.get(f"{side}_lane_exists", False)):
            continue
        if available is not None and lane not in available:
            continue
        return lane
    return None


__all__ = ["StudentPlanAdapter"]
