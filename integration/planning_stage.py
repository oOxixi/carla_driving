"""Route-contract preparation stage, independent from CARLA actor mutation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from car_control_A.routing import RouteReference

from .route_geometry import RouteQuality, evaluate_route_quality
from .scenario_builder import validate_actor_route_coverage
from .scenario_execution import ScenarioSpec


@dataclass(frozen=True, slots=True)
class PreparedScenarioRoute:
    reference: RouteReference
    quality: RouteQuality


def prepare_scenario_route(
    spec: ScenarioSpec,
    route_anchor: Any,
    target_speed_mps: float,
    topology_route: RouteReference | None,
) -> PreparedScenarioRoute:
    reference = (
        replace(topology_route, target_speed_mps=float(target_speed_mps))
        if topology_route is not None else
        RouteReference(
            spec.world_route(
                route_anchor.location.x,
                route_anchor.location.y,
                route_anchor.rotation.yaw,
            ),
            0.0,
            float(target_speed_mps),
        )
    )
    quality = evaluate_route_quality(
        reference.points_xy_m, spec.route_distance_contract_m,
    )
    if spec.expected.get("must_finish_route") is True and not quality.reached_contract:
        raise RuntimeError(
            "generated CARLA route does not satisfy the declared distance contract: "
            f"actual={quality.actual_distance_m:.1f} m "
            f"required={quality.requested_distance_m:.1f} m"
        )
    validate_actor_route_coverage(spec.actors, quality.actual_distance_m)
    return PreparedScenarioRoute(reference, quality)


__all__ = ["PreparedScenarioRoute", "prepare_scenario_route"]
