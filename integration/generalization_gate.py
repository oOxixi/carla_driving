"""Deterministic scenario perturbations for pre-CARLA generalization gates."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


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
    return GeneralizationMatrix(
        source,
        maps,
        weather,
        tuple(int(item) for item in seeds_raw),
        numbers("fixed_delta_seconds", positive=True),
        numbers("actor_longitudinal_offsets_m"),
        numbers("actor_lateral_offsets_m"),
        numbers("actor_speed_scales", positive=True),
        samples,
        holdout,
    )


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
    for actor in actors:
        if not isinstance(actor, dict):
            raise TypeError("scenario actor must be an object")
        position = actor.get("route_position")
        if isinstance(position, dict):
            position["s_m"] = max(0.0, float(position.get("s_m", 0.0)) + case.actor_longitudinal_offset_m)
            position["lateral_offset_m"] = float(position.get("lateral_offset_m", 0.0)) + case.actor_lateral_offset_m
        else:
            spawn = actor.setdefault("spawn", {})
            if not isinstance(spawn, dict):
                raise TypeError("scenario actor spawn must be an object")
            spawn["x"] = max(0.0, float(spawn.get("x", 0.0)) + case.actor_longitudinal_offset_m)
            spawn["y"] = float(spawn.get("y", 0.0)) + case.actor_lateral_offset_m
        behavior = actor.get("behavior")
        if isinstance(behavior, dict):
            for key in ("initial_speed_mps", "target_speed_mps", "speed_mps"):
                if key in behavior:
                    behavior[key] = max(0.0, float(behavior[key]) * case.actor_speed_scale)
    extensions = scenario.setdefault("extensions", {})
    if isinstance(extensions, dict):
        extensions["generalization_case"] = {
            "base_scenario_id": raw_scenario.get("scenario_id"),
            "actor_longitudinal_offset_m": case.actor_longitudinal_offset_m,
            "actor_lateral_offset_m": case.actor_lateral_offset_m,
            "actor_speed_scale": case.actor_speed_scale,
        }
    return scenario


__all__ = [
    "DEFAULT_MATRIX_PATH",
    "GeneralizationMatrix",
    "PerturbationCase",
    "load_generalization_matrix",
    "perturb_scenario",
]
