"""Cross-module gate for temporary safety stops and bounded recovery.

These checks intentionally exercise C's sensor-fusion recommendation through
the runtime speed-cap boundary, plus D's red-light override. A stopped vehicle
must remain safe without turning a temporary condition into a permanent zero-
speed state.
"""

import pytest

from car_control_A import RuntimeVehicleState
from car_control_A.routing import RouteReference
from car_control_B.pure_pursuit import PurePursuitController
from car_control_C import ConservativeSensorFusion, SafetyStateParameters
from car_control_C.safety_state import VisualObservation
from integration import ControlRuntime, PerceptionFrame


def _vehicle(frame: int, sim_time_s: float) -> RuntimeVehicleState:
    return RuntimeVehicleState(
        frame=frame,
        sim_time_s=sim_time_s,
        speed_mps=0.0,
        x_m=0.0,
        y_m=0.0,
        z_m=0.0,
        yaw_deg=0.0,
        lane_id="lane_1",
    )


def _route() -> RouteReference:
    return RouteReference(((0.0, 0.0), (20.0, 0.0)), 0.0, 5.0)


def _assert_stopped_vehicle_can_move_under_cap(
    speed_cap_mps: float,
    *,
    frame: int,
    sim_time_s: float,
) -> None:
    assert speed_cap_mps > 0.0
    runtime = ControlRuntime(PurePursuitController(), default_speed_mps=5.0)
    result = runtime.step(
        _vehicle(frame, sim_time_s),
        PerceptionFrame(frame=frame, sim_time_s=sim_time_s),
        _route(),
        dt_s=0.05,
        speed_cap_mps=speed_cap_mps,
    )
    assert runtime.requested_speed_mps == pytest.approx(5.0)
    assert result.longitudinal is not None
    assert result.longitudinal.target_speed_mps > 0.0
    assert result.final_control.throttle > 0.0
    assert result.final_control.brake == 0.0


def test_generic_lidar_caution_cannot_absorb_stopped_vehicle_at_zero() -> None:
    summary = ConservativeSensorFusion(
        SafetyStateParameters(range_uncertainty_buffer_m=2.0)
    ).update(
        frame=1,
        sim_time_s=0.05,
        ego_speed_mps=0.0,
        front_distance_m=7.5,
        lidar_valid=True,
        lead_speed_mps=0.0,
    )

    assert summary.recommended_action == "SLOW_DOWN"
    assert summary.recommended_speed_cap_mps is not None
    _assert_stopped_vehicle_can_move_under_cap(
        summary.recommended_speed_cap_mps,
        frame=1,
        sim_time_s=0.05,
    )


def test_confirmed_hazard_occlusion_hold_keeps_recoverable_positive_cap() -> None:
    fusion = ConservativeSensorFusion(
        SafetyStateParameters(
            range_uncertainty_buffer_m=2.0,
            front_hazard_occlusion_hold_s=3.0,
        )
    )
    for frame in range(1, 4):
        fusion.update(
            frame=frame,
            sim_time_s=frame * 0.05,
            ego_speed_mps=0.0,
            front_distance_m=7.5,
            lidar_valid=True,
            lead_speed_mps=0.0,
        )
    held = fusion.update(
        frame=4,
        sim_time_s=0.20,
        ego_speed_mps=0.0,
        front_distance_m=None,
        lidar_valid=True,
    )

    assert held.reason == "front_hazard_occlusion_hold"
    assert held.recommended_speed_cap_mps is not None
    _assert_stopped_vehicle_can_move_under_cap(
        held.recommended_speed_cap_mps,
        frame=4,
        sim_time_s=0.20,
    )


def test_vru_caution_hold_remains_slow_but_does_not_permanently_stop() -> None:
    summary = ConservativeSensorFusion().update(
        frame=1,
        sim_time_s=0.05,
        ego_speed_mps=0.0,
        front_distance_m=20.0,
        lidar_valid=True,
        lead_speed_mps=0.0,
        visual=VisualObservation(
            frame=1,
            valid=True,
            object_class="pedestrian",
            confidence=0.99,
        ),
    )

    assert summary.recommended_action == "SLOW_DOWN"
    assert summary.recommended_speed_cap_mps is not None
    _assert_stopped_vehicle_can_move_under_cap(
        summary.recommended_speed_cap_mps,
        frame=1,
        sim_time_s=0.05,
    )


def test_red_light_override_releases_on_green_without_losing_requested_speed() -> None:
    runtime = ControlRuntime(PurePursuitController(), default_speed_mps=5.0)
    stopped = runtime.step(
        _vehicle(1, 0.05),
        PerceptionFrame(
            frame=1,
            sim_time_s=0.05,
            traffic_light="RED",
            distance_to_stop_line_m=5.0,
        ),
        _route(),
        dt_s=0.05,
    )
    assert stopped.safety_reason == "RED_LIGHT_STOP_LINE_GUARD"
    assert stopped.final_control.brake == 1.0

    resumed = runtime.step(
        _vehicle(2, 0.10),
        PerceptionFrame(frame=2, sim_time_s=0.10, traffic_light="GREEN"),
        _route(),
        dt_s=0.05,
    )
    assert runtime.requested_speed_mps == pytest.approx(5.0)
    assert resumed.final_control.throttle > 0.0
    assert resumed.final_control.brake == 0.0
