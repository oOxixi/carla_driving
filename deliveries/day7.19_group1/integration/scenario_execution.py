"""Validated scenario-file loading and deterministic execution helpers.

This module is CARLA-independent.  It owns scenario contracts, local-to-world
route conversion, command scheduling, and trusted scenario-only command
resolution; the CARLA runner remains the sole actor/control owner.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence


SUPPORTED_LEVELS = frozenset({"basic", "advanced", "challenge"})
DEFAULT_RELATIVE_SPEED_STEP_MPS = 5.0 / 3.6
ROUTE_FOLLOWING_INTENTS = frozenset({
    "KEEP_LANE",
    "FOLLOW_ROUTE",
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
})


def _finite_number(value: object, name: str, *, minimum: float | None = None) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def _nonempty_text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class ScheduledCommand:
    time_s: float
    envelope: dict[str, object]


@dataclass(frozen=True)
class ScenarioSpec:
    source_path: Path
    scenario_id: str
    category: str
    official_level: str
    map_name: str
    weather: str
    seed: int
    fixed_delta_s: float
    duration_s: float
    ego_spawn_xyzyaw: tuple[float, float, float, float]
    local_route_xy_m: tuple[tuple[float, float], ...]
    route_resample_interval_m: float
    finish_radius_m: float
    commands: tuple[ScheduledCommand, ...]
    actors: tuple[dict[str, object], ...]
    sensors: dict[str, object]
    expected: dict[str, object]

    @classmethod
    def load(cls, path: str | Path) -> "ScenarioSpec":
        source = Path(path).resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
        if type(data) is not dict:
            raise TypeError("scenario root must be an object")
        if data.get("schema_version") != "1.0":
            raise ValueError("scenario schema_version must be '1.0'")

        level = _nonempty_text(data.get("official_level"), "official_level").lower()
        if level not in SUPPORTED_LEVELS:
            raise ValueError(f"unsupported official_level: {level}")
        seed = data.get("seed")
        if type(seed) is not int or isinstance(seed, bool):
            raise TypeError("seed must be an integer")

        runtime = data.get("runtime")
        route = data.get("route")
        ego_spawn = data.get("ego_spawn")
        if type(runtime) is not dict or type(route) is not dict or type(ego_spawn) is not dict:
            raise TypeError("runtime, ego_spawn and route must be objects")
        if route.get("coordinate_type") != "scenario_local_xy_m":
            raise ValueError("only scenario_local_xy_m routes are currently supported")
        points = route.get("points_xy_m")
        if type(points) is not list or len(points) < 2:
            raise ValueError("route.points_xy_m must contain at least two points")
        parsed_points: list[tuple[float, float]] = []
        for index, point in enumerate(points):
            if type(point) is not list or len(point) != 2:
                raise ValueError(f"route point {index} must be [x, y]")
            parsed_points.append((
                _finite_number(point[0], f"route point {index}.x"),
                _finite_number(point[1], f"route point {index}.y"),
            ))

        raw_commands = data.get("commands")
        if type(raw_commands) is not list:
            raise TypeError("commands must be a list")
        commands = tuple(sorted(
            (_parse_command(item, index) for index, item in enumerate(raw_commands)),
            key=lambda command: command.time_s,
        ))
        actors = data.get("actors", [])
        sensors = data.get("sensors", {})
        expected = data.get("expected", {})
        if type(actors) is not list or any(type(item) is not dict for item in actors):
            raise TypeError("actors must be a list of objects")
        if type(sensors) is not dict or type(expected) is not dict:
            raise TypeError("sensors and expected must be objects")

        return cls(
            source_path=source,
            scenario_id=_nonempty_text(data.get("scenario_id"), "scenario_id"),
            category=_nonempty_text(data.get("category"), "category"),
            official_level=level,
            map_name=_nonempty_text(data.get("map"), "map"),
            weather=_nonempty_text(data.get("weather"), "weather"),
            seed=seed,
            fixed_delta_s=_finite_number(runtime.get("fixed_delta_seconds"), "fixed_delta_seconds", minimum=0.001),
            duration_s=_finite_number(runtime.get("duration_s"), "duration_s", minimum=0.001),
            ego_spawn_xyzyaw=(
                _finite_number(ego_spawn.get("x", 0.0), "ego_spawn.x"),
                _finite_number(ego_spawn.get("y", 0.0), "ego_spawn.y"),
                _finite_number(ego_spawn.get("z", 0.5), "ego_spawn.z"),
                _finite_number(ego_spawn.get("yaw_deg", 0.0), "ego_spawn.yaw_deg"),
            ),
            local_route_xy_m=tuple(parsed_points),
            route_resample_interval_m=_finite_number(
                route.get("resample_interval_m", 1.0),
                "route.resample_interval_m",
                minimum=0.1,
            ),
            finish_radius_m=_finite_number(route.get("finish_radius_m", 3.0), "finish_radius_m", minimum=0.0),
            commands=commands,
            actors=tuple(dict(item) for item in actors),
            sensors=dict(sensors),
            expected=dict(expected),
        )

    @property
    def frame_count(self) -> int:
        return max(1, math.ceil(self.duration_s / self.fixed_delta_s))

    def world_route(self, origin_x_m: float, origin_y_m: float, yaw_deg: float) -> tuple[tuple[float, float], ...]:
        """Rotate, anchor and contract-resample the local scenario route."""
        origin_x = _finite_number(origin_x_m, "origin_x_m")
        origin_y = _finite_number(origin_y_m, "origin_y_m")
        yaw = math.radians(_finite_number(yaw_deg, "yaw_deg"))
        cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
        transformed = tuple(
            (
                origin_x + local_x * cos_yaw - local_y * sin_yaw,
                origin_y + local_x * sin_yaw + local_y * cos_yaw,
            )
            for local_x, local_y in self.local_route_xy_m
        )
        return _resample_polyline(transformed, self.route_resample_interval_m)


def _resample_polyline(
    points: Sequence[tuple[float, float]], spacing_m: float,
) -> tuple[tuple[float, float], ...]:
    """Return approximately uniform arc-length samples, preserving both ends."""
    if len(points) < 2:
        raise ValueError("route needs at least two points")
    spacing = _finite_number(spacing_m, "spacing_m", minimum=0.1)
    samples: list[tuple[float, float]] = [tuple(map(float, points[0]))]
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        length = math.hypot(bx - ax, by - ay)
        if length <= 1e-9:
            continue
        count = max(1, math.ceil(length / spacing))
        samples.extend(
            (ax + (bx - ax) * index / count, ay + (by - ay) * index / count)
            for index in range(1, count + 1)
        )
    if len(samples) < 2:
        raise ValueError("route length must be positive")
    return tuple(samples)


class CommandTimeline:
    """Return each scheduled command exactly once when simulation time reaches it."""

    def __init__(self, commands: Iterable[ScheduledCommand]) -> None:
        self._commands = tuple(sorted(commands, key=lambda item: item.time_s))
        self._next_index = 0

    def due(self, elapsed_s: float) -> tuple[dict[str, object], ...]:
        elapsed = _finite_number(elapsed_s, "elapsed_s", minimum=0.0)
        due: list[dict[str, object]] = []
        while self._next_index < len(self._commands):
            command = self._commands[self._next_index]
            if command.time_s > elapsed + 1e-9:
                break
            due.append(dict(command.envelope))
            self._next_index += 1
        return tuple(due)


def select_best_route_anchor(
    anchors_xyzyaw: Sequence[tuple[float, float, float, float]],
    local_route_xy_m: Sequence[tuple[float, float]],
    distance_to_drivable_m: Callable[[float, float, float], float],
    *,
    sample_interval_m: float = 1.0,
) -> tuple[int, float]:
    """Choose the CARLA spawn whose real road best supports a local B route."""
    if not anchors_xyzyaw:
        raise ValueError("at least one route anchor is required")
    if len(local_route_xy_m) < 2:
        raise ValueError("local route needs at least two points")
    interval = _finite_number(sample_interval_m, "sample_interval_m", minimum=0.1)
    samples: list[tuple[float, float]] = [tuple(map(float, local_route_xy_m[0]))]
    for (ax, ay), (bx, by) in zip(local_route_xy_m, local_route_xy_m[1:]):
        length = math.hypot(bx - ax, by - ay)
        count = max(1, math.ceil(length / interval))
        samples.extend((ax + (bx - ax) * i / count, ay + (by - ay) * i / count) for i in range(1, count + 1))

    best_index, best_score = 0, math.inf
    for index, (origin_x, origin_y, origin_z, yaw_deg) in enumerate(anchors_xyzyaw):
        yaw = math.radians(yaw_deg)
        cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
        distances = [
            float(distance_to_drivable_m(
                origin_x + local_x * cos_yaw - local_y * sin_yaw,
                origin_y + local_x * sin_yaw + local_y * cos_yaw,
                origin_z,
            ))
            for local_x, local_y in samples
        ]
        score = max(distances) + sum(distances) / len(distances)
        if score < best_score:
            best_index, best_score = index, score
    return best_index, best_score


def resolve_scenario_command(
    envelope: Mapping[str, object],
    *,
    requested_speed_mps: float,
    relative_speed_step_mps: float = DEFAULT_RELATIVE_SPEED_STEP_MPS,
) -> dict[str, object]:
    """Resolve trusted scenario shorthand into a concrete runtime command.

    Production voice input never calls this function.  Complex live commands
    therefore retain the new runtime's confirmation/fail-closed behaviour.
    """
    current_speed = _finite_number(requested_speed_mps, "requested_speed_mps", minimum=0.0)
    step = _finite_number(relative_speed_step_mps, "relative_speed_step_mps", minimum=0.001)
    resolved = dict(envelope)
    intent = str(resolved.get("intent", "")).upper()
    parameters = resolved.get("parameters", {})
    if type(parameters) is not dict:
        raise TypeError("scenario command parameters must be an object")

    target_speed_mps: float | None = None
    if intent == "SLOW_DOWN":
        target_speed_mps = max(0.0, current_speed - step)
    elif intent == "SPEED_UP":
        target_speed_mps = current_speed + step
    elif intent in ROUTE_FOLLOWING_INTENTS:
        if "target_speed_mps" in parameters:
            target_speed_mps = _finite_number(
                parameters["target_speed_mps"], "target_speed_mps", minimum=0.0,
            )
        elif "speed" in parameters:
            speed = _finite_number(parameters["speed"], "speed", minimum=0.0)
            unit = str(parameters.get("unit", "km/h")).strip().lower().replace(" ", "")
            if unit in {"km/h", "kph", "kmh"}:
                target_speed_mps = speed / 3.6
            elif unit in {"m/s", "mps"}:
                target_speed_mps = speed
            else:
                raise ValueError(f"unsupported scenario speed unit: {unit!r}")
        else:
            target_speed_mps = current_speed

    if target_speed_mps is not None:
        resolved["scenario_original_intent"] = intent
        resolved["intent"] = "SET_SPEED"
        resolved["parameters"] = {"speed": target_speed_mps, "unit": "m/s"}
        resolved["confirm_required"] = False
    return resolved


def _parse_command(raw: object, index: int) -> ScheduledCommand:
    if type(raw) is not dict:
        raise TypeError(f"commands[{index}] must be an object")
    time_s = _finite_number(raw.get("time_s"), f"commands[{index}].time_s", minimum=0.0)
    intent = _nonempty_text(raw.get("intent"), f"commands[{index}].intent").upper()
    parameters = raw.get("parameters", {})
    if type(parameters) is not dict:
        raise TypeError(f"commands[{index}].parameters must be an object")
    normalized_parameters = dict(parameters)
    if "target_speed_kph" in normalized_parameters and "speed" not in normalized_parameters:
        normalized_parameters["speed"] = normalized_parameters.pop("target_speed_kph")
        normalized_parameters["unit"] = "km/h"
    confidence = _finite_number(raw.get("intent_confidence", 1.0), f"commands[{index}].intent_confidence", minimum=0.0)
    if confidence > 1.0:
        raise ValueError(f"commands[{index}].intent_confidence must be <= 1.0")
    status = str(raw.get("status", "valid"))
    confirm_required = raw.get("confirm_required", False)
    if type(confirm_required) is not bool:
        raise TypeError(f"commands[{index}].confirm_required must be bool")
    envelope: dict[str, object] = {
        "schema_version": "1.0",
        "command_id": f"scenario_cmd_{index:03d}",
        "source_text": str(raw.get("source_text", intent)),
        "intent": intent,
        "parameters": normalized_parameters,
        "intent_confidence": confidence,
        "confidence": confidence,
        "status": status,
        "ambiguity_type": "NONE" if status == "valid" else "AMBIGUOUS",
        "confirm_required": confirm_required,
        "errors": [],
        "warnings": [],
        "valid_duration_s": max(3.0, time_s + 30.0),
    }
    return ScheduledCommand(time_s=time_s, envelope=envelope)


__all__ = [
    "CommandTimeline",
    "DEFAULT_RELATIVE_SPEED_STEP_MPS",
    "ScenarioSpec",
    "ScheduledCommand",
    "select_best_route_anchor",
    "resolve_scenario_command",
]
