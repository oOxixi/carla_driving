"""Base interface for lateral controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod
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
        return self.step(adapt_vehicle_pose(vehicle_state), adapt_route_reference(reference))

    def steer(self, vehicle_state: Any, reference: Any) -> float:
        """Compatibility helper for A handoff wording."""
        return self.step_any(vehicle_state, reference).steer
