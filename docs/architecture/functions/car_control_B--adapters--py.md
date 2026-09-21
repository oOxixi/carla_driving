# adapters：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[car_control_B/adapters.py](../../../car_control_B/adapters.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Adapters that accept dicts or A-side dataclasses.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_get`

源码位置：[car_control_B/adapters.py 第 11 行](../../../car_control_B/adapters.py#L11)。类型：`FunctionDef`。

```python
_get(obj: Any, name: str, default: Any=None) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `adapt_vehicle_pose`

源码位置：[car_control_B/adapters.py 第 17 行](../../../car_control_B/adapters.py#L17)。类型：`FunctionDef`。

```python
adapt_vehicle_pose(vehicle_state: Any) -> VehiclePose
```

Convert A RuntimeVehicleState/dict into B VehiclePose.

Supports both yaw_rad and yaw_deg. A handoff currently exposes yaw_deg, while
some internal tests may use yaw_rad.

### `adapt_route_reference`

源码位置：[car_control_B/adapters.py 第 42 行](../../../car_control_B/adapters.py#L42)。类型：`FunctionDef`。

```python
adapt_route_reference(reference: Any) -> RouteReference
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_get` 调用：`getattr`, `isinstance`, `obj.get`.
- `adapt_vehicle_pose` 调用：`ValueError`, `VehiclePose`, `_get`, `float`, `math.radians`.
- `adapt_route_reference` 调用：`RouteReference`, `ValueError`, `_get`, `dict`, `float`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `adapt_route_reference`，第 47 行：`ValueError('reference must provide points_xy_m')`。
- `adapt_vehicle_pose`，第 30 行：`ValueError('vehicle_state must provide yaw_rad or yaw_deg')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_B/schemas.py](../../../car_control_B/schemas.py)

静态 import 消费者（含测试）：

- [car_control_B/lateral_controller_base.py](../../../car_control_B/lateral_controller_base.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/adapters.py`

来源 SHA256：`1fc2bffe4e8cc9f84c8941977f1c9bfe0e8d3285d079288237a7412cf454ec5b`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `adapt_vehicle_pose` / 30 | `yaw_rad is None AND yaw_deg is None` | `raise ValueError('vehicle_state must provide yaw_rad or yaw_deg')` |
| `adapt_route_reference` / 47 | `points is None` | `raise ValueError('reference must provide points_xy_m')` |
