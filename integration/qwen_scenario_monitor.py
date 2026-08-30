"""CARLA-independent acceptance monitor for ``qwen_expected`` contracts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from runtime.plan_validator import FORBIDDEN_LOW_LEVEL_FIELDS


_ROUTES = frozenset({"FAST_LOCAL", "QWEN_PLAN", "CONFIRM_SAFE"})
_EXPECTED_ROUTES = _ROUTES | {"MIXED"}
_TERMINALS = frozenset({
    "SUCCEEDED", "FAILED", "REJECTED", "EXPIRED", "TIMED_OUT",
    "SAFETY_OVERRIDE", "CONFIRMING",
})


@dataclass(frozen=True, slots=True)
class QwenScenarioReport:
    passed: bool
    checks: Mapping[str, bool]
    failures: tuple[str, ...]
    observed: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": dict(self.checks),
            "failures": list(self.failures),
            "observed": dict(self.observed),
        }


class QwenScenarioMonitor:
    def __init__(self, expected: Mapping[str, Any]) -> None:
        if not isinstance(expected, Mapping):
            raise TypeError("qwen_expected must be a mapping")
        route = str(expected.get("route", ""))
        if route not in _EXPECTED_ROUTES:
            raise ValueError("qwen_expected.route is invalid")
        route_counts = expected.get("route_counts")
        if route == "MIXED":
            if not isinstance(route_counts, Mapping):
                raise ValueError("mixed qwen_expected route requires route_counts")
            normalized_counts = {
                str(key).upper(): value for key, value in route_counts.items()
            }
            if (
                not normalized_counts
                or any(key not in _ROUTES for key in normalized_counts)
                or any(
                    type(value) is not int or isinstance(value, bool) or value < 0
                    for value in normalized_counts.values()
                )
            ):
                raise ValueError("qwen_expected.route_counts is invalid")
        minimum, maximum = expected.get("min_calls"), expected.get("max_calls")
        if (
            type(minimum) is not int or isinstance(minimum, bool)
            or type(maximum) is not int or isinstance(maximum, bool)
            or not 0 <= minimum <= maximum
        ):
            raise ValueError("qwen_expected calls must satisfy 0 <= min <= max")
        self.expected = dict(expected)
        self.routes: list[str] = []
        self.command_ids: set[str] = set()
        self.qwen_calls = 0
        self.behaviors: list[str] = []
        self.terminals: list[str] = []
        self.terminal_reasons: list[str] = []
        self.terminal_counts: dict[str, int] = {}
        self.replans = 0
        self.forbidden_paths: list[str] = []

    def record_routing(
        self,
        route: str,
        *,
        qwen_submitted: bool = False,
        command_id: str | None = None,
    ) -> None:
        normalized = str(route).upper()
        if normalized not in _ROUTES:
            raise ValueError(f"invalid observed route: {route!r}")
        self.routes.append(normalized)
        if command_id is not None:
            normalized_id = str(command_id).strip()
            if not normalized_id:
                raise ValueError("command_id must be non-empty when provided")
            self.command_ids.add(normalized_id)
        if qwen_submitted:
            self.qwen_calls += 1

    def record_plan(self, plan: Mapping[str, Any]) -> None:
        if not isinstance(plan, Mapping):
            raise TypeError("plan must be a mapping")
        self.forbidden_paths.extend(_forbidden_paths(plan))
        if plan.get("schema_version") == "2.0":
            steps = plan.get("steps", ())
            if isinstance(steps, Sequence) and not isinstance(steps, (str, bytes)):
                self.behaviors.extend(
                    str(step.get("behavior", "")).upper()
                    for step in steps if isinstance(step, Mapping)
                )
        elif plan.get("behavior") is not None:
            self.behaviors.append(str(plan["behavior"]).upper())

    def record_behavior(self, behavior: Any) -> None:
        """Record a deterministic fast-path or compiled execution behavior."""
        normalized = str(behavior).strip().upper()
        if not normalized:
            raise ValueError("behavior must be non-empty")
        self.behaviors.append(normalized)

    def record_replan(self) -> None:
        self.replans += 1

    def record_terminal(
        self,
        status: Any,
        *,
        command_id: str | None = None,
        reason_code: Any | None = None,
    ) -> None:
        value = getattr(status, "value", status)
        normalized = str(value).upper()
        if normalized not in _TERMINALS:
            return
        normalized_id = None if command_id is None else str(command_id).strip()
        # The internal qwen-wait STOP owns a different command_id and must not
        # satisfy the terminal expected for the routed user command.
        if self.command_ids and normalized_id not in self.command_ids:
            return
        key = normalized_id or "<unspecified>"
        self.terminals.append(normalized)
        if reason_code is not None:
            self.terminal_reasons.append(str(reason_code).strip().upper())
        self.terminal_counts[key] = self.terminal_counts.get(key, 0) + 1

    def finalize(self) -> QwenScenarioReport:
        expected_behaviors = {
            str(item).upper() for item in self.expected.get("expected_behaviors", ())
        }
        observed_behaviors = set(self.behaviors)
        expected_terminal = str(self.expected.get("expected_terminal", "")).upper()
        expected_reason_prefix = str(
            self.expected.get("expected_terminal_reason_prefix", "")
        ).upper()
        expected_route = str(self.expected["route"])
        route_passed = (
            bool(self.routes)
            and (
                dict(Counter(self.routes)) == {
                    str(key).upper(): int(value)
                    for key, value in self.expected.get("route_counts", {}).items()
                    if int(value) > 0
                }
                if expected_route == "MIXED"
                else all(route == expected_route for route in self.routes)
            )
        )
        checks = {
            "route": route_passed,
            "call_count": (
                int(self.expected["min_calls"]) <= self.qwen_calls
                <= int(self.expected["max_calls"])
            ),
            "behaviors": expected_behaviors.issubset(observed_behaviors),
            "terminal": expected_terminal in self.terminals,
            "terminal_reason": (
                not expected_reason_prefix
                or any(
                    reason.startswith(expected_reason_prefix)
                    for reason in self.terminal_reasons
                )
            ),
            "single_terminal": bool(self.terminals) and all(
                count == 1 for count in self.terminal_counts.values()
            ),
            "replans": self.replans <= int(self.expected.get("allowed_replans", 0)),
            "low_level_boundary": not self.forbidden_paths,
        }
        failures = tuple(name for name, passed in checks.items() if not passed)
        return QwenScenarioReport(
            passed=not failures,
            checks=checks,
            failures=failures,
            observed={
                "routes": list(self.routes),
                "qwen_calls": self.qwen_calls,
                "behaviors": list(self.behaviors),
                "terminals": list(self.terminals),
                "terminal_reasons": list(self.terminal_reasons),
                "terminal_counts": dict(self.terminal_counts),
                "replans": self.replans,
                "forbidden_paths": list(self.forbidden_paths),
            },
        )


def _forbidden_paths(value: Any, path: str = "<root>") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_LOW_LEVEL_FIELDS:
                found.append(child_path)
            found.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return found


__all__ = ["QwenScenarioMonitor", "QwenScenarioReport"]
