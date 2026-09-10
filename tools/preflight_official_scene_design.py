"""Offline topology preflight for official S2/S3 scene design.

This script loads CARLA OpenDRIVE maps without starting a simulator process. It
checks that at least one generic route anchor satisfies the declared lane and
speed corridors, resolves every actor, builds the complete out-and-back lane
change, and proves that event/lifecycle timing leaves enough route to finish.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.route_geometry import route_pose_at_s  # noqa: E402
from integration.route_manager import (  # noqa: E402
    LaneCorridorRequirement,
    RouteManager,
    RoutePlanningError,
    SpeedWindowRequirement,
)
from integration.route_planner import build_lane_change_route_reference  # noqa: E402
from integration.scenario_builder import (  # noqa: E402
    route_relative_carla_transform,
    route_relative_target_location,
    validate_actor_route_coverage,
    validate_actor_transform,
)
from tools.validate_official_scenes import SCENES, validate_all  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_xodr(map_name: str, explicit_root: Path | None) -> Path:
    roots = [explicit_root] if explicit_root is not None else []
    roots.extend((ROOT / "CARLA_0.9.16", ROOT.parents[1] / "CARLA_0.9.16"))
    relative = Path("CarlaUE4/Content/Carla/Maps/OpenDrive") / f"{map_name}.xodr"
    for root in roots:
        if root is not None and (candidate := root / relative).is_file():
            return candidate
    raise FileNotFoundError(
        f"cannot find {map_name}.xodr; pass --carla-root pointing to CARLA_0.9.16"
    )


def _progress_trigger(trigger: Any) -> float | None:
    if not isinstance(trigger, Mapping):
        return None
    if str(trigger.get("type", "")).lower() == "route_progress_greater_than_m":
        return float(trigger["value"])
    children = trigger.get("all", ())
    values = [
        result for child in children
        if (result := _progress_trigger(child)) is not None
    ] if isinstance(children, list) else []
    return max(values) if values else None


def _distance_triggers(trigger: Any) -> list[tuple[str, float]]:
    if not isinstance(trigger, Mapping):
        return []
    result: list[tuple[str, float]] = []
    if str(trigger.get("type", "")).lower() == "ego_distance_to_actor_less_than_m":
        result.append((str(trigger["actor_id"]), float(trigger["value"])))
    children = trigger.get("all", ())
    if isinstance(children, list):
        for child in children:
            result.extend(_distance_triggers(child))
    return result


def _route_candidates(world_map: Any) -> tuple[Any, ...]:
    waypoints = world_map.generate_waypoints(50.0)
    driving = [
        waypoint for waypoint in waypoints
        if str(getattr(waypoint, "lane_type", "Driving")).rsplit(".", 1)[-1].upper()
        == "DRIVING"
    ]
    driving.sort(key=lambda item: (
        int(item.road_id), int(item.section_id), int(item.lane_id), float(item.s),
    ))
    return tuple(waypoint.transform for waypoint in driving)


def _route_requirements(data: Mapping[str, Any]) -> tuple[
    tuple[LaneCorridorRequirement, ...], tuple[SpeedWindowRequirement, ...],
]:
    raw = data["route"]["topology_requirements"]
    return (
        tuple(LaneCorridorRequirement.from_mapping(item) for item in raw["lane_corridors"]),
        tuple(SpeedWindowRequirement.from_mapping(item) for item in raw["speed_windows"]),
    )


def _validate_speed_window_bindings(
    data: Mapping[str, Any],
    requirements: tuple[SpeedWindowRequirement, ...],
) -> dict[str, float]:
    actors = {str(actor["actor_id"]): actor for actor in data["actors"]}
    by_id = {item.requirement_id: item for item in requirements}
    result: dict[str, float] = {}
    for command in data["commands"][1:]:
        phase_id = str(command["phase_id"])
        requirement = by_id.get(phase_id)
        if requirement is None:
            raise ValueError(f"{phase_id}: missing curvature/speed requirement")
        effective_s = float(_progress_trigger(command["trigger"]) or 0.0)
        for actor_id, threshold_m in _distance_triggers(command["trigger"]):
            actor_s = float(actors[actor_id]["route_position"]["s_m"])
            effective_s = max(effective_s, actor_s - threshold_m)
        if not requirement.start_s_m <= effective_s <= requirement.end_s_m:
            raise ValueError(
                f"{phase_id}: effective trigger {effective_s:.2f}m lies outside "
                f"speed window {requirement.start_s_m:.2f}-{requirement.end_s_m:.2f}m"
            )
        result[phase_id] = round(effective_s, 3)
    return result


def _route_length(points: Any) -> float:
    return sum(math.dist(first, second) for first, second in zip(points, points[1:]))


def _validate_maneuvers(
    carla_api: Any,
    world_map: Any,
    manager: RouteManager,
    route: Any,
    data: Mapping[str, Any],
) -> list[dict[str, Any]]:
    actors = {str(actor["actor_id"]): actor for actor in data["actors"]}
    profile = data["extensions"]["lane_change_profile"]
    results: list[dict[str, Any]] = []
    for command in data["commands"]:
        if str(command.get("intent", "")).upper() != "AVOID_OBSTACLE":
            continue
        phase_id = str(command["phase_id"])
        direction = str(command["parameters"]["direction"]).upper()
        progress = _progress_trigger(command["trigger"])
        if progress is None:
            raise ValueError(f"{phase_id}: missing route-progress trigger")
        distances = _distance_triggers(command["trigger"])
        start_s = progress
        for actor_id, threshold_m in distances:
            actor_s = float(actors[actor_id]["route_position"]["s_m"])
            start_s = max(start_s, actor_s - threshold_m)
        pose = route_pose_at_s(route.reference.points_xy_m, start_s)
        parameters = {
            "distance_m": float(profile["route_distance_m"]),
            "step_m": float(profile["step_m"]),
            "transition_start_m": float(profile["transition_start_m"]),
            "transition_length_m": float(profile["transition_length_m"]),
            "target_lane_offset_m": float(profile["target_lane_offset_m"]),
        }
        outbound = build_lane_change_route_reference(
            world_map,
            carla_api.Location(x=pose.x_m, y=pose.y_m, z=0.0),
            route.reference.target_speed_mps,
            direction=direction,
            **parameters,
        )
        target_actor_id = str(command["parameters"]["target_actor_id"])
        target_s = float(actors[target_actor_id]["route_position"]["s_m"])
        return_s = max(start_s + float(profile["transition_start_m"]), target_s + 20.0)
        adjacent = manager.placement(route, return_s, direction)
        reverse = "RIGHT" if direction == "LEFT" else "LEFT"
        inbound = build_lane_change_route_reference(
            world_map,
            carla_api.Location(x=adjacent.x_m, y=adjacent.y_m, z=adjacent.z_m),
            route.reference.target_speed_mps,
            direction=reverse,
            **parameters,
        )
        minimum_length = float(profile["route_distance_m"]) * 0.8
        if _route_length(outbound.points_xy_m) < minimum_length:
            raise ValueError(f"{phase_id}: outbound lane-change route is incomplete")
        if _route_length(inbound.points_xy_m) < minimum_length:
            raise ValueError(f"{phase_id}: return lane-change route is incomplete")
        results.append({
            "phase_id": phase_id,
            "start_s_m": round(start_s, 3),
            "return_s_m": round(return_s, 3),
            "outbound_length_m": round(_route_length(outbound.points_xy_m), 3),
            "return_length_m": round(_route_length(inbound.points_xy_m), 3),
        })
    return results


def _validate_completion(data: Mapping[str, Any]) -> dict[str, float]:
    route_distance = float(data["route"]["distance_contract_m"])
    final_actor_exit = max(
        float(actor["deactivation_trigger"]["value"])
        for actor in data["actors"]
    )
    final_command = float(_progress_trigger(data["commands"][-1]["trigger"]) or 0.0)
    if final_actor_exit >= route_distance:
        raise ValueError("final actor lifecycle leaves no route-completion margin")
    if final_command >= route_distance:
        raise ValueError("final command cannot complete before route end")
    extensions = data["extensions"]
    if str(data["commands"][-1]["intent"]).upper() == "EMERGENCY_STOP":
        recovery = extensions.get("hazard_recovery", {})
        phase_ids = recovery.get("after_phase_ids", ()) if isinstance(recovery, Mapping) else ()
        if data["commands"][-1]["phase_id"] not in phase_ids:
            raise ValueError("final emergency stop has no hazard-clear recovery")
    speed_kph = float(extensions["speed_policy"]["scenario_limit_kph"])
    moving_budget_s = route_distance / (speed_kph / 3.6)
    duration_s = float(data["runtime"]["duration_s"])
    # Include acceleration, traffic-light waits, manoeuvre deceleration and
    # emergency holds instead of budgeting only nominal distance/speed.
    if duration_s < moving_budget_s * 1.5:
        raise ValueError("runtime budget cannot cover route plus event holds")
    return {
        "final_actor_exit_s_m": final_actor_exit,
        "route_completion_margin_m": route_distance - final_actor_exit,
        "minimum_moving_time_s": round(moving_budget_s, 3),
        "minimum_runtime_with_event_reserve_s": round(moving_budget_s * 1.5, 3),
        "runtime_budget_s": duration_s,
    }


def _preflight_scene(
    carla_api: Any,
    label: str,
    data: dict[str, Any],
    xodr: Path,
) -> dict[str, Any]:
    world_map = carla_api.Map(data["map"], xodr.read_text(encoding="utf-8"))
    manager = RouteManager(world_map, sample_step_m=1.0)
    lane_corridors, speed_windows = _route_requirements(data)
    effective_triggers = _validate_speed_window_bindings(data, speed_windows)
    candidates = _route_candidates(world_map)
    try:
        selected_index, route = manager.plan_distance_compatible(
            candidates,
            float(data["route"]["distance_contract_m"]),
            float(data["extensions"]["speed_policy"]["scenario_limit_kph"]) / 3.6,
            lane_corridors=lane_corridors,
            speed_windows=speed_windows,
        )
    except RoutePlanningError as error:
        failures = error.context.get("failures", ())
        counts = Counter(str(item.get("code", "UNKNOWN")) for item in failures)
        example_by_code = {}
        for item in failures:
            example_by_code.setdefault(str(item.get("code", "UNKNOWN")), item.get("detail"))
        raise ValueError(
            f"{label}: no compatible route; reasons={dict(counts)}; examples={example_by_code}"
        ) from error
    validate_actor_route_coverage(data["actors"], route.total_length_m)
    actor_results = []
    for actor in data["actors"]:
        actor_s_m = float(actor["route_position"]["s_m"])
        activation_s_m = _progress_trigger(actor.get("activation_trigger"))
        if activation_s_m is None:
            raise ValueError(f"{actor['actor_id']}: missing route-progress activation")
        activation_lead_m = actor_s_m - activation_s_m
        if activation_lead_m < 0.0 or activation_lead_m > 180.0:
            raise ValueError(
                f"{actor['actor_id']}: activation lead {activation_lead_m:.1f}m "
                "must stay within [0, 180]m to avoid premature actors on looping routes"
            )
        transform = route_relative_carla_transform(
            carla_api, world_map, route.reference.points_xy_m, actor,
        )
        validate_actor_transform(world_map, transform, actor)
        behavior = actor.get("behavior", {})
        if isinstance(behavior, Mapping) and behavior.get("target_route_position") is not None:
            route_relative_target_location(
                carla_api, world_map, route.reference.points_xy_m, actor,
            )
        actor_results.append({
            "actor_id": actor["actor_id"],
            "route_s_m": actor_s_m,
            "activation_lead_m": activation_lead_m,
            "resolved_road_id": int(world_map.get_waypoint(transform.location).road_id),
            "resolved_lane_id": int(world_map.get_waypoint(transform.location).lane_id),
        })
    anchor = world_map.get_waypoint(candidates[selected_index].location)
    route_result = {
        "scenario_id": data["scenario_id"],
        "map": data["map"],
        "route": {
            "candidate_count": len(candidates),
            "selected_candidate_index": selected_index,
            "selected_road_id": int(anchor.road_id),
            "selected_lane_id": int(anchor.lane_id),
            "selected_road_s_m": round(float(anchor.s), 3),
            "length_m": round(route.total_length_m, 3),
            "lane_corridors": len(lane_corridors),
            "speed_windows": len(speed_windows),
            "effective_event_triggers_s_m": effective_triggers,
        },
        "actors": actor_results,
        "maneuvers": _validate_maneuvers(carla_api, world_map, manager, route, data),
        "completion": _validate_completion(data),
        "validation": "PASS",
    }
    return route_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--carla-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scene", choices=("S2", "S3"))
    args = parser.parse_args()
    import carla

    validate_all()
    labels = (args.scene,) if args.scene else ("S2", "S3")
    results = {
        label: _preflight_scene(
            carla,
            label,
            _load(SCENES[label]),
            _find_xodr(_load(SCENES[label])["map"], args.carla_root),
        )
        for label in labels
    }
    payload = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    print("SCENE_DESIGN_PREFLIGHT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
