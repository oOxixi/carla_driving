"""ScenarioRunner 0.9.16 ``--agent`` adapter for evaluator-owned scenarios.

The adapter deliberately knows nothing about repository scenario IDs.  It
consumes only the official sensor dictionary and route plan exposed by
ScenarioRunner's ``AutonomousAgent`` API, then applies the repository D safety
supervisor before returning a CARLA ``VehicleControl``.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from car_control_D import SafetySupervisor

try:  # Available when loaded by ScenarioRunner; intentionally optional in CI.
    import carla  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised through fallback controls
    carla = None

try:  # ScenarioRunner adds its checkout to PYTHONPATH before importing agents.
    from srunner.autoagents.autonomous_agent import AutonomousAgent, Track  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - CARLA-free unit-test boundary
    class AutonomousAgent:  # type: ignore[no-redef]
        def __init__(self, path_to_conf_file: str = "") -> None:
            self._global_plan: list[tuple[Mapping[str, float], object]] = []
            self.setup(path_to_conf_file)

    class Track:  # type: ignore[no-redef]
        SENSORS = "SENSORS"


def get_entry_point() -> str:
    """Compatibility hook used by CARLA leaderboard-style loaders."""
    return "ScenarioRunnerAgent"


@dataclass(frozen=True, slots=True)
class OfficialAgentConfig:
    target_speed_mps: float = 4.0
    obstacle_stop_m: float = 6.0
    lidar_corridor_half_width_m: float = 1.4
    route_lookahead_points: int = 5
    command_file: Path | None = None

    @classmethod
    def load(cls, path: str | Path | None) -> "OfficialAgentConfig":
        if path is None or not str(path).strip():
            return cls()
        source = Path(path).expanduser().resolve()
        payload = json.loads(source.read_text(encoding="utf-8"))
        if type(payload) is not dict:
            raise TypeError("ScenarioRunner agent config root must be an object")
        allowed = {
            "schema_version", "target_speed_mps", "obstacle_stop_m",
            "lidar_corridor_half_width_m", "route_lookahead_points", "command_file",
        }
        unknown = set(payload).difference(allowed)
        if unknown:
            raise ValueError(f"unsupported ScenarioRunner agent config fields: {sorted(unknown)}")
        if payload.get("schema_version", "1.0") != "1.0":
            raise ValueError("ScenarioRunner agent config schema_version must be '1.0'")
        target_speed = _finite(payload.get("target_speed_mps", 4.0), "target_speed_mps", 0.0)
        stop_m = _finite(payload.get("obstacle_stop_m", 6.0), "obstacle_stop_m", 0.1)
        half_width = _finite(
            payload.get("lidar_corridor_half_width_m", 1.4),
            "lidar_corridor_half_width_m",
            0.1,
        )
        lookahead = payload.get("route_lookahead_points", 5)
        if type(lookahead) is not int or isinstance(lookahead, bool) or lookahead < 1:
            raise ValueError("route_lookahead_points must be a positive integer")
        command_file = payload.get("command_file")
        command_path = None
        if command_file is not None:
            if type(command_file) is not str or not command_file.strip():
                raise ValueError("command_file must be a non-empty path")
            candidate = Path(command_file).expanduser()
            command_path = candidate.resolve() if candidate.is_absolute() else (source.parent / candidate).resolve()
        return cls(target_speed, stop_m, half_width, lookahead, command_path)


@dataclass(frozen=True, slots=True)
class OfficialSensorFrame:
    speed_mps: float
    compass_rad: float
    latitude: float
    longitude: float
    lidar_xyz: np.ndarray


class OfficialAgentCore:
    """CARLA-independent route following and fail-closed obstacle arbitration."""

    def __init__(self, config: OfficialAgentConfig) -> None:
        self.config = config
        self.safety = SafetySupervisor()
        self.last_command_error: str | None = None

    def step(
        self,
        frame: OfficialSensorFrame,
        global_plan: Sequence[tuple[Mapping[str, float], object]],
    ) -> tuple[float, float, float, str]:
        target_speed, command_valid = self._target_speed()
        front_distance = _front_lidar_distance(
            frame.lidar_xyz,
            corridor_half_width_m=self.config.lidar_corridor_half_width_m,
        )
        steer = _route_steer(
            frame.latitude,
            frame.longitude,
            frame.compass_rad,
            global_plan,
            self.config.route_lookahead_points,
        )
        speed_error = target_speed - frame.speed_mps
        raw = {
            "throttle": min(0.65, max(0.0, 0.28 * speed_error)),
            "brake": min(1.0, max(0.0, -0.35 * speed_error)),
            "steer": steer,
        }
        alerts = () if command_valid else ("INVALID_OFFICIAL_COMMAND",)
        closing_speed = max(0.0, frame.speed_mps)
        ttc_s = (
            front_distance / closing_speed
            if front_distance is not None and closing_speed > 0.1
            else None
        )
        decision = self.safety.arbitrate(
            raw,
            vehicle_state={
                "speed_mps": frame.speed_mps,
                "front_distance_m": front_distance,
            },
            risk={"ttc_s": ttc_s},
            watchdog_alerts=alerts,
        )
        control = decision.final_control
        # The official adapter's configurable guard may be stricter than D's
        # repository default; never weaken the D result.
        if front_distance is not None and front_distance <= self.config.obstacle_stop_m:
            return 0.0, 1.0, 0.0, "OFFICIAL_LIDAR_OBSTACLE_GUARD"
        return control.throttle, control.brake, control.steer, decision.reason

    def _target_speed(self) -> tuple[float, bool]:
        source = self.config.command_file
        if source is None:
            return self.config.target_speed_mps, True
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            if type(payload) is not dict:
                raise TypeError("command root must be an object")
            forbidden = {"throttle", "brake", "steer"}.intersection(payload)
            if forbidden:
                raise ValueError(
                    "low-level command fields are forbidden: " + ",".join(sorted(forbidden))
                )
            status = str(payload.get("status", "valid")).lower()
            confidence = float(payload.get("intent_confidence", payload.get("confidence", 1.0)))
            if status != "valid" or confidence < 0.8 or payload.get("confirm_required") is True:
                raise ValueError("command is invalid, low-confidence, or requires confirmation")
            intent = str(payload.get("intent", payload.get("action", "KEEP_LANE"))).upper()
            if intent in {"STOP", "EMERGENCY_STOP", "EMERGENCY_BRAKE"}:
                return 0.0, True
            if intent == "SET_SPEED":
                parameters = payload.get("parameters", {})
                if not isinstance(parameters, Mapping):
                    raise TypeError("command parameters must be an object")
                value = payload.get("target_speed_mps", parameters.get("target_speed_mps"))
                if value is None and "target_speed_kph" in parameters:
                    value = float(parameters["target_speed_kph"]) / 3.6
                return _finite(value, "command target speed", 0.0), True
            if intent not in {"KEEP_LANE", "FOLLOW_ROUTE", "START", "FORWARD"}:
                raise ValueError(f"unsupported official command intent: {intent}")
            return self.config.target_speed_mps, True
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            self.last_command_error = f"{type(error).__name__}: {error}"
            return 0.0, False


class ScenarioRunnerAgent(AutonomousAgent):
    """Concrete agent loaded by ``scenario_runner.py --agent``."""

    track = Track.SENSORS

    def setup(self, path_to_conf_file: str) -> None:
        self.config = OfficialAgentConfig.load(path_to_conf_file)
        self.core = OfficialAgentCore(self.config)
        self.last_interface_error: str | None = None
        self._last_nav: tuple[float, float, float] | None = None
        self._last_compass_rad = 0.0

    def sensors(self) -> list[dict[str, object]]:
        return [
            {
                "type": "sensor.camera.rgb", "id": "front_rgb",
                "x": 1.5, "y": 0.0, "z": 2.2,
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
                "width": 640, "height": 360, "fov": 90,
            },
            {
                "type": "sensor.lidar.ray_cast", "id": "lidar",
                "x": 0.0, "y": 0.0, "z": 2.2,
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
                "range": 50.0, "rotation_frequency": 20.0,
                "channels": 32, "upper_fov": 10.0, "lower_fov": -30.0,
                "points_per_second": 56000,
            },
            {"type": "sensor.other.gnss", "id": "gnss", "x": 0.0, "y": 0.0, "z": 0.0},
        ]

    def run_step(self, input_data: Mapping[str, tuple[int, Any]], timestamp: float) -> Any:
        try:
            frame = self._sensor_frame(input_data, timestamp)
            throttle, brake, steer, _ = self.core.step(
                frame,
                tuple(getattr(self, "_global_plan", ()) or ()),
            )
        except (KeyError, TypeError, ValueError) as error:
            self.last_interface_error = f"{type(error).__name__}: {error}"
            throttle, brake, steer = 0.0, 1.0, 0.0
        if carla is None:
            return SimpleNamespace(throttle=throttle, brake=brake, steer=steer, manual_gear_shift=False)
        return carla.VehicleControl(
            throttle=throttle,
            brake=brake,
            steer=steer,
            hand_brake=False,
            reverse=False,
            manual_gear_shift=False,
        )

    def _sensor_frame(
        self,
        input_data: Mapping[str, tuple[int, Any]],
        timestamp: float,
    ) -> OfficialSensorFrame:
        missing = {name for name in ("gnss", "lidar") if name not in input_data}
        if missing:
            raise ValueError(f"official sensor frame missing: {sorted(missing)}")
        gnss = np.asarray(input_data["gnss"][1], dtype=np.float64).reshape(-1)
        lidar = np.asarray(input_data["lidar"][1], dtype=np.float32)
        if gnss.size < 2 or lidar.ndim != 2 or lidar.shape[1] < 3:
            raise ValueError("official sensor payload has an invalid shape")
        latitude, longitude = float(gnss[0]), float(gnss[1])
        if not all(math.isfinite(value) for value in (timestamp, latitude, longitude)):
            raise ValueError("official sensor payload contains non-finite navigation data")

        speed_mps = 0.0
        if self._last_nav is not None:
            previous_time, previous_latitude, previous_longitude = self._last_nav
            dt_s = timestamp - previous_time
            if dt_s > 0.0:
                north_m, east_m = _gps_offset_m(
                    previous_latitude,
                    previous_longitude,
                    latitude,
                    longitude,
                )
                displacement_m = math.hypot(north_m, east_m)
                speed_mps = displacement_m / dt_s
                if displacement_m >= 0.02:
                    self._last_compass_rad = math.atan2(east_m, north_m)
        else:
            self._last_compass_rad = _route_bearing(
                latitude,
                longitude,
                tuple(getattr(self, "_global_plan", ()) or ()),
                self.config.route_lookahead_points,
            )
        self._last_nav = (timestamp, latitude, longitude)
        return OfficialSensorFrame(
            speed_mps,
            self._last_compass_rad,
            latitude,
            longitude,
            lidar[:, :3],
        )


def _front_lidar_distance(points: np.ndarray, *, corridor_half_width_m: float) -> float | None:
    if points.size == 0:
        return None
    finite = np.isfinite(points).all(axis=1)
    corridor = (
        finite
        & (points[:, 0] > 0.0)
        & (np.abs(points[:, 1]) <= corridor_half_width_m)
        & (points[:, 2] >= -2.2)
        & (points[:, 2] <= 0.5)
    )
    return float(np.min(points[corridor, 0])) if np.any(corridor) else None


def _route_steer(
    latitude: float,
    longitude: float,
    compass_rad: float,
    global_plan: Sequence[tuple[Mapping[str, float], object]],
    lookahead_points: int,
) -> float:
    if not global_plan:
        return 0.0
    def distance_sq(item: tuple[Mapping[str, float], object]) -> float:
        point = item[0]
        return (float(point["lat"]) - latitude) ** 2 + (float(point["lon"]) - longitude) ** 2
    nearest = min(range(len(global_plan)), key=lambda index: distance_sq(global_plan[index]))
    bearing = _route_bearing(latitude, longitude, global_plan[nearest:], lookahead_points)
    error = math.atan2(math.sin(bearing - compass_rad), math.cos(bearing - compass_rad))
    return max(-0.6, min(0.6, 0.9 * error))


def _route_bearing(
    latitude: float,
    longitude: float,
    global_plan: Sequence[tuple[Mapping[str, float], object]],
    lookahead_points: int,
) -> float:
    if not global_plan:
        return 0.0
    target = global_plan[min(len(global_plan) - 1, lookahead_points)][0]
    north_m, east_m = _gps_offset_m(
        latitude,
        longitude,
        float(target["lat"]),
        float(target["lon"]),
    )
    return math.atan2(east_m, north_m) if abs(north_m) + abs(east_m) >= 1e-6 else 0.0


def _gps_offset_m(
    latitude: float,
    longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> tuple[float, float]:
    metres_per_degree = 111_320.0
    north_m = (target_latitude - latitude) * metres_per_degree
    east_m = (
        (target_longitude - longitude)
        * metres_per_degree
        * math.cos(math.radians((latitude + target_latitude) * 0.5))
    )
    return north_m, east_m


def _finite(value: object, name: str, minimum: float) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return result


__all__ = [
    "ScenarioRunnerAgent",
    "CarlaLanguageAgent",
    "OfficialAgentConfig",
    "OfficialAgentCore",
    "OfficialSensorFrame",
    "get_entry_point",
]

# Keep the descriptive class name as an import alias for internal callers. The
# pinned ScenarioRunner loader itself requires the filename-derived name above.
CarlaDrivingScenarioAgent = ScenarioRunnerAgent
CarlaLanguageAgent = ScenarioRunnerAgent
