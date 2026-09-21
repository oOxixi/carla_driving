# runtime_loop：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/runtime_loop.py](../../../integration/runtime_loop.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

The single pure-Python composition point for A/B/C/D.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-controlruntime"></a>

### `ControlRuntime`

源码位置：[integration/runtime_loop.py 第 38 行](../../../integration/runtime_loop.py#L38)。类型：`ClassDef`。

Owns command state and composes B/C/D in one deterministic frame order.

<a id="fn-controlruntime---init--"></a>

### `ControlRuntime.__init__`

源码位置：[integration/runtime_loop.py 第 40 行](../../../integration/runtime_loop.py#L40)。类型：`FunctionDef`。

```python
ControlRuntime.__init__(self, lateral: LateralController, *, longitudinal: LongitudinalController | None=None, safety: SafetySupervisor | None=None, voice_adapter: VoiceCommandAdapter | None=None, default_speed_mps: float=5.0, command_timeout_s: float=15.0) -> None
```

lateral由调用方提供；缺longitudinal/safety/voice_adapter时各自创建默认实例，并建立BehaviorFSM/FuzzyCommandPolicy。default_speed_mps默认5、不得<0；command_timeout_s默认15、不得<=0。初始化空活动命令/反馈、停车保持false、黄灯承诺false及空告警锁存；构造器这两项比较本身没有额外isfinite检查。

<a id="fn-controlruntime-yellow-clear-committed"></a>

### `ControlRuntime.yellow_clear_committed`

源码位置：[integration/runtime_loop.py 第 67 行](../../../integration/runtime_loop.py#L67)。类型：`FunctionDef`。

```python
ControlRuntime.yellow_clear_committed(self) -> bool
```

Whether ego legally committed to clear a yellow-light dilemma zone.

<a id="fn-controlruntime-submit-voice"></a>

### `ControlRuntime.submit_voice`

源码位置：[integration/runtime_loop.py 第 71 行](../../../integration/runtime_loop.py#L71)。类型：`FunctionDef`。

```python
ControlRuntime.submit_voice(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand
```

Accept a voice result at the CARLA-time boundary and retain JSON for D.

<a id="fn-controlruntime-safety-latched"></a>

### `ControlRuntime.safety_latched`

源码位置：[integration/runtime_loop.py 第 107 行](../../../integration/runtime_loop.py#L107)。类型：`FunctionDef`。

```python
ControlRuntime.safety_latched(self) -> bool
```

返回bool(_latched_alerts)，表示运行时仍有锁存告警；它不是本帧D safety_override，也不会清除锁存。

<a id="fn-controlruntime-active-command-id"></a>

### `ControlRuntime.active_command_id`

源码位置：[integration/runtime_loop.py 第 111 行](../../../integration/runtime_loop.py#L111)。类型：`FunctionDef`。

```python
ControlRuntime.active_command_id(self) -> str | None
```

返回当前内部活动命令ID或None，不返回原始envelope；多步规划的内部步骤ID可能不同于用户命令ID。

<a id="fn-controlruntime-confirm-voice"></a>

### `ControlRuntime.confirm_voice`

源码位置：[integration/runtime_loop.py 第 114 行](../../../integration/runtime_loop.py#L114)。类型：`FunctionDef`。

```python
ControlRuntime.confirm_voice(self, command_id: str, *, approved: bool, now_s: float) -> ExecutionFeedback | None
```

Resolve a confirmation gate without importing or mutating voice code.

Approval only unlocks commands this runtime can execute
deterministically. A complex multimodal action still fails closed until
a decision provider supplies a concrete manoeuvre.

<a id="fn-controlruntime-reset-safety-latch"></a>

### `ControlRuntime.reset_safety_latch`

源码位置：[integration/runtime_loop.py 第 168 行](../../../integration/runtime_loop.py#L168)。类型：`FunctionDef`。

```python
ControlRuntime.reset_safety_latch(self) -> None
```

Explicitly release a persistent watchdog/integration stop after recovery.

<a id="fn-controlruntime-clear-safety-alerts"></a>

### `ControlRuntime.clear_safety_alerts`

源码位置：[integration/runtime_loop.py 第 172 行](../../../integration/runtime_loop.py#L172)。类型：`FunctionDef`。

```python
ControlRuntime.clear_safety_alerts(self, alerts: tuple[str, ...]) -> None
```

Clear only explicitly recovered alerts, preserving unrelated faults.

<a id="fn-controlruntime-clear-safety-alert-prefix"></a>

### `ControlRuntime.clear_safety_alert_prefix`

源码位置：[integration/runtime_loop.py 第 181 行](../../../integration/runtime_loop.py#L181)。类型：`FunctionDef`。

```python
ControlRuntime.clear_safety_alert_prefix(self, prefix: str) -> tuple[str, ...]
```

Release one recovered fault family without clearing unrelated alerts.

<a id="fn-controlruntime-release-scenario-stop-hold"></a>

### `ControlRuntime.release_scenario_stop_hold`

源码位置：[integration/runtime_loop.py 第 192 行](../../../integration/runtime_loop.py#L192)。类型：`FunctionDef`。

```python
ControlRuntime.release_scenario_stop_hold(self, *, requested_speed_mps: float) -> bool
```

Release a completed scenario emergency hold after its hazard clears.

<a id="fn-controlruntime-fail-active"></a>

### `ControlRuntime.fail_active`

源码位置：[integration/runtime_loop.py 第 203 行](../../../integration/runtime_loop.py#L203)。类型：`FunctionDef`。

```python
ControlRuntime.fail_active(self, *, now_s: float, detail: str, resume_speed_mps: float | None=None) -> ExecutionFeedback | None
```

Terminate the active command when its outer runtime cannot continue.

Ordinary failures remain fail-closed.  A caller that owns a temporary
internal hold (for example, the Qwen request bridge) may explicitly
release only that hold and restore a bounded fallback speed.  The
independent safety supervisor still arbitrates the resumed command.

<a id="fn-controlruntime-complete-active"></a>

### `ControlRuntime.complete_active`

源码位置：[integration/runtime_loop.py 第 238 行](../../../integration/runtime_loop.py#L238)。类型：`FunctionDef`。

```python
ControlRuntime.complete_active(self, *, now_s: float, detail: str) -> ExecutionFeedback | None
```

Complete an internal command whose outer maneuver contract succeeded.

<a id="fn-controlruntime-step"></a>

### `ControlRuntime.step`

源码位置：[integration/runtime_loop.py 第 247 行](../../../integration/runtime_loop.py#L247)。类型：`FunctionDef`。

```python
ControlRuntime.step(self, vehicle: RuntimeVehicleState, scene: PerceptionFrame, route: RouteReference, *, dt_s: float, watchdog_alerts: tuple[str, ...]=(), raw_control_override: object | None=None, speed_cap_mps: float | None=None, safety_override_reason: str | None=None) -> FrameResult
```

Compose lateral, longitudinal and final safety arbitration for one aligned frame.

<a id="fn-controlruntime--completion-feedback"></a>

### `ControlRuntime._completion_feedback`

源码位置：[integration/runtime_loop.py 第 433 行](../../../integration/runtime_loop.py#L433)。类型：`FunctionDef`。

```python
ControlRuntime._completion_feedback(self, vehicle: RuntimeVehicleState) -> ExecutionFeedback | None
```

无活动命令返回None。SET_SPEED需连续3帧与目标相差<=0.25m/s，不满足清计数；STOP/EMERGENCY_BRAKE需速度<=fuzzy配置standstill_speed_mps；KEEP_LANE连续累计3帧即接受成功。成功调用fsm.complete，以vehicle.sim_time_s记时；停车动作置_stop_hold=True，清活动命令并返回反馈。此处不判场景整体通过。

<a id="fn-controlruntime--clear-active-command"></a>

### `ControlRuntime._clear_active_command`

源码位置：[integration/runtime_loop.py 第 461 行](../../../integration/runtime_loop.py#L461)。类型：`FunctionDef`。

```python
ControlRuntime._clear_active_command(self) -> None
```

清活动ID/命令/envelope、红灯停车接近速度和成功帧计数；不清requested_speed_mps、_stop_hold、_yellow_clear_committed或告警锁存。调用方须独立处理这些状态，不能把本方法当完整reset。

<a id="fn-controlruntime--is-qwen-high-level-plan"></a>

### `ControlRuntime._is_qwen_high_level_plan`

源码位置：[integration/runtime_loop.py 第 469 行](../../../integration/runtime_loop.py#L469)。类型：`FunctionDef`。

```python
ControlRuntime._is_qwen_high_level_plan(envelope: Mapping[str, object]) -> bool
```

仅检查envelope.warnings为list/tuple且包含mapping项code=QWEN_HIGH_LEVEL_PLAN；返回bool，不验证Plan/权限，标记不能代替边界校验。

<a id="fn-controlruntime--traffic-stop-approach-active"></a>

### `ControlRuntime._traffic_stop_approach_active`

源码位置：[integration/runtime_loop.py 第 476 行](../../../integration/runtime_loop.py#L476)。类型：`FunctionDef`。

```python
ControlRuntime._traffic_stop_approach_active(self, scene: PerceptionFrame) -> bool
```

仅在已有接近速度、活动STOP命令及RED/YELLOW灯态时继续判断；取停止线/前车的非None距离，至少一项存在且最小值>1m返回True。其他情况False，不修改状态。

<a id="fn-controlruntime--traffic-scene-for-control"></a>

### `ControlRuntime._traffic_scene_for_control`

源码位置：[integration/runtime_loop.py 第 491 行](../../../integration/runtime_loop.py#L491)。类型：`FunctionDef`。

```python
ControlRuntime._traffic_scene_for_control(self, vehicle: RuntimeVehicleState, scene: PerceptionFrame) -> PerceptionFrame
```

Resolve the yellow-light dilemma zone before C and D run.

RED never creates a new permission to proceed. Only a previously seen
YELLOW whose stop would exceed comfortable deceleration can commit ego
to clear the junction. This prevents a yellow-to-red transition from
stopping the vehicle inside the intersection.

## 内部调用与异常路径

- `__init__` 调用：`BehaviorFSM`, `FuzzyCommandPolicy`, `LongitudinalController`, `SafetySupervisor`, `ValueError`, `VoiceCommandAdapter`, `float`.
- `submit_voice` 调用：`dict`, `replace`, `self._clear_active_command`, `self._is_qwen_high_level_plan`, `self._pending_feedback.append`, `self.fsm.fail`, `self.fsm.submit`, `self.voice_adapter.adapt`.
- `safety_latched` 调用：`bool`.
- `confirm_voice` 调用：`TypeError`, `ValueError`, `replace`, `self._clear_active_command`, `self._pending_feedback.append`, `self.fsm.confirm`, `self.fsm.fail`, `type`.
- `reset_safety_latch` 调用：`self._latched_alerts.clear`.
- `clear_safety_alerts` 调用：`TypeError`, `any`, `set`, `type`.
- `clear_safety_alert_prefix` 调用：`ValueError`, `alert.startswith`, `self.clear_safety_alerts`, `tuple`, `type`.
- `release_scenario_stop_hold` 调用：`ValueError`, `float`, `math.isfinite`.
- `fail_active` 调用：`ValueError`, `float`, `isinstance`, `math.isfinite`, `self._clear_active_command`, `self.fsm.fail`, `type`.
- `complete_active` 调用：`self._clear_active_command`, `self.fsm.complete`.
- `step` 调用：`', '.join`, `ControlOutput`, `FrameResult`, `RuntimeError`, `TypeError`, `ValueError`, `expired_alerts.append`, `feedback.append`, `feedback.extend`, `float`, `isinstance`, `list`, `longitudinal_request`, `math.isfinite`, `max`, `max_abs_curvature_ahead`, `min`, `print`, `replace`, `safety_override_reason.strip`, `safety_vehicle_state`, `self._clear_active_command`, `self._completion_feedback`, `self._latched_alerts.append`, `self._pending_feedback.clear`, `self._traffic_scene_for_control`, `self._traffic_stop_approach_active`, `self.fsm.fail`, `self.fsm.safety_override`, `self.fsm.tick`, `self.fuzzy_policy.evaluate`, `self.lateral.step_any`, `self.longitudinal.step`, `self.safety.arbitrate`, `tuple`, `type`.
- `_completion_feedback` 调用：`abs`, `self._clear_active_command`, `self.fsm.complete`.
- `_is_qwen_high_level_plan` 调用：`any`, `envelope.get`, `isinstance`, `item.get`.
- `_traffic_stop_approach_active` 调用：`bool`, `float`, `min`.
- `_traffic_scene_for_control` 调用：`replace`, `self.longitudinal.stop_controller.required_decel_mps2`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 44 行：`ValueError('default_speed_mps must be non-negative and command_timeout_s must be positive')`。
- `clear_safety_alert_prefix`，第 184 行：`ValueError('prefix must be a non-empty string')`。
- `clear_safety_alerts`，第 175 行：`TypeError('alerts must be a tuple of non-empty strings')`。
- `confirm_voice`，第 122 行：`ValueError('command_id must be a non-empty string')`。
- `confirm_voice`，第 124 行：`TypeError('approved must be bool')`。
- `fail_active`，第 224 行：`ValueError('resume_speed_mps must be finite and non-negative')`。
- `release_scenario_stop_hold`，第 196 行：`ValueError('requested_speed_mps must be finite and positive')`。
- `step`，第 255 行：`ValueError('safety_override_reason must be a non-empty string or None')`。
- `step`，第 258 行：`TypeError('speed_cap_mps must be a finite non-negative number or None')`。
- `step`，第 261 行：`ValueError('speed_cap_mps must be a finite non-negative number or None')`。
- `step`，第 337 行：`RuntimeError('fuzzy policy intervened without a longitudinal output')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/behavior_fsm.py](../../../car_control_A/behavior_fsm.py)
- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_B/lateral_controller_base.py](../../../car_control_B/lateral_controller_base.py)
- [car_control_B/path_utils.py](../../../car_control_B/path_utils.py)
- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [integration/perception_bridge.py](../../../integration/perception_bridge.py)
- [integration/voice_adapter.py](../../../integration/voice_adapter.py)

静态 import 消费者（含测试）：

- [integration/__init__.py](../../../integration/__init__.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/demo_offline.py](../../../integration/demo_offline.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-runtime-loop-py"></a>

### `integration/runtime_loop.py`

来源 SHA256：`70ce57169a76b7edc6e58d8fd09ed6c94d4df4a670aa8eab6a92c0b3c70b3aaa`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `ControlRuntime.__init__` / 44 | `default_speed_mps < 0.0 or command_timeout_s <= 0.0` | `raise ValueError('default_speed_mps must be non-negative and command_timeout_s must be positive')` |
| `ControlRuntime.confirm_voice` / 122 | `type(command_id) is not str or not command_id` | `raise ValueError('command_id must be a non-empty string')` |
| `ControlRuntime.confirm_voice` / 124 | `type(approved) is not bool` | `raise TypeError('approved must be bool')` |
| `ControlRuntime.clear_safety_alerts` / 175 | `type(alerts) is not tuple or any((type(alert) is not str or not alert for alert in alerts))` | `raise TypeError('alerts must be a tuple of non-empty strings')` |
| `ControlRuntime.clear_safety_alert_prefix` / 184 | `type(prefix) is not str or not prefix` | `raise ValueError('prefix must be a non-empty string')` |
| `ControlRuntime.release_scenario_stop_hold` / 196 | `not math.isfinite(speed) or speed <= 0.0` | `raise ValueError('requested_speed_mps must be finite and positive')` |
| `ControlRuntime.fail_active` / 224 | `resume_speed_mps is not None AND type(resume_speed_mps) not in (int, float) or isinstance(resume_speed_mps, bool) or (not math.isfinite(float(resume_speed_mps))) or (float(resume_speed_mps) < 0.0)` | `raise ValueError('resume_speed_mps must be finite and non-negative')` |
| `ControlRuntime.step` / 255 | `safety_override_reason is not None and (type(safety_override_reason) is not str or not safety_override_reason.strip())` | `raise ValueError('safety_override_reason must be a non-empty string or None')` |
| `ControlRuntime.step` / 258 | `speed_cap_mps is not None AND type(speed_cap_mps) not in (int, float) or isinstance(speed_cap_mps, bool)` | `raise TypeError('speed_cap_mps must be a finite non-negative number or None')` |
| `ControlRuntime.step` / 261 | `speed_cap_mps is not None AND not math.isfinite(speed_cap_mps) or speed_cap_mps < 0.0` | `raise ValueError('speed_cap_mps must be a finite non-negative number or None')` |
| `ControlRuntime.step` / 337 | `longitudinal is None` | `raise RuntimeError('fuzzy policy intervened without a longitudinal output')` |
