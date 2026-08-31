#!/usr/bin/env python3
"""Probe Town spawn points against the S2 out-and-back lane-change profile."""

from __future__ import annotations

import argparse
import math

from integration.route_planner import (
    build_lane_change_route_reference,
    build_route_reference,
)


def _location_at_distance(carla_api, route, target_m: float):
    distance_m = 0.0
    for start, end in zip(route.points_xy_m, route.points_xy_m[1:]):
        segment_m = math.dist(start, end)
        if distance_m + segment_m >= target_m:
            ratio = (target_m - distance_m) / segment_m if segment_m else 0.0
            return carla_api.Location(
                x=start[0] + (end[0] - start[0]) * ratio,
                y=start[1] + (end[1] - start[1]) * ratio,
                z=0.5,
            )
        distance_m += segment_m
    x_m, y_m = route.points_xy_m[-1]
    return carla_api.Location(x=x_m, y=y_m, z=0.5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--map", default="Town03_Opt")
    parser.add_argument("--candidates", default="")
    parser.add_argument("--sample-step-m", type=int, default=40)
    parser.add_argument("--sample-end-m", type=int, default=200)
    parser.add_argument(
        "--inspect-location",
        help="optional CARLA world x,y,z location to inspect instead of spawn anchors",
    )
    args = parser.parse_args()

    import carla

    client = carla.Client(args.host, args.port)
    client.set_timeout(60.0)
    world = client.get_world()
    if not world.get_map().name.endswith(f"/{args.map}"):
        world = client.load_world(args.map)
    world_map = world.get_map()
    spawn_points = world_map.get_spawn_points()
    if args.inspect_location:
        values = [float(value) for value in args.inspect_location.split(",")]
        if len(values) != 3:
            raise ValueError("--inspect-location must be x,y,z")
        location = carla.Location(x=values[0], y=values[1], z=values[2])
        waypoint = world_map.get_waypoint(location, project_to_road=True)
        print(
            "waypoint=",
            (waypoint.road_id, waypoint.lane_id, str(waypoint.lane_type)),
        )
        for direction, adjacent in (
            ("LEFT", waypoint.get_left_lane()),
            ("RIGHT", waypoint.get_right_lane()),
        ):
            print(
                f"{direction.lower()}_adjacent=",
                None if adjacent is None else (
                    adjacent.road_id, adjacent.lane_id, str(adjacent.lane_type),
                ),
            )
            try:
                route = build_lane_change_route_reference(
                    world_map,
                    location,
                    7.0,
                    direction=direction,
                    distance_m=72.0,
                    step_m=1.0,
                    transition_start_m=8.0,
                    transition_length_m=30.0,
                )
                print(f"{direction.lower()}_route=PASS points={len(route.points_xy_m)}")
            except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                print(f"{direction.lower()}_route=FAIL {type(error).__name__}: {error}")
        return 0
    candidates = (
        [int(value) for value in args.candidates.split(",") if value.strip()]
        if args.candidates
        else list(range(len(spawn_points)))
    )
    samples = range(0, args.sample_end_m + 1, args.sample_step_m)
    passed: list[int] = []
    for index in candidates:
        completed: list[int] = []
        failure = ""
        try:
            mission = build_route_reference(
                world_map,
                spawn_points[index].location,
                8.0,
                distance_m=float(args.sample_end_m + 100),
                step_m=2.0,
            )
            for distance_m in samples:
                start = _location_at_distance(carla, mission, float(distance_m))
                sampled_waypoint = world_map.get_waypoint(start, project_to_road=True)
                print(
                    f"anchor={index} sample={distance_m} "
                    f"xy=({start.x:.2f},{start.y:.2f}) "
                    f"road_lane=({sampled_waypoint.road_id},{sampled_waypoint.lane_id})",
                    flush=True,
                )
                outbound = build_lane_change_route_reference(
                    world_map,
                    start,
                    7.0,
                    direction="LEFT",
                    distance_m=72.0,
                    step_m=1.0,
                    transition_start_m=8.0,
                    transition_length_m=30.0,
                )
                x_m, y_m = outbound.points_xy_m[-1]
                build_lane_change_route_reference(
                    world_map,
                    carla.Location(x=x_m, y=y_m, z=0.5),
                    7.0,
                    direction="RIGHT",
                    distance_m=72.0,
                    step_m=1.0,
                    transition_start_m=8.0,
                    transition_length_m=30.0,
                )
                completed.append(distance_m)
            passed.append(index)
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            failure = f"{type(error).__name__}: {error}"
        print(f"anchor={index} samples={completed} failure={failure}", flush=True)
    print(f"passed={passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
