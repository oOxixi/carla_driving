from __future__ import annotations

import math


def get_speed(vehicle):
    v = vehicle.get_velocity()

    return math.sqrt(
        v.x * v.x +
        v.y * v.y +
        v.z * v.z
    )


def get_vehicle_state(
        vehicle,
        world,
        frame_id,
        traffic_light="UNKNOWN",
        front_distance=None):

    transform = vehicle.get_transform()
    location = transform.location

    snapshot = world.get_snapshot()

    return {
        "frame": int(frame_id),

        "sim_time_s":
            float(snapshot.timestamp.elapsed_seconds),

        "speed_mps":
            float(get_speed(vehicle)),

        "x_m":
            float(location.x),

        "y_m":
            float(location.y),

        "z_m":
            float(location.z),

        "yaw_deg":
            float(transform.rotation.yaw),

        "lane_id":
            0,

        "front_distance_m":
            front_distance,

        "traffic_light":
            traffic_light,

        "collision":
            False,

        "red_light_violation":
            False,

        "lane_invasion":
            False,
    }
