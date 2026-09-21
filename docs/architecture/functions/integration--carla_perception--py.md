# carla_perception：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[integration/carla_perception.py](../../../integration/carla_perception.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Frame-aligned CARLA sensor and simulator-truth perception bridge.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `SensorMount.x_m: float`；默认：`未在声明处设置`。
- `SensorMount.y_m: float`；默认：`未在声明处设置`。
- `SensorMount.z_m: float`；默认：`未在声明处设置`。
- `SensorMount.pitch_deg: float`；默认：`0.0`。
- `SensorMount.yaw_deg: float`；默认：`0.0`。
- `SensorMount.roll_deg: float`；默认：`0.0`。
- `CarlaSensorSpec.sensor_id: str`；默认：`未在声明处设置`。
- `CarlaSensorSpec.blueprint_id: str`；默认：`未在声明处设置`。
- `CarlaSensorSpec.mount: SensorMount`；默认：`未在声明处设置`。
- `CarlaSensorSpec.attributes: Mapping[str, str]`；默认：`field(default_factory=dict)`。
- `CarlaSensorSpec.continuous: bool`；默认：`True`。
- `AttachedCarlaSensors.actors: Mapping[str, Any]`；默认：`未在声明处设置`。
- `AttachedCarlaSensors.events: EventLedger`；默认：`未在声明处设置`。
- `PerceptionSample.frame: PerceptionFrame`；默认：`未在声明处设置`。
- `PerceptionSample.sensor_ready_ns: int`；默认：`未在声明处设置`。
- `PerceptionSample.source_by_field: Mapping[str, str]`；默认：`未在声明处设置`。
- `PerceptionSample.rgb: Any`；默认：`未在声明处设置`。
- `PerceptionSample.lidar: Any`；默认：`未在声明处设置`。
- `PerceptionSample.radar: Any | None`；默认：`未在声明处设置`。
- `PerceptionSample.safety_summary: SafetyStateSummary`；默认：`未在声明处设置`。
- `PerceptionSample.multi_view_rgb: Mapping[str, Any]`；默认：`field(default_factory=dict)`。
- `FrontRadarTarget.distance_m: float`；默认：`未在声明处设置`。
- `FrontRadarTarget.closing_speed_mps: float`；默认：`未在声明处设置`。
- `TemporalLeadTracker.hold_s: float`；默认：`0.75`。
- `TemporalLeadTracker.acquire_within_m: float`；默认：`35.0`。
- `TemporalLeadTracker.max_lead_speed_mps: float`；默认：`20.0`。
- `TemporalLeadTracker.distance_m: float | None`；默认：`None`。
- `TemporalLeadTracker.lead_speed_mps: float | None`；默认：`None`。
- `TemporalLeadTracker.last_update_s: float | None`；默认：`None`。
- `TemporalLeadTracker.last_observed_s: float | None`；默认：`None`。
- `TemporalLeadTracker.last_observed_distance_m: float | None`；默认：`None`。
- `TemporalLeadTracker.ego_travel_since_observation_m: float`；默认：`0.0`。

## 功能入口：输入、输出与实现说明

### `PerceptionAcquisitionError`

