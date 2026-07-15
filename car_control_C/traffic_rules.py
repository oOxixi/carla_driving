"""Conservative traffic-light and stop-line constraints."""

from __future__ import annotations

from car_control_A import SignalState, TrafficConstraint


class TrafficRulePlanner:
    """UNKNOWN is intentionally treated as a stopping constraint, never as green."""

    def stop_required(self, traffic: TrafficConstraint | None) -> bool:
        if traffic is not None and not isinstance(traffic, TrafficConstraint):
            raise TypeError("traffic must be TrafficConstraint or None")
        return traffic is not None and traffic.distance_to_stop_line_m is not None and traffic.signal_state in {
            SignalState.RED, SignalState.YELLOW, SignalState.UNKNOWN,
        }

    def speed_limit_mps(self, traffic: TrafficConstraint | None) -> float | None:
        if traffic is not None and not isinstance(traffic, TrafficConstraint):
            raise TypeError("traffic must be TrafficConstraint or None")
        return None if traffic is None else traffic.speed_limit_mps

    def stop_distance_m(self, traffic: TrafficConstraint | None) -> float | None:
        if traffic is not None and not isinstance(traffic, TrafficConstraint):
            raise TypeError("traffic must be TrafficConstraint or None")
        return traffic.distance_to_stop_line_m if self.stop_required(traffic) else None
