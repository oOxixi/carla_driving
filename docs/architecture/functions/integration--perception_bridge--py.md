# perception_bridge：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[integration/perception_bridge.py](../../../integration/perception_bridge.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Conversions from frame-aligned scene facts to A/C/D inputs.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `longitudinal_request`

源码位置：[integration/perception_bridge.py 第 9 行](../../../integration/perception_bridge.py#L9)。类型：`FunctionDef`。

```python
longitudinal_request(vehicle: RuntimeVehicleState, scene: PerceptionFrame, *, requested_speed_mps: float, path_curvature_per_m: float) -> LongitudinalRequest
```

把同帧 `RuntimeVehicleState` 和 `PerceptionFrame` 转成 C 的 `LongitudinalRequest`。帧号或仿真时间不完全相等会拒绝；只有前车速度而无距离也拒绝。有距离但无速度时按前方物体静止，令 closing speed 等于自车速度；两者都有时用自车速度减前车速度，随后连同灯态、停止线、限速和曲率交给 C。

### `safety_vehicle_state`

源码位置：[integration/perception_bridge.py 第 31 行](../../../integration/perception_bridge.py#L31)。类型：`FunctionDef`。

```python
safety_vehicle_state(vehicle: RuntimeVehicleState, scene: PerceptionFrame, *, road_curvature_per_m: float=0.0, front_actor_type: str | None=None, sensor_margin_scale: float=1.0) -> dict[str, object]
```

D needs a numeric lane id, unlike A's arbitrary string identifier.

## 内部调用与异常路径

- `longitudinal_request` 调用：`LongitudinalRequest`, `SignalState`, `TrafficConstraint`, `ValueError`.
- `safety_vehicle_state` 调用：`abs`, `float`, `int`, `min`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `longitudinal_request`，第 12 行：`ValueError('scene and vehicle must be from the same CARLA frame')`。
- `longitudinal_request`，第 15 行：`ValueError('lead_speed_mps requires lead_distance_m')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [integration/contracts.py](../../../integration/contracts.py)

静态 import 消费者（含测试）：

- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [integration/tests/test_perception_bridge.py](../../../integration/tests/test_perception_bridge.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/perception_bridge.py`

来源 SHA256：`71f6faad1dbe0b64674fe245b865c821489c909f0195eaac35432cca21742cef`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `longitudinal_request` / 12 | `scene.frame != vehicle.frame or scene.sim_time_s != vehicle.sim_time_s` | `raise ValueError('scene and vehicle must be from the same CARLA frame')` |
| `longitudinal_request` / 15 | `scene.lead_distance_m is None and scene.lead_speed_mps is not None` | `raise ValueError('lead_speed_mps requires lead_distance_m')` |
