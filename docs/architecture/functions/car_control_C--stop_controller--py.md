# stop_controller：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/stop_controller.py](../../../car_control_C/stop_controller.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Four-phase longitudinal stopping policy.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `StopParameters.max_decel_mps2: float`；默认：`DEFAULT_STRATEGY.common.max_decel_mps2`。
- `StopParameters.comfortable_decel_mps2: float`；默认：`DEFAULT_STRATEGY.common.comfortable_decel_mps2`。
- `StopParameters.creep_speed_mps: float`；默认：`DEFAULT_STRATEGY.longitudinal.creep_speed_mps`。
- `StopParameters.hold_distance_m: float`；默认：`DEFAULT_STRATEGY.longitudinal.stop_hold_distance_m`。
- `StopParameters.hold_speed_mps: float`；默认：`DEFAULT_STRATEGY.common.standstill_speed_mps`。
- `StopParameters.hold_brake: float`；默认：`DEFAULT_STRATEGY.common.hold_brake`。

## 功能入口：输入、输出与实现说明

### `StopState`

源码位置：[car_control_C/stop_controller.py 第 11 行](../../../car_control_C/stop_controller.py#L11)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StopParameters`

源码位置：[car_control_C/stop_controller.py 第 19 行](../../../car_control_C/stop_controller.py#L19)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StopParameters.__post_init__`

源码位置：[car_control_C/stop_controller.py 第 27 行](../../../car_control_C/stop_controller.py#L27)。类型：`FunctionDef`。

```python
StopParameters.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StopController`

源码位置：[car_control_C/stop_controller.py 第 36 行](../../../car_control_C/stop_controller.py#L36)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StopController.__init__`

源码位置：[car_control_C/stop_controller.py 第 37 行](../../../car_control_C/stop_controller.py#L37)。类型：`FunctionDef`。

```python
StopController.__init__(self, parameters: StopParameters | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StopController.state_for`

源码位置：[car_control_C/stop_controller.py 第 40 行](../../../car_control_C/stop_controller.py#L40)。类型：`FunctionDef`。

```python
StopController.state_for(self, speed_mps: float, distance_m: float | None) -> StopState
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StopController.speed_cap_mps`

源码位置：[car_control_C/stop_controller.py 第 52 行](../../../car_control_C/stop_controller.py#L52)。类型：`FunctionDef`。

```python
StopController.speed_cap_mps(self, speed_mps: float, distance_m: float | None, dt_s: float=0.0) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StopController.required_decel_mps2`

源码位置：[car_control_C/stop_controller.py 第 76 行](../../../car_control_C/stop_controller.py#L76)。类型：`FunctionDef`。

```python
StopController.required_decel_mps2(self, speed_mps: float, distance_m: float | None) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__post_init__` 调用：`finite`.
- `__init__` 调用：`StopParameters`.
- `state_for` 调用：`finite`, `max`.
- `speed_cap_mps` 调用：`finite`, `max`, `self.state_for`.
- `required_decel_mps2` 调用：`finite`, `max`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_C/validation.py](../../../car_control_C/validation.py)
- [compat.py](../../../compat.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py)
- [car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py)
- [car_control_C/tests/test_longitudinal.py](../../../car_control_C/tests/test_longitudinal.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/stop_controller.py`

来源 SHA256：`04524f8b585141c155333e657b0093a2ca0bfdee70228df24c2383f0a058c465`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `StopParameters.max_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.max_decel_mps2` |
| `StopParameters.comfortable_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.comfortable_decel_mps2` |
| `StopParameters.creep_speed_mps` | `float` | `DEFAULT_STRATEGY.longitudinal.creep_speed_mps` |
| `StopParameters.hold_distance_m` | `float` | `DEFAULT_STRATEGY.longitudinal.stop_hold_distance_m` |
| `StopParameters.hold_speed_mps` | `float` | `DEFAULT_STRATEGY.common.standstill_speed_mps` |
| `StopParameters.hold_brake` | `float` | `DEFAULT_STRATEGY.common.hold_brake` |

### car_control_C/stop_controller.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 28 | `finite('max_decel_mps2', self.max_decel_mps2, positive=True)` |
| 29 | `finite('comfortable_decel_mps2', self.comfortable_decel_mps2, positive=True)` |
| 30 | `finite('creep_speed_mps', self.creep_speed_mps, minimum=0.0)` |
| 31 | `finite('hold_distance_m', self.hold_distance_m, minimum=0.0)` |
| 32 | `finite('hold_speed_mps', self.hold_speed_mps, minimum=0.0)` |
| 33 | `finite('hold_brake', self.hold_brake, positive=True, maximum=1.0)` |
| 41 | `finite('speed_mps', speed_mps, minimum=0.0)` |
| 53 | `finite('speed_mps', speed_mps, minimum=0.0)` |
| 54 | `finite('dt_s', dt_s, minimum=0.0)` |
| 77 | `finite('speed_mps', speed_mps, minimum=0.0)` |
| 43 | `finite('distance_m', distance_m, minimum=0.0)` |
| 56 | `finite('distance_m', distance_m, minimum=0.0)` |
| 79 | `finite('distance_m', distance_m, minimum=0.0)` |
