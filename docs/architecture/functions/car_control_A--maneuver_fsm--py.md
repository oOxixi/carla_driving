# maneuver_fsm：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/maneuver_fsm.py](../../../car_control_A/maneuver_fsm.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Deterministic execution state machine for compiled ManeuverPlan V2 steps.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ManeuverEvent.event_type: str`；默认：`未在声明处设置`。
- `ManeuverEvent.command_id: str`；默认：`未在声明处设置`。
- `ManeuverEvent.plan_id: str`；默认：`未在声明处设置`。
- `ManeuverEvent.step_id: str | None`；默认：`未在声明处设置`。
- `ManeuverEvent.state: str`；默认：`未在声明处设置`。
- `ManeuverEvent.reason_code: str`；默认：`未在声明处设置`。
- `ManeuverEvent.now_s: float`；默认：`未在声明处设置`。
- `ManeuverUpdate.state: str`；默认：`未在声明处设置`。
- `ManeuverUpdate.current_step: CompiledPlanStep | None`；默认：`未在声明处设置`。
- `ManeuverUpdate.events: tuple[ManeuverEvent, ...]`；默认：`未在声明处设置`。
- `ManeuverUpdate.safe_behavior: str | None`；默认：`未在声明处设置`。
- `ManeuverUpdate.terminal: bool`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `ManeuverEvent`

