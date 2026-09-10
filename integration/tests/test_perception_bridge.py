from __future__ import annotations

import pytest

from car_control_A import RuntimeVehicleState
from integration.contracts import PerceptionFrame
from integration.perception_bridge import longitudinal_request


def _vehicle(speed_mps: float = 8.0) -> RuntimeVehicleState:
    return RuntimeVehicleState(10, 0.5, speed_mps, 0.0, 0.0, 0.0, 0.0, "1")


def test_unknown_lead_speed_uses_conservative_stationary_assumption() -> None:
    request = longitudinal_request(
        _vehicle(),
        PerceptionFrame(10, 0.5, lead_distance_m=20.0, lead_speed_mps=None),
        requested_speed_mps=10.0,
        path_curvature_per_m=0.0,
    )

    assert request.lead_distance_m == 20.0
    assert request.closing_speed_mps == 8.0


def test_observed_lead_speed_is_used_when_available() -> None:
    request = longitudinal_request(
        _vehicle(),
        PerceptionFrame(10, 0.5, lead_distance_m=20.0, lead_speed_mps=3.0),
        requested_speed_mps=10.0,
        path_curvature_per_m=0.0,
    )

    assert request.closing_speed_mps == pytest.approx(5.0)


def test_absent_lead_range_remains_absent() -> None:
    request = longitudinal_request(
        _vehicle(),
        PerceptionFrame(10, 0.5),
        requested_speed_mps=10.0,
        path_curvature_per_m=0.0,
    )

    assert request.lead_distance_m is None
    assert request.closing_speed_mps is None
