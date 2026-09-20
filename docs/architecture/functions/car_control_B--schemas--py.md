# schemas：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[car_control_B/schemas.py](../../../car_control_B/schemas.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Data contracts for member B lateral control.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `VehiclePose.x_m: float`；默认：`未在声明处设置`。
- `VehiclePose.y_m: float`；默认：`未在声明处设置`。
- `VehiclePose.yaw_rad: float`；默认：`未在声明处设置`。
- `VehiclePose.speed_mps: float`；默认：`未在声明处设置`。
- `VehiclePose.frame: Optional[int]`；默认：`None`。
- `VehiclePose.sim_time_s: Optional[float]`；默认：`None`。
- `RouteReference.points_xy_m: List[Point2D]`；默认：`未在声明处设置`。
- `RouteReference.curvature_per_m: float`；默认：`0.0`。
- `RouteReference.target_speed_mps: float`；默认：`5.0`。
- `RouteReference.route_id: Optional[str]`；默认：`None`。
- `RouteReference.metadata: Dict[str, Any]`；默认：`field(default_factory=dict)`。
- `LateralOutput.steer: float`；默认：`未在声明处设置`。
- `LateralOutput.cross_track_error_m: float`；默认：`未在声明处设置`。
- `LateralOutput.heading_error_rad: float`；默认：`未在声明处设置`。
- `LateralOutput.target_point_xy_m: Point2D`；默认：`未在声明处设置`。
- `LateralOutput.lookahead_distance_m: float`；默认：`未在声明处设置`。
- `LateralOutput.nearest_index: int`；默认：`未在声明处设置`。
- `LateralOutput.target_index: int`；默认：`未在声明处设置`。
- `LateralOutput.status: str`；默认：`'OK'`。
- `LateralOutput.reason: str`；默认：`'NONE'`。

## 功能入口：输入、输出与实现说明

### `SchemaError`

