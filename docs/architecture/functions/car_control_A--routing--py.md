# routing：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/routing.py](../../../car_control_A/routing.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Route reference boundary owned by A; no lateral control algorithm lives here.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RouteReference.points_xy_m: tuple[tuple[float, float], ...]`；默认：`未在声明处设置`。
- `RouteReference.curvature_per_m: float`；默认：`未在声明处设置`。
- `RouteReference.target_speed_mps: float`；默认：`未在声明处设置`。
- `RouteReference.route_id: str | None`；默认：`None`。
- `RouteReference.metadata: dict[str, Any]`；默认：`field(default_factory=dict)`。

## 功能入口：输入、输出与实现说明

<a id="fn-routereference"></a>

### `RouteReference`

源码位置：[car_control_A/routing.py 第 10 行](../../../car_control_A/routing.py#L10)。类型：`ClassDef`。

A到B的路线容器：points_xy_m点列、curvature_per_m有符号曲率、target_speed_mps速度、可空route_id、独立默认空metadata字典。冻结dataclass并不深冻结metadata，且不自带CARLA坐标转换或轨迹生成算法。

<a id="fn-routereference---post-init--"></a>

### `RouteReference.__post_init__`

源码位置：[car_control_A/routing.py 第 17 行](../../../car_control_A/routing.py#L17)。类型：`FunctionDef`。

```python
RouteReference.__post_init__(self) -> None
```

仅检查points长度>=2及target_speed_mps不小于0；不逐点校验二维/数值/有限性，不限制曲率或验证route_id/metadata。NaN速度可绕过负值比较，不能据构造成功声称路线通过完整几何校验。

<a id="fn-lateralcontroller"></a>

### `LateralController`

源码位置：[car_control_A/routing.py 第 25 行](../../../car_control_A/routing.py#L25)。类型：`ClassDef`。

runtime_checkable Protocol，仅声明steer(reference)->float接口。运行时协议匹配检查成员存在，不验证返回[-1,1]或算法安全；归一化范围与最终D约束由实现/集成消费者负责。

<a id="fn-lateralcontroller-steer"></a>

### `LateralController.steer`

源码位置：[car_control_A/routing.py 第 26 行](../../../car_control_A/routing.py#L26)。类型：`FunctionDef`。

```python
LateralController.steer(self, reference: RouteReference) -> float
```

Return only a bounded steering command in [-1, 1].

Protocol只声明reference入参和float返回，无默认算法/范围夹取；实现方应返回[-1,1]，调用方仍应验证。RouteReference不携带当前车辆状态，具体B适配器可能通过自身状态获取。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `len`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 19 行：`ValueError('route needs at least two points')`。
- `__post_init__`，第 21 行：`ValueError('target_speed_mps must be non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_A/tests/test_routing.py](../../../car_control_A/tests/test_routing.py)
- [car_control_B/tests/test_pure_pursuit.py](../../../car_control_B/tests/test_pure_pursuit.py)
- [car_control_D/benchmark.py](../../../car_control_D/benchmark.py)
- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/demo_offline.py](../../../integration/demo_offline.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/planning_stage.py](../../../integration/planning_stage.py)
- [integration/route_manager.py](../../../integration/route_manager.py)
- [integration/route_planner.py](../../../integration/route_planner.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [integration/tests/test_carla_perception.py](../../../integration/tests/test_carla_perception.py)
- [integration/tests/test_runtime_loop.py](../../../integration/tests/test_runtime_loop.py)
- [integration/tests/test_runtime_stages.py](../../../integration/tests/test_runtime_stages.py)
- [tools/validate_c_role.py](../../../tools/validate_c_role.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-car-control-a-routing-py"></a>

### `car_control_A/routing.py`

来源 SHA256：`800816447deb3e014076fd17c5649ea88bd8a0b96ad405240d2adabbbd0cc2c0`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RouteReference.points_xy_m` | `tuple[tuple[float, float], ...]` | `无声明默认；构造/赋值方提供` |
| `RouteReference.curvature_per_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteReference.target_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteReference.route_id` | `str &#124; None` | `None` |
| `RouteReference.metadata` | `dict[str, Any]` | `field(default_factory=dict)` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `RouteReference.__post_init__` / 19 | `len(self.points_xy_m) < 2` | `raise ValueError('route needs at least two points')` |
| `RouteReference.__post_init__` / 21 | `self.target_speed_mps < 0.0` | `raise ValueError('target_speed_mps must be non-negative')` |
