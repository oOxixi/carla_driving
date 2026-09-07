#!/usr/bin/env python3
"""Validate destination route planning against one or more live CARLA maps."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.route_manager import RouteManager, RoutePlanningError


def _map_name(world_map: Any) -> str:
    return str(getattr(world_map, "name", "unknown")).rsplit("/", 1)[-1]


def _candidate_pairs(
    spawn_points: list[Any], minimum_endpoint_gap_m: float,
) -> list[tuple[int, Any, int, Any]]:
    count = len(spawn_points)
    pairs: list[tuple[int, Any, int, Any]] = []
    for start_index in range(count):
        for offset in (1, 2, 5, 10, count // 2, count // 3, (count * 2) // 3, count // 4):
            destination_index = (start_index + max(1, offset)) % count
            start = spawn_points[start_index]
            destination = spawn_points[destination_index]
            gap = math.hypot(
                destination.location.x - start.location.x,
                destination.location.y - start.location.y,
            )
            if gap >= minimum_endpoint_gap_m:
                pairs.append((start_index, start, destination_index, destination))
    return pairs


def validate_map(
    client: Any,
    map_name: str,
    pairs_required: int,
    *,
    minimum_endpoint_gap_m: float,
    minimum_route_length_m: float,
    maximum_route_length_m: float,
    maximum_junction_count: int | None,
) -> dict[str, object]:
    world = client.get_world()
    if _map_name(world.get_map()) != map_name:
        world = client.load_world(map_name)
    world_map = world.get_map()
    spawn_points = list(world_map.get_spawn_points())
    manager = RouteManager(world_map, sample_step_m=2.0)
    successes: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    filtered_route_count = 0
    for start_index, start, destination_index, destination in _candidate_pairs(
        spawn_points, minimum_endpoint_gap_m,
    ):
        try:
            route = manager.plan(start, destination, target_speed_mps=11.1)
        except RoutePlanningError as error:
            failures.append({"reason": error.code, "detail": error.detail})
            continue
        if not minimum_route_length_m <= route.total_length_m <= maximum_route_length_m:
            filtered_route_count += 1
            continue
        if (
            maximum_junction_count is not None
            and route.validation.junction_count > maximum_junction_count
        ):
            filtered_route_count += 1
            continue
        midpoint = route.samples[len(route.samples) // 2]
        state = manager.state(route, midpoint.x_m, midpoint.y_m)
        successes.append({
            "start_xy_m": list(route.start_xy_m),
            "destination_xy_m": list(route.destination_xy_m),
            "start_spawn_index": start_index,
            "destination_spawn_index": destination_index,
            "start_yaw_deg": float(start.rotation.yaw),
            "total_length_m": route.total_length_m,
            "point_count": route.validation.point_count,
            "maximum_gap_m": route.validation.maximum_gap_m,
            "destination_error_m": route.validation.destination_error_m,
            "junction_count": route.validation.junction_count,
            "midpoint_state": state.to_dict(),
        })
        if len(successes) >= pairs_required:
            break
    return {
        "map": _map_name(world_map),
        "spawn_point_count": len(spawn_points),
        "passed": len(successes) >= pairs_required,
        "routes": successes,
        "failed_attempt_count": len(failures),
        "filtered_route_count": filtered_route_count,
        "failure_samples": failures[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--maps", nargs="+", default=["Town03_Opt", "Town05"])
    parser.add_argument("--pairs-per-map", type=int, default=3)
    parser.add_argument("--minimum-endpoint-gap-m", type=float, default=100.0)
    parser.add_argument("--minimum-route-length-m", type=float, default=0.0)
    parser.add_argument("--maximum-route-length-m", type=float, default=float("inf"))
    parser.add_argument("--maximum-junction-count", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.pairs_per_map < 1:
        parser.error("--pairs-per-map must be positive")

    try:
        import carla
    except ImportError as error:
        raise SystemExit(f"CARLA Python API is required: {error}") from error
    client = carla.Client(args.host, args.port)
    client.set_timeout(args.timeout_s)
    results = [
        validate_map(
            client,
            map_name,
            args.pairs_per_map,
            minimum_endpoint_gap_m=args.minimum_endpoint_gap_m,
            minimum_route_length_m=args.minimum_route_length_m,
            maximum_route_length_m=args.maximum_route_length_m,
            maximum_junction_count=args.maximum_junction_count,
        )
        for map_name in args.maps
    ]
    report = {
        "record_type": "route_generalization_validation",
        "passed": all(bool(item["passed"]) for item in results),
        "maps": results,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
