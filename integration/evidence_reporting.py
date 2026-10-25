"""Add explicit scopes to audit statistics without rewriting raw terminal events."""
from __future__ import annotations

from collections import Counter
import math
from typing import Mapping


class LaneOffsetStatistics:
    """Diagnostic partitions only; raw acceptance metrics remain unchanged."""

    def __init__(self) -> None:
        self._groups: dict[str, dict[str, float | int]] = {}
        self.planned_reference_valid = True

    def observe(self, value: object, *, planned_crossing: bool | None, route_error_m: object) -> None:
        verified = type(route_error_m) in (int, float) and math.isfinite(route_error_m)
        if planned_crossing is True and (not verified or abs(route_error_m) > 1.0):
            self.planned_reference_valid = False
        if type(value) not in (int, float) or not math.isfinite(value):
            return
        group = "lane_follow" if planned_crossing is False else "unclassified"
        if planned_crossing is True:
            group = ("planned_maneuver" if verified and abs(route_error_m) <= 1.0 else
                     "off_plan_maneuver" if verified else "unverified_maneuver")
        for key in ("all_frames", group):
            stats = self._groups.setdefault(key, {"frames": 0, "sum_abs_m": 0., "max_abs_m": 0.})
            stats["frames"] += 1
            stats["sum_abs_m"] += abs(value)
            stats["max_abs_m"] = max(stats["max_abs_m"], abs(value))

    def report(self) -> dict:
        return {key: {
            "frames": value["frames"], "max_abs_m": value["max_abs_m"],
            "mean_abs_m": value["sum_abs_m"] / value["frames"],
        } for key, value in self._groups.items()}


def command_scope(command_id: str, disposition: str = "") -> str:
    if disposition.startswith("INTERNAL_QWEN_WAIT") or command_id.startswith("qwen-wait-"):
        return "internal_wait"
    if disposition.startswith("INTERNAL_") or command_id.startswith("qwen-step-"):
        return "internal_step"
    return "external"


def scoped_command_statistics(
    commands: Mapping[str, Mapping[str, object]], terminals: Mapping[str, str],
) -> dict[str, object]:
    result = {}
    for scope in ("external", "internal_step", "internal_wait"):
        ids = {
            command_id for command_id in set(commands) | set(terminals)
            if command_scope(command_id, str(commands.get(command_id, {}).get("disposition", ""))) == scope
        }
        statuses = {key: terminals[key] for key in sorted(ids) if key in terminals}
        result[scope] = {
            "command_count": len(ids), "terminal_statuses": statuses,
            "status_counts": dict(Counter(statuses.values())),
            "missing_terminal_ids": sorted(ids - statuses.keys()),
        }
    return result


def safety_override_category(reason: str) -> str:
    if "RED_LIGHT" in reason or "STOP_LINE" in reason:
        return "traffic_signal"
    if any(token in reason for token in ("TTC", "FRONT_OBSTACLE", "C_HAZARD")):
        return "front_hazard"
    if "ROUTE" in reason or "LATERAL" in reason:
        return "route_control"
    return "other"
