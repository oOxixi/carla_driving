"""CARLA lifecycle primitives owned by member A.

This module deliberately has no module-level ``carla`` import.  It can therefore
be unit tested without a simulator, while real CARLA objects are accepted through
their small duck-typed API at the connection boundary.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import threading
import time
from typing import Any, Callable, Iterable


def _clone_world_settings(settings: Any) -> Any:
    """Clone CARLA ``WorldSettings`` without relying on Python pickling.

    CARLA 0.9.16's Boost.Python ``WorldSettings`` explicitly rejects
    ``copy.copy``.  Its public properties are nevertheless ordinary readable
    and writable fields.  Reconstructing through the concrete settings class
    keeps this module CARLA-import-free and also works with the fake settings
    used in unit tests.
    """
    values: dict[str, Any] = {}
    for name in dir(settings):
        if name.startswith("_"):
            continue
        try:
            value = getattr(settings, name)
        except Exception:
            continue
        if not callable(value):
            values[name] = value
    try:
        return type(settings)(**values)
    except (TypeError, ValueError):
        clone = type(settings)()
        for name, value in values.items():
            try:
                setattr(clone, name, value)
            except (AttributeError, TypeError):
                continue
        return clone


class SensorFrameBuffer:
    """Thread-safe, bounded sensor callback storage keyed by CARLA frame number."""

    def __init__(self, *, max_frames: int = 32) -> None:
        if type(max_frames) is not int or max_frames < 1:
            raise ValueError("max_frames must be a positive integer")
        self._max_frames = max_frames
        self._frames: OrderedDict[int, dict[str, Any]] = OrderedDict()
        # Frames at or below this value were already returned (or skipped by a
        # newer successful alignment) and cannot become useful again.
        self._consumed_through = -1
        self._condition = threading.Condition()

    @property
    def pending_frames(self) -> tuple[int, ...]:
        with self._condition:
            return tuple(sorted(self._frames))

    def push(self, sensor_id: str, frame: int, payload: Any) -> None:
        if type(sensor_id) is not str or not sensor_id:
            raise ValueError("sensor_id must be a non-empty string")
        if type(frame) is not int or frame < 0:
            raise ValueError("frame must be a non-negative integer")
        with self._condition:
            if frame <= self._consumed_through:
                return
            bucket = self._frames.setdefault(frame, {})
            bucket[sensor_id] = payload
            while len(self._frames) > self._max_frames:
                # Capacity is defined in simulation-frame order, not callback
                # arrival order.  This lets lidar for frame N arrive after RGB
                # for N+1 while preventing a much older callback from evicting
                # a newer, potentially complete frame.
                oldest = min(self._frames)
                del self._frames[oldest]
            self._condition.notify_all()

    def callback(self, sensor_id: str) -> Callable[[Any], None]:
        """Return a CARLA sensor callback without importing CARLA itself."""
        if type(sensor_id) is not str or not sensor_id:
            raise ValueError("sensor_id must be a non-empty string")

        def receive(measurement: Any) -> None:
            self.push(sensor_id, measurement.frame, measurement)

        return receive

    def pop_aligned(self, sensor_ids: Iterable[str], frame: int, *, timeout_s: float) -> dict[str, Any]:
        requested = tuple(sensor_ids)
        if not requested or any(type(sensor_id) is not str or not sensor_id for sensor_id in requested):
            raise ValueError("sensor_ids must contain non-empty strings")
        if len(set(requested)) != len(requested):
            raise ValueError("sensor_ids must be unique")
        if type(frame) is not int or frame < 0:
            raise ValueError("frame must be a non-negative integer")
        if type(timeout_s) not in (int, float) or timeout_s < 0:
            raise ValueError("timeout_s must be a non-negative number")

        deadline = time.monotonic() + float(timeout_s)
        with self._condition:
            while True:
                bucket = self._frames.get(frame)
                if bucket is not None and all(sensor_id in bucket for sensor_id in requested):
                    result = {sensor_id: bucket[sensor_id] for sensor_id in requested}
                    del self._frames[frame]
                    # Older samples can never form a set for a subsequent frame.
                    for old_frame in tuple(self._frames):
                        if old_frame < frame:
                            del self._frames[old_frame]
                    self._consumed_through = max(self._consumed_through, frame)
                    return result
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"timed out waiting for aligned sensors at frame={frame}")
                self._condition.wait(remaining)


@dataclass
class ActorRegistry:
    """Owns spawned CARLA actors and releases them in safe reverse order."""

    _actors: list[Any] = field(default_factory=list)

    def track(self, actor: Any) -> Any:
        if actor is None:
            raise ValueError("actor must not be None")
        self._actors.append(actor)
        return actor

    def cleanup(self) -> None:
        actors, self._actors = self._actors, []
        for actor in reversed(actors):
            self.dispose(actor)

    @staticmethod
    def dispose(actor: Any) -> None:
        """Best-effort listener stop and actor destruction used on all failures."""
        stop = getattr(actor, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass
        destroy = getattr(actor, "destroy", None)
        if callable(destroy):
            try:
                destroy()
            except Exception:
                pass


class SynchronousWorld:
    """Temporarily makes one CARLA World synchronous; this is the sole tick API."""

    def __init__(
        self,
        world: Any,
        *,
        traffic_manager: Any | None = None,
        fixed_delta_seconds: float = 0.05,
        tm_previous_synchronous_mode: bool | None = None,
    ) -> None:
        if world is None:
            raise ValueError("world must not be None")
        if type(fixed_delta_seconds) not in (int, float) or fixed_delta_seconds <= 0:
            raise ValueError("fixed_delta_seconds must be positive")
        if traffic_manager is not None and tm_previous_synchronous_mode is None:
            raise ValueError("tm_previous_synchronous_mode must be explicitly provided with traffic_manager")
        if tm_previous_synchronous_mode is not None and type(tm_previous_synchronous_mode) is not bool:
            raise TypeError("tm_previous_synchronous_mode must be bool")
        self._world = world
        self._traffic_manager = traffic_manager
        self._fixed_delta_seconds = float(fixed_delta_seconds)
        self._tm_previous_synchronous_mode = False if tm_previous_synchronous_mode is None else tm_previous_synchronous_mode
        self._previous_settings: Any | None = None
        self._active = False

    def __enter__(self) -> SynchronousWorld:
        if self._active:
            raise RuntimeError("SynchronousWorld is already active")
        previous = self._world.get_settings()
        self._previous_settings = _clone_world_settings(previous)
        current = _clone_world_settings(previous)
        current.synchronous_mode = True
        current.fixed_delta_seconds = self._fixed_delta_seconds
        self._world.apply_settings(current)
        try:
            if self._traffic_manager is not None:
                self._traffic_manager.set_synchronous_mode(True)
        except Exception:
            try:
                # Some backends report an error after accepting the mode
                # change, so restore the explicitly supplied prior state.
                if self._traffic_manager is not None:
                    self._traffic_manager.set_synchronous_mode(self._tm_previous_synchronous_mode)
            except Exception:
                pass
            finally:
                self._world.apply_settings(_clone_world_settings(self._previous_settings))
                self._previous_settings = None
            raise
        self._active = True
        return self

    def tick(self, timeout_s: float | None = None) -> int:
        if not self._active:
            raise RuntimeError("SynchronousWorld.tick() requires an active context")
        if timeout_s is None:
            return self._world.tick()
        return self._world.tick(timeout_s)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        restore_error: Exception | None = None
        try:
            if self._traffic_manager is not None:
                self._traffic_manager.set_synchronous_mode(self._tm_previous_synchronous_mode)
        except Exception as error:
            restore_error = error
        try:
            if self._previous_settings is not None:
                self._world.apply_settings(_clone_world_settings(self._previous_settings))
        except Exception as error:
            if restore_error is None:
                restore_error = error
        finally:
            self._previous_settings = None
            self._active = False
        # A failure while unwinding must never obscure the exception raised by
        # the scenario/body of the context manager.
        if exc_type is None and restore_error is not None:
            raise restore_error


class CarlaSession:
    """One owner for a synchronous world, its sensor actors, and world ticks."""

    def __init__(self, world: Any, **synchronous_world_options: Any) -> None:
        self._world = world
        self._sync = SynchronousWorld(world, **synchronous_world_options)
        self.actors = ActorRegistry()
        self.frame_buffer = SensorFrameBuffer()
        self._active = False

    def __enter__(self) -> CarlaSession:
        self._sync.__enter__()
        self._active = True
        return self

    def track_actor(self, actor: Any) -> Any:
        if not self._active:
            raise RuntimeError("track_actor() requires an active CarlaSession")
        return self.actors.track(actor)

    def tick(self, timeout_s: float | None = None) -> int:
        if not self._active:
            raise RuntimeError("tick() requires an active CarlaSession")
        return self._sync.tick(timeout_s)

    def spawn_ego(self, blueprint: Any, transform: Any) -> Any:
        """Spawn and register the sole ego vehicle for this session."""
        if not self._active:
            raise RuntimeError("spawn_ego() requires an active CarlaSession")
        return self.track_actor(self._world.spawn_actor(blueprint, transform))

    def attach_sensor(self, blueprint: Any, transform: Any, parent: Any, sensor_id: str) -> Any:
        """Spawn a sensor, register it, and wire its callback into frame alignment."""
        if not self._active:
            raise RuntimeError("attach_sensor() requires an active CarlaSession")
        if parent is None:
            raise ValueError("parent must not be None")
        callback = self.frame_buffer.callback(sensor_id)
        sensor = self._world.spawn_actor(blueprint, transform, attach_to=parent)
        listen = getattr(sensor, "listen", None)
        if not callable(listen):
            ActorRegistry.dispose(sensor)
            raise TypeError("sensor actor must provide listen(callback)")
        try:
            listen(callback)
        except Exception:
            ActorRegistry.dispose(sensor)
            raise
        return self.track_actor(sensor)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            self.actors.cleanup()
        finally:
            self._active = False
            self._sync.__exit__(exc_type, exc, traceback)