源码位置：[car_control_A/maneuver_fsm.py 第 35 行](../../../car_control_A/maneuver_fsm.py#L35)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverUpdate`

源码位置：[car_control_A/maneuver_fsm.py 第 46 行](../../../car_control_A/maneuver_fsm.py#L46)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM`

源码位置：[car_control_A/maneuver_fsm.py 第 54 行](../../../car_control_A/maneuver_fsm.py#L54)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM.__init__`

源码位置：[car_control_A/maneuver_fsm.py 第 55 行](../../../car_control_A/maneuver_fsm.py#L55)。类型：`FunctionDef`。

```python
ManeuverFSM.__init__(self, *, replan_cooldown_s: float=2.0, max_replans_per_command: int=2) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM.current_step`

源码位置：[car_control_A/maneuver_fsm.py 第 78 行](../../../car_control_A/maneuver_fsm.py#L78)。类型：`FunctionDef`。

```python
ManeuverFSM.current_step(self) -> CompiledPlanStep | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM.replan_count`

源码位置：[car_control_A/maneuver_fsm.py 第 84 行](../../../car_control_A/maneuver_fsm.py#L84)。类型：`FunctionDef`。

```python
ManeuverFSM.replan_count(self) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM.start`

源码位置：[car_control_A/maneuver_fsm.py 第 87 行](../../../car_control_A/maneuver_fsm.py#L87)。类型：`FunctionDef`。

```python
ManeuverFSM.start(self, plan: CompiledManeuverPlan, *, now_s: float) -> ManeuverUpdate
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM.update`

源码位置：[car_control_A/maneuver_fsm.py 第 107 行](../../../car_control_A/maneuver_fsm.py#L107)。类型：`FunctionDef`。

```python
ManeuverFSM.update(self, snapshot: Mapping[str, Any], *, now_s: float) -> ManeuverUpdate
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM.request_replan`

源码位置：[car_control_A/maneuver_fsm.py 第 240 行](../../../car_control_A/maneuver_fsm.py#L240)。类型：`FunctionDef`。

```python
ManeuverFSM.request_replan(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM.fail`

源码位置：[car_control_A/maneuver_fsm.py 第 263 行](../../../car_control_A/maneuver_fsm.py#L263)。类型：`FunctionDef`。

```python
ManeuverFSM.fail(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM._step_failure`

源码位置：[car_control_A/maneuver_fsm.py 第 266 行](../../../car_control_A/maneuver_fsm.py#L266)。类型：`FunctionDef`。

```python
ManeuverFSM._step_failure(self, step: CompiledPlanStep, reason: str, now: float) -> ManeuverUpdate
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM._finish`

源码位置：[car_control_A/maneuver_fsm.py 第 276 行](../../../car_control_A/maneuver_fsm.py#L276)。类型：`FunctionDef`。

```python
ManeuverFSM._finish(self, state: str, reason: str, now: float, *, safe_behavior: str | None=None, events: list[ManeuverEvent] | None=None) -> ManeuverUpdate
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM._replan_reason`

源码位置：[car_control_A/maneuver_fsm.py 第 294 行](../../../car_control_A/maneuver_fsm.py#L294)。类型：`FunctionDef`。

```python
ManeuverFSM._replan_reason(self, snapshot: Mapping[str, Any]) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM._event`

源码位置：[car_control_A/maneuver_fsm.py 第 311 行](../../../car_control_A/maneuver_fsm.py#L311)。类型：`FunctionDef`。

```python
ManeuverFSM._event(self, event_type: str, now: float, reason: str, *, state: str | None=None) -> ManeuverEvent
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM._update`

源码位置：[car_control_A/maneuver_fsm.py 第 326 行](../../../car_control_A/maneuver_fsm.py#L326)。类型：`FunctionDef`。

```python
ManeuverFSM._update(self, *, events: list[ManeuverEvent] | None=None, safe_behavior: str | None=None) -> ManeuverUpdate
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ManeuverFSM._step_state`

源码位置：[car_control_A/maneuver_fsm.py 第 341 行](../../../car_control_A/maneuver_fsm.py#L341)。类型：`FunctionDef`。

```python
ManeuverFSM._step_state(step: CompiledPlanStep | None) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_time`

源码位置：[car_control_A/maneuver_fsm.py 第 347 行](../../../car_control_A/maneuver_fsm.py#L347)。类型：`FunctionDef`。

```python
_time(value: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_precondition_satisfied`

源码位置：[car_control_A/maneuver_fsm.py 第 353 行](../../../car_control_A/maneuver_fsm.py#L353)。类型：`FunctionDef`。

```python
_precondition_satisfied(condition: str, snapshot: Mapping[str, Any]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_completion_satisfied`

源码位置：[car_control_A/maneuver_fsm.py 第 374 行](../../../car_control_A/maneuver_fsm.py#L374)。类型：`FunctionDef`。

```python
_completion_satisfied(completion: Mapping[str, Any], snapshot: Mapping[str, Any]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_time` 调用：`ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `_precondition_satisfied` 调用：`bool`, `snapshot.get`, `str`, `str(snapshot.get('risk_level', 'LOW')).upper`.
- `_completion_satisfied` 调用：`ValueError`, `abs`, `bool`, `completion.get`, `float`, `snapshot.get`, `str`, `str(completion.get('lane', '')).upper`, `str(snapshot.get('lane', '')).upper`.
- `__init__` 调用：`ValueError`, `float`, `math.isfinite`, `type`.
- `current_step` 调用：`len`.
- `start` 调用：`TypeError`, `_time`, `events.append`, `isinstance`, `self._event`, `self._step_state`, `self._update`.
- `update` 调用：`ManeuverUpdate`, `TypeError`, `_completion_satisfied`, `_precondition_satisfied`, `_time`, `any`, `bool`, `condition.endswith`, `float`, `int`, `isinstance`, `item.endswith`, `self._event`, `self._finish`, `self._replan_reason`, `self._step_failure`, `self._step_state`, `self._update`, `self.request_replan`, `snapshot.get`, `step.completion.get`, `step.target.get`, `str`, `str(snapshot.get('emergency_reason', 'EMERGENCY_PREEMPT')).strip`, `str(snapshot.get('emergency_reason', 'EMERGENCY_PREEMPT')).strip().upper`, `str(snapshot.get('risk_level', '')).upper`, `tuple`.
- `request_replan` 调用：`ValueError`, `_time`, `self._event`, `self._finish`, `self._update`, `str`, `str(reason_code).strip`, `str(reason_code).strip().upper`.
- `fail` 调用：`_time`, `self._finish`, `str`, `str(reason_code).upper`.
- `_step_failure` 调用：`self._finish`, `self.request_replan`.
- `_finish` 调用：`list`, `self._event`, `self._update`, `terminal_events.append`.
- `_replan_reason` 调用：`bool`, `set`, `snapshot.get`.
- `_event` 调用：`ManeuverEvent`.
- `_update` 调用：`ManeuverUpdate`, `tuple`.
- `_step_state` 调用：`_STATE_BY_BEHAVIOR.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 62 行：`ValueError('replan_cooldown_s must be finite and non-negative')`。
- `__init__`，第 64 行：`ValueError('max_replans_per_command must be a non-negative integer')`。
- `_completion_satisfied`，第 404 行：`ValueError(f'unsupported completion type: {kind}')`。
- `_time`，第 349 行：`ValueError('now_s must be finite')`。
- `request_replan`，第 246 行：`ValueError('reason_code must be non-empty')`。
- `start`，第 90 行：`TypeError('plan must be CompiledManeuverPlan')`。
- `update`，第 110 行：`TypeError('snapshot must be a mapping')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/plan_compiler.py](../../../runtime/plan_compiler.py)

静态 import 消费者（含测试）：

- [car_control_A/tests/test_maneuver_fsm.py](../../../car_control_A/tests/test_maneuver_fsm.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_A/maneuver_fsm.py`

来源 SHA256：`6f01cb59516fc099665d0790d20d260116ab29aef072726f1112b251cdbe334f`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ManeuverEvent.event_type` | `str` | `无声明默认；构造/赋值方提供` |
| `ManeuverEvent.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ManeuverEvent.plan_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ManeuverEvent.step_id` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `ManeuverEvent.state` | `str` | `无声明默认；构造/赋值方提供` |
| `ManeuverEvent.reason_code` | `str` | `无声明默认；构造/赋值方提供` |
| `ManeuverEvent.now_s` | `float` | `无声明默认；构造/赋值方提供` |
| `ManeuverUpdate.state` | `str` | `无声明默认；构造/赋值方提供` |
| `ManeuverUpdate.current_step` | `CompiledPlanStep &#124; None` | `无声明默认；构造/赋值方提供` |
| `ManeuverUpdate.events` | `tuple[ManeuverEvent, ...]` | `无声明默认；构造/赋值方提供` |
| `ManeuverUpdate.safe_behavior` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `ManeuverUpdate.terminal` | `bool` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `ManeuverFSM.__init__` / 62 | `not math.isfinite(float(replan_cooldown_s)) or replan_cooldown_s < 0` | `raise ValueError('replan_cooldown_s must be finite and non-negative')` |
| `ManeuverFSM.__init__` / 64 | `type(max_replans_per_command) is not int or max_replans_per_command < 0` | `raise ValueError('max_replans_per_command must be a non-negative integer')` |
| `ManeuverFSM.start` / 90 | `not isinstance(plan, CompiledManeuverPlan)` | `raise TypeError('plan must be CompiledManeuverPlan')` |
| `ManeuverFSM.update` / 110 | `not isinstance(snapshot, Mapping)` | `raise TypeError('snapshot must be a mapping')` |
| `ManeuverFSM.request_replan` / 246 | `not reason` | `raise ValueError('reason_code must be non-empty')` |
| `_time` / 349 | `type(value) not in (int, float) or isinstance(value, bool) or (not math.isfinite(float(value)))` | `raise ValueError('now_s must be finite')` |
| `_completion_satisfied` / 404 | `本地无直接if；检查上下文` | `raise ValueError(f'unsupported completion type: {kind}')` |
