"""Stateful execution helpers kept outside the CARLA orchestration shell."""
from __future__ import annotations

from dataclasses import dataclass
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


__all__ = ["RouteProgressTracker"]
