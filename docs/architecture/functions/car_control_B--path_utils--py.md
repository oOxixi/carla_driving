# path_utils：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[car_control_B/path_utils.py](../../../car_control_B/path_utils.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Path utilities for member B lateral control.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `clamp`

源码位置：[car_control_B/path_utils.py 第 11 行](../../../car_control_B/path_utils.py#L11)。类型：`FunctionDef`。

```python
clamp(value: float, low: float, high: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `wrap_angle_rad`

源码位置：[car_control_B/path_utils.py 第 15 行](../../../car_control_B/path_utils.py#L15)。类型：`FunctionDef`。

```python
wrap_angle_rad(angle: float) -> float
```

Wrap angle to [-pi, pi].

### `distance`

源码位置：[car_control_B/path_utils.py 第 20 行](../../../car_control_B/path_utils.py#L20)。类型：`FunctionDef`。

```python
distance(p1: Point2D, p2: Point2D) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `cumulative_lengths`

源码位置：[car_control_B/path_utils.py 第 24 行](../../../car_control_B/path_utils.py#L24)。类型：`FunctionDef`。

```python
cumulative_lengths(points: Sequence[Point2D]) -> List[float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `resample_path`

源码位置：[car_control_B/path_utils.py 第 33 行](../../../car_control_B/path_utils.py#L33)。类型：`FunctionDef`。

```python
resample_path(points: Sequence[Point2D], spacing_m: float=0.5) -> List[Point2D]
```

Resample a polyline by approximate arc length.

This prevents waypoint spacing jumps at intersections from destabilizing the
controller. The first and last points are always preserved.

### `find_nearest_index`

源码位置：[car_control_B/path_utils.py 第 67 行](../../../car_control_B/path_utils.py#L67)。类型：`FunctionDef`。

```python
find_nearest_index(points: Sequence[Point2D], x: float, y: float, start_index: int=0, search_window: int | None=None) -> int
```

Return index of nearest path point.

search_window limits computation around the previous nearest index when A
provides one; the default searches the whole path.

### `find_lookahead_index`

源码位置：[car_control_B/path_utils.py 第 91 行](../../../car_control_B/path_utils.py#L91)。类型：`FunctionDef`。

```python
find_lookahead_index(points: Sequence[Point2D], start_index: int, current_xy: Point2D, lookahead_distance_m: float) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `compute_path_heading`

源码位置：[car_control_B/path_utils.py 第 100 行](../../../car_control_B/path_utils.py#L100)。类型：`FunctionDef`。

```python
compute_path_heading(points: Sequence[Point2D], index: int) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `signed_cross_track_error`

源码位置：[car_control_B/path_utils.py 第 111 行](../../../car_control_B/path_utils.py#L111)。类型：`FunctionDef`。

```python
signed_cross_track_error(points: Sequence[Point2D], nearest_index: int, x: float, y: float) -> float
```

Signed distance to the nearest adjacent path segment.

Using the tangent of a single nearest waypoint makes the reported error
jump at a polyline corner: the waypoint may be nearest while the vehicle
is still closest to the segment entering that waypoint. Projecting onto
both adjacent segments keeps the metric geometrically meaningful and
gives Stanley-style feedback the correct sign through intersections.
Positive remains path-right in CARLA coordinates.

### `estimate_curvature`

源码位置：[car_control_B/path_utils.py 第 147 行](../../../car_control_B/path_utils.py#L147)。类型：`FunctionDef`。

```python
estimate_curvature(points: Sequence[Point2D], index: int, stride: int=3) -> float
```

Estimate signed curvature from three path points.

### `max_abs_curvature_ahead`

源码位置：[car_control_B/path_utils.py 第 169 行](../../../car_control_B/path_utils.py#L169)。类型：`FunctionDef`。

```python
max_abs_curvature_ahead(points: Sequence[Point2D], start_index: int, *, horizon_m: float=30.0, stride: int=3) -> float
```

Return smoothed peak curvature only over the upcoming local path.

A route-wide maximum makes one distant junction limit every straight in a
long mission.  The local horizon preserves advance slowing for a nearby
curve without carrying that constraint across kilometres of road.

## 内部调用与异常路径

- `clamp` 调用：`max`, `min`.
- `distance` 调用：`math.hypot`.
- `cumulative_lengths` 调用：`ValueError`, `distance`, `len`, `out.append`, `range`.
- `resample_path` 调用：`ValueError`, `cumulative_lengths`, `distance`, `len`, `math.isfinite`, `samples.append`.
- `find_nearest_index` 调用：`ValueError`, `float`, `len`, `math.hypot`, `max`, `min`, `range`.
- `find_lookahead_index` 调用：`ValueError`, `distance`, `len`, `max`, `range`.
- `compute_path_heading` 调用：`ValueError`, `len`, `math.atan2`, `max`, `min`.
- `signed_cross_track_error` 调用：`ValueError`, `clamp`, `len`, `math.isfinite`, `math.sqrt`, `max`, `min`, `range`.
- `estimate_curvature` 调用：`distance`, `len`, `max`, `min`.
- `max_abs_curvature_ahead` 调用：`ValueError`, `abs`, `distance`, `estimate_curvature`, `int`, `len`, `math.isfinite`, `max`, `min`, `range`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `compute_path_heading`，第 102 行：`ValueError('path must contain at least two points')`。
- `cumulative_lengths`，第 26 行：`ValueError('path must contain at least two points')`。
- `find_lookahead_index`，第 93 行：`ValueError('lookahead_distance_m must be positive')`。
- `find_nearest_index`，第 74 行：`ValueError('points is empty')`。
- `max_abs_curvature_ahead`，第 185 行：`ValueError('horizon_m must be positive and finite')`。
- `max_abs_curvature_ahead`，第 187 行：`ValueError('stride must be a positive integer')`。
- `resample_path`，第 40 行：`ValueError('path must contain at least two points')`。
- `resample_path`，第 42 行：`ValueError('spacing_m must be positive and finite')`。
- `resample_path`，第 47 行：`ValueError('path length is zero')`。
- `signed_cross_track_error`，第 122 行：`ValueError('path must contain at least two points')`。
- `signed_cross_track_error`，第 143 行：`ValueError('path contains no non-zero segment adjacent to nearest_index')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_B/lane_change.py](../../../car_control_B/lane_change.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [car_control_B/stanley.py](../../../car_control_B/stanley.py)
- [car_control_B/tests/test_path_utils.py](../../../car_control_B/tests/test_path_utils.py)
- [integration/route_planner.py](../../../integration/route_planner.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [tools/validate_route_generalization.py](../../../tools/validate_route_generalization.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/path_utils.py`

来源 SHA256：`a72293b830140085b29f312aa4278131dcff3b6fcb5af043a37b3e698b0387c2`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `cumulative_lengths` / 26 | `len(points) < 2` | `raise ValueError('path must contain at least two points')` |
| `resample_path` / 40 | `len(points) < 2` | `raise ValueError('path must contain at least two points')` |
| `resample_path` / 42 | `spacing_m <= 0 or not math.isfinite(spacing_m)` | `raise ValueError('spacing_m must be positive and finite')` |
| `resample_path` / 47 | `total == 0` | `raise ValueError('path length is zero')` |
| `find_nearest_index` / 74 | `not points` | `raise ValueError('points is empty')` |
| `find_lookahead_index` / 93 | `lookahead_distance_m <= 0` | `raise ValueError('lookahead_distance_m must be positive')` |
| `compute_path_heading` / 102 | `len(points) < 2` | `raise ValueError('path must contain at least two points')` |
| `signed_cross_track_error` / 122 | `len(points) < 2` | `raise ValueError('path must contain at least two points')` |
| `signed_cross_track_error` / 143 | `not math.isfinite(best_distance_sq)` | `raise ValueError('path contains no non-zero segment adjacent to nearest_index')` |
| `max_abs_curvature_ahead` / 185 | `not math.isfinite(horizon_m) or horizon_m <= 0.0` | `raise ValueError('horizon_m must be positive and finite')` |
| `max_abs_curvature_ahead` / 187 | `type(stride) is not int or stride <= 0` | `raise ValueError('stride must be a positive integer')` |
