# route_planner：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[integration/route_planner.py](../../../integration/route_planner.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

CARLA waypoint route generation shared by the acceptance runner.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `_WaypointSpatialIndex.world_map: Any`；默认：`未在声明处设置`。
- `_WaypointSpatialIndex.step_m: float`；默认：`未在声明处设置`。
- `_WaypointSpatialIndex.buckets: dict[tuple[int, int], tuple[Any, ...]]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_WaypointSpatialIndex`

源码位置：[integration/route_planner.py 第 28 行](../../../integration/route_planner.py#L28)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_wrap_degrees`

源码位置：[integration/route_planner.py 第 37 行](../../../integration/route_planner.py#L37)。类型：`FunctionDef`。

```python
_wrap_degrees(angle: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_yaw`

源码位置：[integration/route_planner.py 第 41 行](../../../integration/route_planner.py#L41)。类型：`FunctionDef`。

```python
_yaw(waypoint: Any) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_branch_delta`

源码位置：[integration/route_planner.py 第 45 行](../../../integration/route_planner.py#L45)。类型：`FunctionDef`。

```python
_branch_delta(current: Any, candidate: Any) -> float
```

CARLA uses a left-handed frame: positive yaw turns to the right.

### `_choose_branch`

源码位置：[integration/route_planner.py 第 50 行](../../../integration/route_planner.py#L50)。类型：`FunctionDef`。

```python
_choose_branch(current: Any, candidates: Iterable[Any], direction: str) -> Any | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_waypoint_visit_key`

源码位置：[integration/route_planner.py 第 68 行](../../../integration/route_planner.py#L68)。类型：`FunctionDef`。

```python
_waypoint_visit_key(waypoint: Any) -> tuple[object, ...]
```

Return a stable lane-position key for coverage-aware long routes.

### `_future_route_capacity`

源码位置：[integration/route_planner.py 第 84 行](../../../integration/route_planner.py#L84)。类型：`FunctionDef`。

```python
_future_route_capacity(waypoint: Any, step_m: float, *, depth: int=8, seen: frozenset[tuple[object, ...]]=frozenset()) -> int
```

Estimate reachable novel topology to avoid choosing immediate dead ends.

### `_choose_coverage_branch`

源码位置：[integration/route_planner.py 第 107 行](../../../integration/route_planner.py#L107)。类型：`FunctionDef`。

```python
_choose_coverage_branch(current: Any, candidates: Iterable[Any], direction: str, visits: dict[tuple[object, ...], int], step_m: float) -> Any | None
```

Choose the requested branch while preferring novel, non-dead-end lanes.

### `_route_curvature`

源码位置：[integration/route_planner.py 第 136 行](../../../integration/route_planner.py#L136)。类型：`FunctionDef`。

```python
_route_curvature(points: tuple[tuple[float, float], ...]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_route_length`

源码位置：[integration/route_planner.py 第 143 行](../../../integration/route_planner.py#L143)。类型：`FunctionDef`。

```python
_route_length(points: Sequence[tuple[float, float]]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_heading`

源码位置：[integration/route_planner.py 第 147 行](../../../integration/route_planner.py#L147)。类型：`FunctionDef`。

```python
_heading(first: tuple[float, float], second: tuple[float, float]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_route_yaw_change`

源码位置：[integration/route_planner.py 第 151 行](../../../integration/route_planner.py#L151)。类型：`FunctionDef`。

```python
_route_yaw_change(points: Sequence[tuple[float, float]]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_is_driving_lane`

源码位置：[integration/route_planner.py 第 158 行](../../../integration/route_planner.py#L158)。类型：`FunctionDef`。

```python
_is_driving_lane(waypoint: Any | None) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_same_direction`

源码位置：[integration/route_planner.py 第 165 行](../../../integration/route_planner.py#L165)。类型：`FunctionDef`。

```python
_same_direction(first: Any, second: Any, tolerance_deg: float=45.0) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_ego_yaw_deg`

源码位置：[integration/route_planner.py 第 169 行](../../../integration/route_planner.py#L169)。类型：`FunctionDef`。

```python
_ego_yaw_deg(ego_or_location: Any) -> float | None
```

Return actor/transform yaw without guessing it from a bare Location.

### `_waypoint_distance_m`

源码位置：[integration/route_planner.py 第 180 行](../../../integration/route_planner.py#L180)。类型：`FunctionDef`。

```python
_waypoint_distance_m(waypoint: Any, location: Any) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `warm_heading_waypoint_cache`

源码位置：[integration/route_planner.py 第 185 行](../../../integration/route_planner.py#L185)。类型：`FunctionDef`。

```python
warm_heading_waypoint_cache(world_map: Any, *, search_step_m: float=1.0) -> int
```

Build a process-local spatial index outside the active control loop.

### `_nearby_indexed_waypoints`

源码位置：[integration/route_planner.py 第 215 行](../../../integration/route_planner.py#L215)。类型：`FunctionDef`。

```python
_nearby_indexed_waypoints(world_map: Any, location: Any, *, search_radius_m: float, search_step_m: float) -> tuple[Any, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `select_heading_compatible_waypoint`

源码位置：[integration/route_planner.py 第 235 行](../../../integration/route_planner.py#L235)。类型：`FunctionDef`。

```python
select_heading_compatible_waypoint(world_map: Any, ego_or_location: Any, *, max_heading_error_deg: float=45.0, search_radius_m: float=5.0, search_step_m: float=1.0) -> Any
```

Project to a nearby driving lane that agrees with the ego heading.

CARLA's ``get_waypoint(project_to_road=True)`` minimizes geometric
distance only. At stacked/crossing road geometry that can select a road
whose tangent points behind the vehicle. A bare ``Location`` has no
heading, so scenario builders retain the legacy nearest projection; live
actor routes always apply this direction gate.

### `_next_straight`

源码位置：[integration/route_planner.py 第 297 行](../../../integration/route_planner.py#L297)。类型：`FunctionDef`。

```python
_next_straight(waypoint: Any, step_m: float) -> Any | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_advance_waypoint`

源码位置：[integration/route_planner.py 第 301 行](../../../integration/route_planner.py#L301)。类型：`FunctionDef`。

```python
_advance_waypoint(waypoint: Any, distance_m: float, step_m: float) -> Any | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_adjacent_driving_lane`

源码位置：[integration/route_planner.py 第 310 行](../../../integration/route_planner.py#L310)。类型：`FunctionDef`。

```python
_adjacent_driving_lane(waypoint: Any, direction: str) -> Any | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_hermite_lane_change`

源码位置：[integration/route_planner.py 第 319 行](../../../integration/route_planner.py#L319)。类型：`FunctionDef`。

```python
_hermite_lane_change(start: Any, end: Any, *, samples: int, tangent_scale_m: float) -> tuple[tuple[float, float], ...]
```

Smoothly join two parallel lane-centre waypoints.

### `build_lane_change_route_reference`

源码位置：[integration/route_planner.py 第 347 行](../../../integration/route_planner.py#L347)。类型：`FunctionDef`。

```python
build_lane_change_route_reference(world_map: Any, anchor_or_location: Any, target_speed_mps: float, *, direction: str, distance_m: float=60.0, step_m: float=1.0, transition_start_m: float=12.0, transition_length_m: float=28.0, target_lane_offset_m: float=0.0, defer_until_safe: bool=False, maximum_transition_deferral_m: float=60.0) -> RouteReference
```

Build a legal same-direction adjacent-lane transition.

### `build_scenario_route_reference`

源码位置：[integration/route_planner.py 第 489 行](../../../integration/route_planner.py#L489)。类型：`FunctionDef`。

```python
build_scenario_route_reference(world_map: Any, anchor_or_location: Any, target_speed_mps: float, *, maneuver: str, distance_m: float, step_m: float=1.0) -> RouteReference
```

Convert a scenario manoeuvre into a CARLA-topology route.

### `build_destination_route_reference`

源码位置：[integration/route_planner.py 第 522 行](../../../integration/route_planner.py#L522)。类型：`FunctionDef`。

```python
build_destination_route_reference(world_map: Any, anchor_or_location: Any, destination_xy_m: tuple[float, float], target_speed_mps: float, *, step_m: float=2.0, maximum_expansions: int=50000) -> RouteReference
```

Plan and validate a deterministic topology route to a destination.

### `select_topology_route_anchor`

源码位置：[integration/route_planner.py 第 561 行](../../../integration/route_planner.py#L561)。类型：`FunctionDef`。

```python
select_topology_route_anchor(world_map: Any, spawn_points: Sequence[Any], *, maneuver: str, target_speed_mps: float, distance_m: float, forbidden_points_xy: Sequence[tuple[float, float]]=(), candidate_index: int=0, route_validator: Callable[[RouteReference], bool] | None=None) -> tuple[int, RouteReference, float]
```

Pick a spawn whose route is legal and satisfies scenario topology.

``route_validator`` lets the caller enforce requirements that depend on
the complete scenario, such as having real same-direction adjacent lanes
at every declared actor position.  Invalid candidates are discarded before
ranking; the selector never relocates an actor onto a semantically different
lane merely to make a spawn succeed.

### `build_route_reference`

源码位置：[integration/route_planner.py 第 640 行](../../../integration/route_planner.py#L640)。类型：`FunctionDef`。

```python
build_route_reference(world_map: Any, ego_or_location: Any, target_speed_mps: float, *, turn_direction: str='STRAIGHT', distance_m: float=500.0, step_m: float=2.0) -> RouteReference
```

Build a bounded forward route and a conservative curvature estimate.

### `command_turn_direction`

源码位置：[integration/route_planner.py 第 701 行](../../../integration/route_planner.py#L701)。类型：`FunctionDef`。

```python
command_turn_direction(command: dict[str, object] | None) -> str
```

Extract only an explicit route direction; all other commands go straight.

## 内部调用与异常路径

- `_wrap_degrees` 调用：`float`.
- `_yaw` 调用：`float`.
- `_branch_delta` 调用：`_wrap_degrees`, `_yaw`.
- `_choose_branch` 调用：`_branch_delta`, `abs`, `len`, `min`, `tuple`.
- `_waypoint_visit_key` 调用：`_yaw`, `float`, `getattr`, `round`.
- `_future_route_capacity` 调用：`_future_route_capacity`, `_waypoint_visit_key`, `frozenset`, `max`, `tuple`, `waypoint.next`.
- `_choose_coverage_branch` 调用：`_branch_delta`, `_future_route_capacity`, `_waypoint_visit_key`, `abs`, `len`, `min`, `scored.append`, `str`, `str(direction).upper`, `tuple`, `visits.get`.
- `_route_curvature` 调用：`abs`, `estimate_curvature`, `len`, `max`, `range`.
- `_route_length` 调用：`math.dist`, `sum`, `zip`.
- `_heading` 调用：`math.atan2`, `math.degrees`.
- `_route_yaw_change` 调用：`_heading`, `_wrap_degrees`, `len`, `min`.
- `_is_driving_lane` 调用：`getattr`, `str`, `str(getattr(waypoint, 'lane_type', 'Driving')).split`, `str(getattr(waypoint, 'lane_type', 'Driving')).split('.')[-1].upper`.
- `_same_direction` 调用：`_wrap_degrees`, `_yaw`, `abs`.
- `_ego_yaw_deg` 调用：`callable`, `ego_or_location.get_transform`, `float`, `getattr`, `hasattr`.
- `_waypoint_distance_m` 调用：`float`, `math.hypot`.
- `warm_heading_waypoint_cache` 调用：`RuntimeError`, `ValueError`, `_WAYPOINT_INDEX_BY_MAP_ID.get`, `_WaypointSpatialIndex`, `_is_driving_lane`, `cached.buckets.values`, `callable`, `float`, `generate`, `getattr`, `id`, `len`, `math.floor`, `math.isfinite`, `mutable.items`, `mutable.setdefault`, `mutable.setdefault(cell, []).append`, `sum`, `tuple`.
- `_nearby_indexed_waypoints` 调用：`float`, `id`, `index.buckets.get`, `int`, `math.ceil`, `math.floor`, `range`, `tuple`, `warm_heading_waypoint_cache`.
- `select_heading_compatible_waypoint` 调用：`RuntimeError`, `ValueError`, `_ego_yaw_deg`, `_is_driving_lane`, `_nearby_indexed_waypoints`, `_waypoint_distance_m`, `_wrap_degrees`, `_yaw`, `abs`, `candidates.append`, `candidates.sort`, `ego_or_location.get_location`, `getattr`, `hasattr`, `world_map.get_waypoint`.
- `_next_straight` 调用：`_choose_branch`, `tuple`, `waypoint.next`.
- `_advance_waypoint` 调用：`_next_straight`, `int`, `math.ceil`, `max`, `range`.
- `_adjacent_driving_lane` 调用：`_is_driving_lane`, `_same_direction`, `callable`, `getattr`, `getter`.
- `_hermite_lane_change` 调用：`_yaw`, `float`, `math.cos`, `math.radians`, `math.sin`, `points.append`, `range`, `tuple`.
- `build_lane_change_route_reference` 调用：`RouteReference`, `ValueError`, `_adjacent_driving_lane`, `_is_driving_lane`, `_next_straight`, `_route_curvature`, `_route_length`, `anchor_or_location.get_location`, `bool`, `float`, `getattr`, `hasattr`, `int`, `math.ceil`, `math.cos`, `math.dist`, `math.isfinite`, `math.radians`, `math.sin`, `max`, `points.append`, `prefix.append`, `range`, `side.lower`, `str`, `str(direction).strip`, `str(direction).strip().upper`, `transition_points.append`, `tuple`, `world_map.get_waypoint`.
- `build_scenario_route_reference` 调用：`ValueError`, `action.removeprefix`, `action.rsplit`, `action.startswith`, `build_lane_change_route_reference`, `build_route_reference`, `str`, `str(maneuver).strip`, `str(maneuver).strip().upper`.
- `build_destination_route_reference` 调用：`RouteManager`, `RouteManager(world_map, sample_step_m=step_m, maximum_expansions=maximum_expansions).plan`, `ValueError`, `any`, `float`, `getattr`, `len`, `map`, `math.isfinite`, `type`, `type(anchor_location)`.
- `select_topology_route_anchor` 调用：`RuntimeError`, `ValueError`, `_route_length`, `_route_yaw_change`, `abs`, `action.startswith`, `build_scenario_route_reference`, `candidates.append`, `candidates.sort`, `enumerate`, `len`, `math.dist`, `max`, `min`, `route_validator`, `str`, `str(maneuver).strip`, `str(maneuver).strip().upper`.
- `build_route_reference` 调用：`RouteReference`, `ValueError`, `_choose_coverage_branch`, `_route_curvature`, `_waypoint_visit_key`, `ego_or_location.get_location`, `float`, `hasattr`, `int`, `len`, `math.ceil`, `math.hypot`, `math.isfinite`, `max`, `points.append`, `range`, `select_heading_compatible_waypoint`, `sorted`, `str`, `str(turn_direction).strip`, `str(turn_direction).strip().upper`, `tuple`, `visits.get`, `waypoint.next`.
- `command_turn_direction` 调用：`command.get`, `isinstance`, `parameters.get`, `str`, `str(command.get('intent', '')).upper`, `str(parameters.get('direction', 'STRAIGHT')).upper`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `build_destination_route_reference`，第 535 行：`ValueError('destination_xy_m must contain two finite numbers')`。
- `build_destination_route_reference`，第 537 行：`ValueError('step_m must be finite and positive')`。
- `build_destination_route_reference`，第 539 行：`ValueError('maximum_expansions must be a positive integer')`。
- `build_lane_change_route_reference`，第 364 行：`ValueError('lane-change direction must be LEFT or RIGHT')`。
- `build_lane_change_route_reference`，第 367 行：`ValueError('target_lane_offset_m must be finite and between 0.0 and 0.30')`。
- `build_lane_change_route_reference`，第 372 行：`ValueError('lane-change anchor is not on a driving lane')`。
- `build_lane_change_route_reference`，第 377 行：`ValueError('maximum_transition_deferral_m must be finite and non-negative')`。
- `build_lane_change_route_reference`，第 385 行：`ValueError('lane-change prefix reaches a junction or dead end')`。
- `build_lane_change_route_reference`，第 390 行：`ValueError('lane-change prefix reaches a junction or dead end')`。
- `build_lane_change_route_reference`，第 419 行：`ValueError('no safe post-junction lane-change corridor')`。
- `build_lane_change_route_reference`，第 426 行：`ValueError('lane-change deferral reaches a dead end')`。
- `build_lane_change_route_reference`，第 443 行：`ValueError('source lane cannot support the full transition')`。
- `build_lane_change_route_reference`，第 446 行：`ValueError(f'no same-direction driving lane on the {side.lower()}')`。
- `build_lane_change_route_reference`，第 464 行：`ValueError('adjacent lane transition produced no target waypoint')`。
- `build_lane_change_route_reference`，第 484 行：`ValueError('adjacent lane route is too short')`。
- `build_route_reference`，第 652 行：`ValueError(f'turn_direction must be one of {sorted(_DIRECTIONS)}')`。
- `build_route_reference`，第 654 行：`ValueError('target_speed_mps must be finite and non-negative')`。
- `build_route_reference`，第 656 行：`ValueError('distance_m must be finite and positive')`。
- `build_route_reference`，第 658 行：`ValueError('step_m must be finite and positive')`。
- `build_scenario_route_reference`，第 501 行：`ValueError(f'unsupported scenario maneuver: {maneuver!r}')`。
- `select_heading_compatible_waypoint`，第 252 行：`ValueError('max_heading_error_deg must be in (0, 90]')`。
- `select_heading_compatible_waypoint`，第 254 行：`ValueError('search radius and step must be positive')`。
- `select_heading_compatible_waypoint`，第 262 行：`RuntimeError('route anchor is not on a driving lane')`。
- `select_heading_compatible_waypoint`，第 290 行：`RuntimeError('no nearby driving waypoint agrees with ego heading; route refresh rejected')`。
- `select_topology_route_anchor`，第 581 行：`ValueError('at least one spawn point is required')`。
- `select_topology_route_anchor`，第 632 行：`RuntimeError(f'no Town route supports maneuver {action}')`。
- `select_topology_route_anchor`，第 636 行：`RuntimeError(f'no Town route has the required topology for {action}')`。
- `warm_heading_waypoint_cache`，第 188 行：`ValueError('search_step_m must be finite and positive')`。
- `warm_heading_waypoint_cache`，第 195 行：`RuntimeError('map cannot enumerate waypoints')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_B/path_utils.py](../../../car_control_B/path_utils.py)
- [integration/route_manager.py](../../../integration/route_manager.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/scenario_builder.py](../../../integration/scenario_builder.py)
- [integration/tests/test_route_manager.py](../../../integration/tests/test_route_manager.py)
- [integration/tests/test_route_planner.py](../../../integration/tests/test_route_planner.py)
- [tools/probe_s2_route_anchor.py](../../../tools/probe_s2_route_anchor.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/route_planner.py`

来源 SHA256：`1795f9f737718b88d276197ddc0d8cda62bd05bb7deab13e4e6a2ac278442855`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `_WaypointSpatialIndex.world_map` | `Any` | `无声明默认；构造/赋值方提供` |
| `_WaypointSpatialIndex.step_m` | `float` | `无声明默认；构造/赋值方提供` |
| `_WaypointSpatialIndex.buckets` | `dict[tuple[int, int], tuple[Any, ...]]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `warm_heading_waypoint_cache` / 188 | `not math.isfinite(float(search_step_m)) or search_step_m <= 0.0` | `raise ValueError('search_step_m must be finite and positive')` |
| `warm_heading_waypoint_cache` / 195 | `not callable(generate)` | `raise RuntimeError('map cannot enumerate waypoints')` |
| `select_heading_compatible_waypoint` / 252 | `max_heading_error_deg <= 0.0 or max_heading_error_deg > 90.0` | `raise ValueError('max_heading_error_deg must be in (0, 90]')` |
| `select_heading_compatible_waypoint` / 254 | `search_radius_m <= 0.0 or search_step_m <= 0.0` | `raise ValueError('search radius and step must be positive')` |
| `select_heading_compatible_waypoint` / 262 | `not _is_driving_lane(nearest)` | `raise RuntimeError('route anchor is not on a driving lane')` |
| `select_heading_compatible_waypoint` / 290 | `not candidates` | `raise RuntimeError('no nearby driving waypoint agrees with ego heading; route refresh rejected')` |
| `build_lane_change_route_reference` / 364 | `side not in {'LEFT', 'RIGHT'}` | `raise ValueError('lane-change direction must be LEFT or RIGHT')` |
| `build_lane_change_route_reference` / 367 | `not math.isfinite(target_lane_offset_m) or not 0.0 <= target_lane_offset_m <= 0.3` | `raise ValueError('target_lane_offset_m must be finite and between 0.0 and 0.30')` |
| `build_lane_change_route_reference` / 372 | `not _is_driving_lane(current)` | `raise ValueError('lane-change anchor is not on a driving lane')` |
| `build_lane_change_route_reference` / 377 | `not math.isfinite(float(maximum_transition_deferral_m)) or maximum_transition_deferral_m < 0.0` | `raise ValueError('maximum_transition_deferral_m must be finite and non-negative')` |
| `build_lane_change_route_reference` / 385 | `next_waypoint is None` | `raise ValueError('lane-change prefix reaches a junction or dead end')` |
| `build_lane_change_route_reference` / 390 | `bool(getattr(current, 'is_junction', False)) and (not defer_until_safe)` | `raise ValueError('lane-change prefix reaches a junction or dead end')` |
| `build_lane_change_route_reference` / 419 | `defer_until_safe AND deferred_m >= float(maximum_transition_deferral_m)` | `raise ValueError('no safe post-junction lane-change corridor')` |
| `build_lane_change_route_reference` / 426 | `defer_until_safe AND next_waypoint is None` | `raise ValueError('lane-change deferral reaches a dead end')` |
| `build_lane_change_route_reference` / 443 | `index AND source is None or bool(getattr(source, 'is_junction', False))` | `raise ValueError('source lane cannot support the full transition')` |
| `build_lane_change_route_reference` / 446 | `adjacent is None or bool(getattr(adjacent, 'is_junction', False))` | `raise ValueError(f'no same-direction driving lane on the {side.lower()}')` |
| `build_lane_change_route_reference` / 464 | `target is None` | `raise ValueError('adjacent lane transition produced no target waypoint')` |
| `build_lane_change_route_reference` / 484 | `accumulated_distance_m < distance_m * 0.8` | `raise ValueError('adjacent lane route is too short')` |
| `build_scenario_route_reference` / 501 | `action not in _MANEUVERS` | `raise ValueError(f'unsupported scenario maneuver: {maneuver!r}')` |
| `build_destination_route_reference` / 535 | `len(destination_xy_m) != 2 or any((not math.isfinite(float(value)) for value in destination_xy_m))` | `raise ValueError('destination_xy_m must contain two finite numbers')` |
| `build_destination_route_reference` / 537 | `not math.isfinite(float(step_m)) or step_m <= 0.0` | `raise ValueError('step_m must be finite and positive')` |
| `build_destination_route_reference` / 539 | `type(maximum_expansions) is not int or maximum_expansions < 1` | `raise ValueError('maximum_expansions must be a positive integer')` |
| `select_topology_route_anchor` / 581 | `not spawn_points` | `raise ValueError('at least one spawn point is required')` |
| `select_topology_route_anchor` / 632 | `not candidates` | `raise RuntimeError(f'no Town route supports maneuver {action}')` |
| `select_topology_route_anchor` / 636 | `score >= 1000.0` | `raise RuntimeError(f'no Town route has the required topology for {action}')` |
| `build_route_reference` / 652 | `direction not in _DIRECTIONS` | `raise ValueError(f'turn_direction must be one of {sorted(_DIRECTIONS)}')` |
| `build_route_reference` / 654 | `not math.isfinite(float(target_speed_mps)) or target_speed_mps < 0.0` | `raise ValueError('target_speed_mps must be finite and non-negative')` |
| `build_route_reference` / 656 | `not math.isfinite(float(distance_m)) or distance_m <= 0.0` | `raise ValueError('distance_m must be finite and positive')` |
| `build_route_reference` / 658 | `not math.isfinite(float(step_m)) or step_m <= 0.0` | `raise ValueError('step_m must be finite and positive')` |
