"""Base interface for lateral controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from .adapters import adapt_route_reference, adapt_vehicle_pose
from .schemas import LateralOutput, RouteReference, VehiclePose


class LateralController(ABC):
    """B-side controller contract.

    A should call step(vehicle_state, route_reference) and use only output.steer.
    B never calls CARLA apply_control and never modifies throttle/brake.
    """

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput:
        pass

    def step_any(self, vehicle_state: Any, reference: Any) -> LateralOutput:
        source_points = (
            reference.get("points_xy_m", reference.get("points"))
            if isinstance(reference, Mapping)
            else getattr(reference, "points_xy_m", getattr(reference, "points", None))
        )
        cache: list[tuple[object, RouteReference]] = getattr(
            self, "_adapted_route_cache", [],
        )
        adapted_reference = next(
            (
                adapted
                for known_points, adapted in cache
                if known_points is source_points
            ),
            None,
        )
        if adapted_reference is None:
            adapted_reference = adapt_route_reference(reference)
            # Keep the source point container itself, not only its integer id:
            # route objects are short-lived and Python may reuse a released id.
            cache.append((source_points, adapted_reference))
            if len(cache) > 32:
                del cache[0]
            setattr(self, "_adapted_route_cache", cache)
        return self.step(adapt_vehicle_pose(vehicle_state), adapted_reference)

    def steer(self, vehicle_state: Any, reference: Any) -> float:
        """Compatibility helper for A handoff wording."""
        return self.step_any(vehicle_state, reference).steer
