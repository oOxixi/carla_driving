"""Scenario-only fault injection at the Qwen client trust boundary."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping
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
        fault: Mapping[str, Any],
        *,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not callable(infer):
            raise TypeError("infer must be callable")
        if not isinstance(fault, Mapping):
            raise TypeError("fault must be a mapping")
        fault_type = str(fault.get("type", "")).upper()
        if fault_type == "TIMEOUT":
            delay_ms = fault.get("delay_ms")
            if (
                type(delay_ms) not in (int, float)
                or isinstance(delay_ms, bool)
                or float(delay_ms) <= 0.0
            ):
                raise ValueError("TIMEOUT fault requires positive delay_ms")
        elif fault_type == "LOW_LEVEL_FIELD":
            field = str(fault.get("field", "")).lower()
            if field not in _LOW_LEVEL_FIELDS:
                raise ValueError("LOW_LEVEL_FIELD fault requires a forbidden control field")
            value = fault.get("value")
            if type(value) not in (int, float) or isinstance(value, bool):
                raise TypeError("LOW_LEVEL_FIELD fault value must be numeric")
        else:
            raise ValueError(f"unsupported qwen fault type: {fault_type or '<missing>'}")
        self._infer = infer
        self._fault = dict(fault)
        self._fault_type = fault_type
        self._sleeper = sleeper

    def __call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if self._fault_type == "TIMEOUT":
            self._sleeper(float(self._fault["delay_ms"]) / 1000.0)
            return self._infer(request)

        response = copy.deepcopy(dict(self._infer(request)))
        steps = response.get("steps")
        if not isinstance(steps, list) or not steps or not isinstance(steps[0], dict):
            raise ValueError("LOW_LEVEL_FIELD fault requires a ManeuverPlan V2 response")
        steps[0][str(self._fault["field"]).lower()] = self._fault["value"]
        return response


__all__ = ["ScenarioQwenFaultInjector"]
