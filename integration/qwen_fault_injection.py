"""Scenario-only fault injection at the Qwen client trust boundary."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any


_LOW_LEVEL_FIELDS = frozenset({
    "throttle", "brake", "steer", "steering_angle", "wheel_angle", "torque",
})


class ScenarioQwenFaultInjector:
    """Wrap a real client while preserving production code paths after inference.

    Faults are loaded only from an explicit scenario file.  A timeout delays the
    worker response; a low-level fault corrupts an otherwise valid response so
    the runtime validator must reject it before vehicle dispatch.
    """

    def __init__(
        self,
        infer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        fault: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        command_times_s: Sequence[float] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not callable(infer):
            raise TypeError("infer must be callable")
        raw_faults = [fault] if isinstance(fault, Mapping) else list(fault)
        if not raw_faults or any(not isinstance(item, Mapping) for item in raw_faults):
            raise TypeError("fault must be a mapping or a non-empty sequence of mappings")
        supported = {
            "TIMEOUT", "LOW_LEVEL_FIELD", "QWEN_RESPONSE_DELAY",
            "QWEN_COMMAND_DELAY", "QWEN_INVALID_TOKEN", "QWEN_SERVICE_DISCONNECT",
        }
        for item in raw_faults:
            fault_type = str(item.get("type", "")).upper()
            if fault_type not in supported:
                raise ValueError(f"unsupported qwen fault type: {fault_type or '<missing>'}")
            if fault_type in {"TIMEOUT", "QWEN_RESPONSE_DELAY", "QWEN_COMMAND_DELAY"}:
                delay_ms = item.get("delay_ms")
                if (
                    type(delay_ms) not in (int, float)
                    or isinstance(delay_ms, bool)
                    or float(delay_ms) <= 0.0
                ):
                    raise ValueError(f"{fault_type} fault requires positive delay_ms")
            elif fault_type == "LOW_LEVEL_FIELD":
                field = str(item.get("field", "")).lower()
                if field not in _LOW_LEVEL_FIELDS:
                    raise ValueError("LOW_LEVEL_FIELD fault requires a forbidden control field")
                value = item.get("value")
                if type(value) not in (int, float) or isinstance(value, bool):
                    raise TypeError("LOW_LEVEL_FIELD fault value must be numeric")
        self._infer = infer
        self._faults = tuple(dict(item) for item in raw_faults)
        self._command_times_s = tuple(float(item) for item in (command_times_s or ()))
        self._call_index = 0
        self._sleeper = sleeper

    def _active_for_call(self, fault: Mapping[str, Any], call_index: int) -> bool:
        explicit_index = fault.get("command_index")
        if explicit_index is not None:
            return int(explicit_index) == call_index
        trigger = fault.get("trigger", {})
        start_s = float(trigger.get("time_s", 0.0)) if isinstance(trigger, Mapping) else 0.0
        duration_s = float(fault.get("duration_s", float("inf")))
        call_time_s = (
            self._command_times_s[call_index]
            if call_index < len(self._command_times_s)
            else 0.0
        )
        return start_s <= call_time_s < start_s + duration_s

    def __call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        call_index = self._call_index
        self._call_index += 1
        active = tuple(
            item for item in self._faults if self._active_for_call(item, call_index)
        )
        for item in active:
            fault_type = str(item["type"]).upper()
            if fault_type in {"TIMEOUT", "QWEN_RESPONSE_DELAY", "QWEN_COMMAND_DELAY"}:
                self._sleeper(float(item["delay_ms"]) / 1000.0)
            elif fault_type == "QWEN_SERVICE_DISCONNECT":
                raise ConnectionError("scenario-injected Qwen service disconnect")
            elif fault_type == "QWEN_INVALID_TOKEN":
                return {"schema_version": "invalid", "token": str(item.get("token", "Z"))}

        response = copy.deepcopy(dict(self._infer(request)))
        for item in active:
            if str(item["type"]).upper() != "LOW_LEVEL_FIELD":
                continue
            steps = response.get("steps")
            if not isinstance(steps, list) or not steps or not isinstance(steps[0], dict):
                raise ValueError("LOW_LEVEL_FIELD fault requires a ManeuverPlan V2 response")
            steps[0][str(item["field"]).lower()] = item["value"]
        return response


__all__ = ["ScenarioQwenFaultInjector"]
