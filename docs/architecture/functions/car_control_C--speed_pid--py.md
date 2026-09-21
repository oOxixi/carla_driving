# speed_pid：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/speed_pid.py](../../../car_control_C/speed_pid.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Longitudinal speed PID operating exclusively in SI units.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `PIDParameters.kp: float`；默认：`DEFAULT_STRATEGY.longitudinal.pid_kp`。
- `PIDParameters.ki: float`；默认：`DEFAULT_STRATEGY.longitudinal.pid_ki`。
- `PIDParameters.kd: float`；默认：`DEFAULT_STRATEGY.longitudinal.pid_kd`。
- `PIDParameters.integral_limit: float`；默认：`DEFAULT_STRATEGY.longitudinal.pid_integral_limit`。
- `PIDParameters.accel_min_mps2: float`；默认：`-DEFAULT_STRATEGY.common.max_decel_mps2`。
- `PIDParameters.accel_max_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.max_accel_mps2`。
- `PIDParameters.target_step_reset_mps: float`；默认：`DEFAULT_STRATEGY.longitudinal.pid_target_step_reset_mps`。

## 功能入口：输入、输出与实现说明

### `PIDParameters`

源码位置：[car_control_C/speed_pid.py 第 11 行](../../../car_control_C/speed_pid.py#L11)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PIDParameters.__post_init__`

源码位置：[car_control_C/speed_pid.py 第 20 行](../../../car_control_C/speed_pid.py#L20)。类型：`FunctionDef`。

```python
PIDParameters.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPID`

源码位置：[car_control_C/speed_pid.py 第 31 行](../../../car_control_C/speed_pid.py#L31)。类型：`ClassDef`。

PID with bounded integral and conditional integration anti-windup.

### `SpeedPID.__init__`

源码位置：[car_control_C/speed_pid.py 第 34 行](../../../car_control_C/speed_pid.py#L34)。类型：`FunctionDef`。

```python
SpeedPID.__init__(self, kp: float=DEFAULT_STRATEGY.longitudinal.pid_kp, ki: float=DEFAULT_STRATEGY.longitudinal.pid_ki, kd: float=DEFAULT_STRATEGY.longitudinal.pid_kd, integral_limit: float=DEFAULT_STRATEGY.longitudinal.pid_integral_limit, accel_min_mps2: float=-DEFAULT_STRATEGY.common.max_decel_mps2, accel_max_mps2: float=DEFAULT_STRATEGY.longitudinal.max_accel_mps2, target_step_reset_mps: float=DEFAULT_STRATEGY.longitudinal.pid_target_step_reset_mps) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPID.reset`

源码位置：[car_control_C/speed_pid.py 第 46 行](../../../car_control_C/speed_pid.py#L46)。类型：`FunctionDef`。

```python
SpeedPID.reset(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPID.step`

源码位置：[car_control_C/speed_pid.py 第 51 行](../../../car_control_C/speed_pid.py#L51)。类型：`FunctionDef`。

```python
SpeedPID.step(self, target_speed_mps: float, speed_mps: float, dt_s: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `finite`, `getattr`.
- `__init__` 调用：`PIDParameters`.
- `step` 调用：`abs`, `finite`, `max`, `min`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 28 行：`ValueError('accel_min_mps2 must be below accel_max_mps2')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_C/validation.py](../../../car_control_C/validation.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/speed_pid.py`

来源 SHA256：`80aff5978a0acc6afb97aaf9484433c143f4514bb557c304389dd2ad7ad53227`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `PIDParameters.kp` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_kp` |
| `PIDParameters.ki` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_ki` |
| `PIDParameters.kd` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_kd` |
| `PIDParameters.integral_limit` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_integral_limit` |
| `PIDParameters.accel_min_mps2` | `float` | `-DEFAULT_STRATEGY.common.max_decel_mps2` |
| `PIDParameters.accel_max_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.max_accel_mps2` |
| `PIDParameters.target_step_reset_mps` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_target_step_reset_mps` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `PIDParameters.__post_init__` / 28 | `self.accel_min_mps2 >= self.accel_max_mps2` | `raise ValueError('accel_min_mps2 must be below accel_max_mps2')` |

### car_control_C/speed_pid.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 23 | `finite('integral_limit', self.integral_limit, positive=True)` |
| 24 | `finite('accel_min_mps2', self.accel_min_mps2)` |
| 25 | `finite('accel_max_mps2', self.accel_max_mps2, positive=True)` |
| 26 | `finite('target_step_reset_mps', self.target_step_reset_mps, positive=True)` |
| 52 | `finite('target_speed_mps', target_speed_mps, minimum=0.0)` |
| 53 | `finite('speed_mps', speed_mps, minimum=0.0)` |
| 54 | `finite('dt_s', dt_s, positive=True)` |
| 22 | `finite(name, getattr(self, name), minimum=0.0)` |
