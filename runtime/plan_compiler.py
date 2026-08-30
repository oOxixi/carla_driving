"""Compile validated ManeuverPlan V2 payloads into deterministic FSM steps."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CompiledPlanStep:
    step_id: str
    source_step_id: str
    behavior: str
    target: Mapping[str, Any]
    preconditions: tuple[str, ...]
    completion: Mapping[str, Any]
    timeout_s: float
    on_failure: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["target"] = dict(self.target)
        payload["preconditions"] = list(self.preconditions)
        payload["completion"] = dict(self.completion)
        return payload


@dataclass(frozen=True, slots=True)
class CompiledManeuverPlan:
    command_id: str
    plan_id: str
    steps: tuple[CompiledPlanStep, ...]
    replan_conditions: tuple[str, ...]
    valid_until_ns: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "plan_id": self.plan_id,
            "steps": [step.to_dict() for step in self.steps],
            "replan_conditions": list(self.replan_conditions),
            "valid_until_ns": self.valid_until_ns,
        }


class PlanCompiler:
    """Expand semantic maneuvers without producing throttle/brake/steer."""

    def compile(
        self,
        plan: Mapping[str, Any],
        *,
        scene: Mapping[str, Any] | None = None,
    ) -> CompiledManeuverPlan:
        if not isinstance(plan, Mapping):
            raise TypeError("plan must be a mapping")
        context = {} if scene is None else scene
        if not isinstance(context, Mapping):
            raise TypeError("scene must be a mapping or None")
        compiled: list[CompiledPlanStep] = []
        return_direction: str | None = None
        for raw in plan["steps"]:
            behavior = str(raw["behavior"])
            if behavior == "AVOID_OBSTACLE":
                avoid_steps = self._compile_avoid(raw, context)
                compiled.extend(avoid_steps)
                avoid_lane = str(avoid_steps[-1].target.get("target_lane", ""))
                return_direction = (
                    "RIGHT" if avoid_lane == "LEFT_ADJACENT"
                    else "LEFT" if avoid_lane == "RIGHT_ADJACENT"
                    else None
                )
            elif behavior == "RETURN_TO_LANE":
                return_context = dict(context)
                if return_direction is not None:
                    return_context["return_direction"] = return_direction
                compiled.append(self._compile_return(raw, return_context))
                return_direction = None
            else:
                compiled.append(_copy_step(raw))
        if not compiled:
            raise ValueError("compiled plan must contain at least one step")
        return CompiledManeuverPlan(
            command_id=str(plan["command_id"]),
            plan_id=str(plan["plan_id"]),
            steps=tuple(compiled),
            replan_conditions=tuple(str(item) for item in plan["replan_conditions"]),
            valid_until_ns=int(plan["valid_until_ns"]),
        )

    @staticmethod
    def _compile_avoid(
        raw: Mapping[str, Any], scene: Mapping[str, Any],
    ) -> tuple[CompiledPlanStep, ...]:
        target = dict(raw["target"])
        lane = target.get("target_lane")
        if lane not in {"LEFT_ADJACENT", "RIGHT_ADJACENT"}:
            if bool(scene.get("left_lane_exists", False)):
                lane = "LEFT_ADJACENT"
            elif bool(scene.get("right_lane_exists", False)):
                lane = "RIGHT_ADJACENT"
            else:
                raise ValueError("AVOID_OBSTACLE requires a verified adjacent target lane")
        side = "LEFT" if lane == "LEFT_ADJACENT" else "RIGHT"
        target["target_lane"] = lane
        speed = target.get("target_speed_mps")
        speed = 3.0 if speed is None else float(speed)
        source_id = str(raw["step_id"])
        timeout = float(raw["timeout_s"])
        failure = str(raw["on_failure"])
        common = tuple(str(item) for item in raw["preconditions"])
        lane_exists = f"{side}_LANE_EXISTS"
        gap_safe = f"{side}_GAP_SAFE"
        return (
            CompiledPlanStep(
                f"{source_id}.slow", source_id, "SLOW_DOWN",
                {**target, "target_speed_mps": speed},
                tuple(dict.fromkeys(common + ("PERCEPTION_FRESH",))),
                {"type": "SPEED_BELOW", "value": speed + 0.3, "lane": None, "hold_frames": 3},
                min(5.0, timeout), failure,
            ),
            CompiledPlanStep(
                f"{source_id}.gap", source_id, "WAIT_SAFE_GAP", target,
                tuple(dict.fromkeys(common + (lane_exists, gap_safe))),
                {"type": "HOLD_FRAMES", "value": None, "lane": lane, "hold_frames": 3},
                min(5.0, timeout), failure,
            ),
            CompiledPlanStep(
                f"{source_id}.lane", source_id, f"CHANGE_LANE_{side}", target,
                tuple(dict.fromkeys(common + (lane_exists, gap_safe))),
                {"type": "LANE_CENTERED", "value": None, "lane": lane, "hold_frames": 8},
                timeout, failure,
            ),
            CompiledPlanStep(
                f"{source_id}.pass", source_id, "PASS_TARGET", target,
                ("PERCEPTION_FRESH", "TARGET_VISIBLE", "NO_EMERGENCY_RISK"),
                {"type": "TARGET_PASSED", "value": None, "lane": lane, "hold_frames": 3},
                timeout, failure,
            ),
        )

    @staticmethod
    def _compile_return(
        raw: Mapping[str, Any], scene: Mapping[str, Any],
    ) -> CompiledPlanStep:
        direction = str(scene.get("return_direction", "")).upper()
        if direction not in {"LEFT", "RIGHT"}:
            current_lane = str(scene.get("current_lane", "")).upper()
            original_lane = str(scene.get("original_lane", "")).upper()
            if current_lane == "LEFT_ADJACENT" and original_lane == "CURRENT":
                direction = "RIGHT"
            elif current_lane == "RIGHT_ADJACENT" and original_lane == "CURRENT":
                direction = "LEFT"
            else:
                raise ValueError("RETURN_TO_LANE requires deterministic return_direction")
        target = dict(raw["target"])
        target["target_lane"] = "CURRENT"
        source_id = str(raw["step_id"])
        lane_exists = f"{direction}_LANE_EXISTS"
        gap_safe = f"{direction}_GAP_SAFE"
        preconditions = tuple(dict.fromkeys(
            tuple(str(item) for item in raw["preconditions"])
            + ("PERCEPTION_FRESH", lane_exists, gap_safe, "NO_EMERGENCY_RISK")
        ))
        return CompiledPlanStep(
            source_id, source_id, f"CHANGE_LANE_{direction}", target,
            preconditions,
            {"type": "LANE_CENTERED", "value": None, "lane": "CURRENT", "hold_frames": int(raw["completion"]["hold_frames"])},
            float(raw["timeout_s"]), str(raw["on_failure"]),
        )


def _copy_step(raw: Mapping[str, Any]) -> CompiledPlanStep:
    return CompiledPlanStep(
        step_id=str(raw["step_id"]),
        source_step_id=str(raw["step_id"]),
        behavior=str(raw["behavior"]),
        target=dict(raw["target"]),
        preconditions=tuple(str(item) for item in raw["preconditions"]),
        completion=dict(raw["completion"]),
        timeout_s=float(raw["timeout_s"]),
        on_failure=str(raw["on_failure"]),
    )


__all__ = ["CompiledManeuverPlan", "CompiledPlanStep", "PlanCompiler"]
