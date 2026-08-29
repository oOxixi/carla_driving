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
    _require(len(data["commands"]) >= 4, f"{label}: command/event sequence is incomplete")
    _require(all(command.get("phase_id") for command in data["commands"]), f"{label}: each command needs phase_id")
    actor_ids = _actor_ids(data)
    for command in data["commands"]:
        trigger = command.get("trigger", {})
        trigger_actor = trigger.get("actor_id") if isinstance(trigger, dict) else None
        if trigger_actor is not None:
            _require(str(trigger_actor) in actor_ids, f"{label}: trigger references unknown actor {trigger_actor}")
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

    s2 = loaded["S2"]
    _require(s2["map"] == "Town03" and s2["weather"] == "CloudySunset", "S2: map/weather mismatch")
    _require(abs(_route_length(s2["route"]["points_xy_m"]) - 8000.0) < 1e-6, "S2: route must be 8km")
    required_s2 = {"bus_at_stop", "crossing_pedestrian", "slow_vehicle", "bicycle_right"}
    _require(required_s2.issubset(_actor_ids(s2)), f"S2: missing actors {sorted(required_s2 - _actor_ids(s2))}")
    bus = next(actor for actor in s2["actors"] if actor["actor_id"] == "bus_at_stop")
    _require(abs(float(bus["spawn"]["y"])) >= 3.0, "S2: stopped bus must remain at the station-side lane")
    _require(s2["extensions"]["sensor_profile"] == "competition_multiview", "S2: multiview profile required")
    _require({"front_rgb", "left_rgb", "right_rgb", "rear_rgb", "lidar"}.issubset(s2["sensors"]), "S2: sensor set incomplete")
    _require(s2["competition_requirements"]["return_to_route_required"] is True, "S2: return-to-route required")

    s3 = loaded["S3"]
    _require(s3["map"] == "Town04" and s3["weather"] == "HardRainNight", "S3: map/weather mismatch")
    _require(abs(_route_length(s3["route"]["points_xy_m"]) - 6000.0) < 1e-6, "S3: route must be 6km")
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
    _require(
        cut_in_trigger.get("type") == "ego_distance_to_actor_less_than_m"
        and cut_in_trigger.get("actor_id") == "cut_in_vehicle",
        "S3: cut-in start must be bound to ego proximity",
    )
    _require(25.0 <= float(cut_in_trigger.get("value", 0.0)) <= 35.0, "S3: cut-in proximity threshold is unsafe")
    _require(s3["extensions"]["sensor_profile"] == "competition_multiview", "S3: multiview profile required")
    weather = s3["extensions"]["weather_parameters"]
    _require(weather["precipitation"] >= 80 and weather["wetness"] == 100, "S3: heavy rain/wet road missing")
    _require(weather["sun_altitude_angle"] < 0 and weather["fog_density"] >= 30, "S3: night/fog conditions missing")

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
