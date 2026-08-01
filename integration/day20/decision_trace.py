from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping


LONGITUDINAL_ACTIONS = {
    "START",
    "STOP",
    "SET_SPEED",
    "EMERGENCY_BRAKE",
}

LATERAL_ACTIONS = {
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "AVOID_OBJECT",
    "RETURN_TO_LANE",
}


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    if is_dataclass(value):
        return asdict(value)

    if hasattr(value, "to_dict"):
        result = value.to_dict()
        if isinstance(result, Mapping):
            return dict(result)

    if hasattr(value, "__dict__"):
        return dict(value.__dict__)

    return {}


def _qwen_executor_consistent(
    intent_data: Mapping[str, Any],
    target_data: Mapping[str, Any],
) -> tuple[bool, str]:
    actions = intent_data.get("actions", [])

    if not actions:
        return False, "Qwen did not produce a valid high-level action"

    action_names = {
        str(item.get("action", "")).upper()
        for item in actions
        if isinstance(item, Mapping)
    }

    if action_names & LATERAL_ACTIONS:
        return (
            True,
            "Lateral action is delegated to the downstream vehicle module",
        )

    if "EMERGENCY_BRAKE" in action_names:
        consistent = (
            bool(target_data.get("emergency_stop"))
            and float(target_data.get("target_speed_kmh", -1)) == 0.0
        )
        return consistent, "Emergency brake mapping checked"

    if "STOP" in action_names:
        consistent = (
            bool(target_data.get("stop"))
            and float(target_data.get("target_speed_kmh", -1)) == 0.0
        )
        return consistent, "Stop mapping checked"

    if "SET_SPEED" in action_names:
        requested_speeds = [
            float(item.get("target_speed_kmh", 0.0))
            for item in actions
            if (
                isinstance(item, Mapping)
                and str(item.get("action", "")).upper() == "SET_SPEED"
            )
        ]

        target_speed = target_data.get("target_speed_kmh")

        if not requested_speeds or target_speed is None:
            return False, "SET_SPEED target is missing"

        consistent = abs(
            float(target_speed) - requested_speeds[-1]
        ) < 1e-6

        return consistent, "SET_SPEED target mapping checked"

    if "START" in action_names:
        consistent = target_data.get("target_speed_kmh") is not None
        return consistent, "Start target mapping checked"

    return False, "Unsupported Qwen action mapping"


def build_decision_trace(
    *,
    command: str,
    scene_state: Mapping[str, Any],
    rgb_path: str | None,
    qwen_raw_output: Any,
    driving_intent: Any,
    executor_target: Any,
    control_result: Mapping[str, Any],
) -> dict[str, Any]:
    intent_data = _to_dict(driving_intent)
    target_data = _to_dict(executor_target)
    control_data = _to_dict(control_result)

    qwen_to_executor, consistency_note = (
        _qwen_executor_consistent(
            intent_data,
            target_data,
        )
    )

    controller_target = control_data.get(
        "target_speed_kmh"
    )
    executor_speed = target_data.get(
        "target_speed_kmh"
    )

    if executor_speed is None:
        executor_to_controller = True
    else:
        executor_to_controller = (
            controller_target is not None
            and abs(
                float(controller_target)
                - float(executor_speed)
            ) < 1e-6
        )

    final_control = control_data.get("control", {})
    final_control_recorded = (
        isinstance(final_control, Mapping)
        and all(
            field in final_control
            for field in ("throttle", "brake", "steer")
        )
    )

    safety_override = bool(
        control_data.get("safety_override", False)
    )

    if not qwen_to_executor or not executor_to_controller:
        status = "INCONSISTENT"
    elif safety_override:
        status = "CONSISTENT_WITH_SAFETY_OVERRIDE"
    elif final_control_recorded:
        status = "CONSISTENT"
    else:
        status = "FINAL_CONTROL_NOT_RECORDED"

    return {
        "schema_version": "day23-trace-v1",
        "input": {
            "command": command,
            "scene_frame_id": scene_state.get("frame_id"),
            "scene_state": dict(scene_state),
            "rgb_path": rgb_path,
        },
        "qwen": {
            "raw_output": qwen_raw_output,
            "driving_intent": intent_data,
        },
        "execution": {
            "executor_target": target_data,
            "final_vehicle_action": control_data,
        },
        "consistency": {
            "qwen_to_executor": qwen_to_executor,
            "executor_to_controller": executor_to_controller,
            "final_control_recorded": final_control_recorded,
            "safety_override": safety_override,
            "status": status,
            "note": consistency_note,
        },
    }
