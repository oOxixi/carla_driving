"""Route reference boundary owned by A; no lateral control algorithm lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class RouteReference:
    points_xy_m: tuple[tuple[float, float], ...]
    curvature_per_m: float
    target_speed_mps: float
    route_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.points_xy_m) < 2:
            raise ValueError("route needs at least two points")
        if self.target_speed_mps < 0.0:
            raise ValueError("target_speed_mps must be non-negative")


@runtime_checkable
class LateralController(Protocol):
    def steer(self, reference: RouteReference) -> float:
        """Return only a bounded steering command in [-1, 1]."""