源码位置：[integration/carla_perception.py 第 52 行](../../../integration/carla_perception.py#L52)。类型：`ClassDef`。

Base error that requires the caller to suppress normal vehicle control.

### `PerceptionTimeoutError`

源码位置：[integration/carla_perception.py 第 58 行](../../../integration/carla_perception.py#L58)。类型：`ClassDef`。

A required continuous sensor did not produce the requested frame.

### `FrameAlignmentError`

源码位置：[integration/carla_perception.py 第 62 行](../../../integration/carla_perception.py#L62)。类型：`ClassDef`。

A callback payload was labelled with a different CARLA frame.

### `PerceptionDataError`

源码位置：[integration/carla_perception.py 第 66 行](../../../integration/carla_perception.py#L66)。类型：`ClassDef`。

A required sensor payload was present but malformed or unusable.

### `ObjectDetectionError`

源码位置：[integration/carla_perception.py 第 70 行](../../../integration/carla_perception.py#L70)。类型：`ClassDef`。

Configured RGB inference failed, so normal control is unsafe.

### `SensorMount`

源码位置：[integration/carla_perception.py 第 75 行](../../../integration/carla_perception.py#L75)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CarlaSensorSpec`

源码位置：[integration/carla_perception.py 第 85 行](../../../integration/carla_perception.py#L85)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sensor_specs_for_profile`

源码位置：[integration/carla_perception.py 第 208 行](../../../integration/carla_perception.py#L208)。类型：`FunctionDef`。

```python
sensor_specs_for_profile(profile: str) -> tuple[CarlaSensorSpec, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `EventLedger`

源码位置：[integration/carla_perception.py 第 221 行](../../../integration/carla_perception.py#L221)。类型：`ClassDef`。

Thread-safe exact-frame storage for sparse CARLA safety events.

### `EventLedger.__init__`

源码位置：[integration/carla_perception.py 第 224 行](../../../integration/carla_perception.py#L224)。类型：`FunctionDef`。

```python
EventLedger.__init__(self, *, retain_frames: int=64) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `EventLedger.collision_callback`

源码位置：[integration/carla_perception.py 第 232 行](../../../integration/carla_perception.py#L232)。类型：`FunctionDef`。

```python
EventLedger.collision_callback(self, event: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `EventLedger.lane_invasion_callback`

源码位置：[integration/carla_perception.py 第 235 行](../../../integration/carla_perception.py#L235)。类型：`FunctionDef`。

```python
EventLedger.lane_invasion_callback(self, event: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `EventLedger._record`

源码位置：[integration/carla_perception.py 第 238 行](../../../integration/carla_perception.py#L238)。类型：`FunctionDef`。

```python
EventLedger._record(self, target: set[int], event: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `EventLedger.flags_for_frame`

源码位置：[integration/carla_perception.py 第 250 行](../../../integration/carla_perception.py#L250)。类型：`FunctionDef`。

```python
EventLedger.flags_for_frame(self, frame: int) -> tuple[bool, bool]
```

Consume all safety events no newer than ``frame``.

Continuous sensor callbacks normally give sparse events enough time to
arrive, but CARLA does not guarantee callback ordering.  An event for
frame N that arrives after N was acquired is therefore surfaced on
frame N+1 instead of being discarded forever.

### `AttachedCarlaSensors`

源码位置：[integration/carla_perception.py 第 269 行](../../../integration/carla_perception.py#L269)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PerceptionSample`

源码位置：[integration/carla_perception.py 第 275 行](../../../integration/carla_perception.py#L275)。类型：`ClassDef`。

Controller frame plus auditable provenance and aligned raw payloads.

### `_make_transform`

源码位置：[integration/carla_perception.py 第 288 行](../../../integration/carla_perception.py#L288)。类型：`FunctionDef`。

```python
_make_transform(carla_api: Any, mount: SensorMount) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_configured_blueprint`

源码位置：[integration/carla_perception.py 第 296 行](../../../integration/carla_perception.py#L296)。类型：`FunctionDef`。

```python
_configured_blueprint(world: Any, spec: CarlaSensorSpec) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `attach_default_sensors`

源码位置：[integration/carla_perception.py 第 307 行](../../../integration/carla_perception.py#L307)。类型：`FunctionDef`。

```python
attach_default_sensors(session: CarlaSession, world: Any, ego: Any, carla_api: Any, *, specs: Sequence[CarlaSensorSpec]=DEFAULT_SENSOR_SPECS, sensor_tick_s: float | None=None) -> AttachedCarlaSensors
```

Attach the standard sensor suite and register all actors with ``session``.

Event sensors intentionally bypass ``session.frame_buffer`` because they do
not emit a no-event sample on every tick.  Their actors still belong to the
session registry and are stopped/destroyed on context exit.

### `attach_event_sensors`

源码位置：[integration/carla_perception.py 第 362 行](../../../integration/carla_perception.py#L362)。类型：`FunctionDef`。

```python
attach_event_sensors(session: CarlaSession, world: Any, ego: Any, carla_api: Any) -> AttachedCarlaSensors
```

Attach collision/lane-invasion sensors without RGB/LiDAR streams.

### `_xyz`

源码位置：[integration/carla_perception.py 第 374 行](../../../integration/carla_perception.py#L374)。类型：`FunctionDef`。

```python
_xyz(value: Any) -> tuple[float, float, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_speed_mps`

源码位置：[integration/carla_perception.py 第 378 行](../../../integration/carla_perception.py#L378)。类型：`FunctionDef`。

```python
_speed_mps(actor: Any) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_lidar_xyz`

源码位置：[integration/carla_perception.py 第 383 行](../../../integration/carla_perception.py#L383)。类型：`FunctionDef`。

```python
_lidar_xyz(measurement: Any) -> np.ndarray
```

Read CARLA float32 x/y/z/intensity data or a test ``points`` array.

### `front_lidar_distance_m`

源码位置：[integration/carla_perception.py 第 399 行](../../../integration/carla_perception.py#L399)。类型：`FunctionDef`。

```python
front_lidar_distance_m(measurement: Any, *, min_range_m: float=1.0, max_range_m: float=60.0, half_width_m: float=1.35, min_height_m: float=-1.8, max_height_m: float=-0.7, minimum_points: int=3) -> float | None
```

Return a conservative low-percentile range inside the ego lane corridor.

The roof LiDAR is mounted at 2.35 m while the competition ego's bounding
box reaches about 1.48 m. Returns above ``-0.70`` in the sensor frame are
therefore outside the ego collision envelope (including a small clearance
margin) and commonly come from tree canopies, traffic-light arms, and
flyover structures. Treating those overhead returns as a lead object can
hold the vehicle stopped forever on an otherwise clear lane.

### `adjacent_lidar_distances_m`

源码位置：[integration/carla_perception.py 第 434 行](../../../integration/carla_perception.py#L434)。类型：`FunctionDef`。

```python
adjacent_lidar_distances_m(measurement: Any, *, min_forward_m: float=1.0, max_forward_m: float=25.0, inner_lateral_m: float=1.75, outer_lateral_m: float=5.25, min_height_m: float=-1.8, max_height_m: float=-0.7, minimum_points: int=3) -> tuple[float | None, float | None]
```

Return LiDAR-grounded left/right adjacent-lane obstacle ranges.

### `adjacent_lidar_distances_m.distance`

源码位置：[integration/carla_perception.py 第 454 行](../../../integration/carla_perception.py#L454)。类型：`FunctionDef`。

```python
adjacent_lidar_distances_m.distance(mask: np.ndarray) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FrontRadarTarget`

源码位置：[integration/carla_perception.py 第 474 行](../../../integration/carla_perception.py#L474)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TemporalLeadTracker`

源码位置：[integration/carla_perception.py 第 480 行](../../../integration/carla_perception.py#L480)。类型：`ClassDef`。

Bridge brief LiDAR dropouts without releasing the following target.

Narrow road users such as bicycles can yield fewer than the required
LiDAR cluster points in an individual scan. Treating that one empty scan
as a clear road makes longitudinal control alternate between cruise and
emergency braking. This tracker keeps only a short, close-range history
and expires quickly so a departed target cannot become a persistent
phantom.

### `TemporalLeadTracker.reset`

源码位置：[integration/carla_perception.py 第 501 行](../../../integration/carla_perception.py#L501)。类型：`FunctionDef`。

```python
TemporalLeadTracker.reset(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TemporalLeadTracker.update`

源码位置：[integration/carla_perception.py 第 509 行](../../../integration/carla_perception.py#L509)。类型：`FunctionDef`。

```python
TemporalLeadTracker.update(self, *, sim_time_s: float, ego_speed_mps: float, observed_distance_m: float | None, observed_lead_speed_mps: float | None) -> tuple[float | None, float | None, bool]
```

Return ``(gap, lead speed, predicted)`` for the current frame.

### `front_radar_target`

源码位置：[integration/carla_perception.py 第 594 行](../../../integration/carla_perception.py#L594)。类型：`FunctionDef`。

```python
front_radar_target(measurement: Any, *, sensor_x_offset_m: float=1.5, min_range_m: float=1.0, max_range_m: float=80.0, half_width_m: float=1.75, min_altitude_deg: float=-3.0, max_altitude_deg: float=3.0) -> FrontRadarTarget | None
```

Select the nearest finite radar return inside the ego corridor.

CARLA reports ``depth`` along the ray. Its implementation computes radial
``velocity`` as ``dot(target_velocity - sensor_velocity, outward_ray)``:
a slower lead approached by ego is therefore negative. The mount offset
converts the range to the ego coordinate origin; absolute lead speed is
derived later from ego speed plus that signed relative velocity.

### `_normalise_light_state`

源码位置：[integration/carla_perception.py 第 640 行](../../../integration/carla_perception.py#L640)。类型：`FunctionDef`。

```python
_normalise_light_state(value: Any) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_upcoming_traffic_light`

源码位置：[integration/carla_perception.py 第 645 行](../../../integration/carla_perception.py#L645)。类型：`FunctionDef`。

```python
_upcoming_traffic_light(ego: Any, traffic_lights: Iterable[Any], *, world_map: Any | None=None, max_distance_m: float=50.0, lateral_gate_m: float=4.5) -> tuple[str, float] | None
```

Find the nearest same-lane stop waypoint before CARLA marks it active.

### `traffic_light_and_stop_distance`

源码位置：[integration/carla_perception.py 第 709 行](../../../integration/carla_perception.py#L709)。类型：`FunctionDef`。

```python
traffic_light_and_stop_distance(ego: Any, traffic_lights: Iterable[Any]=(), *, world_map: Any | None=None) -> tuple[str, float | None, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `actor_speed_limit_mps`

源码位置：[integration/carla_perception.py 第 770 行](../../../integration/carla_perception.py#L770)。类型：`FunctionDef`。

```python
actor_speed_limit_mps(ego: Any) -> float | None
```

Return CARLA's map speed limit in m/s when it is finite and positive.

### `route_deviation_m`

源码位置：[integration/carla_perception.py 第 781 行](../../../integration/carla_perception.py#L781)。类型：`FunctionDef`。

```python
route_deviation_m(x_m: float, y_m: float, route: RouteReference) -> float
```

Return planar distance from a point to the nearest route segment.

### `lane_metrics`

源码位置：[integration/carla_perception.py 第 799 行](../../../integration/carla_perception.py#L799)。类型：`FunctionDef`。

```python
lane_metrics(world_map: Any, ego: Any, route: RouteReference | None) -> tuple[float | None, float | None]
```

Return signed lane-center offset and route deviation from CARLA map geometry.

### `CarlaPerceptionBridge`

源码位置：[integration/carla_perception.py 第 820 行](../../../integration/carla_perception.py#L820)。类型：`ClassDef`。

Convert one exact CARLA sensor frame into the controller contract.

### `CarlaPerceptionBridge.__init__`

源码位置：[integration/carla_perception.py 第 823 行](../../../integration/carla_perception.py#L823)。类型：`FunctionDef`。

```python
CarlaPerceptionBridge.__init__(self, world: Any, world_map: Any, ego: Any, session: CarlaSession, sensors: AttachedCarlaSensors, detector: Any | None=None, *, visual_provider: Callable[[Any], VisualObservation] | None=None, fusion: ConservativeSensorFusion | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CarlaPerceptionBridge.acquire`

源码位置：[integration/carla_perception.py 第 848 行](../../../integration/carla_perception.py#L848)。类型：`FunctionDef`。

```python
CarlaPerceptionBridge.acquire(self, frame: int, sim_time_s: float, *, route: RouteReference | None=None, timeout_s: float=0.25) -> PerceptionSample
```

Acquire a frame or raise a fail-closed ``PerceptionAcquisitionError``.

## 内部调用与异常路径

- `sensor_specs_for_profile` 调用：`ValueError`, `str`, `str(profile).strip`, `str(profile).strip().lower`.
- `_make_transform` 调用：`carla_api.Location`, `carla_api.Rotation`, `carla_api.Transform`.
- `_configured_blueprint` 调用：`LookupError`, `blueprint.has_attribute`, `blueprint.set_attribute`, `hasattr`, `spec.attributes.items`, `world.get_blueprint_library`, `world.get_blueprint_library().find`.
- `attach_default_sensors` 调用：`AttachedCarlaSensors`, `CarlaSensorSpec`, `EventLedger`, `MappingProxyType`, `ValueError`, `_configured_blueprint`, `_make_transform`, `actor.listen`, `dict`, `float`, `math.isfinite`, `session.attach_sensor`, `session.track_actor`, `str`, `type`, `world.spawn_actor`.
- `attach_event_sensors` 调用：`attach_default_sensors`.
- `_xyz` 调用：`float`.
- `_speed_mps` 调用：`_xyz`, `actor.get_velocity`, `math.hypot`.
- `_lidar_xyz` 调用：`ValueError`, `getattr`, `hasattr`, `np.asarray`, `np.frombuffer`, `values.reshape`.
- `front_lidar_distance_m` 调用：`_lidar_xyz`, `float`, `len`, `np.abs`, `np.percentile`.
- `adjacent_lidar_distances_m` 调用：`_lidar_xyz`, `distance`, `float`, `len`, `np.hypot`, `np.percentile`.
- `front_radar_target` 调用：`FrontRadarTarget`, `ValueError`, `abs`, `all`, `candidates.append`, `float`, `getattr`, `iter`, `math.cos`, `math.degrees`, `math.isfinite`, `math.sin`, `min`, `tuple`.
- `_normalise_light_state` 调用：`str`, `str(value).split`, `str(value).split('.')[-1].upper`.
- `_upcoming_traffic_light` 调用：`_normalise_light_state`, `_xyz`, `abs`, `callable`, `candidates.append`, `ego.get_location`, `ego.get_transform`, `ego.get_transform().get_forward_vector`, `float`, `get_state`, `get_waypoint`, `get_waypoints`, `getattr`, `math.hypot`, `max`, `min`, `tuple`, `waypoint_forward`.
- `traffic_light_and_stop_distance` 调用：`_normalise_light_state`, `_upcoming_traffic_light`, `_xyz`, `bool`, `callable`, `candidates.append`, `ego.get_location`, `ego.get_traffic_light_state`, `ego.get_transform`, `ego.get_transform().get_forward_vector`, `float`, `get_light`, `get_stop_waypoints`, `getattr`, `getattr(ego, 'is_at_traffic_light', lambda: False)`, `getattr(light, 'get_transform', lambda: None)`, `light.get_state`, `max`, `min`, `transform.transform`.
- `actor_speed_limit_mps` 调用：`callable`, `float`, `get_speed_limit`, `getattr`, `math.isfinite`.
- `route_deviation_m` 调用：`len`, `math.hypot`, `max`, `min`, `segment_distances.append`, `zip`.
- `lane_metrics` 调用：`_xyz`, `abs`, `ego.get_location`, `route_deviation_m`, `waypoint.transform.get_right_vector`, `world_map.get_waypoint`.
- `__init__` 调用：`ConservativeSensorFusion`, `SensorObjectTracker`, `TemporalLeadTracker`, `ValueError`, `getattr`, `set`, `str`, `str(getattr(actor, 'type_id', '')).startswith`, `threading.Lock`, `tuple`, `type`, `world.get_actors`.
- `collision_callback` 调用：`self._record`.
- `lane_invasion_callback` 调用：`self._record`.
- `_record` 调用：`getattr`, `len`, `sorted`, `target.add`, `type`.
- `flags_for_frame` 调用：`ValueError`, `any`, `type`.
- `distance` 调用：`float`, `np.hypot`, `np.percentile`.
- `update` 调用：`float`, `max`, `min`, `self.reset`.
- `acquire` 调用：`DetectedObject`, `FrameAlignmentError`, `MappingProxyType`, `ObjectDetectionError`, `PerceptionDataError`, `PerceptionFrame`, `PerceptionSample`, `PerceptionTimeoutError`, `TypeError`, `VisualObservation`, `VisualObservation.unavailable`, `_speed_mps`, `abs`, `actor_speed_limit_mps`, `adjacent_lidar_distances_m`, `adjacent_objects.append`, `aligned.get`, `aligned.items`, `driving_corridor_detections`, `front_lidar_distance_m`, `front_radar_target`, `getattr`, `isinstance`, `lane_metrics`, `max`, `min`, `replace`, `self._detector.detect_measurement`, `self._fusion.update`, `self._lead_tracker.update`, `self._object_tracker.update`, `self._sensors.events.flags_for_frame`, `self._session.frame_buffer.pop_aligned_optional`, `self._visual_provider`, `sources.get`, `time.monotonic_ns`, `traffic_light_and_stop_distance`, `tuple`, `type`, `type(error).__name__.upper`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 226 行：`ValueError('retain_frames must be a positive integer')`。
- `__init__`，第 831 行：`ValueError('configure detector or visual_provider, not both')`。
- `_configured_blueprint`，第 299 行：`LookupError(f'CARLA blueprint not found: {spec.blueprint_id}')`。
- `_configured_blueprint`，第 302 行：`LookupError(f'{spec.blueprint_id} does not support attribute {name}')`。
- `_lidar_xyz`，第 388 行：`ValueError('lidar points must have shape (N, >=3)')`。
- `_lidar_xyz`，第 392 行：`ValueError('lidar measurement has neither points nor raw_data')`。
- `_lidar_xyz`，第 395 行：`ValueError('CARLA lidar raw_data length is not divisible by four floats')`。
- `acquire`，第 868 行：`PerceptionTimeoutError(f'required RGB/LiDAR frame {frame} unavailable; pending sensor frames={pending}; normal control must be suppressed')`。
- `acquire`，第 885 行：`FrameAlignmentError(f'{sensor_id} payload frame={payload_frame!r}, expected frame={frame}')`。
- `acquire`，第 899 行：`ObjectDetectionError(f'RGB ONNX detection failed for frame {frame}: {error}')`。
- `acquire`，第 919 行：`TypeError('visual_provider must return VisualObservation')`。
- `acquire`，第 921 行：`ObjectDetectionError(f'configured RGB provider failed for frame {frame}: {error}')`。
- `acquire`，第 925 行：`ObjectDetectionError(f'configured RGB provider returned frame {visual.frame}, expected {frame}')`。
- `acquire`，第 933 行：`PerceptionDataError(f'LiDAR frame {frame} is unusable; normal control must be suppressed')`。
- `attach_default_sensors`，第 323 行：`ValueError('ego must not be None')`。
- `attach_default_sensors`，第 327 行：`ValueError('sensor_tick_s must be finite and positive')`。
- `attach_default_sensors`，第 332 行：`ValueError(f'duplicate sensor_id: {spec.sensor_id}')`。
- `flags_for_frame`，第 259 行：`ValueError('frame must be a non-negative integer')`。
- `front_radar_target`，第 616 行：`ValueError('radar measurement is not iterable')`。
- `sensor_specs_for_profile`，第 213 行：`ValueError(f'unknown sensor profile: {profile!r}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [integration/object_tracker.py](../../../integration/object_tracker.py)
- [integration/rgb_detector.py](../../../integration/rgb_detector.py)

静态 import 消费者（含测试）：

- [integration/__init__.py](../../../integration/__init__.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/sensor_stability.py](../../../integration/sensor_stability.py)
- [integration/tests/test_carla_perception.py](../../../integration/tests/test_carla_perception.py)
- [integration/tests/test_carla_runner_helpers.py](../../../integration/tests/test_carla_runner_helpers.py)
- [integration/tests/test_sensor_profiles.py](../../../integration/tests/test_sensor_profiles.py)
- [integration/tests/test_sensor_stability.py](../../../integration/tests/test_sensor_stability.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/carla_perception.py`

来源 SHA256：`337d3e9dfb6c572c83fd480ba2edd1cba2e75dc34f82e271c9554e0869b758c8`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `SensorMount.x_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorMount.y_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorMount.z_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorMount.pitch_deg` | `float` | `0.0` |
| `SensorMount.yaw_deg` | `float` | `0.0` |
| `SensorMount.roll_deg` | `float` | `0.0` |
| `CarlaSensorSpec.sensor_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CarlaSensorSpec.blueprint_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CarlaSensorSpec.mount` | `SensorMount` | `无声明默认；构造/赋值方提供` |
| `CarlaSensorSpec.attributes` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `CarlaSensorSpec.continuous` | `bool` | `True` |
| `AttachedCarlaSensors.actors` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `AttachedCarlaSensors.events` | `EventLedger` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.frame` | `PerceptionFrame` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.sensor_ready_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.source_by_field` | `Mapping[str, str]` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.rgb` | `Any` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.lidar` | `Any` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.radar` | `Any &#124; None` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.safety_summary` | `SafetyStateSummary` | `无声明默认；构造/赋值方提供` |
| `PerceptionSample.multi_view_rgb` | `Mapping[str, Any]` | `field(default_factory=dict)` |
| `FrontRadarTarget.distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `FrontRadarTarget.closing_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `TemporalLeadTracker.hold_s` | `float` | `0.75` |
| `TemporalLeadTracker.acquire_within_m` | `float` | `35.0` |
| `TemporalLeadTracker.max_lead_speed_mps` | `float` | `20.0` |
| `TemporalLeadTracker.distance_m` | `float &#124; None` | `None` |
| `TemporalLeadTracker.lead_speed_mps` | `float &#124; None` | `None` |
| `TemporalLeadTracker.last_update_s` | `float &#124; None` | `None` |
| `TemporalLeadTracker.last_observed_s` | `float &#124; None` | `None` |
| `TemporalLeadTracker.last_observed_distance_m` | `float &#124; None` | `None` |
| `TemporalLeadTracker.ego_travel_since_observation_m` | `float` | `0.0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `sensor_specs_for_profile` / 213 | `except KeyError` | `raise ValueError(f'unknown sensor profile: {profile!r}') from error` |
| `EventLedger.__init__` / 226 | `type(retain_frames) is not int or retain_frames < 1` | `raise ValueError('retain_frames must be a positive integer')` |
| `EventLedger.flags_for_frame` / 259 | `type(frame) is not int or frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `_configured_blueprint` / 299 | `blueprint is None` | `raise LookupError(f'CARLA blueprint not found: {spec.blueprint_id}')` |
| `_configured_blueprint` / 302 | `hasattr(blueprint, 'has_attribute') and (not blueprint.has_attribute(name))` | `raise LookupError(f'{spec.blueprint_id} does not support attribute {name}')` |
| `attach_default_sensors` / 323 | `ego is None` | `raise ValueError('ego must not be None')` |
| `attach_default_sensors` / 327 | `sensor_tick_s is not None and (type(sensor_tick_s) not in (int, float) or not math.isfinite(float(sensor_tick_s)) or sensor_tick_s <= 0.0)` | `raise ValueError('sensor_tick_s must be finite and positive')` |
| `attach_default_sensors` / 332 | `spec.sensor_id in actors` | `raise ValueError(f'duplicate sensor_id: {spec.sensor_id}')` |
| `attach_default_sensors` / 357 | `NOT (spec.continuous) AND except Exception` | `raise` |
| `_lidar_xyz` / 388 | `hasattr(measurement, 'points') AND points.ndim != 2 or points.shape[1] < 3` | `raise ValueError('lidar points must have shape (N, >=3)')` |
| `_lidar_xyz` / 392 | `raw_data is None` | `raise ValueError('lidar measurement has neither points nor raw_data')` |
| `_lidar_xyz` / 395 | `values.size % 4` | `raise ValueError('CARLA lidar raw_data length is not divisible by four floats')` |
| `front_radar_target` / 616 | `except TypeError` | `raise ValueError('radar measurement is not iterable') from error` |
| `CarlaPerceptionBridge.__init__` / 831 | `detector is not None and visual_provider is not None` | `raise ValueError('configure detector or visual_provider, not both')` |
| `CarlaPerceptionBridge.acquire` / 868 | `except TimeoutError` | `raise PerceptionTimeoutError(f'required RGB/LiDAR frame {frame} unavailable; pending sensor frames={pending}; normal control must be suppressed') from error` |
| `CarlaPerceptionBridge.acquire` / 885 | `payload_frame != frame` | `raise FrameAlignmentError(f'{sensor_id} payload frame={payload_frame!r}, expected frame={frame}')` |
| `CarlaPerceptionBridge.acquire` / 899 | `self._detector is not None AND except Exception` | `raise ObjectDetectionError(f'RGB ONNX detection failed for frame {frame}: {error}') from error` |
| `CarlaPerceptionBridge.acquire` / 919 | `NOT (self._detector is not None) AND NOT (self._visual_provider is None) AND not isinstance(visual, VisualObservation)` | `raise TypeError('visual_provider must return VisualObservation')` |
| `CarlaPerceptionBridge.acquire` / 921 | `NOT (self._detector is not None) AND NOT (self._visual_provider is None) AND except Exception` | `raise ObjectDetectionError(f'configured RGB provider failed for frame {frame}: {error}') from error` |
| `CarlaPerceptionBridge.acquire` / 925 | `NOT (self._detector is not None) AND NOT (self._visual_provider is None) AND visual.frame != frame` | `raise ObjectDetectionError(f'configured RGB provider returned frame {visual.frame}, expected {frame}')` |
| `CarlaPerceptionBridge.acquire` / 933 | `except (TypeError, ValueError)` | `raise PerceptionDataError(f'LiDAR frame {frame} is unusable; normal control must be suppressed') from error` |
