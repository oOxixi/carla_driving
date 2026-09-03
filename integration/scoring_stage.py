"""Read-only construction of scoring context from completed runtime evidence."""
from __future__ import annotations

from typing import Mapping, Sequence

from .scenario_execution import ScenarioSpec


def build_acceptance_context(
    spec: ScenarioSpec,
    *,
    final_route_end_distance_m: float | None,
    final_route_remaining_m: float | None,
    configured_route_deviation_trigger_m: float,
    spawned_scenario_actor_types: Sequence[str],
    extension_acceptance: Mapping[str, object] | None,
    qwen_acceptance: Mapping[str, object] | None,
    extension_event_count: int = 0,
) -> dict[str, object]:
    """Build evaluator inputs without mutating any control-side object."""
    context: dict[str, object] = {
        "route_finished": (
            final_route_remaining_m is not None
            and final_route_remaining_m <= spec.finish_radius_m
        ),
        "route_end_distance_m": final_route_end_distance_m,
        "route_remaining_m": final_route_remaining_m,
        "expected_command_count": len(spec.commands),
        "configured_route_deviation_trigger_m": configured_route_deviation_trigger_m,
        "spawned_scenario_actor_types": sorted(set(spawned_scenario_actor_types)),
        "extension_acceptance": None if extension_acceptance is None else dict(extension_acceptance),
        "qwen_acceptance": None if qwen_acceptance is None else dict(qwen_acceptance),
    }
    if extension_event_count > 0:
        context["event_count"] = int(extension_event_count)
    return context


__all__ = ["build_acceptance_context"]
