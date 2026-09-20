# route_geometry：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[integration/route_geometry.py](../../../integration/route_geometry.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Map-independent route geometry and route-relative scenario placement.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RoutePose.x_m: float`；默认：`未在声明处设置`。
- `RoutePose.y_m: float`；默认：`未在声明处设置`。
- `RoutePose.yaw_deg: float`；默认：`未在声明处设置`。
- `RoutePose.s_m: float`；默认：`未在声明处设置`。
- `RouteQuality.requested_distance_m: float`；默认：`未在声明处设置`。
- `RouteQuality.actual_distance_m: float`；默认：`未在声明处设置`。
- `RouteQuality.point_count: int`；默认：`未在声明处设置`。
- `RouteQuality.maximum_step_m: float`；默认：`未在声明处设置`。
- `RouteQuality.unique_cell_ratio: float`；默认：`未在声明处设置`。
- `RouteQuality.reached_contract: bool`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_finite`

源码位置：[integration/route_geometry.py 第 17 行](../../../integration/route_geometry.py#L17)。类型：`FunctionDef`。

```python
_finite(value: object, name: str) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `polyline_length_m`

源码位置：[integration/route_geometry.py 第 26 行](../../../integration/route_geometry.py#L26)。类型：`FunctionDef`。

```python
polyline_length_m(points: Sequence[Point2D]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `cumulative_distances_m`

源码位置：[integration/route_geometry.py 第 32 行](../../../integration/route_geometry.py#L32)。类型：`FunctionDef`。

```python
cumulative_distances_m(points: Sequence[Point2D]) -> tuple[float, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RoutePose`

源码位置：[integration/route_geometry.py 第 44 行](../../../integration/route_geometry.py#L44)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RouteQuality`

源码位置：[integration/route_geometry.py 第 52 行](../../../integration/route_geometry.py#L52)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RouteQuality.to_dict`

源码位置：[integration/route_geometry.py 第 60 行](../../../integration/route_geometry.py#L60)。类型：`FunctionDef`。

```python
RouteQuality.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `route_pose_at_s`

源码位置：[integration/route_geometry.py 第 71 行](../../../integration/route_geometry.py#L71)。类型：`FunctionDef`。

```python
route_pose_at_s(points: Sequence[Point2D], s_m: float) -> RoutePose
```

Interpolate a pose at route arc length ``s_m``.

Values beyond the route are clamped to its endpoints.  Zero-length
duplicate segments are ignored, which is important around CARLA junctions.

### `offset_route_pose`

源码位置：[integration/route_geometry.py 第 101 行](../../../integration/route_geometry.py#L101)。类型：`FunctionDef`。

```python
offset_route_pose(pose: RoutePose, lateral_m: float, yaw_offset_deg: float=0.0) -> RoutePose
```

Offset a route pose toward CARLA's local positive-Y/right direction.

### `actor_route_coordinates`

源码位置：[integration/route_geometry.py 第 113 行](../../../integration/route_geometry.py#L113)。类型：`FunctionDef`。

```python
actor_route_coordinates(actor_spec: Mapping[str, object]) -> tuple[float, float, float, float]
```

Return ``(s, lateral, z, yaw_offset)`` for new and legacy actors.

New scenarios may declare ``route_position``.  Existing scenarios remain
compatible: their local ``spawn.x/y`` values are interpreted as route arc
length and lateral offset instead of a tangent at only the initial ego pose.

### `project_route_progress_m`

源码位置：[integration/route_geometry.py 第 137 行](../../../integration/route_geometry.py#L137)。类型：`FunctionDef`。

```python
project_route_progress_m(points: Sequence[Point2D], x_m: float, y_m: float, *, previous_s_m: float | None=None, backward_tolerance_m: float=2.0, forward_window_m: float=80.0) -> float
```

Project a position onto a possibly self-overlapping route.

A prior progress value disambiguates loops and crossing roads.  Candidates
far behind or implausibly far ahead are excluded before choosing the
geometrically nearest segment.

### `evaluate_route_quality`

源码位置：[integration/route_geometry.py 第 187 行](../../../integration/route_geometry.py#L187)。类型：`FunctionDef`。

```python
evaluate_route_quality(points: Sequence[Point2D], requested_distance_m: float, *, contract_tolerance_m: float | None=None, uniqueness_cell_m: float=2.0) -> RouteQuality
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_finite` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `polyline_length_m` 调用：`ValueError`, `len`, `math.dist`, `sum`, `zip`.
- `cumulative_distances_m` 调用：`ValueError`, `len`, `math.dist`, `tuple`, `values.append`, `zip`.
- `route_pose_at_s` 调用：`RoutePose`, `_finite`, `cumulative_distances_m`, `enumerate`, `float`, `math.atan2`, `math.degrees`, `max`, `min`, `zip`.
- `offset_route_pose` 调用：`RoutePose`, `_finite`, `math.cos`, `math.radians`, `math.sin`.
- `actor_route_coordinates` 调用：`TypeError`, `_finite`, `actor_spec.get`, `isinstance`, `max`, `spawn.get`, `values.get`.
- `project_route_progress_m` 调用：`ValueError`, `_finite`, `abs`, `candidates.append`, `cumulative_distances_m`, `enumerate`, `fallback.append`, `math.sqrt`, `max`, `min`, `zip`.
- `evaluate_route_quality` 调用：`RouteQuality`, `ValueError`, `_finite`, `float`, `len`, `math.dist`, `max`, `polyline_length_m`, `round`, `tuple`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_finite`，第 19 行：`TypeError(f'{name} must be a number')`。
- `_finite`，第 22 行：`ValueError(f'{name} must be finite')`。
- `actor_route_coordinates`，第 122 行：`TypeError('scenario actor spawn must be an object')`。
- `actor_route_coordinates`，第 125 行：`TypeError('scenario actor route_position must be an object')`。
- `cumulative_distances_m`，第 34 行：`ValueError('route needs at least two points')`。
- `cumulative_distances_m`，第 39 行：`ValueError('route length must be positive')`。
- `evaluate_route_quality`，第 196 行：`ValueError('requested_distance_m must be positive')`。
- `evaluate_route_quality`，第 201 行：`ValueError('uniqueness_cell_m must be positive')`。
- `polyline_length_m`，第 28 行：`ValueError('route needs at least two points')`。
- `project_route_progress_m`，第 175 行：`ValueError('route has no non-zero segments')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/execution_stage.py](../../../integration/execution_stage.py)
- [integration/planning_stage.py](../../../integration/planning_stage.py)
- [integration/route_manager.py](../../../integration/route_manager.py)
- [integration/scenario_builder.py](../../../integration/scenario_builder.py)
- [integration/tests/test_route_geometry.py](../../../integration/tests/test_route_geometry.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/route_geometry.py`

来源 SHA256：`650f6e0b87716a81de5a892bec5bb01701a543edbe5357be168ec1de2d4ef114`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RoutePose.x_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePose.y_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePose.yaw_deg` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePose.s_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteQuality.requested_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteQuality.actual_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteQuality.point_count` | `int` | `无声明默认；构造/赋值方提供` |
| `RouteQuality.maximum_step_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteQuality.unique_cell_ratio` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteQuality.reached_contract` | `bool` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_finite` / 19 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be a number')` |
| `_finite` / 22 | `not math.isfinite(result)` | `raise ValueError(f'{name} must be finite')` |
| `polyline_length_m` / 28 | `len(points) < 2` | `raise ValueError('route needs at least two points')` |
| `cumulative_distances_m` / 34 | `len(points) < 2` | `raise ValueError('route needs at least two points')` |
| `cumulative_distances_m` / 39 | `values[-1] <= 1e-09` | `raise ValueError('route length must be positive')` |
| `actor_route_coordinates` / 122 | `not isinstance(spawn, Mapping)` | `raise TypeError('scenario actor spawn must be an object')` |
| `actor_route_coordinates` / 125 | `position is not None and (not isinstance(position, Mapping))` | `raise TypeError('scenario actor route_position must be an object')` |
| `project_route_progress_m` / 175 | `not fallback` | `raise ValueError('route has no non-zero segments')` |
| `evaluate_route_quality` / 196 | `requested <= 0.0` | `raise ValueError('requested_distance_m must be positive')` |
| `evaluate_route_quality` / 201 | `cell <= 0.0` | `raise ValueError('uniqueness_cell_m must be positive')` |

### integration/route_geometry.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 103 | `_finite(lateral_m, 'lateral_m')` |
| 152 | `_finite(x_m, 'x_m')` |
| 153 | `_finite(y_m, 'y_m')` |
| 194 | `_finite(requested_distance_m, 'requested_distance_m')` |
| 199 | `_finite(uniqueness_cell_m, 'uniqueness_cell_m')` |
| 131 | `_finite(lateral_value, 'actor route lateral_offset_m')` |
| 132 | `_finite(spawn.get('z', 0.5), 'actor spawn z')` |
| 133 | `_finite(values.get('yaw_offset_deg', spawn.get('yaw_deg', 0.0)), 'actor yaw offset')` |
| 78 | `_finite(s_m, 's_m')` |
| 108 | `_finite(yaw_offset_deg, 'yaw_offset_deg')` |
| 130 | `_finite(s_value, 'actor route s_m')` |
| 155 | `_finite(previous_s_m, 'previous_s_m')` |
| 209 | `_finite(contract_tolerance_m, 'contract_tolerance_m')` |
