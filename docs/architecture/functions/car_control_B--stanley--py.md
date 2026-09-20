# stanley：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[car_control_B/stanley.py](../../../car_control_B/stanley.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Stanley controller as a backup/comparison controller.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `StanleyParams.gain: float`；默认：`DEFAULT_STRATEGY.lateral.stanley_gain`。
- `StanleyParams.softening_speed_mps: float`；默认：`DEFAULT_STRATEGY.lateral.stanley_softening_speed_mps`。
- `StanleyParams.curvature_gain: float`；默认：`DEFAULT_STRATEGY.lateral.stanley_curvature_gain`。
- `StanleyParams.max_steer_angle_rad: float`；默认：`DEFAULT_STRATEGY.lateral.max_steer_angle_rad`。
- `StanleyParams.max_steer: float`；默认：`DEFAULT_STRATEGY.lateral.max_steer`。
- `StanleyParams.min_steer_limit: float`；默认：`DEFAULT_STRATEGY.lateral.min_steer_limit`。
- `StanleyParams.high_speed_steer_reduction_per_mps: float`；默认：`DEFAULT_STRATEGY.lateral.high_speed_steer_reduction_per_mps`。
- `StanleyParams.curvature_steer_gain: float`；默认：`DEFAULT_STRATEGY.lateral.curvature_steer_gain`。
- `StanleyParams.max_steer_delta_per_step: float`；默认：`DEFAULT_STRATEGY.lateral.base_steer_delta_per_step`。
- `StanleyParams.min_steer_delta_per_step: float`；默认：`DEFAULT_STRATEGY.lateral.min_steer_delta_per_step`。
- `StanleyParams.adaptive_max_steer_delta_per_step: float`；默认：`DEFAULT_STRATEGY.lateral.max_steer_delta_per_step`。
- `StanleyParams.low_speed_steer_gain: float`；默认：`DEFAULT_STRATEGY.lateral.low_speed_steer_gain`。
- `StanleyParams.curvature_rate_gain: float`；默认：`DEFAULT_STRATEGY.lateral.curvature_rate_gain`。
- `StanleyParams.error_rate_gain: float`；默认：`DEFAULT_STRATEGY.lateral.error_rate_gain`。
- `StanleyParams.steer_sign: float`；默认：`DEFAULT_STRATEGY.lateral.steer_sign`。
- `StanleyParams.nearest_search_window: int | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

### `StanleyParams`

源码位置：[car_control_B/stanley.py 第 15 行](../../../car_control_B/stanley.py#L15)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StanleyParams.__post_init__`

