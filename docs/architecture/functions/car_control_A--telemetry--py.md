# telemetry：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/telemetry.py](../../../car_control_A/telemetry.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Monotonic, replay-friendly command latency tracing.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `LatencyTrace`

源码位置：[car_control_A/telemetry.py 第 11 行](../../../car_control_A/telemetry.py#L11)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyTrace.__init__`

源码位置：[car_control_A/telemetry.py 第 12 行](../../../car_control_A/telemetry.py#L12)。类型：`FunctionDef`。

```python
LatencyTrace.__init__(self, command_id: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyTrace.mark`

源码位置：[car_control_A/telemetry.py 第 18 行](../../../car_control_A/telemetry.py#L18)。类型：`FunctionDef`。

```python
LatencyTrace.mark(self, stage: str, *, timestamp_ns: int | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyTrace.segment_ms`

源码位置：[car_control_A/telemetry.py 第 30 行](../../../car_control_A/telemetry.py#L30)。类型：`FunctionDef`。

```python
LatencyTrace.segment_ms(self, start_stage: str, end_stage: str) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyTrace.end_to_end_ms`

源码位置：[car_control_A/telemetry.py 第 34 行](../../../car_control_A/telemetry.py#L34)。类型：`FunctionDef`。

```python
LatencyTrace.end_to_end_ms(self) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyTrace.to_dict`

源码位置：[car_control_A/telemetry.py 第 40 行](../../../car_control_A/telemetry.py#L40)。类型：`FunctionDef`。

```python
LatencyTrace.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyTrace.append_jsonl`

源码位置：[car_control_A/telemetry.py 第 43 行](../../../car_control_A/telemetry.py#L43)。类型：`FunctionDef`。

```python
LatencyTrace.append_jsonl(self, path: str | Path, *, extra: Mapping[str, object] | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__init__` 调用：`ValueError`, `type`.
- `mark` 调用：`ValueError`, `max`, `self._marks.values`, `time.monotonic_ns`, `type`.
- `end_to_end_ms` 调用：`len`, `self._marks.values`, `tuple`.
- `to_dict` 调用：`dict`.
- `append_jsonl` 调用：`Path`, `ValueError`, `handle.write`, `json.dumps`, `record.update`, `self.to_dict`, `set`, `set(record).intersection`, `sorted`, `target.open`, `target.parent.mkdir`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 14 行：`ValueError('command_id must be a non-empty string')`。
- `append_jsonl`，第 48 行：`ValueError(f'extra may not overwrite trace fields: {sorted(overlap)}')`。
- `mark`，第 20 行：`ValueError('stage must be a non-empty string')`。
- `mark`，第 22 行：`ValueError('stage already marked')`。
- `mark`，第 25 行：`ValueError('timestamp_ns must be a non-negative integer')`。
- `mark`，第 27 行：`ValueError('timestamps must be monotonic')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_A/tests/test_telemetry.py](../../../car_control_A/tests/test_telemetry.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_A/telemetry.py`

来源 SHA256：`a3f50b71343baa631bdc269b3aca4a57b38c6eccbc37b31084f2f08c72bf1951`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `LatencyTrace.__init__` / 14 | `type(command_id) is not str or not command_id` | `raise ValueError('command_id must be a non-empty string')` |
| `LatencyTrace.mark` / 20 | `type(stage) is not str or not stage` | `raise ValueError('stage must be a non-empty string')` |
| `LatencyTrace.mark` / 22 | `stage in self._marks` | `raise ValueError('stage already marked')` |
| `LatencyTrace.mark` / 25 | `type(stamp) is not int or stamp < 0` | `raise ValueError('timestamp_ns must be a non-negative integer')` |
| `LatencyTrace.mark` / 27 | `self._marks and stamp < max(self._marks.values())` | `raise ValueError('timestamps must be monotonic')` |
| `LatencyTrace.append_jsonl` / 48 | `extra is not None AND overlap` | `raise ValueError(f'extra may not overwrite trace fields: {sorted(overlap)}')` |
