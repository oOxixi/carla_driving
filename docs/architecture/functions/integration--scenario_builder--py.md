# scenario_builder：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/scenario_builder.py](../../../integration/scenario_builder.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Generic CARLA scenario placement built on route-relative geometry.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `ActorPlacementError`

源码位置：[integration/scenario_builder.py 第 18 行](../../../integration/scenario_builder.py#L18)。类型：`ClassDef`。

A route-relative actor candidate is not legal on the current map.

### `_wrap_degrees`

源码位置：[integration/scenario_builder.py 第 22 行](../../../integration/scenario_builder.py#L22)。类型：`FunctionDef`。

```python
_wrap_degrees(value: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_is_vehicle`

源码位置：[integration/scenario_builder.py 第 26 行](../../../integration/scenario_builder.py#L26)。类型：`FunctionDef`。

```python
_is_vehicle(actor_spec: Mapping[str, object]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_lane_width_m`

源码位置：[integration/scenario_builder.py 第 30 行](../../../integration/scenario_builder.py#L30)。类型：`FunctionDef`。

```python
_lane_width_m(waypoint: Any) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_same_direction`

源码位置：[integration/scenario_builder.py 第 35 行](../../../integration/scenario_builder.py#L35)。类型：`FunctionDef`。

```python
_same_direction(base: Any, target: Any, *, tolerance_deg: float=45.0) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_lane_relation`

源码位置：[integration/scenario_builder.py 第 41 行](../../../integration/scenario_builder.py#L41)。类型：`FunctionDef`。

```python
_lane_relation(actor_spec: Mapping[str, object]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_target_lane_waypoint`

源码位置：[integration/scenario_builder.py 第 51 行](../../../integration/scenario_builder.py#L51)。类型：`FunctionDef`。

```python
_target_lane_waypoint(world_map: Any, base: Any, relation: str) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_legacy_vehicle_lane`

源码位置：[integration/scenario_builder.py 第 73 行](../../../integration/scenario_builder.py#L73)。类型：`FunctionDef`。

```python
_legacy_vehicle_lane(world_map: Any, base: Any, lateral_m: float) -> tuple[Any, float]
```

Convert legacy lane-width offsets into topology lane relations.

Older JSON files used ``spawn.y = +/-3.5`` to mean an adjacent lane.  On
curves that places the vehicle on a marking because the offset is applied
after projecting the route point.  Walk the real CARLA lane graph and keep
only the residual in-lane offset instead.

### `route_relative_carla_transform`

源码位置：[integration/scenario_builder.py 第 100 行](../../../integration/scenario_builder.py#L100)。类型：`FunctionDef`。

```python
route_relative_carla_transform(carla_api: Any, world_map: Any, route_points_xy_m: Sequence[tuple[float, float]], actor_spec: Mapping[str, object], *, forward_offset_m: float=0.0) -> Any
```

Build a CARLA transform tied to route arc length and lane topology.

### `offset_actor_route_position`

源码位置：[integration/scenario_builder.py 第 150 行](../../../integration/scenario_builder.py#L150)。类型：`FunctionDef`。

```python
offset_actor_route_position(actor_spec: Mapping[str, object], *, longitudinal_m: float=0.0, lateral_m: float=0.0) -> dict[str, object]
```

Return a copy with route offsets applied to either schema generation.

### `offset_actor_route_position.shift_progress_triggers`

源码位置：[integration/scenario_builder.py 第 180 行](../../../integration/scenario_builder.py#L180)。类型：`FunctionDef`。

```python
offset_actor_route_position.shift_progress_triggers(value: object) -> object
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `offset_actor_route_position.shift_progress_triggers.visit`

源码位置：[integration/scenario_builder.py 第 183 行](../../../integration/scenario_builder.py#L183)。类型：`FunctionDef`。

```python
offset_actor_route_position.shift_progress_triggers.visit(node: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `rebase_actor_route_position`

源码位置：[integration/scenario_builder.py 第 230 行](../../../integration/scenario_builder.py#L230)。类型：`FunctionDef`。

```python
rebase_actor_route_position(actor_spec: Mapping[str, object], mission_progress_offset_m: float) -> dict[str, object]
```

Map mission-absolute actor coordinates onto a replanned local route.

Activation/deactivation triggers intentionally remain mission-absolute;
only coordinates consumed by the active route geometry are rebased.

### `rebase_actor_route_position.rebase_s`

源码位置：[integration/scenario_builder.py 第 244 行](../../../integration/scenario_builder.py#L244)。类型：`FunctionDef`。

```python
rebase_actor_route_position.rebase_s(container: dict[str, object], key: str, label: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `actor_resample_offsets`

源码位置：[integration/scenario_builder.py 第 283 行](../../../integration/scenario_builder.py#L283)。类型：`FunctionDef`。

```python
actor_resample_offsets(actor_spec: Mapping[str, object], *, seed: int, max_attempts: int=17) -> tuple[tuple[float, float], ...]
```

Return deterministic, reproducible nearby samples for failed spawns.

Longitudinal-only retries cannot recover an otherwise valid actor whose
declared lateral offset lands just outside a lane centre on a curved or
variable-width road.  Try small in-lane lateral corrections first, then
retain the established longitudinal fallback sequence.  The corrections
stay below one metre so they cannot silently move an actor to another
lane.

### `validate_actor_transform`

源码位置：[integration/scenario_builder.py 第 315 行](../../../integration/scenario_builder.py#L315)。类型：`FunctionDef`。

```python
validate_actor_transform(world_map: Any, transform: Any, actor_spec: Mapping[str, object], *, occupied_locations: Sequence[Any]=()) -> None
```

Reject off-lane, misaligned, buried, or overlapping actor candidates.

### `route_relative_target_location`

源码位置：[integration/scenario_builder.py 第 375 行](../../../integration/scenario_builder.py#L375)。类型：`FunctionDef`。

```python
route_relative_target_location(carla_api: Any, world_map: Any, route_points_xy_m: Sequence[tuple[float, float]], actor_spec: Mapping[str, object]) -> Any
```

Resolve a walker's target with the same route frame as its spawn.

### `validate_actor_route_coverage`

源码位置：[integration/scenario_builder.py 第 408 行](../../../integration/scenario_builder.py#L408)。类型：`FunctionDef`。

```python
validate_actor_route_coverage(actor_specs: Sequence[Mapping[str, object]], route_length_m: float) -> None
```

Fail before CARLA mutation if an actor lies outside the route contract.

## 内部调用与异常路径

- `_wrap_degrees` 调用：`float`.
- `_is_vehicle` 调用：`actor_spec.get`, `str`, `str(actor_spec.get('type', 'vehicle')).strip`, `str(actor_spec.get('type', 'vehicle')).strip().lower`.
- `_lane_width_m` 调用：`float`, `getattr`, `math.isfinite`.
- `_same_direction` 调用：`_wrap_degrees`, `abs`, `float`.
- `_lane_relation` 调用：`ValueError`, `actor_spec.get`, `isinstance`, `position.get`, `str`, `str(position.get('lane_relation', 'CURRENT')).strip`, `str(position.get('lane_relation', 'CURRENT')).strip().upper`.
- `_target_lane_waypoint` 调用：`ActorPlacementError`, `_same_direction`, `callable`, `getattr`, `getter`, `relation.lower`, `str`, `str(getattr(target, 'lane_type', 'Driving')).rsplit`, `str(getattr(target, 'lane_type', 'Driving')).rsplit('.', 1)[-1].upper`.
- `_legacy_vehicle_lane` 调用：`_lane_width_m`, `_target_lane_waypoint`, `abs`, `float`, `math.copysign`, `range`.
- `route_relative_carla_transform` 调用：`ActorPlacementError`, `_is_vehicle`, `_lane_relation`, `_legacy_vehicle_lane`, `_target_lane_waypoint`, `actor_route_coordinates`, `actor_spec.get`, `carla_api.Location`, `carla_api.Rotation`, `carla_api.Transform`, `float`, `getattr`, `max`, `offset_route_pose`, `route_pose_at_s`, `select_heading_compatible_waypoint`, `type`, `type(pose)`.
- `offset_actor_route_position` 调用：`TypeError`, `actor_spec.get`, `behavior.get`, `deepcopy`, `dict`, `float`, `isinstance`, `len`, `max`, `node.get`, `node.values`, `shift_progress_triggers`, `str`, `str(node.get('type', '')).lower`, `updated.get`, `updated_target.get`, `visit`.
- `rebase_actor_route_position` 调用：`ActorPlacementError`, `ValueError`, `behavior.get`, `container.get`, `deepcopy`, `dict`, `float`, `isinstance`, `len`, `math.isfinite`, `max`, `rebase_s`, `result.get`.
- `actor_resample_offsets` 调用：`ValueError`, `actor_spec.get`, `candidates.extend`, `enumerate`, `int`, `ord`, `random.Random`, `rng.shuffle`, `str`, `sum`, `tuple`.
- `validate_actor_transform` 调用：`ActorPlacementError`, `_lane_width_m`, `_wrap_degrees`, `abs`, `actor_spec.get`, `any`, `float`, `getattr`, `math.hypot`, `math.isfinite`, `math.sqrt`, `max`, `str`, `str(actor_spec.get('type', 'vehicle')).strip`, `str(actor_spec.get('type', 'vehicle')).strip().lower`, `str(getattr(projected, 'lane_type', 'Driving')).rsplit`, `str(getattr(projected, 'lane_type', 'Driving')).rsplit('.', 1)[-1].upper`, `world_map.get_waypoint`.
- `route_relative_target_location` 调用：`TypeError`, `actor_spec.get`, `behavior.get`, `dict`, `isinstance`, `len`, `route_relative_carla_transform`, `spawn.get`, `target.get`.
- `validate_actor_route_coverage` 调用：`ValueError`, `actor.get`, `actor_route_coordinates`, `float`, `math.isfinite`.
- `shift_progress_triggers` 调用：`deepcopy`, `float`, `isinstance`, `max`, `node.get`, `node.values`, `str`, `str(node.get('type', '')).lower`, `visit`.
- `rebase_s` 调用：`ActorPlacementError`, `container.get`, `float`, `max`.
- `visit` 调用：`float`, `isinstance`, `max`, `node.get`, `node.values`, `str`, `str(node.get('type', '')).lower`, `visit`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_lane_relation`，第 47 行：`ValueError(f'unsupported route_position.lane_relation: {relation!r}')`。
- `_target_lane_waypoint`，第 58 行：`ActorPlacementError(f'scenario actor requires unavailable {relation.lower()} lane')`。
- `_target_lane_waypoint`，第 63 行：`ActorPlacementError(f'scenario actor target lane is not driving: {lane_type}')`。
- `_target_lane_waypoint`，第 67 行：`ActorPlacementError(f'scenario actor target {relation.lower()} lane runs in the opposite direction')`。
- `actor_resample_offsets`，第 299 行：`ValueError('max_attempts must be positive')`。
- `offset_actor_route_position`，第 172 行：`TypeError('scenario actor spawn must be an object')`。
- `rebase_actor_route_position`，第 241 行：`ValueError('mission_progress_offset_m must be finite and non-negative')`。
- `rebase_actor_route_position`，第 248 行：`ActorPlacementError(f'{label} at mission s={original_s:.2f} m is behind replan origin s={offset_m:.2f} m')`。
- `rebase_actor_route_position`，第 272 行：`ActorPlacementError(f'legacy actor target at mission s={original_s:.2f} m is behind replan origin s={offset_m:.2f} m')`。
- `rebase_s`，第 248 行：`ActorPlacementError(f'{label} at mission s={original_s:.2f} m is behind replan origin s={offset_m:.2f} m')`。
- `route_relative_carla_transform`，第 135 行：`ActorPlacementError('cannot resolve adjacent lane without a CARLA waypoint')`。
- `route_relative_target_location`，第 385 行：`TypeError('scenario walker requires spawn and behavior objects')`。
- `route_relative_target_location`，第 390 行：`TypeError('scenario walker target_xy_m must be [x, y]')`。
- `route_relative_target_location`，第 393 行：`TypeError('target_route_position must be an object')`。
- `validate_actor_route_coverage`，第 414 行：`ValueError('route_length_m must be finite and positive')`。
- `validate_actor_route_coverage`，第 419 行：`ValueError(f'scenario actor {actor_id!r} at s={s_m:.2f} m exceeds route length {route_length_m:.2f} m')`。
- `validate_actor_transform`，第 330 行：`ActorPlacementError('candidate transform contains a non-finite value')`。
- `validate_actor_transform`，第 334 行：`ActorPlacementError('candidate cannot be projected to a CARLA waypoint')`。
- `validate_actor_transform`，第 339 行：`ActorPlacementError(f'vehicle candidate is on {lane_type}, not DRIVING')`。
- `validate_actor_transform`，第 346 行：`ActorPlacementError(f'vehicle candidate is too close to a lane marking: centre_error={centre_error_m:.2f}m')`。
- `validate_actor_transform`，第 353 行：`ActorPlacementError(f'vehicle yaw is not aligned with its lane: error={heading_error:.1f}deg')`。
- `validate_actor_transform`，第 359 行：`ActorPlacementError(f'candidate height is invalid: z={float(location.z):.2f}, road_z={road_z:.2f}')`。
- `validate_actor_transform`，第 370 行：`ActorPlacementError(f'candidate overlaps another actor: separation={separation_m:.2f}m')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/route_geometry.py](../../../integration/route_geometry.py)
- [integration/route_planner.py](../../../integration/route_planner.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/generalization_gate.py](../../../integration/generalization_gate.py)
- [integration/planning_stage.py](../../../integration/planning_stage.py)
- [integration/tests/test_generalization_gate.py](../../../integration/tests/test_generalization_gate.py)
- [integration/tests/test_scenario_builder.py](../../../integration/tests/test_scenario_builder.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/scenario_builder.py`

来源 SHA256：`c4e4e8c06cfa2e446f5b64c513a00637b6ae7859526f1a1a508eb91b743537ec`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_lane_relation` / 47 | `relation not in _LANE_RELATIONS` | `raise ValueError(f'unsupported route_position.lane_relation: {relation!r}')` |
| `_target_lane_waypoint` / 58 | `target is None` | `raise ActorPlacementError(f'scenario actor requires unavailable {relation.lower()} lane')` |
| `_target_lane_waypoint` / 63 | `lane_type != 'DRIVING'` | `raise ActorPlacementError(f'scenario actor target lane is not driving: {lane_type}')` |
| `_target_lane_waypoint` / 67 | `not _same_direction(base, target)` | `raise ActorPlacementError(f'scenario actor target {relation.lower()} lane runs in the opposite direction')` |
| `route_relative_carla_transform` / 135 | `NOT (waypoint is not None) AND relation not in {'CURRENT', 'ORIGINAL'}` | `raise ActorPlacementError('cannot resolve adjacent lane without a CARLA waypoint')` |
| `offset_actor_route_position` / 172 | `NOT (isinstance(position, Mapping)) AND not isinstance(spawn, Mapping)` | `raise TypeError('scenario actor spawn must be an object')` |
| `rebase_actor_route_position` / 241 | `not math.isfinite(offset_m) or offset_m < 0.0` | `raise ValueError('mission_progress_offset_m must be finite and non-negative')` |
| `rebase_actor_route_position` / 272 | `isinstance(behavior, dict) AND NOT (isinstance(target, dict)) AND isinstance(behavior.get('target_xy_m'), (list, tuple)) AND len(target_xy) == 2 AND original_s - offset_m < -1e-06` | `raise ActorPlacementError(f'legacy actor target at mission s={original_s:.2f} m is behind replan origin s={offset_m:.2f} m')` |
| `rebase_actor_route_position.rebase_s` / 248 | `local_s < -1e-06` | `raise ActorPlacementError(f'{label} at mission s={original_s:.2f} m is behind replan origin s={offset_m:.2f} m')` |
| `actor_resample_offsets` / 299 | `max_attempts < 1` | `raise ValueError('max_attempts must be positive')` |
| `validate_actor_transform` / 330 | `any((not math.isfinite(value) for value in values))` | `raise ActorPlacementError('candidate transform contains a non-finite value')` |
| `validate_actor_transform` / 334 | `projected is None` | `raise ActorPlacementError('candidate cannot be projected to a CARLA waypoint')` |
| `validate_actor_transform` / 339 | `actor_type == 'vehicle' AND lane_type != 'DRIVING'` | `raise ActorPlacementError(f'vehicle candidate is on {lane_type}, not DRIVING')` |
| `validate_actor_transform` / 346 | `actor_type == 'vehicle' AND centre_error_m > max(0.35, _lane_width_m(projected) * 0.45)` | `raise ActorPlacementError(f'vehicle candidate is too close to a lane marking: centre_error={centre_error_m:.2f}m')` |
| `validate_actor_transform` / 353 | `actor_type == 'vehicle' AND heading_error > 30.0` | `raise ActorPlacementError(f'vehicle yaw is not aligned with its lane: error={heading_error:.1f}deg')` |
| `validate_actor_transform` / 359 | `float(location.z) < road_z - 0.1 or float(location.z) > road_z + 3.0` | `raise ActorPlacementError(f'candidate height is invalid: z={float(location.z):.2f}, road_z={road_z:.2f}')` |
| `validate_actor_transform` / 370 | `separation_m < minimum_separation_m` | `raise ActorPlacementError(f'candidate overlaps another actor: separation={separation_m:.2f}m')` |
| `route_relative_target_location` / 385 | `not isinstance(behavior, Mapping) or not isinstance(spawn, Mapping)` | `raise TypeError('scenario walker requires spawn and behavior objects')` |
| `route_relative_target_location` / 390 | `target is None AND not isinstance(target_xy, (list, tuple)) or len(target_xy) != 2` | `raise TypeError('scenario walker target_xy_m must be [x, y]')` |
| `route_relative_target_location` / 393 | `not isinstance(target, Mapping)` | `raise TypeError('target_route_position must be an object')` |
| `validate_actor_route_coverage` / 414 | `not math.isfinite(float(route_length_m)) or route_length_m <= 0.0` | `raise ValueError('route_length_m must be finite and positive')` |
| `validate_actor_route_coverage` / 419 | `s_m > route_length_m + 1e-06` | `raise ValueError(f'scenario actor {actor_id!r} at s={s_m:.2f} m exceeds route length {route_length_m:.2f} m')` |
