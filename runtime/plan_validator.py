"""Strict schema and scene-feasibility validation for ManeuverPlan V2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import time
from typing import Any

from .interface_registry import InterfaceRegistry, InterfaceValidationError


FORBIDDEN_LOW_LEVEL_FIELDS = frozenset({
    "throttle", "brake", "steer", "steering_angle", "wheel_angle",
    "torque", "raw_waypoints", "actor_handle", "carla_actor",
})
ADVANCING_BEHAVIORS = frozenset({
    "KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "FOLLOW", "TURN_LEFT", "TURN_RIGHT",
    "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT", "AVOID_OBSTACLE", "RETURN_TO_LANE",
    "PULL_OVER",
})
_SPEED_BEHAVIORS = frozenset({"SET_SPEED", "SLOW_DOWN", "FOLLOW"})
_TARGET_BEHAVIORS = frozenset({"FOLLOW", "AVOID_OBSTACLE"})
_LANE_REQUIREMENTS = {
    "CHANGE_LANE_LEFT": "LEFT_ADJACENT",
    "CHANGE_LANE_RIGHT": "RIGHT_ADJACENT",
}
_OBSERVABILITY_KEYS = {
    "LEFT_LANE_EXISTS": "left_lane_exists",
    "RIGHT_LANE_EXISTS": "right_lane_exists",
    "LEFT_GAP_SAFE": "left_gap_safe",
    "RIGHT_GAP_SAFE": "right_gap_safe",
    "ROUTE_AVAILABLE": "route_available",
    "INTERSECTION_AHEAD": "intersection_ahead",
    "STOP_LINE_CLEAR": "stop_line_clear",
}


class PlanValidationError(ValueError):
    """A plan failed a stable, machine-readable safety boundary."""

    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


class PlanValidator:
    def __init__(
        self,
        *,
        registry: InterfaceRegistry | None = None,
        maximum_speed_mps: float = 13.8888888889,
        minimum_confidence: float = 0.80,
        clock_ns: Any = time.monotonic_ns,
    ) -> None:
        if not math.isfinite(float(maximum_speed_mps)) or maximum_speed_mps <= 0:
            raise ValueError("maximum_speed_mps must be finite and positive")
        if not 0.0 <= float(minimum_confidence) <= 1.0:
            raise ValueError("minimum_confidence must be in [0, 1]")
        self.registry = registry or InterfaceRegistry()
        self.maximum_speed_mps = float(maximum_speed_mps)
        self.minimum_confidence = float(minimum_confidence)
        self._clock_ns = clock_ns

    def validate(
        self,
        payload: Mapping[str, Any],
        *,
        scene: Mapping[str, Any],
        expected_request_id: str | None = None,
        expected_command_id: str | None = None,
        now_ns: int | None = None,
        allow_confirmation: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise PlanValidationError("INVALID_PLAN_SCHEMA", "plan must be a JSON object")
        if not isinstance(scene, Mapping):
            raise TypeError("scene must be a mapping")
        forbidden_paths = tuple(_find_forbidden_fields(payload))
        if forbidden_paths:
            raise PlanValidationError(
                "LOW_LEVEL_OUTPUT_FORBIDDEN",
                "forbidden control field(s): " + ", ".join(forbidden_paths),
            )
        try:
            plan = self.registry.validate("maneuver_plan", payload)
        except InterfaceValidationError as error:
            raise PlanValidationError("INVALID_PLAN_SCHEMA", str(error)) from error

        now = self._clock_ns() if now_ns is None else now_ns
        if type(now) is not int or now < 0:
            raise ValueError("now_ns must be a non-negative integer")
        if expected_request_id is not None and plan["request_id"] != expected_request_id:
            raise PlanValidationError("REQUEST_ID_MISMATCH", "plan request_id does not match request")
        if expected_command_id is not None and plan["command_id"] != expected_command_id:
            raise PlanValidationError("COMMAND_ID_MISMATCH", "plan command_id does not match request")
        if plan["created_at_ns"] >= plan["valid_until_ns"]:
            raise PlanValidationError("INVALID_PLAN_VALIDITY", "valid_until_ns must follow created_at_ns")
        if now >= plan["valid_until_ns"]:
            raise PlanValidationError("PLAN_EXPIRED", "plan validity boundary elapsed")
        if type(allow_confirmation) is not bool:
            raise TypeError("allow_confirmation must be bool")
        if (
            not allow_confirmation
            and (float(plan["confidence"]) < self.minimum_confidence or plan["requires_confirmation"])
        ):
            raise PlanValidationError(
                "PLAN_CONFIRMATION_REQUIRED",
                "plan confidence is too low or model requested confirmation",
            )
        if bool(scene.get("stale", False)) or not bool(_nested(scene, "sync", "within_tolerance", True)):
            raise PlanValidationError("PERCEPTION_STALE", "plan cannot execute on stale perception")

        step_ids = [str(step["step_id"]) for step in plan["steps"]]
        if len(step_ids) != len(set(step_ids)):
            raise PlanValidationError("DUPLICATE_STEP_ID", "every step_id must be unique")
        available_targets = {
            str(item["track_id"])
            for item in scene.get("objects", ())
            if isinstance(item, Mapping) and item.get("track_id")
        }
        # A scenario actor may be grounded by the live CARLA actor registry
        # before the vision tracker assigns it an opaque ID.  Keep these IDs
        # separate from ``objects`` so they are never represented as visual
        # detections, while still allowing a completion-only clearance gate.
        available_targets.update(
            str(item) for item in scene.get("grounded_target_ids", ()) if item
        )
        available_lanes = _available_lanes(scene)
        speed_limit = _speed_limit(scene, self.maximum_speed_mps)
        must_stop = _must_stop(scene)

        for index, step in enumerate(plan["steps"]):
            behavior = str(step["behavior"])
            target = step["target"]
            target_id = target.get("target_id")
            target_lane = target.get("target_lane")
            target_speed = target.get("target_speed_mps")
            completion = step["completion"]
            prefix = f"steps[{index}]"

            if must_stop and behavior in ADVANCING_BEHAVIORS:
                raise PlanValidationError(
                    "MUST_STOP_PROPULSION_FORBIDDEN",
                    f"{prefix} {behavior} conflicts with red-light or emergency constraint",
                )
            if target_id is not None and target_id not in available_targets:
                raise PlanValidationError(
                    "TARGET_NOT_FOUND", f"{prefix} target_id {target_id!r} is not visible",
                )
            if behavior in _TARGET_BEHAVIORS and not target_id:
                raise PlanValidationError(
                    "TARGET_REQUIRED", f"{prefix} {behavior} requires a visible target_id",
                )
            if target_speed is not None and float(target_speed) > speed_limit + 1e-9:
                raise PlanValidationError(
                    "SPEED_LIMIT_EXCEEDED",
                    f"{prefix} target_speed_mps {target_speed} exceeds {speed_limit}",
                )
            if behavior in _SPEED_BEHAVIORS and target_speed is None:
                raise PlanValidationError(
                    "TARGET_SPEED_REQUIRED", f"{prefix} {behavior} requires target_speed_mps",
                )
            required_lane = _LANE_REQUIREMENTS.get(behavior)
            if required_lane is not None and target_lane != required_lane:
                raise PlanValidationError(
                    "TARGET_LANE_MISMATCH",
                    f"{prefix} {behavior} requires target_lane={required_lane}",
                )
            if target_lane in {"LEFT_ADJACENT", "RIGHT_ADJACENT", "SHOULDER"}:
                if available_lanes is None:
                    raise PlanValidationError(
                        "LANE_CONTEXT_MISSING",
                        f"{prefix} cannot verify target lane {target_lane}",
                    )
                if target_lane not in available_lanes:
                    raise PlanValidationError(
                        "TARGET_LANE_UNAVAILABLE", f"{prefix} lane {target_lane} is unavailable",
                    )
            self._validate_preconditions(step["preconditions"], scene, prefix)
            self._validate_completion(behavior, completion, prefix)
        return plan

    @staticmethod
    def _validate_preconditions(
        preconditions: Sequence[str], scene: Mapping[str, Any], prefix: str,
    ) -> None:
        for condition in preconditions:
            if condition == "PERCEPTION_FRESH":
                continue
            if condition == "NO_EMERGENCY_RISK":
                continue
            if condition == "TARGET_VISIBLE":
                if "objects" not in scene:
                    raise PlanValidationError(
                        "PRECONDITION_UNOBSERVABLE", f"{prefix} cannot observe TARGET_VISIBLE",
                    )
                continue
            key = _OBSERVABILITY_KEYS.get(condition)
            if key is not None and key not in scene:
                raise PlanValidationError(
                    "PRECONDITION_UNOBSERVABLE",
                    f"{prefix} cannot observe {condition}; missing scene.{key}",
                )

    @staticmethod
    def _validate_completion(
        behavior: str, completion: Mapping[str, Any], prefix: str,
    ) -> None:
        completion_type = str(completion["type"])
        if completion_type in {"SPEED_BELOW", "SPEED_REACHED", "TARGET_GAP_REACHED"}:
            if completion.get("value") is None:
                raise PlanValidationError(
                    "COMPLETION_VALUE_REQUIRED", f"{prefix} {completion_type} requires value",
                )
        if completion_type == "LANE_CENTERED" and completion.get("lane") is None:
            raise PlanValidationError(
                "COMPLETION_LANE_REQUIRED", f"{prefix} LANE_CENTERED requires lane",
            )
        expected_types = {
            "TURN_LEFT": {"JUNCTION_EXITED"},
            "TURN_RIGHT": {"JUNCTION_EXITED"},
            "CHANGE_LANE_LEFT": {"LANE_CENTERED"},
            "CHANGE_LANE_RIGHT": {"LANE_CENTERED"},
            "STOP": {"STOPPED", "SPEED_BELOW"},
            "FOLLOW": {"TARGET_GAP_REACHED", "HOLD_FRAMES"},
            "YIELD": {"HOLD_FRAMES"},
            "PULL_OVER": {"STOPPED", "LANE_CENTERED"},
        }.get(behavior)
        if expected_types is not None and completion_type not in expected_types:
            raise PlanValidationError(
                "COMPLETION_BEHAVIOR_MISMATCH",
                f"{prefix} {behavior} cannot use completion {completion_type}",
            )


def _find_forbidden_fields(value: Any, path: str = "<root>") -> Sequence[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_LOW_LEVEL_FIELDS:
                found.append(child_path)
            found.extend(_find_forbidden_fields(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_fields(child, f"{path}[{index}]"))
    return found


def _nested(payload: Mapping[str, Any], outer: str, inner: str, default: Any) -> Any:
    nested = payload.get(outer)
    return nested.get(inner, default) if isinstance(nested, Mapping) else default


def _speed_limit(scene: Mapping[str, Any], configured: float) -> float:
    value = scene.get("speed_limit_mps")
    if type(value) not in (int, float) or isinstance(value, bool) or value is None:
        return configured
    return min(configured, max(0.0, float(value)))


def _must_stop(scene: Mapping[str, Any]) -> bool:
    if bool(scene.get("must_stop", False)):
        return True
    if str(scene.get("risk_level", "UNKNOWN")).upper() == "EMERGENCY":
        return True
    return (
        str(scene.get("traffic_light", "UNKNOWN")).upper() in {"RED", "YELLOW"}
        and scene.get("distance_to_stop_line_m") is not None
    )


def _available_lanes(scene: Mapping[str, Any]) -> set[str] | None:
    value = scene.get("available_lanes")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return {str(item).upper() for item in value}
    derived = {"CURRENT"}
    observed = False
    for key, lane in (
        ("left_lane_exists", "LEFT_ADJACENT"),
        ("right_lane_exists", "RIGHT_ADJACENT"),
        ("shoulder_exists", "SHOULDER"),
    ):
        if key in scene:
            observed = True
            if bool(scene[key]):
                derived.add(lane)
    return derived if observed else None


__all__ = [
    "ADVANCING_BEHAVIORS",
    "FORBIDDEN_LOW_LEVEL_FIELDS",
    "PlanValidationError",
    "PlanValidator",
]
