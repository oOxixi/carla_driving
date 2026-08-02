from __future__ import annotations

import threading
import time

import pytest

from car_control_A.simulator import ActorRegistry, CarlaSession, SensorFrameBuffer, SynchronousWorld


class FakeSettings:
    def __init__(self, synchronous_mode: bool = False, fixed_delta_seconds: float | None = None) -> None:
        self.synchronous_mode = synchronous_mode
        self.fixed_delta_seconds = fixed_delta_seconds


class FakeWorld:
    def __init__(self) -> None:
        self.settings = FakeSettings()
        self.applied: list[FakeSettings] = []
        self.ticks = 0

    def get_settings(self) -> FakeSettings:
        return self.settings

    def apply_settings(self, settings: FakeSettings) -> None:
        self.settings = settings
        self.applied.append(settings)

    def tick(self) -> int:
        self.ticks += 1
        return self.ticks


class FakeTrafficManager:
    def __init__(self) -> None:
        self.calls: list[bool] = []

    def set_synchronous_mode(self, enabled: bool) -> None:
        self.calls.append(enabled)


class FakeActor:
    def __init__(self, name: str, events: list[str]) -> None:
        self.name = name
        self.events = events

    def stop(self) -> None:
        self.events.append(f"stop:{self.name}")

    def destroy(self) -> None:
        self.events.append(f"destroy:{self.name}")


def test_synchronous_world_restores_settings_and_traffic_manager() -> None:
    world = FakeWorld()
    tm = FakeTrafficManager()
    original = world.settings

    with SynchronousWorld(world, traffic_manager=tm, fixed_delta_seconds=0.05, tm_previous_synchronous_mode=True) as sync:
        assert world.settings.synchronous_mode is True
        assert world.settings.fixed_delta_seconds == 0.05
        assert sync.tick() == 1
        assert world.ticks == 1

    assert world.settings is not original
    assert world.settings.synchronous_mode is False
    assert world.settings.fixed_delta_seconds is None
    assert tm.calls == [True, True]


def test_traffic_manager_requires_an_explicit_previous_state() -> None:
    with pytest.raises(ValueError, match="tm_previous_synchronous_mode"):
        SynchronousWorld(FakeWorld(), traffic_manager=FakeTrafficManager())

    world = FakeWorld()
    tm = FakeTrafficManager()
    with SynchronousWorld(world, traffic_manager=tm, tm_previous_synchronous_mode=False):
        pass
    assert tm.calls == [True, False]


def test_world_settings_restore_even_if_traffic_manager_restore_fails() -> None:
    class FailingRestoreTrafficManager(FakeTrafficManager):
        def set_synchronous_mode(self, enabled: bool) -> None:
            super().set_synchronous_mode(enabled)
            if enabled is False:
                raise RuntimeError("TM unavailable")

    world = FakeWorld()
    tm = FailingRestoreTrafficManager()
    with pytest.raises(RuntimeError, match="TM unavailable"):
        with SynchronousWorld(world, traffic_manager=tm, tm_previous_synchronous_mode=False):
            pass
    assert world.settings.synchronous_mode is False
    assert world.settings.fixed_delta_seconds is None


def test_world_and_tm_restore_when_tm_enable_changes_state_then_raises() -> None:
    class FailingEnableTrafficManager(FakeTrafficManager):
        def set_synchronous_mode(self, enabled: bool) -> None:
            super().set_synchronous_mode(enabled)
            if enabled is True:
                raise RuntimeError("TM enabled then failed")

    world = FakeWorld()
    tm = FailingEnableTrafficManager()
    with pytest.raises(RuntimeError, match="TM enabled then failed"):
        SynchronousWorld(world, traffic_manager=tm, tm_previous_synchronous_mode=False).__enter__()
    assert tm.calls == [True, False]
    assert world.settings.synchronous_mode is False
    assert world.settings.fixed_delta_seconds is None


