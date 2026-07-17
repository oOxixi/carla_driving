"""Frame-aligned CARLA sensor and simulator-truth perception bridge.

The module deliberately avoids a module-level :mod:`carla` import so its
geometry and failure behaviour can be tested without starting Unreal.  RGB and
LiDAR are continuous sensors and must match the requested simulation frame.
Collision and lane-invasion sensors are event streams and are recorded in a
separate frame-keyed ledger.

This is a bridge, not an object detector.  The front range comes from LiDAR;
CARLA actor truth is used only to associate that range with a vehicle speed.
Every derived field carries an explicit source label in ``PerceptionSample``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import threading
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from car_control_A import CarlaSession
from car_control_A.routing import RouteReference

from .contracts import PerceptionFrame


RGB_SENSOR_ID = "rgb_front"
LIDAR_SENSOR_ID = "lidar_roof"
COLLISION_SENSOR_ID = "collision"
LANE_INVASION_SENSOR_ID = "lane_invasion"
CONTINUOUS_SENSOR_IDS = (RGB_SENSOR_ID, LIDAR_SENSOR_ID)


class PerceptionAcquisitionError(RuntimeError):
    """Base error that requires the caller to suppress normal vehicle control."""

    emergency_brake_required = True


class PerceptionTimeoutError(PerceptionAcquisitionError, TimeoutError):
    """A required continuous sensor did not produce the requested frame."""


class FrameAlignmentError(PerceptionAcquisitionError):
    """A callback payload was labelled with a different CARLA frame."""


@dataclass(frozen=True, slots=True)
class SensorMount:
    x_m: float
    y_m: float
    z_m: float
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    roll_deg: float = 0.0


@dataclass(frozen=True, slots=True)
class CarlaSensorSpec:
    sensor_id: str
    blueprint_id: str
    mount: SensorMount
    attributes: Mapping[str, str] = field(default_factory=dict)
    continuous: bool = True


DEFAULT_SENSOR_SPECS: tuple[CarlaSensorSpec, ...] = (
    CarlaSensorSpec(
        RGB_SENSOR_ID,
        "sensor.camera.rgb",
        SensorMount(1.5, 0.0, 2.2, pitch_deg=-8.0),
        MappingProxyType({
            "image_size_x": "800", "image_size_y": "450", "fov": "100",
            "sensor_tick": "0.05",
        }),
    ),
    CarlaSensorSpec(
        LIDAR_SENSOR_ID,
        "sensor.lidar.ray_cast",
        SensorMount(0.0, 0.0, 2.35),
        MappingProxyType({
            "channels": "32", "range": "80", "rotation_frequency": "20",
            "points_per_second": "56000", "upper_fov": "10",
            "lower_fov": "-30", "sensor_tick": "0.05",
        }),
    ),
    CarlaSensorSpec(
        COLLISION_SENSOR_ID, "sensor.other.collision", SensorMount(0.0, 0.0, 0.0),
        MappingProxyType({}), continuous=False,
    ),
    CarlaSensorSpec(
        LANE_INVASION_SENSOR_ID, "sensor.other.lane_invasion", SensorMount(0.0, 0.0, 0.0),
        MappingProxyType({}), continuous=False,
    ),
)


class EventLedger:
    """Thread-safe exact-frame storage for sparse CARLA safety events."""

    def __init__(self, *, retain_frames: int = 64) -> None:
        if type(retain_frames) is not int or retain_frames < 1:
            raise ValueError("retain_frames must be a positive integer")
        self._retain_frames = retain_frames
        self._collision_frames: set[int] = set()
        self._lane_invasion_frames: set[int] = set()
        self._lock = threading.Lock()

    def collision_callback(self, event: Any) -> None:
        self._record(self._collision_frames, event)

    def lane_invasion_callback(self, event: Any) -> None:
        self._record(self._lane_invasion_frames, event)

    def _record(self, target: set[int], event: Any) -> None:
        frame = getattr(event, "frame", None)
        if type(frame) is not int or frame < 0:
            return
        with self._lock:
            target.add(frame)
            all_frames = self._collision_frames | self._lane_invasion_frames
            if len(all_frames) > self._retain_frames:
                keep_after = sorted(all_frames)[-self._retain_frames]
                self._collision_frames = {item for item in self._collision_frames if item >= keep_after}
                self._lane_invasion_frames = {item for item in self._lane_invasion_frames if item >= keep_after}

    def flags_for_frame(self, frame: int) -> tuple[bool, bool]:
        """Consume all safety events no newer than ``frame``.

        Continuous sensor callbacks normally give sparse events enough time to
        arrive, but CARLA does not guarantee callback ordering.  An event for
        frame N that arrives after N was acquired is therefore surfaced on
        frame N+1 instead of being discarded forever.
        """
        if type(frame) is not int or frame < 0:
            raise ValueError("frame must be a non-negative integer")
        with self._lock:
            collision = any(item <= frame for item in self._collision_frames)
            lane_invasion = any(item <= frame for item in self._lane_invasion_frames)
            self._collision_frames = {item for item in self._collision_frames if item > frame}
            self._lane_invasion_frames = {item for item in self._lane_invasion_frames if item > frame}
        return collision, lane_invasion


@dataclass(frozen=True, slots=True)
class AttachedCarlaSensors:
    actors: Mapping[str, Any]
    events: EventLedger


@dataclass(frozen=True, slots=True)
class PerceptionSample:
    """Controller frame plus auditable provenance and aligned raw payloads."""

    frame: PerceptionFrame
    source_by_field: Mapping[str, str]
    rgb: Any
    lidar: Any


def _make_transform(carla_api: Any, mount: SensorMount) -> Any:
    location = carla_api.Location(x=mount.x_m, y=mount.y_m, z=mount.z_m)
    rotation = carla_api.Rotation(
        pitch=mount.pitch_deg, yaw=mount.yaw_deg, roll=mount.roll_deg,
    )
    return carla_api.Transform(location, rotation)


def _configured_blueprint(world: Any, spec: CarlaSensorSpec) -> Any:
    blueprint = world.get_blueprint_library().find(spec.blueprint_id)
    if blueprint is None:
        raise LookupError(f"CARLA blueprint not found: {spec.blueprint_id}")
    for name, value in spec.attributes.items():
        if hasattr(blueprint, "has_attribute") and not blueprint.has_attribute(name):
            raise LookupError(f"{spec.blueprint_id} does not support attribute {name}")
        blueprint.set_attribute(name, value)
    return blueprint


def attach_default_sensors(
    session: CarlaSession,
    world: Any,
    ego: Any,
    carla_api: Any,
    *,
    specs: Sequence[CarlaSensorSpec] = DEFAULT_SENSOR_SPECS,
    sensor_tick_s: float | None = None,
) -> AttachedCarlaSensors:
    """Attach the standard sensor suite and register all actors with ``session``.

    Event sensors intentionally bypass ``session.frame_buffer`` because they do
    not emit a no-event sample on every tick.  Their actors still belong to the
    session registry and are stopped/destroyed on context exit.
    """
    if ego is None:
        raise ValueError("ego must not be None")
    if sensor_tick_s is not None and (
        type(sensor_tick_s) not in (int, float) or not math.isfinite(float(sensor_tick_s)) or sensor_tick_s <= 0.0
    ):
        raise ValueError("sensor_tick_s must be finite and positive")
    events = EventLedger()
    actors: dict[str, Any] = {}
    for spec in specs:
        if spec.sensor_id in actors:
            raise ValueError(f"duplicate sensor_id: {spec.sensor_id}")
        effective_spec = spec
        if spec.continuous and sensor_tick_s is not None:
            attributes = dict(spec.attributes)
            attributes["sensor_tick"] = str(float(sensor_tick_s))
            effective_spec = CarlaSensorSpec(
                spec.sensor_id, spec.blueprint_id, spec.mount,
                MappingProxyType(attributes), spec.continuous,
            )
        blueprint = _configured_blueprint(world, effective_spec)
        transform = _make_transform(carla_api, spec.mount)
        if spec.continuous:
            actor = session.attach_sensor(blueprint, transform, ego, spec.sensor_id)
        else:
            actor = world.spawn_actor(blueprint, transform, attach_to=ego)
            actor = session.track_actor(actor)
            callback = (
                events.collision_callback
                if spec.sensor_id == COLLISION_SENSOR_ID
                else events.lane_invasion_callback
            )
            try:
                actor.listen(callback)
            except Exception:
                # The registry owns cleanup after a successful track_actor.
                raise
        actors[spec.sensor_id] = actor
    return AttachedCarlaSensors(MappingProxyType(actors), events)


def _xyz(value: Any) -> tuple[float, float, float]:
    return float(value.x), float(value.y), float(value.z)


def _speed_mps(actor: Any) -> float:
    x, y, z = _xyz(actor.get_velocity())
    return math.hypot(x, y)


def _lidar_xyz(measurement: Any) -> np.ndarray:
    """Read CARLA float32 x/y/z/intensity data or a test ``points`` array."""
    if hasattr(measurement, "points"):
        points = np.asarray(measurement.points, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] < 3:
            raise ValueError("lidar points must have shape (N, >=3)")
        return points[:, :3]
    raw_data = getattr(measurement, "raw_data", None)
    if raw_data is None:
        raise ValueError("lidar measurement has neither points nor raw_data")
    values = np.frombuffer(raw_data, dtype=np.float32)
    if values.size % 4:
        raise ValueError("CARLA lidar raw_data length is not divisible by four floats")
    return values.reshape((-1, 4))[:, :3]


def front_lidar_distance_m(
    measurement: Any,
    *,
    min_range_m: float = 1.0,
    max_range_m: float = 60.0,
    half_width_m: float = 1.35,
    min_height_m: float = -2.2,
    max_height_m: float = 1.0,
    minimum_points: int = 3,
) -> float | None:
    """Return a conservative low-percentile range inside the ego lane corridor."""
    points = _lidar_xyz(measurement)
    if not len(points):
        return None
    mask = (
        (points[:, 0] >= min_range_m) & (points[:, 0] <= max_range_m)
        & (np.abs(points[:, 1]) <= half_width_m)
        & (points[:, 2] >= min_height_m) & (points[:, 2] <= max_height_m)
    )
    forward = points[mask, 0]
    if forward.size < minimum_points:
        return None
    # Requiring a small cluster and using the 10th percentile rejects most
    # isolated rays while remaining conservative for an obstacle face.
    return float(np.percentile(forward, 10.0))


def _iter_vehicle_actors(world: Any) -> Iterable[Any]:
    actors = world.get_actors()
    if hasattr(actors, "filter"):
        return actors.filter("vehicle.*")
    return (actor for actor in actors if str(getattr(actor, "type_id", "")).startswith("vehicle."))


def _associated_lead_speed(
    world: Any, ego: Any, lidar_distance_m: float, *, lateral_gate_m: float = 2.5,
    range_gate_m: float = 4.0,
) -> float | None:
    ego_location = ego.get_location()
    ex, ey, ez = _xyz(ego_location)
    forward = ego.get_transform().get_forward_vector()
    fx, fy, _ = _xyz(forward)
    norm = math.hypot(fx, fy)
    if norm <= 1e-6:
        return None
    fx, fy = fx / norm, fy / norm
    best: tuple[float, Any] | None = None
    ego_id = getattr(ego, "id", None)
    for actor in _iter_vehicle_actors(world):
        if actor is ego or (ego_id is not None and getattr(actor, "id", None) == ego_id):
            continue
        if not getattr(actor, "is_alive", True):
            continue
        ax, ay, az = _xyz(actor.get_location())
        dx, dy = ax - ex, ay - ey
        longitudinal = dx * fx + dy * fy
        lateral = abs(-dx * fy + dy * fx)
        if longitudinal <= 0.0 or lateral > lateral_gate_m:
            continue
        mismatch = abs(longitudinal - lidar_distance_m)
        if mismatch <= range_gate_m and (best is None or mismatch < best[0]):
            best = mismatch, actor
    return None if best is None else _speed_mps(best[1])


def _normalise_light_state(value: Any) -> str:
    state = str(value).split(".")[-1].upper()
    return state if state in {"RED", "YELLOW", "GREEN"} else "UNKNOWN"


def _traffic_light_and_stop_distance(ego: Any) -> tuple[str, float | None, str]:
    light = None
    get_light = getattr(ego, "get_traffic_light", None)
    if callable(get_light):
        light = get_light()
    at_light = bool(getattr(ego, "is_at_traffic_light", lambda: False)())
    if light is None and not at_light:
        return "UNKNOWN", None, "NO_ACTIVE_TRAFFIC_LIGHT"
    if light is not None and callable(getattr(light, "get_state", None)):
        state = _normalise_light_state(light.get_state())
    else:
        state = _normalise_light_state(ego.get_traffic_light_state())
    if light is None:
        return state, None, "CARLA_EGO_TRAFFIC_LIGHT_STATE"

    ego_location = ego.get_location()
    ex, ey, _ = _xyz(ego_location)
    forward = ego.get_transform().get_forward_vector()
    fx, fy, _ = _xyz(forward)
    candidates: list[float] = []
    get_stop_waypoints = getattr(light, "get_stop_waypoints", None)
    if callable(get_stop_waypoints):
        for waypoint in get_stop_waypoints() or ():
            wx, wy, _ = _xyz(waypoint.transform.location)
            along = (wx - ex) * fx + (wy - ey) * fy
            if along >= -0.5:
                candidates.append(max(0.0, along))
    if candidates:
        return state, min(candidates), "CARLA_MAP_STOP_WAYPOINT"

    # Some CARLA traffic-light actors expose only a local trigger volume.  It
    # is an approximation, explicitly labelled as such in the provenance map.
    trigger = getattr(light, "trigger_volume", None)
    transform = getattr(light, "get_transform", lambda: None)()
    if trigger is not None and transform is not None:
        location = trigger.location
        if callable(getattr(transform, "transform", None)):
            location = transform.transform(location)
        tx, ty, _ = _xyz(location)
        along = (tx - ex) * fx + (ty - ey) * fy
        return state, max(0.0, along), "CARLA_TRIGGER_VOLUME_APPROXIMATION"
    return state, None, "CARLA_EGO_TRAFFIC_LIGHT_STATE"


def _lane_metrics(world_map: Any, ego: Any, route: RouteReference | None) -> tuple[float | None, float | None]:
    location = ego.get_location()
    waypoint = world_map.get_waypoint(location, project_to_road=True)
    lane_offset: float | None = None
    if waypoint is not None:
        center = waypoint.transform.location
        cx, cy, _ = _xyz(center)
        ex, ey, _ = _xyz(location)
        right = waypoint.transform.get_right_vector()
        rx, ry, _ = _xyz(right)
        lane_offset = (ex - cx) * rx + (ey - cy) * ry
    route_deviation: float | None = None
    if route is not None:
        ex, ey, _ = _xyz(location)
        route_deviation = min(math.hypot(ex - x, ey - y) for x, y in route.points_xy_m)
    elif lane_offset is not None:
        route_deviation = abs(lane_offset)
    return lane_offset, route_deviation


class CarlaPerceptionBridge:
    """Convert one exact CARLA sensor frame into the controller contract."""

    def __init__(
        self, world: Any, world_map: Any, ego: Any, session: CarlaSession,
        sensors: AttachedCarlaSensors,
    ) -> None:
        self._world = world
        self._map = world_map
        self._ego = ego
        self._session = session
        self._sensors = sensors

    def acquire(
        self, frame: int, sim_time_s: float, *, route: RouteReference | None = None,
        timeout_s: float = 0.25,
    ) -> PerceptionSample:
        """Acquire a frame or raise a fail-closed ``PerceptionAcquisitionError``."""
        try:
            aligned = self._session.frame_buffer.pop_aligned(
                CONTINUOUS_SENSOR_IDS, frame, timeout_s=timeout_s,
            )
        except TimeoutError as error:
            pending = self._session.frame_buffer.pending_frames
            raise PerceptionTimeoutError(
                f"required RGB/LiDAR frame {frame} unavailable; pending sensor frames={pending}; "
                "normal control must be suppressed"
            ) from error
        rgb, lidar = aligned[RGB_SENSOR_ID], aligned[LIDAR_SENSOR_ID]
        for sensor_id, payload in aligned.items():
            payload_frame = getattr(payload, "frame", None)
            if payload_frame != frame:
                raise FrameAlignmentError(
                    f"{sensor_id} payload frame={payload_frame!r}, expected frame={frame}"
                )

        sources: dict[str, str] = {}
        lead_distance = front_lidar_distance_m(lidar)
        lead_speed: float | None = None
        if lead_distance is not None:
            lead_speed = _associated_lead_speed(self._world, self._ego, lead_distance)
            sources["lead_distance_m"] = "LIDAR_FRONT_CORRIDOR"
            if lead_speed is None:
                # A detected but unclassified obstacle is conservatively
                # treated as stationary.  It must not disappear from C/D just
                # because actor association failed.
                lead_speed = 0.0
                sources["lead_speed_mps"] = "LIDAR_STATIC_OBSTACLE_ASSUMPTION"
            else:
                sources["lead_speed_mps"] = "CARLA_TRUTH_LIDAR_ASSOCIATED_ACTOR"

        traffic_light, stop_distance, traffic_source = _traffic_light_and_stop_distance(self._ego)
        sources["traffic_light"] = traffic_source
        if stop_distance is not None:
            sources["distance_to_stop_line_m"] = traffic_source
        speed_limit = None
        get_speed_limit = getattr(self._ego, "get_speed_limit", None)
        if callable(get_speed_limit):
            speed_limit_kph = float(get_speed_limit())
            if math.isfinite(speed_limit_kph) and speed_limit_kph > 0.0:
                speed_limit = speed_limit_kph / 3.6
                sources["speed_limit_mps"] = "CARLA_MAP_SPEED_LIMIT"

        lane_offset, route_deviation = _lane_metrics(self._map, self._ego, route)
        if lane_offset is not None:
            sources["lane_offset_m"] = "CARLA_MAP_WAYPOINT"
        if route_deviation is not None:
            sources["route_deviation_m"] = "ROUTE_REFERENCE_NEAREST_POINT" if route else "CARLA_MAP_WAYPOINT"
        collision, lane_invasion = self._sensors.events.flags_for_frame(frame)
        red_light_violation = (
            traffic_light == "RED" and stop_distance is not None and stop_distance <= 0.5
            and _speed_mps(self._ego) > 0.5
        )
        sources["collision"] = "CARLA_COLLISION_EVENT"
        sources["lane_invasion"] = "CARLA_LANE_INVASION_EVENT"
        sources["red_light_violation"] = "CARLA_RED_LIGHT_STOP_LINE_CROSSING"

        perception = PerceptionFrame(
            frame=frame,
            sim_time_s=sim_time_s,
            lead_distance_m=lead_distance,
            lead_speed_mps=lead_speed,
            traffic_light=traffic_light,
            distance_to_stop_line_m=stop_distance,
            speed_limit_mps=speed_limit,
            lane_offset_m=lane_offset,
            route_deviation_m=route_deviation,
            collision=collision,
            red_light_violation=red_light_violation,
            lane_invasion=lane_invasion,
        )
        return PerceptionSample(perception, MappingProxyType(sources), rgb, lidar)
