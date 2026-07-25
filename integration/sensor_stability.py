"""Small, fail-fast CARLA sensor stability probe.

The probe deliberately uses the currently loaded world and never calls
``load_world``.  It owns every actor it creates and restores the previous
world settings through :class:`car_control_A.CarlaSession`.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import threading
import time
from typing import Any, Callable, Sequence

from car_control_A import CarlaSession

from .carla_perception import (
    CarlaSensorSpec,
    LIDAR_SENSOR_ID,
    RGB_SENSOR_ID,
    sensor_specs_for_profile,
)


SENSOR_MODES: dict[str, tuple[str, ...]] = {
    "rgb": (RGB_SENSOR_ID,),
    "lidar": (LIDAR_SENSOR_ID,),
    "both": (RGB_SENSOR_ID, LIDAR_SENSOR_ID),
}


def map_contract_name(name: str) -> str:
    """Return the comparable leaf name of a CARLA map path."""
    return str(name).replace("\\", "/").rstrip("/").split("/")[-1]


def selected_sensor_specs(mode: str, profile: str) -> tuple[CarlaSensorSpec, ...]:
    """Select only continuous RGB/LiDAR specs for a probe invocation."""
    key = str(mode).strip().lower()
    try:
        requested = SENSOR_MODES[key]
    except KeyError as error:
        raise ValueError(f"unknown sensor mode: {mode!r}") from error
    by_id = {spec.sensor_id: spec for spec in sensor_specs_for_profile(profile)}
    try:
        return tuple(by_id[sensor_id] for sensor_id in requested)
    except KeyError as error:
        raise ValueError(f"sensor profile {profile!r} is missing {error.args[0]!r}") from error


class SensorFrameCounter:
    """Thread-safe callback ledger used by the live probe and offline tests."""

    def __init__(self, sensor_ids: Sequence[str]) -> None:
        ids = tuple(sensor_ids)
        if not ids or any(type(sensor_id) is not str or not sensor_id for sensor_id in ids):
            raise ValueError("sensor_ids must contain non-empty strings")
        if len(set(ids)) != len(ids):
            raise ValueError("sensor_ids must be unique")
        self._sensor_ids = ids
        self._frames = {sensor_id: set() for sensor_id in ids}
        self._invalid_callbacks = {sensor_id: 0 for sensor_id in ids}
        self._condition = threading.Condition()

    def callback(self, sensor_id: str) -> Callable[[Any], None]:
        if sensor_id not in self._frames:
            raise KeyError(sensor_id)

        def receive(measurement: Any) -> None:
            frame = getattr(measurement, "frame", None)
            with self._condition:
                if type(frame) is int and frame >= 0:
                    self._frames[sensor_id].add(frame)
                else:
                    self._invalid_callbacks[sensor_id] += 1
                self._condition.notify_all()

        return receive

    def wait_for_frame(
        self,
        sensor_ids: Sequence[str],
        frame: int,
        *,
        timeout_s: float,
    ) -> bool:
        requested = tuple(sensor_ids)
        if any(sensor_id not in self._frames for sensor_id in requested):
            raise KeyError("unknown sensor id")
        if type(frame) is not int or frame < 0:
            raise ValueError("frame must be a non-negative integer")
        if (
            type(timeout_s) not in (int, float)
            or not math.isfinite(float(timeout_s))
            or timeout_s < 0
        ):
            raise ValueError("timeout_s must be finite and non-negative")
        deadline = time.monotonic() + float(timeout_s)
        with self._condition:
            while not all(frame in self._frames[sensor_id] for sensor_id in requested):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def counts(self) -> dict[str, int]:
        with self._condition:
            return {
                sensor_id: len(self._frames[sensor_id])
                for sensor_id in self._sensor_ids
            }

    def frame_bounds(self) -> dict[str, tuple[int | None, int | None]]:
        with self._condition:
            return {
                sensor_id: (
                    min(frames) if frames else None,
                    max(frames) if frames else None,
                )
                for sensor_id, frames in self._frames.items()
            }

    def invalid_callbacks(self) -> dict[str, int]:
        with self._condition:
            return dict(self._invalid_callbacks)


@dataclass(frozen=True, slots=True)
class SensorProbeResult:
    success: bool
    reason: str
    map_name: str
    mode: str
    profile: str
    requested_frames: int
    aligned_frames: int
    callback_counts: dict[str, int]
    frame_bounds: dict[str, tuple[int | None, int | None]]
    invalid_callbacks: dict[str, int]
    duration_s: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def _make_transform(carla_api: Any, spec: CarlaSensorSpec) -> Any:
    mount = spec.mount
    return carla_api.Transform(
        carla_api.Location(x=mount.x_m, y=mount.y_m, z=mount.z_m),
        carla_api.Rotation(
            pitch=mount.pitch_deg,
            yaw=mount.yaw_deg,
            roll=mount.roll_deg,
        ),
    )


def _configure_blueprint(world: Any, spec: CarlaSensorSpec) -> Any:
    blueprint = world.get_blueprint_library().find(spec.blueprint_id)
    if blueprint is None:
        raise LookupError(f"CARLA blueprint not found: {spec.blueprint_id}")
    for name, value in spec.attributes.items():
        if hasattr(blueprint, "has_attribute") and not blueprint.has_attribute(name):
            raise LookupError(f"{spec.blueprint_id} does not support attribute {name}")
        blueprint.set_attribute(name, value)
    return blueprint


def _spawn_ego(session: CarlaSession, world: Any, spawn_index: int) -> Any:
    library = world.get_blueprint_library()
    candidates = list(library.filter("vehicle.*model3*"))
    if not candidates:
        candidates = list(library.filter("vehicle.*"))
    if not candidates:
        raise RuntimeError("no vehicle blueprint is available")
    blueprint = candidates[0]
    if hasattr(blueprint, "has_attribute") and blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", "sensor_probe")
    spawn_points = list(world.get_map().get_spawn_points())
    if not spawn_points:
        raise RuntimeError("current map has no vehicle spawn points")
    start = spawn_index % len(spawn_points)
    for offset in range(len(spawn_points)):
        transform = spawn_points[(start + offset) % len(spawn_points)]
        ego = world.try_spawn_actor(blueprint, transform)
        if ego is not None:
            ego = session.track_actor(ego)
            set_autopilot = getattr(ego, "set_autopilot", None)
            if callable(set_autopilot):
                set_autopilot(False)
            return ego
    raise RuntimeError("unable to spawn ego at any current-map spawn point")


def run_sensor_probe(
    *,
    carla_api: Any,
    host: str = "127.0.0.1",
    port: int = 2000,
    timeout_s: float = 10.0,
    sensor_timeout_s: float = 2.0,
    fixed_delta_s: float = 0.05,
    mode: str = "rgb",
    profile: str = "low",
    frames: int = 100,
    startup_frames: int = 10,
    spawn_index: int = 0,
    expected_map: str | None = None,
) -> SensorProbeResult:
    """Run a live probe against the currently loaded CARLA world."""
    if type(frames) is not int or frames < 1:
        raise ValueError("frames must be a positive integer")
    if type(startup_frames) is not int or startup_frames < 0:
        raise ValueError("startup_frames must be a non-negative integer")
    specs = selected_sensor_specs(mode, profile)
    sensor_ids = tuple(spec.sensor_id for spec in specs)
    started_at = time.monotonic()
    print(f"probe stage=connect host={host} port={port}", flush=True)
    client = carla_api.Client(host, port)
    client.set_timeout(timeout_s)
    world = client.get_world()
    map_name = world.get_map().name
    print(f"probe stage=world current_map={map_name}", flush=True)
    if expected_map and (
        map_contract_name(map_name).lower()
        != map_contract_name(expected_map).lower()
    ):
        raise RuntimeError(
            f"current map is {map_name!r}, expected {expected_map!r}; "
            "probe will not call load_world"
        )

    counter = SensorFrameCounter(sensor_ids)
    aligned_frames = 0
    reason = "requested aligned frames received"
    success = False
    with CarlaSession(world, fixed_delta_seconds=fixed_delta_s) as session:
        print("probe stage=spawn_ego", flush=True)
        ego = _spawn_ego(session, world, spawn_index)
        session.tick(timeout_s)
        for spec in specs:
            print(
                f"probe stage=attach sensor={spec.sensor_id} "
                f"blueprint={spec.blueprint_id}",
                flush=True,
            )
            blueprint = _configure_blueprint(world, spec)
            sensor = world.spawn_actor(
                blueprint,
                _make_transform(carla_api, spec),
                attach_to=ego,
            )
            sensor = session.track_actor(sensor)
            sensor.listen(counter.callback(spec.sensor_id))
        print(
            f"probe stage=stream mode={mode} profile={profile} "
            f"requested_frames={frames}",
            flush=True,
        )
        startup_misses = 0
        stream_started = False
        while aligned_frames < frames:
            frame = session.tick(timeout_s)
            received = counter.wait_for_frame(
                sensor_ids, frame, timeout_s=sensor_timeout_s,
            )
            if received:
                stream_started = True
                aligned_frames += 1
                if aligned_frames == 1 or aligned_frames % 25 == 0 or aligned_frames == frames:
                    print(
                        f"probe progress={aligned_frames}/{frames} frame={frame} "
                        f"counts={counter.counts()}",
                        flush=True,
                    )
                continue
            if not stream_started and startup_misses < startup_frames:
                startup_misses += 1
                print(
                    f"probe stage=startup_wait miss={startup_misses}/{startup_frames} "
                    f"frame={frame} counts={counter.counts()}",
                    flush=True,
                )
                continue
            reason = (
                f"sensor callback timeout at simulation frame {frame}; "
                f"counts={counter.counts()}"
            )
            break
        else:
            success = True

    result = SensorProbeResult(
        success=success,
        reason=reason,
        map_name=map_name,
        mode=mode,
        profile=profile,
        requested_frames=frames,
        aligned_frames=aligned_frames,
        callback_counts=counter.counts(),
        frame_bounds=counter.frame_bounds(),
        invalid_callbacks=counter.invalid_callbacks(),
        duration_s=round(time.monotonic() - started_at, 3),
    )
    print(f"probe result={result.to_json()}", flush=True)
    return result


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--sensor-timeout", type=float, default=2.0)
    parser.add_argument("--fixed-delta", type=float, default=0.05)
    parser.add_argument("--sensor", choices=tuple(SENSOR_MODES), default="rgb")
    parser.add_argument("--profile", choices=("default", "low"), default="low")
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--startup-frames", type=int, default=10)
    parser.add_argument("--spawn-index", type=int, default=0)
    parser.add_argument("--expected-map")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        import carla

        result = run_sensor_probe(
            carla_api=carla,
            host=args.host,
            port=args.port,
            timeout_s=args.timeout,
            sensor_timeout_s=args.sensor_timeout,
            fixed_delta_s=args.fixed_delta,
            mode=args.sensor,
            profile=args.profile,
            frames=args.frames,
            startup_frames=args.startup_frames,
            spawn_index=args.spawn_index,
            expected_map=args.expected_map,
        )
    except Exception as error:
        print(
            "probe error="
            + json.dumps(
                {"type": type(error).__name__, "message": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return 2
    return 0 if result.success else 1
