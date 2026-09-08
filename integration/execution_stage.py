"""Stateful execution helpers kept outside the CARLA orchestration shell."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .route_geometry import project_route_progress_m


@dataclass(slots=True)
class RouteProgressTracker:
    points_xy_m: Sequence[tuple[float, float]]
    progress_m: float = 0.0

    def update(self, x_m: float, y_m: float, *, speed_mps: float, delta_s: float) -> float:
        self.progress_m = project_route_progress_m(
            self.points_xy_m,
            x_m,
            y_m,
            previous_s_m=self.progress_m,
            forward_window_m=max(20.0, float(speed_mps) * float(delta_s) * 8.0),
        )
        return self.progress_m


@dataclass(slots=True)
class DistanceCoverageTracker:
    """Accumulate real driven distance while rejecting simulator teleports.

    Topology-coverage contracts measure continuous distance travelled, not
    closeness to one fixed lane-centre polyline. A legitimate permanent lane
    change otherwise makes route projection stall even while the ego keeps
    driving. Large discontinuities are ignored so recovery teleports cannot
    satisfy the contract.
    """

    progress_m: float = 0.0
    previous_xy_m: tuple[float, float] | None = None
    minimum_jump_gate_m: float = 2.0

    def update(self, x_m: float, y_m: float, *, speed_mps: float, delta_s: float) -> float:
        current = (float(x_m), float(y_m))
        if not all(math.isfinite(value) for value in current):
            raise ValueError("coverage position must be finite")
        if self.previous_xy_m is None:
            self.previous_xy_m = current
            return self.progress_m
        step_m = math.dist(self.previous_xy_m, current)
        self.previous_xy_m = current
        jump_gate_m = max(
            float(self.minimum_jump_gate_m),
            max(0.0, float(speed_mps)) * max(0.0, float(delta_s)) * 3.0 + 1.0,
        )
        if step_m <= jump_gate_m:
            self.progress_m += step_m
        return self.progress_m


__all__ = ["DistanceCoverageTracker", "RouteProgressTracker"]
