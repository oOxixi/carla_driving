"""Conversions from frame-aligned scene facts to A/C/D inputs."""
from __future__ import annotations

from car_control_A import LongitudinalRequest, RuntimeVehicleState, SignalState, TrafficConstraint

from .contracts import PerceptionFrame


def longitudinal_request(vehicle: RuntimeVehicleState, scene: PerceptionFrame, *, requested_speed_mps: float,
                         path_curvature_per_m: float) -> LongitudinalRequest:
    if scene.frame != vehicle.frame or scene.sim_time_s != vehicle.sim_time_s:
        raise ValueError("scene and vehicle must be from the same CARLA frame")
    traffic = TrafficConstraint(SignalState(scene.traffic_light), scene.distance_to_stop_line_m, scene.speed_limit_mps)
    if scene.lead_distance_m is None and scene.lead_speed_mps is not None:
        raise ValueError("lead_speed_mps requires lead_distance_m")
    # A fresh LiDAR track can provide range one frame before temporal speed is
    # available.  Treat that short interval conservatively as a stationary
    # lead instead of turning a valid sensor frame into a latched integration
    # failure.
    closing = (
        None
        if scene.lead_distance_m is None
        else vehicle.speed_mps - (
            0.0 if scene.lead_speed_mps is None else scene.lead_speed_mps
        )
    )
    return LongitudinalRequest(vehicle, requested_speed_mps, path_curvature_per_m, traffic,
                               scene.lead_distance_m, closing)


def safety_vehicle_state(vehicle: RuntimeVehicleState, scene: PerceptionFrame) -> dict[str, object]:
    """D needs a numeric lane id, unlike A's arbitrary string identifier."""
    try:
        lane_id = int(vehicle.lane_id)
    except ValueError:
        lane_id = 0
    return {"frame": vehicle.frame, "sim_time_s": vehicle.sim_time_s, "speed_mps": vehicle.speed_mps,
            "x_m": vehicle.x_m, "y_m": vehicle.y_m, "z_m": vehicle.z_m, "yaw_deg": vehicle.yaw_deg,
            "lane_id": lane_id, "front_distance_m": scene.lead_distance_m,
            "distance_to_stop_line_m": scene.distance_to_stop_line_m, "traffic_light": scene.traffic_light,
            "lane_offset_m": scene.lane_offset_m, "route_deviation_m": scene.route_deviation_m,
            "collision": scene.collision, "red_light_violation": scene.red_light_violation,
            "lane_invasion": scene.lane_invasion}
