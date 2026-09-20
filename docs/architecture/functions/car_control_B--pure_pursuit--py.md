# pure_pursuit：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Pure Pursuit lateral controller for CARLA.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `PurePursuitParams.wheel_base_m: float`；默认：`DEFAULT_STRATEGY.lateral.wheel_base_m`。
- `PurePursuitParams.base_lookahead_m: float`；默认：`DEFAULT_STRATEGY.lateral.base_lookahead_m`。
- `PurePursuitParams.speed_gain_s: float`；默认：`DEFAULT_STRATEGY.lateral.speed_gain_s`。
- `PurePursuitParams.min_lookahead_m: float`；默认：`DEFAULT_STRATEGY.lateral.min_lookahead_m`。
- `PurePursuitParams.max_lookahead_m: float`；默认：`DEFAULT_STRATEGY.lateral.max_lookahead_m`。
- `PurePursuitParams.curvature_lookahead_gain: float`；默认：`DEFAULT_STRATEGY.lateral.curvature_lookahead_gain`。
- `PurePursuitParams.error_lookahead_gain: float`；默认：`DEFAULT_STRATEGY.lateral.error_lookahead_gain`。
- `PurePursuitParams.max_steer_angle_rad: float`；默认：`DEFAULT_STRATEGY.lateral.max_steer_angle_rad`。
- `PurePursuitParams.steer_gain: float`；默认：`DEFAULT_STRATEGY.lateral.steer_gain`。
- `PurePursuitParams.max_steer: float`；默认：`DEFAULT_STRATEGY.lateral.max_steer`。
- `PurePursuitParams.min_steer_limit: float`；默认：`DEFAULT_STRATEGY.lateral.min_steer_limit`。
- `PurePursuitParams.high_speed_steer_reduction_per_mps: float`；默认：`DEFAULT_STRATEGY.lateral.high_speed_steer_reduction_per_mps`。
- `PurePursuitParams.curvature_steer_gain: float`；默认：`DEFAULT_STRATEGY.lateral.curvature_steer_gain`。
- `PurePursuitParams.max_steer_delta_per_step: float`；默认：`DEFAULT_STRATEGY.lateral.base_steer_delta_per_step`。
- `PurePursuitParams.min_steer_delta_per_step: float`；默认：`DEFAULT_STRATEGY.lateral.min_steer_delta_per_step`。
- `PurePursuitParams.adaptive_max_steer_delta_per_step: float`；默认：`DEFAULT_STRATEGY.lateral.max_steer_delta_per_step`。
- `PurePursuitParams.low_speed_steer_gain: float`；默认：`DEFAULT_STRATEGY.lateral.low_speed_steer_gain`。
- `PurePursuitParams.curvature_rate_gain: float`；默认：`DEFAULT_STRATEGY.lateral.curvature_rate_gain`。
- `PurePursuitParams.error_rate_gain: float`；默认：`DEFAULT_STRATEGY.lateral.error_rate_gain`。
- `PurePursuitParams.cross_track_gain: float`；默认：`0.8`。
- `PurePursuitParams.cross_track_softening_speed_mps: float`；默认：`1.0`。
- `PurePursuitParams.steer_sign: float`；默认：`DEFAULT_STRATEGY.lateral.steer_sign`。
- `PurePursuitParams.nearest_search_window: int | None`；默认：`None`。
- `PurePursuitParams.route_reacquire_search_window: int | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

### `PurePursuitParams`

源码位置：[car_control_B/pure_pursuit.py 第 24 行](../../../car_control_B/pure_pursuit.py#L24)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitParams.__post_init__`