源码位置：[car_control_B/stanley.py 第 34 行](../../../car_control_B/stanley.py#L34)。类型：`FunctionDef`。

```python
StanleyParams.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StanleyController`

源码位置：[car_control_B/stanley.py 第 57 行](../../../car_control_B/stanley.py#L57)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StanleyController.__init__`

源码位置：[car_control_B/stanley.py 第 58 行](../../../car_control_B/stanley.py#L58)。类型：`FunctionDef`。

```python
StanleyController.__init__(self, params: StanleyParams | None=None) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StanleyController.reset`

源码位置：[car_control_B/stanley.py 第 63 行](../../../car_control_B/stanley.py#L63)。类型：`FunctionDef`。

```python
StanleyController.reset(self, *, preserve_steer: bool=False) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StanleyController.step`

源码位置：[car_control_B/stanley.py 第 70 行](../../../car_control_B/stanley.py#L70)。类型：`FunctionDef`。

```python
StanleyController.step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `any`, `float`, `getattr`, `math.isfinite`, `numeric.values`, `set`, `type`.
- `__init__` 调用：`StanleyParams`.
- `reset` 调用：`TypeError`, `type`.
- `step` 调用：`LateralOutput`, `abs`, `clamp`, `compute_path_heading`, `find_nearest_index`, `math.atan2`, `max`, `signed_cross_track_error`, `wrap_angle_rad`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 41 行：`ValueError('all Stanley parameters must be finite numbers')`。
- `__post_init__`，第 44 行：`ValueError('Stanley magnitudes must be non-negative')`。
- `__post_init__`，第 46 行：`ValueError('min_steer_limit must not exceed max_steer')`。
- `__post_init__`，第 48 行：`ValueError('adaptive steer delta limits are inverted')`。
- `__post_init__`，第 50 行：`ValueError('steer_sign must be -1 or 1')`。
- `__post_init__`，第 54 行：`ValueError('nearest_search_window must be a positive integer or None')`。
- `reset`，第 65 行：`TypeError('preserve_steer must be bool')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_B/lateral_controller_base.py](../../../car_control_B/lateral_controller_base.py)
- [car_control_B/path_utils.py](../../../car_control_B/path_utils.py)
- [car_control_B/schemas.py](../../../car_control_B/schemas.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_B/__init__.py](../../../car_control_B/__init__.py)
- [car_control_B/tests/test_stanley.py](../../../car_control_B/tests/test_stanley.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/stanley.py`

来源 SHA256：`1af91bcc12293c692f1dd39d4b018b13aa5c8f8047f30af8c59af77aff070262`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `StanleyParams.gain` | `float` | `DEFAULT_STRATEGY.lateral.stanley_gain` |
| `StanleyParams.softening_speed_mps` | `float` | `DEFAULT_STRATEGY.lateral.stanley_softening_speed_mps` |
| `StanleyParams.curvature_gain` | `float` | `DEFAULT_STRATEGY.lateral.stanley_curvature_gain` |
| `StanleyParams.max_steer_angle_rad` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_angle_rad` |
| `StanleyParams.max_steer` | `float` | `DEFAULT_STRATEGY.lateral.max_steer` |
| `StanleyParams.min_steer_limit` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_limit` |
| `StanleyParams.high_speed_steer_reduction_per_mps` | `float` | `DEFAULT_STRATEGY.lateral.high_speed_steer_reduction_per_mps` |
| `StanleyParams.curvature_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_steer_gain` |
| `StanleyParams.max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.base_steer_delta_per_step` |
| `StanleyParams.min_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_delta_per_step` |
| `StanleyParams.adaptive_max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_delta_per_step` |
| `StanleyParams.low_speed_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.low_speed_steer_gain` |
| `StanleyParams.curvature_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_rate_gain` |
| `StanleyParams.error_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.error_rate_gain` |
| `StanleyParams.steer_sign` | `float` | `DEFAULT_STRATEGY.lateral.steer_sign` |
| `StanleyParams.nearest_search_window` | `int &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `StanleyParams.__post_init__` / 41 | `any((type(value) not in (int, float) or not math.isfinite(float(value)) for value in numeric.values()))` | `raise ValueError('all Stanley parameters must be finite numbers')` |
| `StanleyParams.__post_init__` / 44 | `any((float(numeric[name]) < 0.0 for name in positive))` | `raise ValueError('Stanley magnitudes must be non-negative')` |
| `StanleyParams.__post_init__` / 46 | `self.min_steer_limit > self.max_steer` | `raise ValueError('min_steer_limit must not exceed max_steer')` |
| `StanleyParams.__post_init__` / 48 | `self.min_steer_delta_per_step > self.adaptive_max_steer_delta_per_step` | `raise ValueError('adaptive steer delta limits are inverted')` |
| `StanleyParams.__post_init__` / 50 | `self.steer_sign not in {-1.0, 1.0}` | `raise ValueError('steer_sign must be -1 or 1')` |
| `StanleyParams.__post_init__` / 54 | `self.nearest_search_window is not None and (type(self.nearest_search_window) is not int or self.nearest_search_window <= 0)` | `raise ValueError('nearest_search_window must be a positive integer or None')` |
| `StanleyController.reset` / 65 | `type(preserve_steer) is not bool` | `raise TypeError('preserve_steer must be bool')` |
