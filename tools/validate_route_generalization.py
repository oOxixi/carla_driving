#!/usr/bin/env python3
"""Validate destination route planning against one or more live CARLA maps."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.route_manager import RouteManager, RoutePlanningError
from car_control_B.path_utils import estimate_curvature


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


def _route_profiles(route: Any) -> tuple[tuple[str, ...], dict[str, object]]:
    points = route.reference.points_xy_m
    maximum_curvature = max(
        (
            abs(estimate_curvature(points, index, stride=1))
            for index in range(1, len(points) - 1)
        ),
        default=0.0,
    )
    road_ids = {
        int(sample.road_id)
        for sample in route.samples
        if sample.road_id is not None
    }
    length_m = float(route.total_length_m)
    junction_count = int(route.validation.junction_count)
    profiles = {
        "straight" if maximum_curvature < 0.01 else "curved",
        "junction_free" if junction_count == 0 else "junction",
        (
            "short_route" if length_m < 300.0
            else "medium_route" if length_m < 1_000.0
            else "long_route"
        ),
    }
    if junction_count >= 3:
        profiles.add("multi_junction")
    if len(road_ids) >= 3:
        profiles.add("multi_road")
    return tuple(sorted(profiles)), {
        "maximum_curvature_per_m": maximum_curvature,
        "road_count": len(road_ids),
    }


def _select_diverse_routes(
    candidates: list[dict[str, object]],
    count: int,
) -> list[dict[str, object]]:
    """Greedily retain deterministic routes that add structural coverage."""
    selected: list[dict[str, object]] = []
    remaining = list(candidates)
    covered: set[str] = set()
    starts: set[int] = set()
    destinations: set[int] = set()
    while remaining and len(selected) < count:
        best = max(
            enumerate(remaining),
            key=lambda item: (
                len(set(item[1]["profiles"]) - covered),
                int(item[1]["start_spawn_index"] not in starts),
                int(item[1]["destination_spawn_index"] not in destinations),
                float(item[1]["total_length_m"]),
                -item[0],
            ),
        )[1]
        remaining.remove(best)
        selected.append(best)
        covered.update(str(value) for value in best["profiles"])
        starts.add(int(best["start_spawn_index"]))
        destinations.add(int(best["destination_spawn_index"]))
    return selected


def validate_map(
    client: Any,
    map_name: str,
    pairs_required: int,
    *,
    minimum_endpoint_gap_m: float,
    minimum_route_length_m: float,
    maximum_route_length_m: float,
    maximum_junction_count: int | None,
    required_profiles: tuple[str, ...] = (),
    candidate_limit: int = 120,
) -> dict[str, object]:
    world = client.get_world()
    if _map_name(world.get_map()) != map_name:
        world = client.load_world(map_name)
    world_map = world.get_map()
    spawn_points = list(world_map.get_spawn_points())
    manager = RouteManager(world_map, sample_step_m=2.0)
    candidates: list[dict[str, object]] = []
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
        profiles, structure = _route_profiles(route)
        candidates.append({
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
            "profiles": list(profiles),
            **structure,
            "midpoint_state": state.to_dict(),
        })
        if len(candidates) >= candidate_limit:
            break
    successes = _select_diverse_routes(candidates, pairs_required)
    covered_profiles = sorted({
        str(profile)
        for route in successes
        for profile in route["profiles"]
    })
    missing_profiles = sorted(set(required_profiles) - set(covered_profiles))
    planning_attempt_count = len(candidates) + len(failures) + filtered_route_count
    reason_counts = Counter(item["reason"] for item in failures)
    return {
        "map": _map_name(world_map),
        "spawn_point_count": len(spawn_points),
        "passed": len(successes) >= pairs_required and not missing_profiles,
        "routes": successes,
        "candidate_route_count": len(candidates),
        "covered_profiles": covered_profiles,
        "required_profiles": list(required_profiles),
        "missing_profiles": missing_profiles,
        "planning_attempt_count": planning_attempt_count,
        "candidate_success_rate": (
            0.0
            if planning_attempt_count == 0
            else len(candidates) / planning_attempt_count
        ),
        "failed_attempt_count": len(failures),
        "failure_reason_counts": dict(sorted(reason_counts.items())),
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
    parser.add_argument(
        "--required-profiles",
        nargs="*",
        default=(),
        choices=(
            "straight", "curved", "junction_free", "junction",
            "multi_junction", "short_route", "medium_route", "long_route",
            "multi_road",
        ),
    )
    parser.add_argument("--candidate-limit", type=int, default=120)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.pairs_per_map < 1:
        parser.error("--pairs-per-map must be positive")
    if args.candidate_limit < args.pairs_per_map:
        parser.error("--candidate-limit must be >= --pairs-per-map")

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
            required_profiles=tuple(args.required_profiles),
            candidate_limit=args.candidate_limit,
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