def test_exit_clears_sync_state_when_world_restore_raises_and_preserves_business_error() -> None:
    class FailingRestoreWorld(FakeWorld):
        def __init__(self) -> None:
            super().__init__()
            self.fail_restore = False

        def apply_settings(self, settings: FakeSettings) -> None:
            if self.fail_restore:
                self.fail_restore = False
                raise RuntimeError("restore failed")
            super().apply_settings(settings)

    world = FailingRestoreWorld()
    sync = SynchronousWorld(world)
    sync.__enter__()
    world.fail_restore = True
    with pytest.raises(RuntimeError, match="restore failed"):
        sync.__exit__(None, None, None)
    with pytest.raises(RuntimeError, match="requires an active"):
        sync.tick()
    # The same context object must be reusable despite the restore failure.
    with sync:
        pass

    world = FailingRestoreWorld()
    with pytest.raises(ValueError, match="business failure"):
        with SynchronousWorld(world):
            world.fail_restore = True
            raise ValueError("business failure")


def test_session_is_the_single_tick_owner_and_cleans_actors_in_reverse_order() -> None:
    world = FakeWorld()
    events: list[str] = []
    first, second = FakeActor("first", events), FakeActor("second", events)

    with CarlaSession(world) as session:
        session.track_actor(first)
        session.track_actor(second)
        assert session.tick() == 1
        assert world.ticks == 1

    assert events == ["stop:second", "destroy:second", "stop:first", "destroy:first"]


def test_session_spawns_ego_and_attaches_listening_sensor() -> None:
    events: list[str] = []

    class ListeningActor(FakeActor):
        def __init__(self, name: str, events: list[str]) -> None:
            super().__init__(name, events)
            self.listener = None

        def listen(self, callback: object) -> None:
            self.events.append(f"listen:{self.name}")
            self.listener = callback

    class SpawnWorld(FakeWorld):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[tuple[object, object, object | None]] = []

        def spawn_actor(self, blueprint: object, transform: object, attach_to: object | None = None) -> ListeningActor:
            self.calls.append((blueprint, transform, attach_to))
            return ListeningActor("ego" if attach_to is None else "rgb", events)

    world = SpawnWorld()
    with CarlaSession(world) as session:
        ego = session.spawn_ego("vehicle.bp", "ego-transform")
        sensor = session.attach_sensor("camera.bp", "sensor-transform", ego, "rgb")
        assert world.calls == [
            ("vehicle.bp", "ego-transform", None),
            ("camera.bp", "sensor-transform", ego),
        ]
        measurement = type("Measurement", (), {"frame": 4})()
        sensor.listener(measurement)  # type: ignore[union-attr]
        assert session.frame_buffer.pop_aligned(("rgb",), 4, timeout_s=0.01) == {"rgb": measurement}
    assert events == [
        "listen:rgb", "stop:rgb", "destroy:rgb", "stop:ego", "destroy:ego",
    ]


def test_attach_sensor_validates_before_spawn_and_immediately_releases_listen_failure() -> None:
    events: list[str] = []

    class FailingSensor(FakeActor):
        def listen(self, callback: object) -> None:
            events.append("listen:sensor")
            raise RuntimeError("listen failed")

    class SpawnWorld(FakeWorld):
        def __init__(self) -> None:
            super().__init__()
            self.spawn_count = 0

        def spawn_actor(self, blueprint: object, transform: object, attach_to: object | None = None) -> FailingSensor:
            self.spawn_count += 1
            return FailingSensor("sensor", events)

    world = SpawnWorld()
    with CarlaSession(world) as session:
        with pytest.raises(ValueError, match="sensor_id"):
            session.attach_sensor("bp", "transform", object(), "")
        assert world.spawn_count == 0
        with pytest.raises(RuntimeError, match="listen failed"):
            session.attach_sensor("bp", "transform", object(), "rgb")
        assert events == ["listen:sensor", "stop:sensor", "destroy:sensor"]
    assert events == ["listen:sensor", "stop:sensor", "destroy:sensor"]


