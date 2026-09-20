# longitudinal_controller：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

C's CARLA-independent longitudinal orchestration layer.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `LongitudinalParameters.max_lateral_accel_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.max_lateral_accel_mps2`。
- `LongitudinalParameters.command_accel_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.command_accel_mps2`。
- `LongitudinalParameters.command_decel_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.command_decel_mps2`。
- `LongitudinalParameters.max_accel_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.max_accel_mps2`。
- `LongitudinalParameters.max_decel_mps2: float`；默认：`DEFAULT_STRATEGY.common.max_decel_mps2`。
- `LongitudinalParameters.max_control_delta_per_s: float`；默认：`DEFAULT_STRATEGY.longitudinal.max_control_delta_per_s`。
- `LongitudinalParameters.hold_brake: float`；默认：`DEFAULT_STRATEGY.common.hold_brake`。
- `LongitudinalParameters.emergency_brake: float`；默认：`DEFAULT_STRATEGY.common.emergency_brake`。
- `LongitudinalParameters.standstill_gap_m: float`；默认：`DEFAULT_STRATEGY.safety_distance.standstill_gap_m`。
- `LongitudinalParameters.time_gap_s: float`；默认：`DEFAULT_STRATEGY.safety_distance.reaction_time_s`。
- `LongitudinalParameters.emergency_ttc_s: float`；默认：`DEFAULT_STRATEGY.common.emergency_ttc_s`。
- `LongitudinalParameters.comfortable_decel_mps2: float`；默认：`DEFAULT_STRATEGY.common.comfortable_decel_mps2`。

## 功能入口：输入、输出与实现说明

### `LongitudinalParameters`

源码位置：[car_control_C/longitudinal_controller.py 第 19 行](../../../car_control_C/longitudinal_controller.py#L19)。类型：`ClassDef`。

Explicit, SI-only tuning for C; final safety arbitration belongs to D.

### `LongitudinalParameters.__post_init__`

源码位置：[car_control_C/longitudinal_controller.py 第 35 行](../../../car_control_C/longitudinal_controller.py#L35)。类型：`FunctionDef`。

```python
LongitudinalParameters.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LongitudinalController`

源码位置：[car_control_C/longitudinal_controller.py 第 45 行](../../../car_control_C/longitudinal_controller.py#L45)。类型：`ClassDef`。

Plans a speed and maps it to exclusive throttle/brake controls.

It intentionally emits ``RiskMetrics`` instead of overriding a future D
supervisor. ``target_accel_mps2`` is C's requested acceleration, not a
final vehicle-authority command; D retains final arbitration.  The
emergency-brake control here is a local C fallback only.

### `LongitudinalController.__init__`

源码位置：[car_control_C/longitudinal_controller.py 第 54 行](../../../car_control_C/longitudinal_controller.py#L54)。类型：`FunctionDef`。

```python
LongitudinalController.__init__(self, parameters: LongitudinalParameters | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LongitudinalController._rate_limited_control`

源码位置：[car_control_C/longitudinal_controller.py 第 78 行](../../../car_control_C/longitudinal_controller.py#L78)。类型：`FunctionDef`。

```python
LongitudinalController._rate_limited_control(self, accel_mps2: float, dt_s: float) -> ControlOutput
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LongitudinalController.step`

源码位置：[car_control_C/longitudinal_controller.py 第 99 行](../../../car_control_C/longitudinal_controller.py#L99)。类型：`FunctionDef`。

```python
LongitudinalController.step(self, request: LongitudinalRequest, dt_s: float) -> LongitudinalOutput
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LongitudinalController.reset`

源码位置：[car_control_C/longitudinal_controller.py 第 135 行](../../../car_control_C/longitudinal_controller.py#L135)。类型：`FunctionDef`。

```python
LongitudinalController.reset(self) -> None
```

Forget all episode-local histories before a CARLA respawn/reset.

## 内部调用与异常路径

- `__post_init__` 调用：`finite`, `getattr`.
- `__init__` 调用：`FollowingController`, `FollowingParameters`, `LongitudinalParameters`, `SpeedPID`, `SpeedPlanner`, `SpeedPlannerParameters`, `StopController`, `StopParameters`, `TrafficRulePlanner`.
- `_rate_limited_control` 调用：`ControlOutput`, `max`, `min`.
- `step` 调用：`ControlOutput`, `LongitudinalOutput`, `TypeError`, `finite`, `isinstance`, `max`, `self._rate_limited_control`, `self.following_controller.risk`, `self.pid.step`, `self.speed_planner.plan`, `self.stop_controller.required_decel_mps2`, `self.stop_controller.state_for`, `self.traffic_rules.stop_distance_m`.
- `reset` 调用：`self.pid.reset`, `self.speed_planner.reset`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `step`，第 101 行：`TypeError('request must be LongitudinalRequest')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_C/following_controller.py](../../../car_control_C/following_controller.py)
- [car_control_C/speed_pid.py](../../../car_control_C/speed_pid.py)
- [car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py)
- [car_control_C/stop_controller.py](../../../car_control_C/stop_controller.py)
- [car_control_C/traffic_rules.py](../../../car_control_C/traffic_rules.py)
- [car_control_C/validation.py](../../../car_control_C/validation.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_C/__init__.py](../../../car_control_C/__init__.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/longitudinal_controller.py`

来源 SHA256：`02bf9a712ebbe931d44a52d30c06d83db5af9bad127e12ba186eb3e6729d6202`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `LongitudinalParameters.max_lateral_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.max_lateral_accel_mps2` |
| `LongitudinalParameters.command_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.command_accel_mps2` |
| `LongitudinalParameters.command_decel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.command_decel_mps2` |
| `LongitudinalParameters.max_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.max_accel_mps2` |
| `LongitudinalParameters.max_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.max_decel_mps2` |
| `LongitudinalParameters.max_control_delta_per_s` | `float` | `DEFAULT_STRATEGY.longitudinal.max_control_delta_per_s` |
| `LongitudinalParameters.hold_brake` | `float` | `DEFAULT_STRATEGY.common.hold_brake` |
| `LongitudinalParameters.emergency_brake` | `float` | `DEFAULT_STRATEGY.common.emergency_brake` |
| `LongitudinalParameters.standstill_gap_m` | `float` | `DEFAULT_STRATEGY.safety_distance.standstill_gap_m` |
| `LongitudinalParameters.time_gap_s` | `float` | `DEFAULT_STRATEGY.safety_distance.reaction_time_s` |
| `LongitudinalParameters.emergency_ttc_s` | `float` | `DEFAULT_STRATEGY.common.emergency_ttc_s` |
| `LongitudinalParameters.comfortable_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.comfortable_decel_mps2` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `LongitudinalController.step` / 101 | `not isinstance(request, LongitudinalRequest)` | `raise TypeError('request must be LongitudinalRequest')` |

### car_control_C/longitudinal_controller.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 40 | `finite('standstill_gap_m', self.standstill_gap_m, minimum=0.0)` |
| 41 | `finite('hold_brake', self.hold_brake, positive=True, maximum=1.0)` |
| 42 | `finite('emergency_brake', self.emergency_brake, minimum=0.0, maximum=1.0)` |
| 102 | `finite('dt_s', dt_s, positive=True)` |
| 39 | `finite(name, getattr(self, name), positive=True)` |
