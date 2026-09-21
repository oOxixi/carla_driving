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

<a id="fn-maneuverevent"></a>

### `ManeuverEvent`

源码位置：[car_control_A/maneuver_fsm.py 第 35 行](../../../car_control_A/maneuver_fsm.py#L35)。类型：`ClassDef`。

冻结事件：event_type、command_id、plan_id、可空step_id、state、reason_code、now_s；时间是调用方传入的秒，事件自身没有校验或I/O。原计划用户ID与内部步骤ID分别保留。

<a id="fn-maneuverupdate"></a>

### `ManeuverUpdate`

源码位置：[car_control_A/maneuver_fsm.py 第 46 行](../../../car_control_A/maneuver_fsm.py#L46)。类型：`ClassDef`。

每次调用返回state/current_step/events/safe_behavior/terminal；safe_behavior是建议动作或None，不是已施加控制。terminal由状态集合计算，CONFIRMING在本FSM也算终态，与BehaviorFSM待确认活动态不同。

<a id="fn-maneuverfsm"></a>

### `ManeuverFSM`

源码位置：[car_control_A/maneuver_fsm.py 第 54 行](../../../car_control_A/maneuver_fsm.py#L54)。类型：`ClassDef`。

消费已编译计划和确定性snapshot，推进单个步骤；不连接Qwen、不生成B/C/D控制。前置条件进入后锁存，完成按连续update调用数计；没有按传感器frame去重，没有直接读取plan.valid_until_ns。

<a id="fn-maneuverfsm---init--"></a>

### `ManeuverFSM.__init__`

源码位置：[car_control_A/maneuver_fsm.py 第 55 行](../../../car_control_A/maneuver_fsm.py#L55)。类型：`FunctionDef`。

```python
ManeuverFSM.__init__(self, *, replan_cooldown_s: float=2.0, max_replans_per_command: int=2) -> None
```

replan_cooldown_s默认2秒且要求有限非负，max_replans_per_command默认2且为非负exact int；初始IDLE、无plan、index0、无开始/重规划时间，锁存与终态标志False、完成/重规划计数0。未启动线程。

<a id="fn-maneuverfsm-current-step"></a>

### `ManeuverFSM.current_step`

源码位置：[car_control_A/maneuver_fsm.py 第 78 行](../../../car_control_A/maneuver_fsm.py#L78)。类型：`FunctionDef`。

```python
ManeuverFSM.current_step(self) -> CompiledPlanStep | None
```

plan不存在或index超出steps时None，否则返回steps[index]对象引用；即使FSM处于失败终态，index未耗尽仍可能有current_step，因此先看terminal再决定是否执行。

<a id="fn-maneuverfsm-replan-count"></a>

### `ManeuverFSM.replan_count`

源码位置：[car_control_A/maneuver_fsm.py 第 84 行](../../../car_control_A/maneuver_fsm.py#L84)。类型：`FunctionDef`。

```python
ManeuverFSM.replan_count(self) -> int
```

返回本次start之后触发重规划的计数；冷却期suppressed不增加。start即使接收同一个command_id也清零，名字不保证跨计划替换的每命令累计额度。

<a id="fn-maneuverfsm-start"></a>

### `ManeuverFSM.start`

源码位置：[car_control_A/maneuver_fsm.py 第 87 行](../../../car_control_A/maneuver_fsm.py#L87)。类型：`FunctionDef`。

```python
ManeuverFSM.start(self, plan: CompiledManeuverPlan, *, now_s: float) -> ManeuverUpdate
```

now须有限数，plan须CompiledManeuverPlan；旧计划非终态时先发SUPERSEDED终态事件，随后重置index/计时/锁存/完成计数/终态标志/重规划计数。按首步设状态并发plan_started与step_started。此处不再Schema验证、不查valid_until_ns、不保证steps非空；正常调用前需Validator/Compiler保证契约。

<a id="fn-maneuverfsm-update"></a>

### `ManeuverFSM.update`

源码位置：[car_control_A/maneuver_fsm.py 第 107 行](../../../car_control_A/maneuver_fsm.py#L107)。类型：`FunctionDef`。

```python
ManeuverFSM.update(self, snapshot: Mapping[str, Any], *, now_s: float) -> ManeuverUpdate
```

顺序为无计划/终态短路→紧急风险→声明的replan条件→严格大于timeout→未锁存前置条件→完成连续计数→推进。红灯stop-line guard置WAIT_TRAFFIC_SIGNAL并每次重置step_started_s/完成计数、建议STOP；YIELD/SLOW_DOWN遇紧急风险保留任务但仍受原timeout限制，建议EMERGENCY_STOP；其他紧急风险终结SAFETY_OVERRIDE。前置未满足清计数并建议SLOW_DOWN（gap则WAIT_SAFE_GAP），满足后不逐帧重新检查；PASS_TARGET允许target_seen替代当前可见。详见本页snapshot参数表。

<a id="fn-maneuverfsm-request-replan"></a>

### `ManeuverFSM.request_replan`

源码位置：[car_control_A/maneuver_fsm.py 第 240 行](../../../car_control_A/maneuver_fsm.py#L240)。类型：`FunctionDef`。

```python
ManeuverFSM.request_replan(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
```

无计划/已终态返回快照；reason strip/upper后非空。距上次触发<cooldown时发suppressed且不加计数；达到额度则FAILED/REPLAN_LIMIT_EXCEEDED并建议STOP；否则加计数、记录时间、置REPLAN_PENDING并发triggered、建议SLOW_DOWN。不会调用模型，也不阻止下一次update在触发条件消失后继续原步骤。

<a id="fn-maneuverfsm-fail"></a>

### `ManeuverFSM.fail`

源码位置：[car_control_A/maneuver_fsm.py 第 263 行](../../../car_control_A/maneuver_fsm.py#L263)。类型：`FunctionDef`。

```python
ManeuverFSM.fail(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
```

reason转大写、校验now有限后调用_finish(FAILED, safe_behavior=STOP)。reason不strip/不强制非空；尚未start时_event断言plan非空会失败，因此不是无条件安全的初始化清理接口。

<a id="fn-maneuverfsm--step-failure"></a>

### `ManeuverFSM._step_failure`

源码位置：[car_control_A/maneuver_fsm.py 第 266 行](../../../car_control_A/maneuver_fsm.py#L266)。类型：`FunctionDef`。

```python
ManeuverFSM._step_failure(self, step: CompiledPlanStep, reason: str, now: float) -> ManeuverUpdate
```

step.on_failure=REPLAN则请求重规划；CONFIRM结为CONFIRMING并建议STOP；SAFE_STOP结FAILED且STOP；其他值结FAILED且KEEP_LANE。正常枚举由上游Schema限制，此方法不自行拒绝未知策略。

<a id="fn-maneuverfsm--finish"></a>

### `ManeuverFSM._finish`

源码位置：[car_control_A/maneuver_fsm.py 第 276 行](../../../car_control_A/maneuver_fsm.py#L276)。类型：`FunctionDef`。

```python
ManeuverFSM._finish(self, state: str, reason: str, now: float, *, safe_behavior: str | None=None, events: list[ManeuverEvent] | None=None) -> ManeuverUpdate
```

设置终态，最多追加一次qwen_terminal；若已经终态且已发事件，只返回无新事件快照。保留plan/index，current_step可能仍非空；safe_behavior只在本次调用返回，后续普通update不自动重发上次建议。

<a id="fn-maneuverfsm--replan-reason"></a>

### `ManeuverFSM._replan_reason`

源码位置：[car_control_A/maneuver_fsm.py 第 294 行](../../../car_control_A/maneuver_fsm.py#L294)。类型：`FunctionDef`。

```python
ManeuverFSM._replan_reason(self, snapshot: Mapping[str, Any]) -> str | None
```

仅对plan.replan_conditions中已声明的原因检查snapshot。按TARGET_LOST、LANE_BLOCKED、ROUTE_MISMATCH、NEW_EMERGENCY_OBJECT、PROGRESS_STALLED、ROUTE_DEVIATION、PLAN_EXPIRING固定顺序，返回第一个truthy条件；PLAN_EXPIRING是输入布尔量，不自行比较有效期。

<a id="fn-maneuverfsm--event"></a>

### `ManeuverFSM._event`

源码位置：[car_control_A/maneuver_fsm.py 第 311 行](../../../car_control_A/maneuver_fsm.py#L311)。类型：`FunctionDef`。

```python
ManeuverFSM._event(self, event_type: str, now: float, reason: str, *, state: str | None=None) -> ManeuverEvent
```

要求plan已存在（assert），取当前command/plan/step身份生成事件；state参数None则使用当前FSM状态，否则用指定状态。step_id取创建事件时的游标，不能当作整个计划的唯一ID。

<a id="fn-maneuverfsm--update"></a>

### `ManeuverFSM._update`

源码位置：[car_control_A/maneuver_fsm.py 第 326 行](../../../car_control_A/maneuver_fsm.py#L326)。类型：`FunctionDef`。

```python
ManeuverFSM._update(self, *, events: list[ManeuverEvent] | None=None, safe_behavior: str | None=None) -> ManeuverUpdate
```

构造ManeuverUpdate，将events列表转tuple，默认无事件/无安全建议；terminal状态集合是SUCCEEDED/FAILED/SAFETY_OVERRIDE/SUPERSEDED/CONFIRMING。不做副作用派发。

<a id="fn-maneuverfsm--step-state"></a>

### `ManeuverFSM._step_state`

源码位置：[car_control_A/maneuver_fsm.py 第 341 行](../../../car_control_A/maneuver_fsm.py#L341)。类型：`FunctionDef`。

```python
ManeuverFSM._step_state(step: CompiledPlanStep | None) -> str
```

WAIT_SAFE_GAP保持同名；TURN左右→TURNING、CHANGE_LANE左右→CHANGING_LANE、AVOID_OBSTACLE/PASS_TARGET→AVOIDING、RETURN_TO_LANE→RETURNING_TO_LANE、PULL_OVER→PULLING_OVER；其余PLAN_EXECUTING，无step返回SUCCEEDED。

<a id="fn--time"></a>

### `_time`

源码位置：[car_control_A/maneuver_fsm.py 第 347 行](../../../car_control_A/maneuver_fsm.py#L347)。类型：`FunctionDef`。

```python
_time(value: float) -> float
```

接受exact int/float并拒绝bool与非有限数，转float返回；不要求非负，也不检查相较上次时间是否回退，故调用方必须维持一致单调秒时钟。

<a id="fn--precondition-satisfied"></a>

### `_precondition_satisfied`

源码位置：[car_control_A/maneuver_fsm.py 第 353 行](../../../car_control_A/maneuver_fsm.py#L353)。类型：`FunctionDef`。

```python
_precondition_satisfied(condition: str, snapshot: Mapping[str, Any]) -> bool
```

按10项固定映射读取snapshot并bool转换；PERCEPTION_FRESH默认not stale（stale缺失默认False），NO_EMERGENCY_RISK默认risk_level非EMERGENCY（缺省LOW），其余缺省False。未知条件抛KeyError；不校验snapshot键值一定为bool。进入后锁存，持续安全由update紧急分支及外层D负责。

<a id="fn--completion-satisfied"></a>

### `_completion_satisfied`

源码位置：[car_control_A/maneuver_fsm.py 第 374 行](../../../car_control_A/maneuver_fsm.py#L374)。类型：`FunctionDef`。

```python
_completion_satisfied(completion: Mapping[str, Any], snapshot: Mapping[str, Any]) -> bool
```

SPEED_BELOW阈值加默认0.05m/s；SPEED_REACHED绝对误差<=默认0.6m/s；LANE_CENTERED需lane大写相等且横向误差<=默认0.3m；JUNCTION_EXITED/TARGET_PASSED读bool；TARGET_GAP_REACHED检查gap秒>=value；STOPPED速度<=默认0.1m/s；HOLD_FRAMES读取hold_condition默认True。缺速度/误差通常以∞导致不满足；未知类型抛ValueError。这里只判单次真假，连续次数与SLOW_DOWN观察时间在update中处理。

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

<a id="fn-car-control-a-maneuver-fsm-py"></a>

### `car_control_A/maneuver_fsm.py`

来源 SHA256：`48463dea955caf3cfc05e25e7d44b2aa7cd5342835f1f47db93eb17a437fc35a`。


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

## snapshot字段与完成判定参数表

snapshot为Mapping，函数按需读取，没有完整Schema校验。布尔分支多用bool转换，字符串"false"会被当作真，调用方必须提供约定类型。

| 字段 / 条件 | 缺省 / 单位 | 消费行为 |
|---|---|---|
| emergency / risk_level / emergency_reason | False / 空串 / EMERGENCY_PREEMPT | emergency truthy或risk_level=EMERGENCY进入安全分支；RED_LIGHT_STOP_LINE_GUARD暂停步骤 |
| perception_fresh / stale | not stale / False | 仅未锁存入口前置判定，缺两项时被视为新鲜 |
| no_emergency_risk | risk_level非EMERGENCY，缺省LOW | 前置条件默认推导；update另行持续检查紧急字段 |
| left/right_lane_exists、left/right_gap_safe、target_visible、route_available、intersection_ahead、stop_line_clear | False | 对应前置条件；进入后锁存不复验 |
| target_seen | False | PASS_TARGET在曾看到目标后可越过TARGET_VISIBLE前置限制 |
| target_lost/lane_blocked/route_mismatch/new_emergency_object/progress_stalled/route_deviation/plan_expiring | False | 仅plan声明的replan_conditions生效；固定优先级见_replan_reason |
| speed_mps / speed_below_tolerance_mps | ∞ / 0.05 m/s | SPEED_BELOW: speed<=value+tolerance |
| speed_tolerance_mps | 0.6 m/s | SPEED_REACHED误差带；也用于SLOW_DOWN+TARGET_PASSED的实际降速门禁 |
| lane / lateral_error_m / lane_center_tolerance_m | 空串 / ∞ / 0.3 m | LANE_CENTERED需目标lane匹配及绝对偏差不超限 |
| junction_exited / target_passed | False | JUNCTION_EXITED/TARGET_PASSED单次事实 |
| target_gap_s | -∞ s | TARGET_GAP_REACHED需>=completion.value |
| stopped_threshold_mps | 0.1 m/s | STOPPED速度阈值；不同于ControlRuntime自身停车策略配置 |
| hold_condition | True | HOLD_FRAMES每次update缺该键也算满足，连续计数不是实际frame去重 |

completion.hold_frames控制连续update次数；不满足清零，一次调用最多推进一步。SLOW_DOWN+TARGET_PASSED还要求target_speed_mps非None、实际速度<=目标+speed_tolerance_mps，且now-step_started>=completion.value（缺值视0秒）。计时从进入步骤开始，包含前置等待；红灯分支会重置计时，不能解释为严格累计运动/观察时长。

WAIT_SAFE_GAP成功后，紧接同source_step_id的CHANGE_LANE_LEFT/RIGHT/RETURN_TO_LANE继承锁存；其他下一步重新检查。start不会直接拒绝已过期plan，也不会检查时间单调性；外层期限/撤销与D安全仍必需。