def test_actor_registry_cleans_every_actor_when_one_destroy_fails() -> None:
    events: list[str] = []

    class BrokenActor(FakeActor):
        def destroy(self) -> None:
            super().destroy()
            raise RuntimeError("network lost")

    registry = ActorRegistry()
    registry.track(FakeActor("first", events))
    registry.track(BrokenActor("second", events))
    registry.cleanup()
    assert events == ["stop:second", "destroy:second", "stop:first", "destroy:first"]


def test_sensor_buffer_only_returns_a_complete_matching_frame() -> None:
    buffer = SensorFrameBuffer(max_frames=3)
    buffer.push("rgb", 10, "old-image")
    buffer.push("rgb", 11, "image")
    buffer.push("lidar", 11, "cloud")

    assert buffer.pop_aligned(("rgb", "lidar"), 11, timeout_s=0.01) == {"rgb": "image", "lidar": "cloud"}
    assert buffer.pending_frames == ()


def test_sensor_buffer_degrades_when_optional_sensor_is_missing() -> None:
    buffer = SensorFrameBuffer()
    buffer.push("rgb", 20, "rgb-20")
    buffer.push("lidar", 20, "lidar-20")
    assert buffer.pop_aligned_optional(
        ("rgb", "lidar"), ("radar",), 20,
        timeout_s=0.1, optional_grace_s=0.0,
    ) == {"rgb": "rgb-20", "lidar": "lidar-20"}


def test_sensor_buffer_includes_same_frame_optional_sensor() -> None:
    buffer = SensorFrameBuffer()
    buffer.push("radar", 21, "radar-21")
    buffer.push("rgb", 21, "rgb-21")
    buffer.push("lidar", 21, "lidar-21")
    assert buffer.pop_aligned_optional(
        ("rgb", "lidar"), ("radar",), 21,
        timeout_s=0.1, optional_grace_s=0.01,
    ) == {
        "rgb": "rgb-21", "lidar": "lidar-21", "radar": "radar-21",
    }


def test_sensor_buffer_discards_evicted_frames_and_times_out_for_incomplete_frame() -> None:
    buffer = SensorFrameBuffer(max_frames=2)
    buffer.push("rgb", 1, "one")
    buffer.push("rgb", 2, "two")
    buffer.push("rgb", 3, "three")
    assert buffer.pending_frames == (2, 3)
    with pytest.raises(TimeoutError, match="frame=1"):
        buffer.pop_aligned(("rgb", "lidar"), 1, timeout_s=0.001)


def test_late_old_frame_is_dropped_without_evicting_newer_frames() -> None:
    buffer = SensorFrameBuffer(max_frames=2)
    buffer.push("rgb", 10, "ten")
    buffer.push("rgb", 11, "eleven")
    buffer.push("lidar", 9, "late")
    assert buffer.pending_frames == (10, 11)


def test_out_of_order_sensor_callbacks_can_still_align_an_unconsumed_frame() -> None:
    buffer = SensorFrameBuffer(max_frames=3)
    buffer.push("rgb", 10, "rgb-10")
    buffer.push("rgb", 11, "rgb-11")
    buffer.push("lidar", 10, "lidar-10")
    assert buffer.pop_aligned(("rgb", "lidar"), 10, timeout_s=0.01) == {
        "rgb": "rgb-10", "lidar": "lidar-10",
    }


def test_sensor_buffer_waits_for_callback_thread() -> None:
    buffer = SensorFrameBuffer()

    def publish() -> None:
        time.sleep(0.01)
        buffer.push("rgb", 7, "image")
        buffer.push("lidar", 7, "cloud")

    thread = threading.Thread(target=publish)
    thread.start()
    assert buffer.pop_aligned(("rgb", "lidar"), 7, timeout_s=0.5) == {"rgb": "image", "lidar": "cloud"}
    thread.join()


def test_invalid_sensor_buffer_arguments_fail_early() -> None:
    buffer = SensorFrameBuffer(max_frames=1)
    with pytest.raises(ValueError):
        buffer.push("", 1, object())
    with pytest.raises(ValueError):
        buffer.push("rgb", -1, object())
    with pytest.raises(ValueError):
        buffer.pop_aligned((), 1, timeout_s=0.1)
