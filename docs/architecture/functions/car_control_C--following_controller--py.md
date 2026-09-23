# following_controller：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/following_controller.py](../../../car_control_C/following_controller.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Time-gap following and local TTC risk estimation.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `FollowingParameters.standstill_gap_m: float`；默认：`DEFAULT_STRATEGY.safety_distance.standstill_gap_m`。
- `FollowingParameters.time_gap_s: float`；默认：`DEFAULT_STRATEGY.safety_distance.reaction_time_s`。
- `FollowingParameters.emergency_ttc_s: float`；默认：`DEFAULT_STRATEGY.common.emergency_ttc_s`。
- `FollowingParameters.comfortable_decel_mps2: float`；默认：`DEFAULT_STRATEGY.common.comfortable_decel_mps2`。

## 功能入口：输入、输出与实现说明

### `FollowingParameters`

源码位置：[car_control_C/following_controller.py 第 13 行](../../../car_control_C/following_controller.py#L13)。类型：`ClassDef`。

冻结的 SI 参数合同：静止间距（m）、时间间距和紧急 TTC（s）、舒适减速度（m/s²）；默认均来自统一策略配置。

### `FollowingParameters.__post_init__`

源码位置：[car_control_C/following_controller.py 第 19 行](../../../car_control_C/following_controller.py#L19)。类型：`FunctionDef`。

```python
FollowingParameters.__post_init__(self) -> None
```

要求静止间距有限且非负，其余三项有限且严格为正；不建立速度上限，也不修改输入。

### `FollowingController`

源码位置：[car_control_C/following_controller.py 第 26 行](../../../car_control_C/following_controller.py#L26)。类型：`ClassDef`。

无历史状态的时距跟车与局部 TTC 估计器。它产生期望间距、速度硬上限和 `RiskMetrics`，但不直接制动，也不替代 D 的最终仲裁。

### `FollowingController.__init__`

源码位置：[car_control_C/following_controller.py 第 27 行](../../../car_control_C/following_controller.py#L27)。类型：`FunctionDef`。

```python
FollowingController.__init__(self, parameters: FollowingParameters | None=None) -> None
```

保存调用方参数或构造默认 `FollowingParameters`；无传感器、线程、文件或 CARLA 副作用。

### `FollowingController.desired_gap_m`

源码位置：[car_control_C/following_controller.py 第 30 行](../../../car_control_C/following_controller.py#L30)。类型：`FunctionDef`。

```python
FollowingController.desired_gap_m(self, ego_speed_mps: float) -> float
```

校验非负自车速度后计算 `standstill_gap + time_gap*speed + sensor_base_margin + sensor_uncertainty_time*speed`。结果是规划间距，不是碰撞距离真值。

### `FollowingController.risk`

源码位置：[car_control_C/following_controller.py 第 38 行](../../../car_control_C/following_controller.py#L38)。类型：`FunctionDef`。

```python
FollowingController.risk(self, *, ego_speed_mps: float, lead_distance_m: float | None, closing_speed_mps: float | None) -> RiskMetrics
```

距离或接近速度任一缺失时返回 `ttc=None/emergency=False`；接近速度小于等于零同样不算 TTC。只有正接近速度才用 `distance/closing_speed`，并按 `<= emergency_ttc_s` 请求局部紧急制动。

### `FollowingController.speed_cap_mps`

源码位置：[car_control_C/following_controller.py 第 52 行](../../../car_control_C/following_controller.py#L52)。类型：`FunctionDef`。

```python
FollowingController.speed_cap_mps(self, *, ego_speed_mps: float, lead_distance_m: float | None, closing_speed_mps: float | None) -> float | None
```

测量缺失返回 `None`，否则以 `lead_speed=max(0, ego-closing)` 和 `sqrt(2*a*max(0,gap-desired))` 计算非负硬上限。负接近速度可提高估计前车速度，但返回值仍不低于零。

## 内部调用与异常路径

- `__post_init__` 调用：`finite`.
- `__init__` 调用：`FollowingParameters`.
- `desired_gap_m` 调用：`finite`.
- `risk` 调用：`RiskMetrics`, `finite`, `self.desired_gap_m`.
- `speed_cap_mps` 调用：`finite`, `max`, `self.desired_gap_m`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_C/validation.py](../../../car_control_C/validation.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [car_control_C/fuzzy_command_policy.py](../../../car_control_C/fuzzy_command_policy.py)
- [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py)
- [car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/following_controller.py`

来源 SHA256：`fc9925c97c9ed262479bd3f2c9314e5c1131ca9c93524b366b38f474e38fe447`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `FollowingParameters.standstill_gap_m` | `float` | `DEFAULT_STRATEGY.safety_distance.standstill_gap_m` |
| `FollowingParameters.time_gap_s` | `float` | `DEFAULT_STRATEGY.safety_distance.reaction_time_s` |
| `FollowingParameters.emergency_ttc_s` | `float` | `DEFAULT_STRATEGY.common.emergency_ttc_s` |
| `FollowingParameters.comfortable_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.comfortable_decel_mps2` |

### car_control_C/following_controller.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 20 | `finite('standstill_gap_m', self.standstill_gap_m, minimum=0.0)` |
| 21 | `finite('time_gap_s', self.time_gap_s, positive=True)` |
| 22 | `finite('emergency_ttc_s', self.emergency_ttc_s, positive=True)` |
| 23 | `finite('comfortable_decel_mps2', self.comfortable_decel_mps2, positive=True)` |
| 31 | `finite('ego_speed_mps', ego_speed_mps, minimum=0.0)` |
| 40 | `finite('ego_speed_mps', ego_speed_mps, minimum=0.0)` |
| 44 | `finite('lead_distance_m', lead_distance_m, minimum=0.0)` |
| 45 | `finite('closing_speed_mps', closing_speed_mps)` |
| 54 | `finite('ego_speed_mps', ego_speed_mps, minimum=0.0)` |
| 57 | `finite('lead_distance_m', lead_distance_m, minimum=0.0)` |
| 58 | `finite('closing_speed_mps', closing_speed_mps)` |
