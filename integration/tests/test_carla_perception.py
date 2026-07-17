from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from car_control_A.routing import RouteReference
from car_control_A.simulator import SensorFrameBuffer
from integration.carla_perception import (
    COLLISION_SENSOR_ID,
    CONTINUOUS_SENSOR_IDS,
    LANE_INVASION_SENSOR_ID,
    LIDAR_SENSOR_ID,
    RGB_SENSOR_ID,
    AttachedCarlaSensors,
    CarlaPerceptionBridge,
    EventLedger,
    FrameAlignmentError,
    PerceptionTimeoutError,
    attach_default_sensors,
    front_lidar_distance_m,
)


@dataclass
class Vec:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance(self, other: "Vec") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2) ** 0.5


class Transform:
    def __init__(self, location: Vec | None = None, rotation=None):
        self.location = location or Vec()
        self.rotation = rotation

    def get_forward_vector(self):
        return Vec(1.0, 0.0, 0.0)

    def get_right_vector(self):
        return Vec(0.0, 1.0, 0.0)

    def transform(self, location):
        return Vec(self.location.x + location.x, self.location.y + location.y, self.location.z + location.z)


class CarlaApi:
    Location = Vec

    class Rotation:
        def __init__(self, **values):
            self.values = values

    Transform = Transform


class Blueprint:
    def __init__(self, blueprint_id):
        self.id = blueprint_id
        self.attributes = {}

    def has_attribute(self, name):
        return True

    def set_attribute(self, name, value):
        self.attributes[name] = value


class BlueprintLibrary:
    def __init__(self):
        self.items = {}

    def find(self, blueprint_id):
        return self.items.setdefault(blueprint_id, Blueprint(blueprint_id))


class Sensor:
    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.callback = None

    def listen(self, callback):
        self.callback = callback


class Session:
    def __init__(self):
        self.frame_buffer = SensorFrameBuffer()
        self.continuous = []
        self.tracked = []

    def attach_sensor(self, blueprint, transform, ego, sensor_id):
        sensor = Sensor(blueprint)
        sensor.listen(self.frame_buffer.callback(sensor_id))
        self.continuous.append((sensor_id, transform, sensor))
        return sensor

    def track_actor(self, actor):
        self.tracked.append(actor)
        return actor


class ActorList(list):
    def filter(self, pattern):
        return [item for item in self if item.type_id.startswith("vehicle.")]


class World:
    def __init__(self, actors=()):
        self.blueprints = BlueprintLibrary()
        self.spawned = []
        self.actors = ActorList(actors)

    def get_blueprint_library(self):
        return self.blueprints

    def spawn_actor(self, blueprint, transform, attach_to=None):
        sensor = Sensor(blueprint)
        self.spawned.append((blueprint.id, transform, attach_to, sensor))
        return sensor

    def get_actors(self):
        return self.actors


class Waypoint:
    def __init__(self, x, y):
        self.transform = Transform(Vec(x, y, 0.0))


class WorldMap:
    def get_waypoint(self, location, project_to_road=True):
        return Waypoint(location.x, 0.0)


class TrafficLight:
    def __init__(self, state="Red", stop_x=20.0):
        self.state = state
        self.stop_x = stop_x

    def get_state(self):
        return self.state

    def get_stop_waypoints(self):
        return [Waypoint(self.stop_x, 0.0)]


class Actor:
    type_id = "vehicle.test"
    is_alive = True

    def __init__(self, actor_id, x=0.0, y=0.0, speed=0.0, traffic_light=None):
        self.id = actor_id
        self.location = Vec(x, y, 0.0)
        self.speed = speed
        self.traffic_light = traffic_light

    def get_location(self):
        return self.location

    def get_velocity(self):
        return Vec(self.speed, 0.0, 0.0)

    def get_transform(self):
        return Transform(self.location)

    def get_traffic_light(self):
        return self.traffic_light

    def is_at_traffic_light(self):
        return self.traffic_light is not None

    def get_traffic_light_state(self):
        return "Red" if self.traffic_light else "Unknown"

    def get_speed_limit(self):
        return 36.0


class Measurement:
    def __init__(self, frame, points=None):
        self.frame = frame
        self.points = np.empty((0, 3), dtype=np.float32) if points is None else np.asarray(points, dtype=np.float32)


def _suite(session, events=None):
    return AttachedCarlaSensors({}, events or EventLedger())


def test_attach_default_sensor_suite_configures_continuous_and_event_callbacks() -> None:
    world, session, ego = World(), Session(), Actor(1)
    attached = attach_default_sensors(session, world, ego, CarlaApi)

    assert tuple(item[0] for item in session.continuous) == CONTINUOUS_SENSOR_IDS
    assert set(attached.actors) == {RGB_SENSOR_ID, LIDAR_SENSOR_ID, COLLISION_SENSOR_ID, LANE_INVASION_SENSOR_ID}
    assert len(session.tracked) == 2
    assert world.blueprints.items["sensor.camera.rgb"].attributes["sensor_tick"] == "0.05"
    collision_sensor = next(item[3] for item in world.spawned if item[0] == "sensor.other.collision")
    collision_sensor.callback(type("Event", (), {"frame": 9})())
    assert attached.events.flags_for_frame(9) == (True, False)


def test_sensor_tick_tracks_world_fixed_delta() -> None:
    world, session, ego = World(), Session(), Actor(1)
    attach_default_sensors(session, world, ego, CarlaApi, sensor_tick_s=0.1)
    assert world.blueprints.items["sensor.camera.rgb"].attributes["sensor_tick"] == "0.1"
    assert world.blueprints.items["sensor.lidar.ray_cast"].attributes["sensor_tick"] == "0.1"


