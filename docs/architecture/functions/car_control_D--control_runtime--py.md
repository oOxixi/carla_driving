# control_runtime：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

D's unique final-control exit for canonical V1 pipeline objects.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `FinalControlFrame.command_id: str`；默认：`未在声明处设置`。
- `FinalControlFrame.final_control: ControlOutput`；默认：`未在声明处设置`。
- `FinalControlFrame.safety: SafetyDecision`；默认：`未在声明处设置`。
- `FinalControlFrame.arbitration_ms: float`；默认：`未在声明处设置`。
- `FinalControlFrame.feedback: Mapping[str, Any]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `FinalControlFrame`

源码位置：[car_control_D/control_runtime.py 第 18 行](../../../car_control_D/control_runtime.py#L18)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DControlRuntime`

源码位置：[car_control_D/control_runtime.py 第 26 行](../../../car_control_D/control_runtime.py#L26)。类型：`ClassDef`。

Validate high-level authority and expose the only final control value.

### `DControlRuntime.__init__`

源码位置：[car_control_D/control_runtime.py 第 29 行](../../../car_control_D/control_runtime.py#L29)。类型：`FunctionDef`。

```python
DControlRuntime.__init__(self, *, supervisor: SafetySupervisor | None=None, registry: InterfaceRegistry | None=None, lifecycle: ExecutionFeedbackTracker | None=None, clock_ns: Callable[[], int]=time.monotonic_ns) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DControlRuntime.apply`

源码位置：[car_control_D/control_runtime.py 第 45 行](../../../car_control_D/control_runtime.py#L45)。类型：`FunctionDef`。

```python
DControlRuntime.apply(self, control_command: Mapping[str, Any], perception_state: Mapping[str, Any], vehicle_state: Mapping[str, Any], planned_control: Any, *, now_ns: int | None=None) -> FinalControlFrame
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DControlRuntime.complete`

源码位置：[car_control_D/control_runtime.py 第 120 行](../../../car_control_D/control_runtime.py#L120)。类型：`FunctionDef`。

```python
DControlRuntime.complete(self, command_id: str, *, succeeded: bool, reason: str, now_ns: int | None=None) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DControlRuntime.metrics`

源码位置：[car_control_D/control_runtime.py 第 129 行](../../../car_control_D/control_runtime.py#L129)。类型：`FunctionDef`。

```python
DControlRuntime.metrics(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DControlRuntime._command_view`

源码位置：[car_control_D/control_runtime.py 第 154 行](../../../car_control_D/control_runtime.py#L154)。类型：`FunctionDef`。

```python
DControlRuntime._command_view(command: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__init__` 调用：`ExecutionFeedbackTracker`, `InterfaceRegistry`, `SafetySupervisor`.
- `apply` 调用：`FinalControlFrame`, `ValueError`, `control_command.get`, `decision.final_control.to_dict`, `decision.raw_control.to_dict`, `dict`, `isinstance`, `self._cadence_hz.append`, `self._clock_ns`, `self._command_view`, `self._latencies_ms.append`, `self.lifecycle.executing`, `self.lifecycle.received`, `self.lifecycle.safety_override`, `self.registry.validate`, `self.supervisor.arbitrate`, `str`, `time.perf_counter_ns`, `type`, `vehicle_view.update`, `watchdog.append`.
- `complete` 调用：`self.lifecycle.finish`.
- `metrics` 调用：`int`, `len`, `list`, `max`, `min`, `sorted`, `statistics.fmean`, `sum`.
- `_command_view` 调用：`command.get`, `command['target'].get`, `str`, `{'EMERGENCY_STOP': 'EMERGENCY_STOP', 'STOP': 'STOP', 'SET_SPEED': 'SET_SPEED', 'SLOW_DOWN': 'SLOW_DOWN', 'KEEP_LANE': 'KEEP_LANE'}.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `apply`，第 56 行：`ValueError('now_ns must be non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/execution_feedback.py](../../../car_control_D/execution_feedback.py)
- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [car_control_D/schemas.py](../../../car_control_D/schemas.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [tools/benchmark_control_runtime.py](../../../tools/benchmark_control_runtime.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/control_runtime.py`

来源 SHA256：`3dc4e6ebe9e1af1fafc62e61da1d35b2ac80dc9997e2c2549398a56e31d627f1`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `FinalControlFrame.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `FinalControlFrame.final_control` | `ControlOutput` | `无声明默认；构造/赋值方提供` |
| `FinalControlFrame.safety` | `SafetyDecision` | `无声明默认；构造/赋值方提供` |
| `FinalControlFrame.arbitration_ms` | `float` | `无声明默认；构造/赋值方提供` |
| `FinalControlFrame.feedback` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `DControlRuntime.apply` / 56 | `type(now) is not int or now < 0` | `raise ValueError('now_ns must be non-negative')` |