源码位置：[car_control_B/pure_pursuit.py 第 53 行](../../../car_control_B/pure_pursuit.py#L53)。类型：`FunctionDef`。

```python
PurePursuitParams.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitController`

源码位置：[car_control_B/pure_pursuit.py 第 83 行](../../../car_control_B/pure_pursuit.py#L83)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitController.__init__`

源码位置：[car_control_B/pure_pursuit.py 第 84 行](../../../car_control_B/pure_pursuit.py#L84)。类型：`FunctionDef`。

```python
PurePursuitController.__init__(self, params: PurePursuitParams | None=None) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitController.reset`

源码位置：[car_control_B/pure_pursuit.py 第 95 行](../../../car_control_B/pure_pursuit.py#L95)。类型：`FunctionDef`。

```python
PurePursuitController.reset(self, *, preserve_steer: bool=False) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitController.synchronize_route_progress`

源码位置：[car_control_B/pure_pursuit.py 第 105 行](../../../car_control_B/pure_pursuit.py#L105)。类型：`FunctionDef`。

```python
PurePursuitController.synchronize_route_progress(self, reference: Any, progress_m: float) -> int
```

Synchronize a retained route with an external monotonic tracker.

Temporary manoeuvre routes can advance farther than the controller's
bounded geometric reacquisition window.  The mission progress tracker
already resolves loops by arc length, so use that evidence to restore
the exact route slot without a global nearest-point snap.

### `PurePursuitController._lookahead`

源码位置：[car_control_B/pure_pursuit.py 第 155 行](../../../car_control_B/pure_pursuit.py#L155)。类型：`FunctionDef`。

```python
PurePursuitController._lookahead(self, speed_mps: float, curvature_per_m: float=0.0, cross_track_error_m: float=0.0, heading_error_rad: float=0.0) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitController._steer_limit`

源码位置：[car_control_B/pure_pursuit.py 第 169 行](../../../car_control_B/pure_pursuit.py#L169)。类型：`FunctionDef`。

```python
PurePursuitController._steer_limit(self, speed_mps: float, curvature_per_m: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitController._steer_delta_limit`

源码位置：[car_control_B/pure_pursuit.py 第 178 行](../../../car_control_B/pure_pursuit.py#L178)。类型：`FunctionDef`。

```python
PurePursuitController._steer_delta_limit(self, speed_mps: float, curvature_per_m: float, cross_track_error_m: float, heading_error_rad: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PurePursuitController.step`

源码位置：[car_control_B/pure_pursuit.py 第 193 行](../../../car_control_B/pure_pursuit.py#L193)。类型：`FunctionDef`。

```python
PurePursuitController.step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `any`, `float`, `getattr`, `math.isfinite`, `numeric.values`, `set`, `type`.
- `__init__` 调用：`PurePursuitParams`.
- `reset` 调用：`TypeError`, `self._route_progress.clear`, `type`.
- `synchronize_route_progress` 调用：`ValueError`, `abs`, `cumulative.append`, `enumerate`, `float`, `getattr`, `len`, `math.dist`, `math.isfinite`, `min`, `next`, `range`, `self._adapt_reference_any`, `self._route_progress.append`, `zip`.
- `_lookahead` 调用：`abs`, `clamp`.
- `_steer_limit` 调用：`abs`, `clamp`.
- `_steer_delta_limit` 调用：`abs`, `clamp`, `max`.
- `step` 调用：`LateralOutput`, `clamp`, `compute_path_heading`, `enumerate`, `find_lookahead_index`, `find_nearest_index`, `len`, `math.atan`, `math.atan2`, `math.cos`, `math.sin`, `max`, `max_abs_curvature_ahead`, `next`, `self._lookahead`, `self._route_progress.append`, `self._steer_delta_limit`, `self._steer_limit`, `signed_cross_track_error`, `wrap_angle_rad`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 60 行：`ValueError('all Pure Pursuit parameters must be finite numbers')`。
- `__post_init__`，第 63 行：`ValueError('Pure Pursuit magnitudes must be non-negative')`。
- `__post_init__`，第 65 行：`ValueError('min_lookahead_m must not exceed max_lookahead_m')`。
- `__post_init__`，第 67 行：`ValueError('min_steer_limit must not exceed max_steer')`。
- `__post_init__`，第 69 行：`ValueError('adaptive steer delta limits are inverted')`。
- `__post_init__`，第 71 行：`ValueError('steer_sign must be -1 or 1')`。
- `__post_init__`，第 75 行：`ValueError('nearest_search_window must be a positive integer or None')`。
- `__post_init__`，第 80 行：`ValueError('route_reacquire_search_window must be a positive integer or None')`。
- `reset`，第 97 行：`TypeError('preserve_steer must be bool')`。
- `synchronize_route_progress`，第 115 行：`ValueError('route progress must be finite and non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_B/lateral_controller_base.py](../../../car_control_B/lateral_controller_base.py)
- [car_control_B/path_utils.py](../../../car_control_B/path_utils.py)
- [car_control_B/schemas.py](../../../car_control_B/schemas.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_B/__init__.py](../../../car_control_B/__init__.py)
- [car_control_B/demo_fake_lateral.py](../../../car_control_B/demo_fake_lateral.py)
- [car_control_B/tests/test_pure_pursuit.py](../../../car_control_B/tests/test_pure_pursuit.py)
- [car_control_D/benchmark.py](../../../car_control_D/benchmark.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/demo_offline.py](../../../integration/demo_offline.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/tests/test_runtime_loop.py](../../../integration/tests/test_runtime_loop.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)
- [tools/validate_c_role.py](../../../tools/validate_c_role.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/pure_pursuit.py`

来源 SHA256：`c5003f9e37769a7a4f753db86425dbb49f7ee3f35cf3f0ff1dcdd174bf4b24a2`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `PurePursuitParams.wheel_base_m` | `float` | `DEFAULT_STRATEGY.lateral.wheel_base_m` |
| `PurePursuitParams.base_lookahead_m` | `float` | `DEFAULT_STRATEGY.lateral.base_lookahead_m` |
| `PurePursuitParams.speed_gain_s` | `float` | `DEFAULT_STRATEGY.lateral.speed_gain_s` |
| `PurePursuitParams.min_lookahead_m` | `float` | `DEFAULT_STRATEGY.lateral.min_lookahead_m` |
| `PurePursuitParams.max_lookahead_m` | `float` | `DEFAULT_STRATEGY.lateral.max_lookahead_m` |
| `PurePursuitParams.curvature_lookahead_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_lookahead_gain` |
| `PurePursuitParams.error_lookahead_gain` | `float` | `DEFAULT_STRATEGY.lateral.error_lookahead_gain` |
| `PurePursuitParams.max_steer_angle_rad` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_angle_rad` |
| `PurePursuitParams.steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.steer_gain` |
| `PurePursuitParams.max_steer` | `float` | `DEFAULT_STRATEGY.lateral.max_steer` |
| `PurePursuitParams.min_steer_limit` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_limit` |
| `PurePursuitParams.high_speed_steer_reduction_per_mps` | `float` | `DEFAULT_STRATEGY.lateral.high_speed_steer_reduction_per_mps` |
| `PurePursuitParams.curvature_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_steer_gain` |
| `PurePursuitParams.max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.base_steer_delta_per_step` |
| `PurePursuitParams.min_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_delta_per_step` |
| `PurePursuitParams.adaptive_max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_delta_per_step` |
| `PurePursuitParams.low_speed_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.low_speed_steer_gain` |
| `PurePursuitParams.curvature_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_rate_gain` |
| `PurePursuitParams.error_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.error_rate_gain` |
| `PurePursuitParams.cross_track_gain` | `float` | `0.8` |
| `PurePursuitParams.cross_track_softening_speed_mps` | `float` | `1.0` |
| `PurePursuitParams.steer_sign` | `float` | `DEFAULT_STRATEGY.lateral.steer_sign` |
| `PurePursuitParams.nearest_search_window` | `int &#124; None` | `None` |
| `PurePursuitParams.route_reacquire_search_window` | `int &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `PurePursuitParams.__post_init__` / 60 | `any((type(value) not in (int, float) or not math.isfinite(float(value)) for value in numeric.values()))` | `raise ValueError('all Pure Pursuit parameters must be finite numbers')` |
| `PurePursuitParams.__post_init__` / 63 | `any((float(numeric[name]) < 0.0 for name in positive))` | `raise ValueError('Pure Pursuit magnitudes must be non-negative')` |
| `PurePursuitParams.__post_init__` / 65 | `self.min_lookahead_m > self.max_lookahead_m` | `raise ValueError('min_lookahead_m must not exceed max_lookahead_m')` |
| `PurePursuitParams.__post_init__` / 67 | `self.min_steer_limit > self.max_steer` | `raise ValueError('min_steer_limit must not exceed max_steer')` |
| `PurePursuitParams.__post_init__` / 69 | `self.min_steer_delta_per_step > self.adaptive_max_steer_delta_per_step` | `raise ValueError('adaptive steer delta limits are inverted')` |
| `PurePursuitParams.__post_init__` / 71 | `self.steer_sign not in {-1.0, 1.0}` | `raise ValueError('steer_sign must be -1 or 1')` |
| `PurePursuitParams.__post_init__` / 75 | `self.nearest_search_window is not None and (type(self.nearest_search_window) is not int or self.nearest_search_window <= 0)` | `raise ValueError('nearest_search_window must be a positive integer or None')` |
| `PurePursuitParams.__post_init__` / 80 | `self.route_reacquire_search_window is not None and (type(self.route_reacquire_search_window) is not int or self.route_reacquire_search_window <= 0)` | `raise ValueError('route_reacquire_search_window must be a positive integer or None')` |
| `PurePursuitController.reset` / 97 | `type(preserve_steer) is not bool` | `raise TypeError('preserve_steer must be bool')` |
| `PurePursuitController.synchronize_route_progress` / 115 | `not math.isfinite(progress) or progress < 0.0` | `raise ValueError('route progress must be finite and non-negative')` |
