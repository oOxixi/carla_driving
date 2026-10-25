"""Add explicit scopes to audit statistics without rewriting raw terminal events."""
from __future__ import annotations

from collections import Counter
from typing import Mapping


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