源码位置：[car_control_B/schemas.py 第 18 行](../../../car_control_B/schemas.py#L18)。类型：`ClassDef`。

Raised when an input contract is invalid.

### `_finite`

源码位置：[car_control_B/schemas.py 第 22 行](../../../car_control_B/schemas.py#L22)。类型：`FunctionDef`。

```python
_finite(name: str, value: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_point_list`

源码位置：[car_control_B/schemas.py 第 31 行](../../../car_control_B/schemas.py#L31)。类型：`FunctionDef`。

```python
_point_list(points: Sequence[Sequence[float]]) -> List[Point2D]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VehiclePose`

源码位置：[car_control_B/schemas.py 第 43 行](../../../car_control_B/schemas.py#L43)。类型：`ClassDef`。

Frame-aligned ego pose consumed by B.

yaw_rad is the vehicle heading in radians, x-axis points forward in the map
coordinate convention used by the route points.

### `VehiclePose.__post_init__`

源码位置：[car_control_B/schemas.py 第 57 行](../../../car_control_B/schemas.py#L57)。类型：`FunctionDef`。

```python
VehiclePose.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VehiclePose.to_dict`

源码位置：[car_control_B/schemas.py 第 66 行](../../../car_control_B/schemas.py#L66)。类型：`FunctionDef`。

```python
VehiclePose.to_dict(self) -> Dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RouteReference`

源码位置：[car_control_B/schemas.py 第 73 行](../../../car_control_B/schemas.py#L73)。类型：`ClassDef`。

Local route reference from A to B.

points_xy_m must be in map/world meters and preferably equally spaced.
target_speed_mps is advisory for gain scheduling only; C still owns speed.

### `RouteReference.__post_init__`

源码位置：[car_control_B/schemas.py 第 86 行](../../../car_control_B/schemas.py#L86)。类型：`FunctionDef`。

```python
RouteReference.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RouteReference.to_dict`

源码位置：[car_control_B/schemas.py 第 94 行](../../../car_control_B/schemas.py#L94)。类型：`FunctionDef`。

```python
RouteReference.to_dict(self) -> Dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LateralOutput`

源码位置：[car_control_B/schemas.py 第 101 行](../../../car_control_B/schemas.py#L101)。类型：`ClassDef`。

B output to A/D.

``steer`` is passed directly to ``carla.VehicleControl``.  Its physical
left/right mapping is selected by the controller's ``steer_sign``
calibration rather than inferred by a downstream consumer.

### `LateralOutput.__post_init__`

源码位置：[car_control_B/schemas.py 第 119 行](../../../car_control_B/schemas.py#L119)。类型：`FunctionDef`。

```python
LateralOutput.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LateralOutput.to_dict`

源码位置：[car_control_B/schemas.py 第 130 行](../../../car_control_B/schemas.py#L130)。类型：`FunctionDef`。

```python
LateralOutput.to_dict(self) -> Dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_finite` 调用：`SchemaError`, `float`, `isinstance`, `math.isfinite`.
- `_point_list` 调用：`SchemaError`, `_finite`, `enumerate`, `len`, `out.append`.
- `__post_init__` 调用：`SchemaError`, `_finite`, `_point_list`, `object.__setattr__`.
- `to_dict` 调用：`asdict`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 63 行：`SchemaError('speed_mps must be non-negative')`。
- `__post_init__`，第 91 行：`SchemaError('target_speed_mps must be non-negative')`。
- `__post_init__`，第 122 行：`SchemaError('steer must be in [-1, 1]')`。
- `__post_init__`，第 128 行：`SchemaError('nearest_index and target_index must be non-negative')`。
- `_finite`，第 24 行：`SchemaError(f'{name} must be a finite number')`。
- `_finite`，第 27 行：`SchemaError(f'{name} must be finite')`。
- `_point_list`，第 33 行：`SchemaError('points_xy_m must contain at least two points')`。
- `_point_list`，第 37 行：`SchemaError(f'points_xy_m[{idx}] must be length 2')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_B/__init__.py](../../../car_control_B/__init__.py)
- [car_control_B/adapters.py](../../../car_control_B/adapters.py)
- [car_control_B/demo_fake_lateral.py](../../../car_control_B/demo_fake_lateral.py)
- [car_control_B/lateral_controller_base.py](../../../car_control_B/lateral_controller_base.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [car_control_B/stanley.py](../../../car_control_B/stanley.py)
- [car_control_B/tests/test_pure_pursuit.py](../../../car_control_B/tests/test_pure_pursuit.py)
- [car_control_B/tests/test_stanley.py](../../../car_control_B/tests/test_stanley.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [integration/tests/test_carla_runner_helpers.py](../../../integration/tests/test_carla_runner_helpers.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/schemas.py`

来源 SHA256：`ec49c1ffdf9f76e0ac5cf367826b8e82c83dc0f9c2ea0f4a0aef9a2c6a1dcf93`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `VehiclePose.x_m` | `float` | `无声明默认；构造/赋值方提供` |
| `VehiclePose.y_m` | `float` | `无声明默认；构造/赋值方提供` |
| `VehiclePose.yaw_rad` | `float` | `无声明默认；构造/赋值方提供` |
| `VehiclePose.speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `VehiclePose.frame` | `Optional[int]` | `None` |
| `VehiclePose.sim_time_s` | `Optional[float]` | `None` |
| `RouteReference.points_xy_m` | `List[Point2D]` | `无声明默认；构造/赋值方提供` |
| `RouteReference.curvature_per_m` | `float` | `0.0` |
| `RouteReference.target_speed_mps` | `float` | `5.0` |
| `RouteReference.route_id` | `Optional[str]` | `None` |
| `RouteReference.metadata` | `Dict[str, Any]` | `field(default_factory=dict)` |
| `LateralOutput.steer` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralOutput.cross_track_error_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralOutput.heading_error_rad` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralOutput.target_point_xy_m` | `Point2D` | `无声明默认；构造/赋值方提供` |
| `LateralOutput.lookahead_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralOutput.nearest_index` | `int` | `无声明默认；构造/赋值方提供` |
| `LateralOutput.target_index` | `int` | `无声明默认；构造/赋值方提供` |
| `LateralOutput.status` | `str` | `'OK'` |
| `LateralOutput.reason` | `str` | `'NONE'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_finite` / 24 | `isinstance(value, bool) or not isinstance(value, (int, float))` | `raise SchemaError(f'{name} must be a finite number')` |
| `_finite` / 27 | `not math.isfinite(value)` | `raise SchemaError(f'{name} must be finite')` |
| `_point_list` / 33 | `points is None or len(points) < 2` | `raise SchemaError('points_xy_m must contain at least two points')` |
| `_point_list` / 37 | `len(item) != 2` | `raise SchemaError(f'points_xy_m[{idx}] must be length 2')` |
| `VehiclePose.__post_init__` / 63 | `speed < 0` | `raise SchemaError('speed_mps must be non-negative')` |
| `RouteReference.__post_init__` / 91 | `target_speed < 0` | `raise SchemaError('target_speed_mps must be non-negative')` |
| `LateralOutput.__post_init__` / 122 | `not -1.0 <= steer <= 1.0` | `raise SchemaError('steer must be in [-1, 1]')` |
| `LateralOutput.__post_init__` / 128 | `self.nearest_index < 0 or self.target_index < 0` | `raise SchemaError('nearest_index and target_index must be non-negative')` |

### car_control_B/schemas.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 61 | `_finite('speed_mps', self.speed_mps)` |
| 89 | `_finite('target_speed_mps', self.target_speed_mps)` |
| 120 | `_finite('steer', self.steer)` |
| 58 | `_finite('x_m', self.x_m)` |
| 59 | `_finite('y_m', self.y_m)` |
| 60 | `_finite('yaw_rad', self.yaw_rad)` |
| 88 | `_finite('curvature_per_m', self.curvature_per_m)` |
| 124 | `_finite('cross_track_error_m', self.cross_track_error_m)` |
| 125 | `_finite('heading_error_rad', self.heading_error_rad)` |
| 126 | `_finite('lookahead_distance_m', self.lookahead_distance_m)` |
| 38 | `_finite(f'points_xy_m[{idx}][0]', item[0])` |
| 38 | `_finite(f'points_xy_m[{idx}][1]', item[1])` |
