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

<a id="fn-behaviorstate"></a>

### `BehaviorState`

源码位置：[car_control_A/behavior_fsm.py 第 11 行](../../../car_control_A/behavior_fsm.py#L11)。类型：`ClassDef`。

全局行为状态枚举：IDLE、LANE_FOLLOW、APPROACH_STOP、STOPPED、FOLLOWING、YIELDING、CONFIRMING、EMERGENCY_BRAKE、RECOVERING。状态不是ExecutionStatus终态；例如STOPPED是所有SUCCEEDED的统一落点，不证明该任务物理上已停车。

<a id="fn-behaviorresult"></a>

### `BehaviorResult`

源码位置：[car_control_A/behavior_fsm.py 第 24 行](../../../car_control_A/behavior_fsm.py#L24)。类型：`ClassDef`。

冻结返回值(state, feedback=None)。feedback=None可表示新请求被接纳、重复活动ID或确认后继续执行，不能仅据None判断发生了新的提交；存在feedback时是已存储的命令终态。

<a id="fn--activecommand"></a>

### `_ActiveCommand`

源码位置：[car_control_A/behavior_fsm.py 第 30 行](../../../car_control_A/behavior_fsm.py#L30)。类型：`ClassDef`。

保存DrivingCommand与FSM接受时started_at_s；相对timeout从接受时间计，绝对有效期仍取command.expires_at_s。确认不会重置这两个时点。

<a id="fn-behaviorfsm"></a>

### `BehaviorFSM`

源码位置：[car_control_A/behavior_fsm.py 第 35 行](../../../car_control_A/behavior_fsm.py#L35)。类型：`ClassDef`。

A内部命令生命周期状态机，维护一个全局行为状态、活动ID表与永久终态缓存。正常新命令会终结旧活动命令；不运行车辆、模型或计时线程，必须由调用方驱动submit/confirm/tick/complete。

<a id="fn-behaviorfsm---init--"></a>

### `BehaviorFSM.__init__`

源码位置：[car_control_A/behavior_fsm.py 第 36 行](../../../car_control_A/behavior_fsm.py#L36)。类型：`FunctionDef`。

```python
BehaviorFSM.__init__(self, *, command_timeout_s: float=15.0) -> None
```

command_timeout_s默认15秒，只检查>0再转float，未独立拒绝NaN/Infinity；初始化IDLE和空活动/终态字典。无终态淘汰策略、无锁，适合由单控制循环调用。

<a id="fn-behaviorfsm-state"></a>

### `BehaviorFSM.state`

源码位置：[car_control_A/behavior_fsm.py 第 45 行](../../../car_control_A/behavior_fsm.py#L45)。类型：`FunctionDef`。

```python
BehaviorFSM.state(self) -> BehaviorState
```

返回当前全局BehaviorState，不查询车辆速度或当前路由；不要从STOPPED字面推断真实车速为零。

<a id="fn-behaviorfsm-submit"></a>

### `BehaviorFSM.submit`

源码位置：[car_control_A/behavior_fsm.py 第 48 行](../../../car_control_A/behavior_fsm.py#L48)。类型：`FunctionDef`。

```python
BehaviorFSM.submit(self, command: DrivingCommand, *, now_s: float) -> BehaviorResult
```

同ID已有终态则返回原反馈，已有活动记录则不替换payload也不重置计时。先检查输入命令到期，已到期立即EXPIRED；否则将已有活动命令结为FAILED/superseded（反馈缓存但本次不逐项返回），保存新命令并按requires_confirmation或action定状态。过期新ID分支会经_finish改变全局状态，却不清除其他活动ID，见M03-01。

<a id="fn-behaviorfsm-confirm"></a>

### `BehaviorFSM.confirm`

源码位置：[car_control_A/behavior_fsm.py 第 68 行](../../../car_control_A/behavior_fsm.py#L68)。类型：`FunctionDef`。

```python
BehaviorFSM.confirm(self, command_id: str, *, approved: bool, now_s: float) -> BehaviorResult
```

未知ID返回当前状态及可能已有终态；活动ID先检查绝对到期/相对timeout，优先终结。approved为false则REJECTED，truthy则映射action状态；本方法未要求当前一定CONFIRMING、未强制approved为bool，也不修改原DrivingCommand的确认字段。ControlRuntime外层另校验bool并更新授权副本。

<a id="fn-behaviorfsm-complete"></a>

### `BehaviorFSM.complete`

源码位置：[car_control_A/behavior_fsm.py 第 80 行](../../../car_control_A/behavior_fsm.py#L80)。类型：`FunctionDef`。

```python
BehaviorFSM.complete(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
```

未知ID返回None，已终态返回原对象；活动ID先检查到期/timeout，再保存SUCCEEDED。只接收调用者的完成判断，不自己测车速/路径，任何成功都会使全局状态STOPPED。

<a id="fn-behaviorfsm-fail"></a>

### `BehaviorFSM.fail`

源码位置：[car_control_A/behavior_fsm.py 第 89 行](../../../car_control_A/behavior_fsm.py#L89)。类型：`FunctionDef`。

```python
BehaviorFSM.fail(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
```

活动命令先检查到期/timeout，仍有效才记录FAILED；已终态原样返回、未知ID为None。不能用fail覆盖已有EXPIRED/TIMED_OUT或成功结论。

<a id="fn-behaviorfsm-safety-override"></a>

### `BehaviorFSM.safety_override`

源码位置：[car_control_A/behavior_fsm.py 第 97 行](../../../car_control_A/behavior_fsm.py#L97)。类型：`FunctionDef`。

```python
BehaviorFSM.safety_override(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
```

Terminate a command whose authority was pre-empted by D.

已有终态原样返回、未知ID为None；活动ID仍先经过期/timeout检查，仍有效才保存SAFETY_OVERRIDE。故安全事件发生在到期后时，本接口可能返回EXPIRED，详细安全证据需另行记录。

<a id="fn-behaviorfsm-tick"></a>

### `BehaviorFSM.tick`

源码位置：[car_control_A/behavior_fsm.py 第 106 行](../../../car_control_A/behavior_fsm.py#L106)。类型：`FunctionDef`。

```python
BehaviorFSM.tick(self, *, now_s: float) -> tuple[ExecutionFeedback, ...]
```

遍历当前活动ID，调用_due_feedback并返回本轮新产生反馈tuple；没有后台自动tick。它只处理时限，不评估车辆完成、确认超时以外的安全或路线条件。

<a id="fn-behaviorfsm--due-feedback"></a>

### `BehaviorFSM._due_feedback`

源码位置：[car_control_A/behavior_fsm.py 第 114 行](../../../car_control_A/behavior_fsm.py#L114)。类型：`FunctionDef`。

```python
BehaviorFSM._due_feedback(self, command_id: str, now_s: float) -> ExecutionFeedback | None
```

Finish an active command whose authority has elapsed, if any.

Every operation that could complete or alter an active command calls
this first.  Thus callers cannot bypass a missed ``tick`` and report a
stale command as successful or normally failed.

绝对有效期先检查now>=expires，再检查now-started>command_timeout_s；若同时命中返回EXPIRED而非TIMED_OUT。超时边界严格大于，确认不重置started。该方法只在调用入口时执行，无自动定时器。

<a id="fn-behaviorfsm--finish"></a>

### `BehaviorFSM._finish`

源码位置：[car_control_A/behavior_fsm.py 第 130 行](../../../car_control_A/behavior_fsm.py#L130)。类型：`FunctionDef`。

```python
BehaviorFSM._finish(self, command_id: str, status: ExecutionStatus, now_s: float, detail: str, command: DrivingCommand | None=None) -> BehaviorResult
```

若ID已终态直接返回原反馈；否则pop该ID，构建并缓存ExecutionFeedback，SUCCEEDED置STOPPED，其余状态置RECOVERING。可为不在活动表的ID建终态，且仍改全局状态；可选command参数当前未消费。不自动发布反馈给记录器。

<a id="fn-behaviorfsm--state-for"></a>

### `BehaviorFSM._state_for`

源码位置：[car_control_A/behavior_fsm.py 第 142 行](../../../car_control_A/behavior_fsm.py#L142)。类型：`FunctionDef`。

```python
BehaviorFSM._state_for(action: str) -> BehaviorState
```

STOP→APPROACH_STOP、EMERGENCY_BRAKE→EMERGENCY_BRAKE、KEEP_LANE/SET_SPEED→LANE_FOLLOW、FOLLOW→FOLLOWING、YIELD→YIELDING；其他字符串RECOVERING。不是动作合法性校验，不执行该动作。

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

<a id="fn-car-control-a-behavior-fsm-py"></a>

### `car_control_A/behavior_fsm.py`

来源 SHA256：`0aead9bd63573bb55cc7d46465b23657bab83bbf1f6538d5a70432595337da4d`。


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
