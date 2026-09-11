"""Encode frozen planner contracts into fixed-shape Student supervision.

The encoder is deliberately independent of the Student architecture.  It
validates the real ModelRequest V1 and ManeuverPlan V2 payloads, grounds every
Teacher target ID to its position in the current request, and masks padded
steps and optional numeric fields so they never contribute to training loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from challenge.student.contract import (
    BEHAVIORS,
    BEHAVIOR_TO_ID,
    COMPLETION_TYPES,
    COMPLETION_TYPE_TO_ID,
    ON_FAILURE,
    ON_FAILURE_TO_ID,
    REPLAN_CONDITIONS,
    TARGET_LANES,
    TARGET_LANE_TO_ID,
)
from runtime.interface_registry import InterfaceRegistry


FAILURE_ACTIONS = ON_FAILURE
PAD_CLASS_INDICES = {
    "behavior": BEHAVIOR_TO_ID["HOLD"],
    "target_lane": TARGET_LANE_TO_ID["NONE"],
    "completion_type": COMPLETION_TYPE_TO_ID["HOLD_FRAMES"],
    "on_failure": ON_FAILURE_TO_ID["HOLD_CURRENT_LANE"],
}
_INTERFACES = InterfaceRegistry()


class LabelEncodingError(ValueError):
    """A valid planner record cannot be represented by the Student contract."""


@dataclass(frozen=True, slots=True)
class DistillationLabelEncoder:
    max_steps: int = 4
    max_targets: int = 8
    validate_contracts: bool = True

    def __post_init__(self) -> None:
        if type(self.max_steps) is not int or self.max_steps != 4:
            raise ValueError("A1 Student V0 requires max_steps=4")
        if type(self.max_targets) is not int or self.max_targets != 8:
            raise ValueError("A1 Student V0 requires max_targets=8")
        if type(self.validate_contracts) is not bool:
            raise TypeError("validate_contracts must be bool")

    @property
    def vocabulary(self) -> dict[str, tuple[str, ...]]:
        return {
            "behavior": BEHAVIORS,
            "target_lane": TARGET_LANES,
            "completion_type": COMPLETION_TYPES,
            "on_failure": FAILURE_ACTIONS,
            "replan_condition": REPLAN_CONDITIONS,
        }

    def encode(
        self,
        request: Mapping[str, Any],
        plan: Mapping[str, Any],
    ) -> dict[str, Any]:
        if self.validate_contracts:
            request = _INTERFACES.validate("model_request", request)
            plan = _INTERFACES.validate("maneuver_plan", plan)
        else:
            request, plan = dict(request), dict(plan)

        if request.get("request_id") != plan.get("request_id"):
            raise LabelEncodingError("Teacher plan request_id does not match ModelRequest")
        if request.get("command_id") != plan.get("command_id"):
            raise LabelEncodingError("Teacher plan command_id does not match ModelRequest")

        steps = list(plan.get("steps", ()))
        if not steps or len(steps) > self.max_steps:
            raise LabelEncodingError(
                f"Teacher plan has {len(steps)} steps; Student supports 1..{self.max_steps}"
            )
        targets = list(request.get("targets", ()))
        if len(targets) > self.max_targets:
            raise LabelEncodingError(
                f"ModelRequest has {len(targets)} targets; Student supports {self.max_targets}"
            )
        target_positions = {
            str(item["target_id"]): index for index, item in enumerate(targets)
        }

        labels: dict[str, Any] = {
            "plan_length": len(steps) - 1,
            "behavior": [PAD_CLASS_INDICES["behavior"]] * self.max_steps,
            "target_pointer": [self.max_targets] * self.max_steps,
            "target_lane": [PAD_CLASS_INDICES["target_lane"]] * self.max_steps,
            "target_speed_mps": [0.0] * self.max_steps,
            "completion_type": [PAD_CLASS_INDICES["completion_type"]] * self.max_steps,
            "on_failure": [PAD_CLASS_INDICES["on_failure"]] * self.max_steps,
            "step_mask": [False] * self.max_steps,
            "target_speed_mask": [False] * self.max_steps,
            "confidence": float(plan["confidence"]),
            "requires_confirmation": float(bool(plan["requires_confirmation"])),
            "replan_conditions": [0.0] * len(REPLAN_CONDITIONS),
        }
        for index, step in enumerate(steps):
            target = step.get("target", {})
            completion = step.get("completion", {})
            labels["step_mask"][index] = True
            labels["behavior"][index] = _category_index(
                BEHAVIORS, step.get("behavior"), "behavior",
            )
            labels["target_pointer"][index] = self._target_pointer(
                target.get("target_id"), target_positions,
            )
            lane = target.get("target_lane")
            labels["target_lane"][index] = _category_index(
                TARGET_LANES, "NONE" if lane is None else lane, "target_lane",
            )
            speed = target.get("target_speed_mps")
            if speed is not None:
                labels["target_speed_mps"][index] = float(speed)
                labels["target_speed_mask"][index] = True
            labels["completion_type"][index] = _category_index(
                COMPLETION_TYPES, completion.get("type"), "completion.type",
            )
            labels["on_failure"][index] = _category_index(
                FAILURE_ACTIONS, step.get("on_failure"), "on_failure",
            )

        replan_index = {name: index for index, name in enumerate(REPLAN_CONDITIONS)}
        for condition in plan.get("replan_conditions", ()):
            try:
                labels["replan_conditions"][replan_index[str(condition)]] = 1.0
            except KeyError as error:
                raise LabelEncodingError(
                    f"unsupported replan condition: {condition!r}"
                ) from error
        return labels

    def _target_pointer(
        self,
        target_id: object,
        target_positions: Mapping[str, int],
    ) -> int:
        if target_id is None:
            return self.max_targets
        normalized = str(target_id)
        try:
            return target_positions[normalized]
        except KeyError as error:
            raise LabelEncodingError(
                f"Teacher target_id {normalized!r} is absent from ModelRequest.targets"
            ) from error


def _category_index(
    values: Sequence[str], value: object, field_name: str,
) -> int:
    normalized = str(value)
    try:
        return values.index(normalized)
    except ValueError as error:
        raise LabelEncodingError(
            f"unsupported {field_name} value: {normalized!r}"
        ) from error


__all__ = [
    "BEHAVIORS", "COMPLETION_TYPES", "DistillationLabelEncoder",
    "FAILURE_ACTIONS", "LabelEncodingError", "REPLAN_CONDITIONS",
    "TARGET_LANES",
]
