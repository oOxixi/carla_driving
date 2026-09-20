# sensor_adapter：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/sensor_adapter.py](../../../car_control_C/sensor_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

C-role sensor timestamp and extrinsics audit helpers.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `SensorFrameStamp.frame_id: int`；默认：`未在声明处设置`。
- `SensorFrameStamp.timestamp_s: float`；默认：`未在声明处设置`。
- `SensorFrameStamp.source: str`；默认：`'CARLA_SENSOR'`。
- `SensorAudit.frame_id: int`；默认：`未在声明处设置`。
- `SensorAudit.sim_time_s: float`；默认：`未在声明处设置`。
- `SensorAudit.stamps: Mapping[str, SensorFrameStamp]`；默认：`未在声明处设置`。
- `SensorAudit.extrinsics: Mapping[str, Mapping[str, float]]`；默认：`未在声明处设置`。
- `SensorAudit.max_frame_delta: int`；默认：`未在声明处设置`。
- `SensorAudit.max_time_delta_s: float`；默认：`未在声明处设置`。
- `SensorAudit.alignment_ok: bool`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `SensorFrameStamp`

源码位置：[car_control_C/sensor_adapter.py 第 16 行](../../../car_control_C/sensor_adapter.py#L16)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFrameStamp.__post_init__`

源码位置：[car_control_C/sensor_adapter.py 第 21 行](../../../car_control_C/sensor_adapter.py#L21)。类型：`FunctionDef`。

```python
SensorFrameStamp.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFrameStamp.to_dict`

源码位置：[car_control_C/sensor_adapter.py 第 29 行](../../../car_control_C/sensor_adapter.py#L29)。类型：`FunctionDef`。

```python
SensorFrameStamp.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorAudit`

源码位置：[car_control_C/sensor_adapter.py 第 38 行](../../../car_control_C/sensor_adapter.py#L38)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorAudit.to_dict`

源码位置：[car_control_C/sensor_adapter.py 第 47 行](../../../car_control_C/sensor_adapter.py#L47)。类型：`FunctionDef`。

```python
SensorAudit.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_sensor_audit`

源码位置：[car_control_C/sensor_adapter.py 第 63 行](../../../car_control_C/sensor_adapter.py#L63)。类型：`FunctionDef`。

```python
build_sensor_audit(*, frame_id: int, sim_time_s: float, stamps: Mapping[str, SensorFrameStamp], extrinsics: Mapping[str, Mapping[str, float]] | None=None, max_allowed_frame_delta: int=0, max_allowed_time_delta_s: float=0.05) -> SensorAudit
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `build_sensor_audit` 调用：`SensorAudit`, `ValueError`, `abs`, `dict`, `float`, `max`, `stamps.values`, `type`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `str`, `str(self.source).strip`, `type`.
- `to_dict` 调用：`float`, `round`, `self.extrinsics.items`, `self.stamps.items`, `stamp.to_dict`, `values.items`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 23 行：`ValueError('frame_id must be a non-negative integer')`。
- `__post_init__`，第 25 行：`TypeError('timestamp_s must be numeric')`。
- `__post_init__`，第 27 行：`ValueError('source must be non-empty')`。
- `build_sensor_audit`，第 73 行：`ValueError('frame_id must be a non-negative integer')`。
- `build_sensor_audit`，第 75 行：`ValueError('at least one sensor stamp is required')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_C/tests/test_c_deliverables.py](../../../car_control_C/tests/test_c_deliverables.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/sensor_adapter.py`

来源 SHA256：`6fdab658a360c8a31e0a51fad34046a221b3058405cdafc966a8ffc85fcd3b6b`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `SensorFrameStamp.frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `SensorFrameStamp.timestamp_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorFrameStamp.source` | `str` | `'CARLA_SENSOR'` |
| `SensorAudit.frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `SensorAudit.sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorAudit.stamps` | `Mapping[str, SensorFrameStamp]` | `无声明默认；构造/赋值方提供` |
| `SensorAudit.extrinsics` | `Mapping[str, Mapping[str, float]]` | `无声明默认；构造/赋值方提供` |
| `SensorAudit.max_frame_delta` | `int` | `无声明默认；构造/赋值方提供` |
| `SensorAudit.max_time_delta_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorAudit.alignment_ok` | `bool` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `SensorFrameStamp.__post_init__` / 23 | `type(self.frame_id) is not int or self.frame_id < 0` | `raise ValueError('frame_id must be a non-negative integer')` |
| `SensorFrameStamp.__post_init__` / 25 | `type(self.timestamp_s) not in (int, float)` | `raise TypeError('timestamp_s must be numeric')` |
| `SensorFrameStamp.__post_init__` / 27 | `not str(self.source).strip()` | `raise ValueError('source must be non-empty')` |
| `build_sensor_audit` / 73 | `type(frame_id) is not int or frame_id < 0` | `raise ValueError('frame_id must be a non-negative integer')` |
| `build_sensor_audit` / 75 | `not stamps` | `raise ValueError('at least one sensor stamp is required')` |
