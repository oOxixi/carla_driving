"""Decode Student tensors into a strict, grounded ManeuverPlan V2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import torch
from torch import Tensor

from challenge.student.contract import (
    BEHAVIORS,
    COMPLETION_TYPES,
    ON_FAILURE,
    REPLAN_CONDITIONS,
    TARGET_LANES,
)
from challenge.student.preprocess import _expanded_allowed_behaviors


class StudentPlanAdapter:
    def __init__(self, *, model_id: str = "student-v0-fp32") -> None:
        self.model_id = model_id

    def decode(
        self,
        request: Mapping[str, Any],
        outputs: Sequence[Tensor],
    ) -> dict[str, Any]:
        if len(outputs) != 10:
            raise ValueError("Student V0 must return exactly 10 structured heads")
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
        ) = outputs
        maximum_steps = int(behavior_logits.shape[1])
        plan_length = int(plan_length_logits[0].argmax().item()) + 1
        plan_length = max(1, min(plan_length, maximum_steps))
        allowed = _feasible_behaviors(request, _expanded_allowed_behaviors(request))
        must_stop = bool(request["constraints"]["must_stop"])
        if must_stop:
            plan_length = 1

        steps: list[dict[str, Any]] = []
        for index in range(plan_length):
            behavior = "STOP" if must_stop else _best_allowed(
                behavior_logits[0, index], BEHAVIORS, allowed,
            )
            pointer = int(target_pointer_logits[0, index].argmax().item())
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
            ))

        confidence = max(0.0, min(1.0, float(confidence_value[0, 0].item())))
        confirmation = bool(confirmation_logits[0, 0].item() >= 0.0 or confidence < 0.80)
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
            "plan_id": f"student-{request['request_id']}",
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
    if not bool(capabilities.get("intersection_ahead", False)):
        feasible.difference_update(("TURN_LEFT", "TURN_RIGHT"))
    return feasible or {"HOLD"}


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
    if behavior in {"SET_SPEED", "SLOW_DOWN"}:
        return "SPEED_REACHED"
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
) -> dict[str, Any]:
    lane: str | None = None
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
    elif behavior in {"FOLLOW", "AVOID_OBSTACLE"}:
        preconditions.append("TARGET_VISIBLE")

    if behavior == "PULL_OVER":
        lane = "SHOULDER" if predicted_lane == "SHOULDER" else None

    target_id = (
        target["target_id"]
        if target is not None and behavior in {"FOLLOW", "AVOID_OBSTACLE"}
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


__all__ = ["StudentPlanAdapter"]
