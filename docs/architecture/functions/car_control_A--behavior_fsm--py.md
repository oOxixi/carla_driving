# behavior_fsm：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/behavior_fsm.py](../../../car_control_A/behavior_fsm.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Auditable command lifecycle and high-level behaviour state machine.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `BehaviorResult.state: BehaviorState`；默认：`未在声明处设置`。
- `BehaviorResult.feedback: ExecutionFeedback | None`；默认：`None`。
- `_ActiveCommand.command: DrivingCommand`；默认：`未在声明处设置`。
- `_ActiveCommand.started_at_s: float`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `BehaviorState`

源码位置：[car_control_A/behavior_fsm.py 第 11 行](../../../car_control_A/behavior_fsm.py#L11)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorResult`

源码位置：[car_control_A/behavior_fsm.py 第 24 行](../../../car_control_A/behavior_fsm.py#L24)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_ActiveCommand`

源码位置：[car_control_A/behavior_fsm.py 第 30 行](../../../car_control_A/behavior_fsm.py#L30)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM`

源码位置：[car_control_A/behavior_fsm.py 第 35 行](../../../car_control_A/behavior_fsm.py#L35)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM.__init__`

源码位置：[car_control_A/behavior_fsm.py 第 36 行](../../../car_control_A/behavior_fsm.py#L36)。类型：`FunctionDef`。

```python
BehaviorFSM.__init__(self, *, command_timeout_s: float=15.0) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM.state`

源码位置：[car_control_A/behavior_fsm.py 第 45 行](../../../car_control_A/behavior_fsm.py#L45)。类型：`FunctionDef`。

```python
BehaviorFSM.state(self) -> BehaviorState
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM.submit`

源码位置：[car_control_A/behavior_fsm.py 第 48 行](../../../car_control_A/behavior_fsm.py#L48)。类型：`FunctionDef`。

```python
BehaviorFSM.submit(self, command: DrivingCommand, *, now_s: float) -> BehaviorResult
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM.confirm`

源码位置：[car_control_A/behavior_fsm.py 第 68 行](../../../car_control_A/behavior_fsm.py#L68)。类型：`FunctionDef`。

```python
BehaviorFSM.confirm(self, command_id: str, *, approved: bool, now_s: float) -> BehaviorResult
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM.complete`

源码位置：[car_control_A/behavior_fsm.py 第 80 行](../../../car_control_A/behavior_fsm.py#L80)。类型：`FunctionDef`。

```python
BehaviorFSM.complete(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM.fail`

源码位置：[car_control_A/behavior_fsm.py 第 89 行](../../../car_control_A/behavior_fsm.py#L89)。类型：`FunctionDef`。

```python
BehaviorFSM.fail(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM.safety_override`

源码位置：[car_control_A/behavior_fsm.py 第 97 行](../../../car_control_A/behavior_fsm.py#L97)。类型：`FunctionDef`。

```python
BehaviorFSM.safety_override(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
```

Terminate a command whose authority was pre-empted by D.

### `BehaviorFSM.tick`

源码位置：[car_control_A/behavior_fsm.py 第 106 行](../../../car_control_A/behavior_fsm.py#L106)。类型：`FunctionDef`。

```python
BehaviorFSM.tick(self, *, now_s: float) -> tuple[ExecutionFeedback, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM._due_feedback`

源码位置：[car_control_A/behavior_fsm.py 第 114 行](../../../car_control_A/behavior_fsm.py#L114)。类型：`FunctionDef`。

```python
BehaviorFSM._due_feedback(self, command_id: str, now_s: float) -> ExecutionFeedback | None
```

Finish an active command whose authority has elapsed, if any.

Every operation that could complete or alter an active command calls
this first.  Thus callers cannot bypass a missed ``tick`` and report a
stale command as successful or normally failed.

### `BehaviorFSM._finish`

源码位置：[car_control_A/behavior_fsm.py 第 130 行](../../../car_control_A/behavior_fsm.py#L130)。类型：`FunctionDef`。

```python
BehaviorFSM._finish(self, command_id: str, status: ExecutionStatus, now_s: float, detail: str, command: DrivingCommand | None=None) -> BehaviorResult
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BehaviorFSM._state_for`

源码位置：[car_control_A/behavior_fsm.py 第 142 行](../../../car_control_A/behavior_fsm.py#L142)。类型：`FunctionDef`。

```python
BehaviorFSM._state_for(action: str) -> BehaviorState
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__init__` 调用：`ValueError`, `float`.
- `submit` 调用：`BehaviorResult`, `_ActiveCommand`, `command.is_expired_at`, `self._finish`, `self._state_for`, `self._terminal.get`, `tuple`.
- `confirm` 调用：`BehaviorResult`, `self._active.get`, `self._due_feedback`, `self._finish`, `self._state_for`, `self._terminal.get`.
- `complete` 调用：`self._active.get`, `self._due_feedback`, `self._finish`, `self._terminal.get`.
- `fail` 调用：`self._due_feedback`, `self._finish`, `self._terminal.get`.
- `safety_override` 调用：`self._due_feedback`, `self._finish`, `self._terminal.get`.
- `tick` 调用：`feedback.append`, `self._due_feedback`, `tuple`.
- `_due_feedback` 调用：`active.command.is_expired_at`, `self._active.get`, `self._finish`.
- `_finish` 调用：`BehaviorResult`, `ExecutionFeedback`, `self._active.pop`, `self._terminal.get`.
- `_state_for` 调用：`{'STOP': BehaviorState.APPROACH_STOP, 'EMERGENCY_BRAKE': BehaviorState.EMERGENCY_BRAKE, 'KEEP_LANE': BehaviorState.LANE_FOLLOW, 'SET_SPEED': BehaviorState.LANE_FOLLOW, 'FOLLOW': BehaviorState.FOLLOWING, 'YIELD': BehaviorState.YIELDING}.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 38 行：`ValueError('command_timeout_s must be positive')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/contracts.py](../../../car_control_A/contracts.py)
- [compat.py](../../../compat.py)

静态 import 消费者（含测试）：

- [car_control_A/tests/test_ac_integration.py](../../../car_control_A/tests/test_ac_integration.py)
- [car_control_A/tests/test_behavior_fsm.py](../../../car_control_A/tests/test_behavior_fsm.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_A/behavior_fsm.py`

来源 SHA256：`5a3217e46a97f9a109fdd4edb45d2e5e4678ebfd074127f780d6d08a924658c0`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `BehaviorResult.state` | `BehaviorState` | `无声明默认；构造/赋值方提供` |
| `BehaviorResult.feedback` | `ExecutionFeedback &#124; None` | `None` |
| `_ActiveCommand.command` | `DrivingCommand` | `无声明默认；构造/赋值方提供` |
| `_ActiveCommand.started_at_s` | `float` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `BehaviorFSM.__init__` / 38 | `command_timeout_s <= 0.0` | `raise ValueError('command_timeout_s must be positive')` |
