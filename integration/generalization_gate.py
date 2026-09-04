"""Deterministic scenario perturbations for pre-CARLA generalization gates."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from .scenario_builder import offset_actor_route_position


DEFAULT_MATRIX_PATH = Path(__file__).resolve().parents[1] / "config" / "generalization_matrix.json"


def _sequence(raw: object, name: str) -> tuple[object, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"generalization matrix {name} must be a non-empty list")
    return tuple(raw)


@dataclass(frozen=True, slots=True)
class PerturbationCase:
    case_id: str
    map_name: str
    weather: str
    seed: int
    fixed_delta_s: float
    actor_longitudinal_offset_m: float
    actor_lateral_offset_m: float
    actor_speed_scale: float
    brake_time_offset_s: float
    pedestrian_start_offset_s: float
    actor_count_scale: float
    target_lane_relation: str
    sensor_condition: str


@dataclass(frozen=True, slots=True)
class GeneralizationMatrix:
    source_path: Path
    maps: tuple[str, ...]
    weather_profiles: tuple[str, ...]
    seeds: tuple[int, ...]
    fixed_delta_seconds: tuple[float, ...]
    actor_longitudinal_offsets_m: tuple[float, ...]
    actor_lateral_offsets_m: tuple[float, ...]
    actor_speed_scales: tuple[float, ...]
    brake_time_offsets_s: tuple[float, ...]
    pedestrian_start_offsets_s: tuple[float, ...]
    actor_count_scales: tuple[float, ...]
    target_lane_relations: tuple[str, ...]
    sensor_conditions: tuple[str, ...]
    samples_per_scenario: int
    holdout_scenarios: tuple[str, ...]

    def cases(self, scenario_id: str) -> Iterator[PerturbationCase]:
        """Yield a bounded Latin-cycle sample instead of an explosive product."""
        for index in range(self.samples_per_scenario):
            yield PerturbationCase(
                case_id=f"{scenario_id}__GEN_{index:03d}",
                map_name=self.maps[index % len(self.maps)],
                weather=self.weather_profiles[(index * 2) % len(self.weather_profiles)],
                seed=self.seeds[(index * 3) % len(self.seeds)],
                fixed_delta_s=self.fixed_delta_seconds[(index * 5) % len(self.fixed_delta_seconds)],
                actor_longitudinal_offset_m=self.actor_longitudinal_offsets_m[(index * 7) % len(self.actor_longitudinal_offsets_m)],
                actor_lateral_offset_m=self.actor_lateral_offsets_m[(index * 11) % len(self.actor_lateral_offsets_m)],
                actor_speed_scale=self.actor_speed_scales[(index * 13) % len(self.actor_speed_scales)],
                brake_time_offset_s=self.brake_time_offsets_s[(index * 17) % len(self.brake_time_offsets_s)],
                pedestrian_start_offset_s=self.pedestrian_start_offsets_s[(index * 19) % len(self.pedestrian_start_offsets_s)],
                actor_count_scale=self.actor_count_scales[(index * 23) % len(self.actor_count_scales)],
                target_lane_relation=self.target_lane_relations[(index * 29) % len(self.target_lane_relations)],
                sensor_condition=self.sensor_conditions[(index * 31) % len(self.sensor_conditions)],
            )


def load_generalization_matrix(path: str | Path | None = None) -> GeneralizationMatrix:
    source = DEFAULT_MATRIX_PATH if path is None else Path(path).expanduser().resolve()
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != "1.0":
        raise ValueError("generalization matrix schema_version must be '1.0'")
    maps = tuple(str(item) for item in _sequence(raw.get("maps"), "maps"))
    weather = tuple(str(item) for item in _sequence(raw.get("weather_profiles"), "weather_profiles"))
    seeds_raw = _sequence(raw.get("seeds"), "seeds")
    if any(type(item) is not int or isinstance(item, bool) for item in seeds_raw):
        raise TypeError("generalization matrix seeds must be integers")

    def numbers(name: str, *, positive: bool = False) -> tuple[float, ...]:
        values = _sequence(raw.get(name), name)
        result = tuple(float(item) for item in values)
        if any(not math.isfinite(item) or (positive and item <= 0.0) for item in result):
            raise ValueError(f"generalization matrix {name} contains invalid values")
        return result

    samples = raw.get("samples_per_scenario")
    if type(samples) is not int or samples < 1:
        raise ValueError("samples_per_scenario must be a positive integer")
    holdout = tuple(str(item) for item in _sequence(raw.get("holdout_scenarios"), "holdout_scenarios"))
    lane_relations = tuple(
        str(item).strip().upper()
        for item in _sequence(raw.get("target_lane_relations"), "target_lane_relations")
    )
    allowed_lanes = {"CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT"}
    if any(item not in allowed_lanes for item in lane_relations):
        raise ValueError("generalization matrix target_lane_relations contains an unsupported lane")
    sensor_conditions = tuple(
        str(item).strip().lower()
        for item in _sequence(raw.get("sensor_conditions"), "sensor_conditions")
    )
    allowed_sensors = {"nominal", "reduced_rgb", "sparse_lidar"}
    if any(item not in allowed_sensors for item in sensor_conditions):
        raise ValueError("generalization matrix sensor_conditions contains an unsupported profile")
    return GeneralizationMatrix(
        source,
        maps,
        weather,
        tuple(int(item) for item in seeds_raw),
        numbers("fixed_delta_seconds", positive=True),
        numbers("actor_longitudinal_offsets_m"),
        numbers("actor_lateral_offsets_m"),
        numbers("actor_speed_scales", positive=True),
        numbers("brake_time_offsets_s"),
        numbers("pedestrian_start_offsets_s"),
        numbers("actor_count_scales", positive=True),
        lane_relations,
        sensor_conditions,
        samples,
        holdout,
    )


def _referenced_actor_ids(scenario: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in {"actor_id", "target_actor_id"} and isinstance(child, str):
                    result.add(child)
                else:
                    visit(child)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for child in value:
                visit(child)

    for key in ("commands", "expected", "qwen_expected", "extensions"):
        visit(scenario.get(key))
    return result


def _scale_auxiliary_vehicles(
    actors: list[dict[str, Any]],
    scale: float,
    referenced_actor_ids: set[str],
) -> list[dict[str, Any]]:
    vehicles = [
        actor for actor in actors
        if str(actor.get("type", "")).lower() == "vehicle"
    ]
    if not vehicles:
        return actors
    target_count = max(1, round(len(vehicles) * float(scale)))
    auxiliary = [
        actor for actor in vehicles
        if str(actor.get("actor_id", "")) not in referenced_actor_ids
    ]
    result = list(actors)
    while len([item for item in result if str(item.get("type", "")).lower() == "vehicle"]) > target_count and auxiliary:
        result.remove(auxiliary.pop())
    source_index = 0
    while len([item for item in result if str(item.get("type", "")).lower() == "vehicle"]) < target_count and auxiliary:
        source = auxiliary[source_index % len(auxiliary)]
        clone_index = source_index + 1
        clone = offset_actor_route_position(source, longitudinal_m=12.0 * clone_index)
        clone["actor_id"] = f"{source.get('actor_id', 'npc')}__density_{clone_index:02d}"
        result.append(clone)
        source_index += 1
    return result


def _apply_sensor_condition(scenario: dict[str, Any], condition: str) -> None:
    sensors = scenario.get("sensors")
    if not isinstance(sensors, dict) or condition == "nominal":
        return
    if condition == "reduced_rgb":
        for sensor_id, config in sensors.items():
            if "rgb" not in str(sensor_id).lower() or not isinstance(config, dict):
                continue
            for key in ("width", "height"):
                if key in config:
                    config[key] = max(64, round(float(config[key]) * 0.75))
    elif condition == "sparse_lidar":
        lidar = sensors.get("lidar")
        if isinstance(lidar, dict) and "channels" in lidar:
            lidar["channels"] = max(8, round(float(lidar["channels"]) * 0.5))


def perturb_scenario(raw_scenario: Mapping[str, Any], case: PerturbationCase) -> dict[str, Any]:
    """Return an in-memory variant without changing semantic commands/oracles."""
    scenario = deepcopy(dict(raw_scenario))
    scenario["scenario_id"] = case.case_id
    scenario["map"] = case.map_name
    scenario["weather"] = case.weather
    scenario["seed"] = case.seed
    runtime = scenario.setdefault("runtime", {})
    if not isinstance(runtime, dict):
        raise TypeError("scenario runtime must be an object")
    runtime["fixed_delta_seconds"] = case.fixed_delta_s
    actors = scenario.get("actors", [])
    if not isinstance(actors, list):
        raise TypeError("scenario actors must be a list")
    materialized_actors: list[dict[str, Any]] = []
    for actor in actors:
        if not isinstance(actor, dict):
            raise TypeError("scenario actor must be an object")
        actor = offset_actor_route_position(
            actor,
            longitudinal_m=case.actor_longitudinal_offset_m,
            lateral_m=case.actor_lateral_offset_m,
        )
        position = actor.get("route_position")
        parameterization = actor.get("parameterization", {})
        if (
            isinstance(position, dict)
            and isinstance(parameterization, Mapping)
            and parameterization.get("vary_lane_relation") is True
        ):
            allowed_relations = parameterization.get("lane_relations")
            if isinstance(allowed_relations, Sequence) and not isinstance(
                allowed_relations, (str, bytes),
            ) and allowed_relations:
                normalized_allowed = tuple(str(item).upper() for item in allowed_relations)
                position["lane_relation"] = (
                    case.target_lane_relation
                    if case.target_lane_relation in normalized_allowed
                    else normalized_allowed[case.seed % len(normalized_allowed)]
                )
            else:
                position["lane_relation"] = case.target_lane_relation
        behavior = actor.get("behavior")
        if isinstance(behavior, dict):
            for key in ("initial_speed_mps", "target_speed_mps", "speed_mps"):
                if key in behavior:
                    behavior[key] = max(0.0, float(behavior[key]) * case.actor_speed_scale)
            if "brake_at_s" in behavior:
                behavior["brake_at_s"] = max(
                    0.0, float(behavior["brake_at_s"]) + case.brake_time_offset_s,
                )
            if str(actor.get("type", "")).lower().startswith("walker") and "start_time_s" in behavior:
                behavior["start_time_s"] = max(
                    0.0,
                    float(behavior["start_time_s"]) + case.pedestrian_start_offset_s,
                )
        materialized_actors.append(actor)
    actors = _scale_auxiliary_vehicles(
        materialized_actors,
        case.actor_count_scale,
        _referenced_actor_ids(scenario),
    )
    scenario["actors"] = actors
    _apply_sensor_condition(scenario, case.sensor_condition)
    extensions = scenario.setdefault("extensions", {})
    if isinstance(extensions, dict):
        if case.map_name != str(raw_scenario.get("map", "")):
            extensions.pop("route_anchor_spawn_index", None)
        extensions["generalization_case"] = {
            "base_scenario_id": raw_scenario.get("scenario_id"),
            "kind": (
                "variant"
                if case.map_name == str(raw_scenario.get("map", ""))
                else "unseen"
            ),
            "actor_longitudinal_offset_m": case.actor_longitudinal_offset_m,
            "actor_lateral_offset_m": case.actor_lateral_offset_m,
            "actor_speed_scale": case.actor_speed_scale,
            "brake_time_offset_s": case.brake_time_offset_s,
            "pedestrian_start_offset_s": case.pedestrian_start_offset_s,
            "actor_count_scale": case.actor_count_scale,
            "target_lane_relation": case.target_lane_relation,
            "sensor_condition": case.sensor_condition,
        }
    return scenario


__all__ = [
    "DEFAULT_MATRIX_PATH",
    "GeneralizationMatrix",
    "PerturbationCase",
    "load_generalization_matrix",
    "perturb_scenario",
]
