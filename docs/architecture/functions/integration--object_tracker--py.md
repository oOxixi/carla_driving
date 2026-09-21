# object_tracker：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[integration/object_tracker.py](../../../integration/object_tracker.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Sensor-only temporal IDs for detected road users.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `_Track.detection: DetectedObject`；默认：`未在声明处设置`。
- `_Track.last_frame: int`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_center`

源码位置：[integration/object_tracker.py 第 10 行](../../../integration/object_tracker.py#L10)。类型：`FunctionDef`。

```python
_center(detection: DetectedObject) -> tuple[float, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_Track`

源码位置：[integration/object_tracker.py 第 16 行](../../../integration/object_tracker.py#L16)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorObjectTracker`

源码位置：[integration/object_tracker.py 第 21 行](../../../integration/object_tracker.py#L21)。类型：`ClassDef`。

Greedy class/range/image association with opaque stable IDs.

### `SensorObjectTracker.__init__`

源码位置：[integration/object_tracker.py 第 24 行](../../../integration/object_tracker.py#L24)。类型：`FunctionDef`。

```python
SensorObjectTracker.__init__(self, *, maximum_frame_gap: int=5, maximum_center_shift: float=0.25, minimum_range_gate_m: float=3.0) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorObjectTracker.update`

源码位置：[integration/object_tracker.py 第 39 行](../../../integration/object_tracker.py#L39)。类型：`FunctionDef`。

```python
SensorObjectTracker.update(self, frame: int, detections: Sequence[DetectedObject]) -> tuple[DetectedObject, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorObjectTracker._best_match`

源码位置：[integration/object_tracker.py 第 60 行](../../../integration/object_tracker.py#L60)。类型：`FunctionDef`。

```python
SensorObjectTracker._best_match(self, detection: DetectedObject, available: set[str]) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__init__` 调用：`ValueError`, `float`, `int`.
- `update` 调用：`_Track`, `available.discard`, `int`, `output.append`, `replace`, `self._best_match`, `self._tracks.items`, `set`, `tuple`.
- `_best_match` 调用：`_center`, `abs`, `candidates.append`, `detection.class_name.lower`, `max`, `min`, `previous.class_name.lower`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 32 行：`ValueError('maximum_frame_gap must be positive')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/contracts.py](../../../integration/contracts.py)

静态 import 消费者（含测试）：

- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/tests/test_object_tracker.py](../../../integration/tests/test_object_tracker.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/object_tracker.py`

来源 SHA256：`a5b699aac863dc833a56e0c71bcbfd768600f4356cd8692a052f769bef0db09f`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `_Track.detection` | `DetectedObject` | `无声明默认；构造/赋值方提供` |
| `_Track.last_frame` | `int` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `SensorObjectTracker.__init__` / 32 | `maximum_frame_gap < 1` | `raise ValueError('maximum_frame_gap must be positive')` |
