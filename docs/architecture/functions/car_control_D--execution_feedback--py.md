# execution_feedback：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/execution_feedback.py](../../../car_control_D/execution_feedback.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

D-owned command lifecycle with schema-validated terminal feedback.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `_Lifecycle.status: str`；默认：`未在声明处设置`。
- `_Lifecycle.received_at_ns: int`；默认：`未在声明处设置`。
- `_Lifecycle.t_action_apply_ns: int | None`；默认：`None`。
- `_Lifecycle.terminal_feedback: dict[str, Any] | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

### `_Lifecycle`

源码位置：[car_control_D/execution_feedback.py 第 19 行](../../../car_control_D/execution_feedback.py#L19)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker`

源码位置：[car_control_D/execution_feedback.py 第 26 行](../../../car_control_D/execution_feedback.py#L26)。类型：`ClassDef`。

Guarantee deterministic transitions and at most one terminal per ID.

### `ExecutionFeedbackTracker.__init__`

源码位置：[car_control_D/execution_feedback.py 第 29 行](../../../car_control_D/execution_feedback.py#L29)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.__init__(self, *, registry: InterfaceRegistry | None=None, clock_ns: Callable[[], int]=time.monotonic_ns) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker.received`

源码位置：[car_control_D/execution_feedback.py 第 40 行](../../../car_control_D/execution_feedback.py#L40)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.received(self, command_id: str, action_summary: str, *, emitted_at_ns: int | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker.executing`

源码位置：[car_control_D/execution_feedback.py 第 53 行](../../../car_control_D/execution_feedback.py#L53)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.executing(self, command_id: str, action_summary: str, *, t_action_apply_ns: int | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker.finish`

源码位置：[car_control_D/execution_feedback.py 第 69 行](../../../car_control_D/execution_feedback.py#L69)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.finish(self, command_id: str, status: str, action_summary: str, terminal_reason: str, *, emitted_at_ns: int | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker.safety_override`

源码位置：[car_control_D/execution_feedback.py 第 94 行](../../../car_control_D/execution_feedback.py#L94)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.safety_override(self, command_id: str, *, reason_code: str, raw_control: Mapping[str, Any], final_control: Mapping[str, Any], action_summary: str='D safety override applied', emitted_at_ns: int | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker.fail_unfinished`

源码位置：[car_control_D/execution_feedback.py 第 131 行](../../../car_control_D/execution_feedback.py#L131)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.fail_unfinished(self, *, reason: str, emitted_at_ns: int | None=None) -> tuple[dict[str, Any], ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker.events`

源码位置：[car_control_D/execution_feedback.py 第 140 行](../../../car_control_D/execution_feedback.py#L140)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.events(self) -> tuple[Mapping[str, Any], ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker.unfinished_command_ids`

源码位置：[car_control_D/execution_feedback.py 第 144 行](../../../car_control_D/execution_feedback.py#L144)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker.unfinished_command_ids(self) -> tuple[str, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker._emit`

源码位置：[car_control_D/execution_feedback.py 第 150 行](../../../car_control_D/execution_feedback.py#L150)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker._emit(self, command_id: str, status: str, summary: str, now: int, applied: int | None, latency: float | None, terminal_reason: str | None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker._require_active`

源码位置：[car_control_D/execution_feedback.py 第 172 行](../../../car_control_D/execution_feedback.py#L172)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker._require_active(self, command_id: str) -> _Lifecycle
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker._identity`

源码位置：[car_control_D/execution_feedback.py 第 180 行](../../../car_control_D/execution_feedback.py#L180)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker._identity(command_id: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker._control`

源码位置：[car_control_D/execution_feedback.py 第 185 行](../../../car_control_D/execution_feedback.py#L185)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker._control(control: Mapping[str, Any], *, allow_overlap: bool) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ExecutionFeedbackTracker._now`

源码位置：[car_control_D/execution_feedback.py 第 191 行](../../../car_control_D/execution_feedback.py#L191)。类型：`FunctionDef`。

```python
ExecutionFeedbackTracker._now(self, value: int | None) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__init__` 调用：`InterfaceRegistry`.
- `received` 调用：`_Lifecycle`, `dict`, `self._commands.get`, `self._emit`, `self._events.append`, `self._identity`, `self._now`.
- `executing` 调用：`ValueError`, `dict`, `self._emit`, `self._events.append`, `self._now`, `self._require_active`.
- `finish` 调用：`ValueError`, `dict`, `self._emit`, `self._events.append`, `self._now`, `self._require_active`.
- `safety_override` 调用：`dict`, `self._control`, `self._events.append`, `self._now`, `self._require_active`, `self.registry.validate`.
- `fail_unfinished` 调用：`results.append`, `self._commands.items`, `self._now`, `self.finish`, `tuple`.
- `events` 调用：`dict`, `tuple`.
- `unfinished_command_ids` 调用：`self._commands.items`, `sorted`, `tuple`.
- `_emit` 调用：`self.registry.validate`.
- `_require_active` 调用：`KeyError`, `self._identity`.
- `_identity` 调用：`ValueError`, `type`.
- `_control` 调用：`ValueError`, `float`.
- `_now` 调用：`ValueError`, `self._clock_ns`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_control`，第 188 行：`ValueError('feedback control cannot contain throttle/brake overlap')`。
- `_identity`，第 182 行：`ValueError('command_id must be non-empty')`。
- `_now`，第 194 行：`ValueError('timestamp must be a non-negative integer')`。
- `_require_active`，第 177 行：`KeyError(f'command has not been received: {command_id}')`。
- `executing`，第 59 行：`ValueError('action timestamp precedes command receipt')`。
- `finish`，第 79 行：`ValueError('finish status must be a non-safety terminal status')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/execution_feedback.py`

来源 SHA256：`fe2f8d50c26cf1c57f35d5e5521018764f93b93a39a86252e0e64aead0c63f75`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `_Lifecycle.status` | `str` | `无声明默认；构造/赋值方提供` |
| `_Lifecycle.received_at_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `_Lifecycle.t_action_apply_ns` | `int &#124; None` | `None` |
| `_Lifecycle.terminal_feedback` | `dict[str, Any] &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `ExecutionFeedbackTracker.executing` / 59 | `now < lifecycle.received_at_ns` | `raise ValueError('action timestamp precedes command receipt')` |
| `ExecutionFeedbackTracker.finish` / 79 | `status not in TERMINAL - {'SAFETY_OVERRIDE'}` | `raise ValueError('finish status must be a non-safety terminal status')` |
| `ExecutionFeedbackTracker._require_active` / 177 | `except KeyError` | `raise KeyError(f'command has not been received: {command_id}') from error` |
| `ExecutionFeedbackTracker._identity` / 182 | `type(command_id) is not str or not command_id` | `raise ValueError('command_id must be non-empty')` |
| `ExecutionFeedbackTracker._control` / 188 | `not allow_overlap and values['throttle'] > 0.0 and (values['brake'] > 0.0)` | `raise ValueError('feedback control cannot contain throttle/brake overlap')` |
| `ExecutionFeedbackTracker._now` / 194 | `type(result) is not int or result < 0` | `raise ValueError('timestamp must be a non-negative integer')` |
