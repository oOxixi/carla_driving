"""CARLA-independent contract checks for the three official competition scenes."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.scenario_execution import ScenarioSpec  # noqa: E402
from tools.validate_scenarios import validate_one  # noqa: E402


SCENE_DIR = ROOT / "scenarios" / "official_competition"
SCENES = {
    "S1": SCENE_DIR / "S1_basic_voice_control_5km.json",
    "S2": SCENE_DIR / "S2_complex_avoidance_8km.json",
    "S3": SCENE_DIR / "S3_extreme_emergency_6km.json",
}


class ContractFailure(AssertionError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractFailure(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _route_length(points: Iterable[Iterable[float]]) -> float:
    parsed = [tuple(map(float, point)) for point in points]
    return sum(math.dist(first, second) for first, second in zip(parsed, parsed[1:]))


def _actor_ids(data: dict[str, Any]) -> set[str]:
    return {str(actor.get("actor_id", "")) for actor in data.get("actors", [])}


def _trigger_actor_ids(trigger: Any) -> set[str]:
    if not isinstance(trigger, dict):
        return set()
    result = {
        str(trigger["actor_id"])
        for _ in (0,)
        if trigger.get("actor_id") is not None
    }
    children = trigger.get("all", ())
    if isinstance(children, list):
        for child in children:
            result.update(_trigger_actor_ids(child))
    return result


def _trigger_route_progress_m(trigger: Any) -> float | None:
    if not isinstance(trigger, dict):
        return None
    if str(trigger.get("type", "")).lower() == "route_progress_greater_than_m":
        return float(trigger.get("value", 0.0))
    children = trigger.get("all", ())
    if isinstance(children, list):
        values = [
            value for child in children
            if (value := _trigger_route_progress_m(child)) is not None
        ]
        return max(values) if values else None
    return None


def _triggers_of_type(trigger: Any, trigger_type: str) -> list[dict[str, Any]]:
    if not isinstance(trigger, dict):
        return []
    result = [trigger] if str(trigger.get("type", "")).lower() == trigger_type.lower() else []
    children = trigger.get("all", ())
    if isinstance(children, list):
        for child in children:
            result.extend(_triggers_of_type(child, trigger_type))
    return result


def _validate_route_designed_events(label: str, data: dict[str, Any]) -> None:
    route = data["route"]
    _require(route.get("planning_mode") == "topology_coverage", f"{label}: topology_coverage route required")
    topology = route.get("topology_requirements", {})
    _require(isinstance(topology, dict), f"{label}: topology requirements must be an object")
    _require(topology.get("lane_corridors"), f"{label}: lane corridor requirements are missing")
    _require(topology.get("speed_windows"), f"{label}: curvature/speed windows are missing")
    _require("route_anchor_spawn_index" not in data["extensions"], f"{label}: fixed spawn anchor is forbidden")
    requirements = set(data["extensions"]["runtime_support"]["requirements"])
    _require("compatible_topology_route" in requirements, f"{label}: compatible route selection is undeclared")

    previous_phase = str(data["commands"][0]["phase_id"])
    actors_by_id = {
        str(actor.get("actor_id", "")): actor
        for actor in data["actors"]
    }
    for command in data["commands"][1:]:
        trigger = command.get("trigger")
        terminals = _triggers_of_type(trigger, "previous_command_terminal")
        progress = _triggers_of_type(trigger, "route_progress_greater_than_m")
        distances = _triggers_of_type(trigger, "ego_distance_to_actor_less_than_m")
        phase_id = str(command["phase_id"])
        _require(
            len(terminals) == 1 and terminals[0].get("phase_id") == previous_phase,
            f"{label}: {phase_id} must depend on completion of {previous_phase}",
        )
        _require(progress and distances, f"{label}: {phase_id} needs progress and actor-distance gates")
        for distance_gate in distances:
            actor_id = str(distance_gate.get("actor_id", ""))
            actor = actors_by_id.get(actor_id, {})
            behavior = actor.get("behavior", {}) if isinstance(actor, dict) else {}
            motion_gates = _triggers_of_type(
                behavior.get("trigger"), "ego_distance_to_actor_less_than_m"
            )
            for event in behavior.get("events", ()) if isinstance(behavior, dict) else ():
                if isinstance(event, dict):
                    motion_gates.extend(_triggers_of_type(
                        event.get("trigger"), "ego_distance_to_actor_less_than_m"
                    ))
            self_motion_gates = [
                gate for gate in motion_gates
                if str(gate.get("actor_id", "")) == actor_id
            ]
            if self_motion_gates:
                command_distance = float(distance_gate.get("value", 0.0))
                motion_distance = max(float(gate.get("value", 0.0)) for gate in self_motion_gates)
                _require(
                    command_distance >= motion_distance,
                    f"{label}: {phase_id} can miss moving actor {actor_id}; "
                    f"command distance {command_distance:g}m is below actor motion distance {motion_distance:g}m",
                )
        previous_phase = phase_id

    for actor in data["actors"]:
        actor_id = str(actor.get("actor_id", ""))
        _require(isinstance(actor.get("route_position"), dict), f"{label}: {actor_id} needs route_position")
        start = _trigger_route_progress_m(actor.get("activation_trigger"))
        end = _trigger_route_progress_m(actor.get("deactivation_trigger"))
        _require(start is not None and end is not None and end > start, f"{label}: {actor_id} has invalid lifecycle")


def _validate_common(label: str, path: Path, data: dict[str, Any]) -> ScenarioSpec:
    generic_errors = validate_one(path)
    _require(not generic_errors, f"{label}: generic scenario errors: {generic_errors}")
    spec = ScenarioSpec.load(path)
    _require(data["seed"] > 0, f"{label}: fixed positive seed required")
    _require(data["runtime"]["sync_mode"] is True, f"{label}: synchronous mode required")
    _require(data["runtime"]["fixed_delta_seconds"] == 0.05, f"{label}: fixed delta must be 0.05s")
    _require(data["expected"]["must_start_carla"] is True, f"{label}: startup proof required")
    _require(data["expected"]["must_spawn_ego"] is True, f"{label}: ego spawn proof required")
    _require(data["expected"]["must_finish_route"] is True, f"{label}: route completion required")
    _require(data["expected"]["must_no_collision"] is True, f"{label}: zero collision required")
    _require(data["expected"]["must_generate_logs"] is True, f"{label}: evidence logs required")
    _require(data["extensions"]["fixed_random_seed"] is True, f"{label}: fixed_random_seed marker required")
    _require(data["extensions"].get("input_mode") == "raw_text_qwen", f"{label}: raw_text_qwen input required")
    qwen_policy = data["extensions"].get("qwen_policy", {})
    _require(isinstance(qwen_policy, dict), f"{label}: qwen_policy must be an object")
    _require(qwen_policy.get("required_for_every_voice_event") is True, f"{label}: every normal voice event must be Qwen-audited")
    _require(qwen_policy.get("high_level_only") is True, f"{label}: Qwen must remain high-level only")
    _require(qwen_policy.get("safety_preemption") is True, f"{label}: local safety preemption required")
    _require(len(data["commands"]) >= 4, f"{label}: command/event sequence is incomplete")
    _require(all(command.get("phase_id") for command in data["commands"]), f"{label}: each command needs phase_id")
    actor_ids = _actor_ids(data)
    for command in data["commands"]:
        trigger = command.get("trigger", {})
        for trigger_actor in _trigger_actor_ids(trigger):
            _require(trigger_actor in actor_ids, f"{label}: trigger references unknown actor {trigger_actor}")
    required_qwen_metrics = {
        "qwen_route", "qwen_request_id", "qwen_plan", "qwen_latency_ms",
        "command_step_status", "command_terminal", "sensor_to_control_ms",
    }
    actual_metrics = set(data.get("logging", {}).get("required_metrics", ()))
    _require(required_qwen_metrics.issubset(actual_metrics), f"{label}: Qwen/e2e evidence metrics incomplete")
    _require(
        data["logging"].get("required_files") == ["*.jsonl", "*.summary.json"],
        f"{label}: evidence filenames must match ScenarioEvidenceRecorder outputs",
    )
    required_summary = {
        "acceptance", "latency", "score", "score_report", "command_terminal_statuses",
    }
    actual_summary = set(data["logging"].get("required_summary_sections", ()))
    _require(required_summary.issubset(actual_summary), f"{label}: summary evidence sections incomplete")
    return spec


def validate_all() -> dict[str, Any]:
    loaded = {label: _load(path) for label, path in SCENES.items()}
    specs = {
        label: _validate_common(label, SCENES[label], data)
        for label, data in loaded.items()
    }

    s1 = loaded["S1"]
    _require(s1["map"] == "Town05" and s1["weather"] == "ClearNoon", "S1: map/weather mismatch")
    _require(abs(_route_length(s1["route"]["points_xy_m"]) - 5000.0) < 1e-6, "S1: route must be 5km")
    _require(s1["actors"] == [], "S1: dynamic interference is forbidden")
    s1_intents = {command["intent"] for command in s1["commands"]}
    _require({"KEEP_LANE", "TURN_RIGHT", "CHANGE_LANE_LEFT"}.issubset(s1_intents), "S1: missing base manoeuvres")
    _require(s1["competition_requirements"]["lane_invasion_max"] == 0, "S1: lane invasion must be zero")
    _require(s1["runtime"]["duration_s"] >= 500.0, "S1: runtime budget is too short for 5km with manoeuvres")
    _require(s1["qwen_expected"]["min_calls"] == len(s1["commands"]), "S1: every command must call Qwen")
    _require(s1["qwen_expected"]["max_calls"] == len(s1["commands"]), "S1: unexpected Qwen call budget")

    s2 = loaded["S2"]
    _require(s2["map"] == "Town03_Opt" and s2["weather"] == "CloudySunset", "S2: map/weather mismatch")
    _require(abs(_route_length(s2["route"]["points_xy_m"]) - 8000.0) < 1e-6, "S2: route must be 8km")
    _validate_route_designed_events("S2", s2)
    required_s2 = {
        "bus_at_stop", "crossing_pedestrian", "slow_vehicle", "bicycle_ahead",
        "intersection_cut_in_car", "late_crossing_pedestrian",
    }
    _require(required_s2.issubset(_actor_ids(s2)), f"S2: missing actors {sorted(required_s2 - _actor_ids(s2))}")
    bus = next(actor for actor in s2["actors"] if actor["actor_id"] == "bus_at_stop")
    _require(
        str(bus.get("route_position", {}).get("lane_relation", "")).upper()
        in {"LEFT_ADJACENT", "RIGHT_ADJACENT"},
        "S2: stopped bus must remain in a real adjacent station-side lane",
    )
    _require(s2["extensions"]["sensor_profile"] == "competition_multiview", "S2: multiview profile required")
    _require({"front_rgb", "left_rgb", "right_rgb", "rear_rgb", "lidar"}.issubset(s2["sensors"]), "S2: sensor set incomplete")
    _require(s2["competition_requirements"]["return_to_route_required"] is True, "S2: return-to-route required")
    _require(s2["competition_requirements"]["lane_invasion_max"] == 0, "S2: lane invasion must be zero")
    _require(s2["expected"]["must_no_lane_invasion"] is True, "S2: lane-invasion acceptance is required")
    _require(float(s2["commands"][0]["parameters"]["target_speed_kph"]) > 30.0, "S2: bus-stop phase needs a measurable deceleration")
    _require(
        float(s2["commands"][1]["parameters"]["target_speed_kph"]) == 30.0,
        "S2: bus-stop instruction must reduce speed to 30km/h",
    )
    event_progress = [
        _trigger_route_progress_m(command.get("trigger"))
        for command in s2["commands"][1:]
    ]
    _require(all(value is not None for value in event_progress), "S2: every event must be route-progress gated")
    distributed = [float(value) for value in event_progress if value is not None]
    _require(
        len(distributed) >= 5
        and distributed[0] >= 800.0
        and distributed[-1] >= 6800.0
        and all(800.0 <= second - first <= 2000.0 for first, second in zip(distributed, distributed[1:])),
        "S2: events must be distributed through the full 8km route",
    )
    composite_text = str(s2["commands"][2].get("source_text", ""))
    _require(
        all(token in composite_text for token in ("行人", "减速", "变道", "超越", "回到原车道", "恢复")),
        "S2: pedestrian/overtake command must remain one complete composite instruction",
    )
    _require(float(s2["expected"]["min_front_gap_m"]) >= 3.0, "S2: bicycle clearance must be at least 3m")
    _require(s2["qwen_expected"]["min_calls"] == len(s2["commands"]), "S2: every combination command must call Qwen")
    _require(s2["qwen_expected"]["max_calls"] == len(s2["commands"]), "S2: unexpected Qwen call budget")
    s2_extensions = s2["extensions"]
    s2_acceptance = s2_extensions["proposed_acceptance"]
    _require(s2_acceptance["must_return_to_original_lane"] is True, "S2: route return needs executable acceptance")
    _require(
        s2_acceptance["minimum_actor_distances_m"] == {"bicycle_ahead": 3.0},
        "S2: bicycle-specific 3m clearance acceptance is required",
    )
    _require(float(s2_acceptance["maximum_route_deviation_m"]) <= 1.0, "S2: route deviation acceptance is too loose")
    _require(s2_extensions.get("maneuver_route_mode") == "dynamic_out_and_back", "S2: dynamic out-and-back route required")
    lane_profile = s2_extensions.get("lane_change_profile", {})
    _require(float(lane_profile.get("route_distance_m", 0.0)) >= 60.0, "S2: manoeuvre route is too short")
    _require(float(lane_profile.get("transition_start_m", -1.0)) >= 0.0, "S2: invalid lane transition start")
    _require(float(lane_profile.get("transition_length_m", 0.0)) >= 20.0, "S2: lane transition is too abrupt")
    runtime_requirements = set(s2_extensions["runtime_support"]["requirements"])
    _require(
        {
            "dynamic_out_and_back_route", "per_actor_minimum_distance_acceptance",
            "route_progress_actor_activation", "route_progress_actor_lifecycle",
            "route_progress_speed_acceptance",
        }.issubset(runtime_requirements),
        "S2: runtime requirements do not declare the member-3 route/distance owners",
    )
    speed_policy = s2_extensions.get("speed_policy", {})
    _require(
        float(speed_policy.get("scenario_limit_kph", 0.0)) > 30.0
        and speed_policy.get("map_limit_handling") == "replace",
        "S2: Town03_Opt needs an explicit >30km/h competition cruise contract",
    )
    activations = [
        float(actor.get("activation_trigger", {}).get("value", -1.0))
        for actor in s2["actors"]
    ]
    _require(
        all(value >= 0.0 for value in activations),
        "S2: every distributed actor must be activated by route progress",
    )
    deactivations = [
        float(actor.get("deactivation_trigger", {}).get("value", -1.0))
        for actor in s2["actors"]
    ]
    _require(
        all(end > start for start, end in zip(activations, deactivations)),
        "S2: every distributed actor must retire after its activation window",
    )
    passenger_triggers = [
        actor.get("behavior", {}).get("trigger")
        for actor in s2["actors"]
        if str(actor.get("actor_id", "")).startswith("bus_passenger_")
    ]
    _require(all(isinstance(item, dict) for item in passenger_triggers), "S2: bus passengers must be ego-triggered")
    bicycle = next(actor for actor in s2["actors"] if actor["actor_id"] == "bicycle_ahead")
    _require(
        bicycle["route_position"].get("lane_relation") == "CURRENT"
        and bicycle["behavior"].get("mode") == "lead_vehicle",
        "S2: bicycle must be a slow lead actor in the current lane",
    )
    cut_in_s2 = next(actor for actor in s2["actors"] if actor["actor_id"] == "intersection_cut_in_car")
    _require(
        cut_in_s2["route_position"].get("lane_relation") == "LEFT_ADJACENT"
        and cut_in_s2["behavior"].get("direction") == "RIGHT",
        "S2: cut-in must enter rightward from the left adjacent lane",
    )

    s3 = loaded["S3"]
    _require(s3["map"] == "Town04" and s3["weather"] == "HardRainNight", "S3: map/weather mismatch")
    _require(abs(_route_length(s3["route"]["points_xy_m"]) - 6000.0) < 1e-6, "S3: route must be 6km")
    _validate_route_designed_events("S3", s3)
    required_s3 = {"construction_warning", "cut_in_vehicle", "emergency_pedestrian"}
    _require(required_s3.issubset(_actor_ids(s3)), f"S3: missing actors {sorted(required_s3 - _actor_ids(s3))}")
    cones = [actor for actor in s3["actors"] if actor.get("blueprint_id") == "static.prop.trafficcone01"]
    _require(len(cones) >= 5, "S3: at least five cones are required to show lane narrowing")
    cut_in = next(actor for actor in s3["actors"] if actor["actor_id"] == "cut_in_vehicle")
    _require(cut_in["behavior"]["mode"] == "cut_in", "S3: cut-in actor needs deterministic lateral behaviour")
    _require(cut_in["behavior"].get("cut_in_on_first_event") is True, "S3: cut-in must be proximity-event driven")
    cut_in_events = cut_in["behavior"].get("events", [])
    _require(len(cut_in_events) == 1, "S3: cut-in needs exactly one deterministic start event")
    cut_in_trigger = cut_in_events[0].get("trigger", {})
    cut_in_distance_triggers = _triggers_of_type(cut_in_trigger, "ego_distance_to_actor_less_than_m")
    _require(
        len(cut_in_distance_triggers) == 1
        and cut_in_distance_triggers[0].get("actor_id") == "cut_in_vehicle",
        "S3: cut-in start must be bound to ego proximity",
    )
    _require(
        25.0 <= float(cut_in_distance_triggers[0].get("value", 0.0)) <= 35.0,
        "S3: cut-in proximity threshold is unsafe",
    )
    _require(
        cut_in["route_position"].get("lane_relation") == "LEFT_ADJACENT"
        and cut_in["behavior"].get("direction") == "RIGHT",
        "S3: cut-in direction and source lane are inconsistent",
    )
    s3_event_progress = [
        float(_trigger_route_progress_m(command["trigger"]))
        for command in s3["commands"][1:]
    ]
    _require(
        1700.0 <= s3_event_progress[0] <= 1900.0
        and 3600.0 <= s3_event_progress[1] <= 3900.0
        and 5300.0 <= s3_event_progress[2] <= 5550.0,
        "S3: construction/cut-in/pedestrian must be distributed near 1.8/3.7/5.4km",
    )
    _require(s3["extensions"]["sensor_profile"] == "competition_multiview", "S3: multiview profile required")
    weather = s3["extensions"]["weather_parameters"]
    _require(weather["precipitation"] >= 80 and weather["wetness"] == 100, "S3: heavy rain/wet road missing")
    _require(weather["sun_altitude_angle"] < 0 and weather["fog_density"] >= 30, "S3: night/fog conditions missing")
    _require(s3["runtime"]["duration_s"] >= 1000.0, "S3: runtime budget is too short for 6km plus event holds")
    _require(
        "恢复35公里每小时" in s3["commands"][1]["source_text"],
        "S3: construction detour must restore the declared rain cruise speed",
    )
    s3_qwen = s3["extensions"]["proposed_acceptance"]
    _require(s3_qwen["qwen_request_count"] == 2, "S3: two normal semantic commands must call Qwen")
    _require(s3["qwen_expected"]["route"] == "MIXED", "S3: mixed Qwen/safety routing contract required")
    _require(
        s3["qwen_expected"]["route_counts"]
        == {"QWEN_PLAN": 2, "FAST_LOCAL": 2, "CONFIRM_SAFE": 0},
        "S3: expected routes must be two Qwen plans and two local emergencies",
    )
    _require(s3["extensions"]["qwen_policy"].get("emergency_fast_local") is True, "S3: emergency fast-local exception must be explicit")
    recovery = s3["extensions"].get("hazard_recovery", {})
    _require(
        recovery.get("after_phase_ids")
        == ["S3_P3_CUT_IN_EMERGENCY", "S3_P4_PEDESTRIAN_STOP_HOLD"]
        and int(recovery.get("clear_frames", 0)) >= 2
        and float(recovery.get("minimum_hold_s", 0.0)) > 0.0,
        "S3: both emergency stops need sensor-cleared hold recovery",
    )
    _require(
        s3_qwen.get("hazard_recovery_count") == 2
        and float(s3_qwen.get("restart_displacement_m", 0.0)) > 0.0,
        "S3: recovery and post-stop route completion need executable acceptance",
    )

    ids = [spec.scenario_id for spec in specs.values()]
    _require(len(ids) == len(set(ids)), "scenario_id values must be unique")
    seeds = [spec.seed for spec in specs.values()]
    _require(len(seeds) == len(set(seeds)), "fixed seeds must be unique")
    return {
        label: {
            "scenario_id": specs[label].scenario_id,
            "map": specs[label].map_name,
            "weather": specs[label].weather,
            "seed": specs[label].seed,
            "route_distance_m": _route_length(loaded[label]["route"]["points_xy_m"]),
            "commands": len(specs[label].commands),
            "actors": len(specs[label].actors),
            "sensor_profile": loaded[label]["extensions"]["sensor_profile"],
            "validation": "PASS",
        }
        for label in ("S1", "S2", "S3")
    }


def main() -> None:
    try:
        result = validate_all()
    except (ContractFailure, KeyError, TypeError, ValueError) as error:
        print(f"OFFICIAL_SCENE_VALIDATION=FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("OFFICIAL_SCENE_VALIDATION=PASS")


if __name__ == "__main__":
    main()