def test_bridge_combines_aligned_lidar_events_map_and_associated_actor_truth() -> None:
    ego = Actor(1, x=0.0, y=0.6, speed=5.0, traffic_light=TrafficLight("Red", 20.0))
    lead = Actor(2, x=12.0, y=0.2, speed=3.0)
    world, session, events = World((ego, lead)), Session(), EventLedger()
    events.collision_callback(type("Event", (), {"frame": 42})())
    events.lane_invasion_callback(type("Event", (), {"frame": 42})())
    points = [[11.8, -0.3, -0.5], [12.0, 0.0, -0.4], [12.2, 0.3, -0.6], [40.0, 8.0, 0.0]]
    session.frame_buffer.push(RGB_SENSOR_ID, 42, Measurement(42))
    session.frame_buffer.push(LIDAR_SENSOR_ID, 42, Measurement(42, points))
    bridge = CarlaPerceptionBridge(world, WorldMap(), ego, session, _suite(session, events))

    sample = bridge.acquire(
        42, 2.1, route=RouteReference(((0.0, 0.0), (30.0, 0.0)), 0.0, 5.0), timeout_s=0.01,
    )

    frame = sample.frame
    assert frame.frame == 42
    assert frame.lead_distance_m == pytest.approx(11.84, abs=0.02)
    assert frame.lead_speed_mps == 3.0
    assert frame.traffic_light == "RED"
    assert frame.distance_to_stop_line_m == 20.0
    assert frame.speed_limit_mps == 10.0
    assert frame.lane_offset_m == pytest.approx(0.6)
    assert frame.route_deviation_m == pytest.approx(0.6)
    assert frame.collision and frame.lane_invasion
    assert not frame.red_light_violation
    assert sample.source_by_field["lead_distance_m"] == "LIDAR_FRONT_CORRIDOR"
    assert sample.source_by_field["lead_speed_mps"] == "CARLA_TRUTH_LIDAR_ASSOCIATED_ACTOR"
    assert sample.source_by_field["distance_to_stop_line_m"] == "CARLA_MAP_STOP_WAYPOINT"


def test_lidar_obstacle_without_actor_is_kept_as_stationary_hazard() -> None:
    ego, session = Actor(1), Session()
    points = [[6.0, -0.2, 0.0], [6.1, 0.0, 0.0], [6.2, 0.2, 0.0]]
    session.frame_buffer.push(RGB_SENSOR_ID, 3, Measurement(3))
    session.frame_buffer.push(LIDAR_SENSOR_ID, 3, Measurement(3, points))
    bridge = CarlaPerceptionBridge(World((ego,)), WorldMap(), ego, session, _suite(session))

    sample = bridge.acquire(3, 0.15, timeout_s=0.01)

    assert sample.frame.lead_distance_m == pytest.approx(6.02)
    assert sample.frame.lead_speed_mps == 0.0
    assert sample.source_by_field["lead_speed_mps"] == "LIDAR_STATIC_OBSTACLE_ASSUMPTION"


def test_moving_through_red_stop_waypoint_sets_violation() -> None:
    ego = Actor(1, speed=2.0, traffic_light=TrafficLight("Red", 0.0))
    session = Session()
    session.frame_buffer.push(RGB_SENSOR_ID, 4, Measurement(4))
    session.frame_buffer.push(LIDAR_SENSOR_ID, 4, Measurement(4))
    bridge = CarlaPerceptionBridge(World((ego,)), WorldMap(), ego, session, _suite(session))
    sample = bridge.acquire(4, 0.2, timeout_s=0.01)
    assert sample.frame.red_light_violation


def test_missing_continuous_sensor_times_out_fail_closed() -> None:
    ego, session = Actor(1), Session()
    session.frame_buffer.push(RGB_SENSOR_ID, 8, Measurement(8))
    bridge = CarlaPerceptionBridge(World((ego,)), WorldMap(), ego, session, _suite(session))

    with pytest.raises(PerceptionTimeoutError, match="normal control must be suppressed") as caught:
        bridge.acquire(8, 0.4, timeout_s=0.001)
    assert caught.value.emergency_brake_required is True


def test_late_sparse_safety_event_is_reported_on_next_control_frame() -> None:
    events = EventLedger()
    assert events.flags_for_frame(10) == (False, False)
    events.collision_callback(type("LateEvent", (), {"frame": 10})())
    assert events.flags_for_frame(11) == (True, False)
    assert events.flags_for_frame(12) == (False, False)


def test_payload_frame_mismatch_is_rejected() -> None:
    ego, session = Actor(1), Session()
    session.frame_buffer.push(RGB_SENSOR_ID, 7, Measurement(6))
    session.frame_buffer.push(LIDAR_SENSOR_ID, 7, Measurement(7))
    bridge = CarlaPerceptionBridge(World((ego,)), WorldMap(), ego, session, _suite(session))

    with pytest.raises(FrameAlignmentError, match="expected frame=7"):
        bridge.acquire(7, 0.35, timeout_s=0.01)


def test_front_lidar_requires_a_cluster_in_lane_corridor() -> None:
    isolated = Measurement(1, [[5.0, 0.0, 0.0], [4.0, 5.0, 0.0], [3.0, 0.0, 3.0]])
    assert front_lidar_distance_m(isolated) is None
