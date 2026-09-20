# speed_planner：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Multi-constraint target-speed planner.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `SpeedPlannerParameters.max_lateral_accel_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.max_lateral_accel_mps2`。
- `SpeedPlannerParameters.command_accel_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.command_accel_mps2`。
- `SpeedPlannerParameters.command_decel_mps2: float`；默认：`DEFAULT_STRATEGY.longitudinal.command_decel_mps2`。
- `SpeedPlan.safe_target_speed_mps: float`；默认：`未在声明处设置`。
- `SpeedPlan.limiting_constraint: str`；默认：`未在声明处设置`。
- `SpeedPlan.constraint_caps_mps: Mapping[str, float]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `SpeedPlannerParameters`

源码位置：[car_control_C/speed_planner.py 第 19 行](../../../car_control_C/speed_planner.py#L19)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPlannerParameters.__post_init__`

源码位置：[car_control_C/speed_planner.py 第 24 行](../../../car_control_C/speed_planner.py#L24)。类型：`FunctionDef`。

```python
SpeedPlannerParameters.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPlan`

源码位置：[car_control_C/speed_planner.py 第 31 行](../../../car_control_C/speed_planner.py#L31)。类型：`ClassDef`。

Auditable result of fusing every longitudinal speed constraint.

### `SpeedPlan.to_dict`

源码位置：[car_control_C/speed_planner.py 第 38 行](../../../car_control_C/speed_planner.py#L38)。类型：`FunctionDef`。

```python
SpeedPlan.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPlanner`

源码位置：[car_control_C/speed_planner.py 第 46 行](../../../car_control_C/speed_planner.py#L46)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPlanner.__init__`

源码位置：[car_control_C/speed_planner.py 第 47 行](../../../car_control_C/speed_planner.py#L47)。类型：`FunctionDef`。

```python
SpeedPlanner.__init__(self, parameters: SpeedPlannerParameters | None=None, traffic_rules: TrafficRulePlanner | None=None, stop_controller: StopController | None=None, following_controller: FollowingController | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPlanner.plan`

源码位置：[car_control_C/speed_planner.py 第 58 行](../../../car_control_C/speed_planner.py#L58)。类型：`FunctionDef`。

```python
SpeedPlanner.plan(self, request: LongitudinalRequest, dt_s: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SpeedPlanner.reset`

源码位置：[car_control_C/speed_planner.py 第 104 行](../../../car_control_C/speed_planner.py#L104)。类型：`FunctionDef`。

```python
SpeedPlanner.reset(self) -> None
```

Forget target history at the start of an independent episode.

## 内部调用与异常路径

- `__post_init__` 调用：`finite`.
- `to_dict` 调用：`dict`.
- `__init__` 调用：`FollowingController`, `SpeedPlannerParameters`, `StopController`, `TrafficRulePlanner`.
- `plan` 调用：`MappingProxyType`, `SpeedPlan`, `TypeError`, `abs`, `finite`, `float`, `hard_caps.items`, `isinstance`, `math.isfinite`, `math.sqrt`, `max`, `min`, `self.following_controller.speed_cap_mps`, `self.stop_controller.speed_cap_mps`, `self.traffic_rules.speed_limit_mps`, `self.traffic_rules.stop_distance_m`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `plan`，第 60 行：`TypeError('request must be LongitudinalRequest')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_C/following_controller.py](../../../car_control_C/following_controller.py)
- [car_control_C/stop_controller.py](../../../car_control_C/stop_controller.py)
- [car_control_C/traffic_rules.py](../../../car_control_C/traffic_rules.py)
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

### `car_control_C/speed_planner.py`

来源 SHA256：`1b597b9f4017bd876494b2fc4d4e0eba59f192feafa1c80fc7ede336ef6b0fea`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `SpeedPlannerParameters.max_lateral_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.max_lateral_accel_mps2` |
| `SpeedPlannerParameters.command_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.command_accel_mps2` |
| `SpeedPlannerParameters.command_decel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.command_decel_mps2` |
| `SpeedPlan.safe_target_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `SpeedPlan.limiting_constraint` | `str` | `无声明默认；构造/赋值方提供` |
| `SpeedPlan.constraint_caps_mps` | `Mapping[str, float]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `SpeedPlanner.plan` / 60 | `not isinstance(request, LongitudinalRequest)` | `raise TypeError('request must be LongitudinalRequest')` |

### car_control_C/speed_planner.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 25 | `finite('max_lateral_accel_mps2', self.max_lateral_accel_mps2, positive=True)` |
| 26 | `finite('command_accel_mps2', self.command_accel_mps2, positive=True)` |
| 27 | `finite('command_decel_mps2', self.command_decel_mps2, positive=True)` |
| 61 | `finite('dt_s', dt_s, positive=True)` |
