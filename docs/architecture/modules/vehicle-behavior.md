# Command adaptation and behavior state machines

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [授权、确认、过期与停车保持](../functions/command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](../functions/maneuver-progress.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

VoiceCommandAdapter consumes schema_version, command_id, intent, parameters, confidence, status, errors, confirm_required and valid_duration_s. It converts speed to m/s; invalid input becomes unauthorized NO_OP. BehaviorFSM owns confirmation, timeout and terminal feedback. ManeuverFSM owns compiled steps, preconditions, completion, failure and replan. A dataclasses are process-local and require adapters to frozen JSON contracts. Simulator, examples, routing, watchdog and telemetry support offline execution and diagnostics.


## 模块接口与参数核对（2026-09-20）

VoiceCommandAdapter负责外部envelope到A内部命令；BehaviorFSM处理授权、确认、超时与终态，ManeuverFSM处理步骤前置条件、完成/失败和重规划。A DrivingCommand的received_at_s/expires_at_s是内部秒时钟，不直接等同于JSON纳秒deadline。

### 参数语义与生效边界

LongitudinalRequest.requested_speed_mps为请求速度；traffic、lead_distance_m、closing_speed_mps均可缺失。DrivingCommand.target_speed_mps=None不是0速；confirmation_requested与is_ambiguous必须保留，不能丢掉后执行。

### 上下游与修改影响

ExecutionFeedback.completed_at_s/ExecutionStatus需经adapter映射到跨进程协议。新增意图要查语音、canonical、模型、编译器、状态机和验收；新增内部步骤需保留source_step身份。

### [car_control_A/contracts.py](../../../car_control_A/contracts.py) 的入口与声明

```python
RuntimeVehicleState.to_dict(self) -> dict[str, object]
RuntimeVehicleState.from_dict(cls, payload: object) -> RuntimeVehicleState
DrivingCommand.is_expired_at(self, sim_time_s: float) -> bool
DrivingCommand.requires_confirmation(self) -> bool
DrivingCommand.to_dict(self) -> dict[str, object]
DrivingCommand.from_dict(cls, payload: object) -> DrivingCommand
TrafficConstraint.to_dict(self) -> dict[str, object]
TrafficConstraint.from_dict(cls, payload: object) -> TrafficConstraint
LongitudinalRequest.to_dict(self) -> dict[str, object]
LongitudinalRequest.from_dict(cls, payload: object) -> LongitudinalRequest
ControlOutput.to_dict(self) -> dict[str, object]
ControlOutput.from_dict(cls, payload: object) -> ControlOutput
RiskMetrics.to_dict(self) -> dict[str, object]
RiskMetrics.from_dict(cls, payload: object) -> RiskMetrics
LongitudinalOutput.to_dict(self) -> dict[str, object]
LongitudinalOutput.from_dict(cls, payload: object) -> LongitudinalOutput
ExecutionFeedback.is_terminal(self) -> bool
ExecutionFeedback.to_dict(self) -> dict[str, object]
ExecutionFeedback.from_dict(cls, payload: object) -> ExecutionFeedback
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `RuntimeVehicleState.frame` | `int` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.sim_time_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.x_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.y_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.z_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.yaw_deg` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.lane_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.received_at_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.expires_at_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.confidence` | `float` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.action` | `str` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.target_speed_mps` | `float &#124; None` | `None` |
| `DrivingCommand.is_ambiguous` | `bool` | `False` |
| `DrivingCommand.confirmation_requested` | `bool` | `False` |
| `TrafficConstraint.signal_state` | `SignalState` | `无声明默认（构造/赋值方提供）` |
| `TrafficConstraint.distance_to_stop_line_m` | `float &#124; None` | `无声明默认（构造/赋值方提供）` |
| `TrafficConstraint.speed_limit_mps` | `float &#124; None` | `None` |
| `LongitudinalRequest.vehicle` | `RuntimeVehicleState` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalRequest.requested_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalRequest.path_curvature_per_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalRequest.traffic` | `TrafficConstraint &#124; None` | `None` |
| `LongitudinalRequest.lead_distance_m` | `float &#124; None` | `None` |
| `LongitudinalRequest.closing_speed_mps` | `float &#124; None` | `None` |
| `ControlOutput.throttle` | `float` | `无声明默认（构造/赋值方提供）` |
| `ControlOutput.brake` | `float` | `无声明默认（构造/赋值方提供）` |
| `ControlOutput.steer` | `float` | `0.0` |
| `RiskMetrics.ttc_s` | `float &#124; None` | `无声明默认（构造/赋值方提供）` |
| `RiskMetrics.desired_gap_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RiskMetrics.emergency_brake_requested` | `bool` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.control` | `ControlOutput` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.target_accel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.target_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.state` | `str` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.reason` | `str` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.risk` | `RiskMetrics` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.status` | `ExecutionStatus` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.completed_at_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.detail` | `str` | `无声明默认（构造/赋值方提供）` |

### [car_control_A/behavior_fsm.py](../../../car_control_A/behavior_fsm.py) 的入口与声明

```python
BehaviorFSM.__init__(self, *, command_timeout_s: float=15.0) -> None
BehaviorFSM.state(self) -> BehaviorState
BehaviorFSM.submit(self, command: DrivingCommand, *, now_s: float) -> BehaviorResult
BehaviorFSM.confirm(self, command_id: str, *, approved: bool, now_s: float) -> BehaviorResult
BehaviorFSM.complete(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
BehaviorFSM.fail(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
BehaviorFSM.safety_override(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
BehaviorFSM.tick(self, *, now_s: float) -> tuple[ExecutionFeedback, ...]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `BehaviorResult.state` | `BehaviorState` | `无声明默认（构造/赋值方提供）` |
| `BehaviorResult.feedback` | `ExecutionFeedback &#124; None` | `None` |

### [car_control_A/maneuver_fsm.py](../../../car_control_A/maneuver_fsm.py) 的入口与声明

```python
ManeuverFSM.__init__(self, *, replan_cooldown_s: float=2.0, max_replans_per_command: int=2) -> None
ManeuverFSM.current_step(self) -> CompiledPlanStep | None
ManeuverFSM.replan_count(self) -> int
ManeuverFSM.start(self, plan: CompiledManeuverPlan, *, now_s: float) -> ManeuverUpdate
ManeuverFSM.update(self, snapshot: Mapping[str, Any], *, now_s: float) -> ManeuverUpdate
ManeuverFSM.request_replan(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
ManeuverFSM.fail(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `ManeuverEvent.event_type` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.plan_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.step_id` | `str &#124; None` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.state` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.reason_code` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.now_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.state` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.current_step` | `CompiledPlanStep &#124; None` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.events` | `tuple[ManeuverEvent, ...]` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.safe_behavior` | `str &#124; None` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.terminal` | `bool` | `无声明默认（构造/赋值方提供）` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [car_control_A/__init__.py](../../../car_control_A/__init__.py) - module/resource/documentation
- [car_control_A/ARCHITECTURE.md](../../../car_control_A/ARCHITECTURE.md) - module/resource/documentation
- [car_control_A/behavior_fsm.py](../../../car_control_A/behavior_fsm.py) - `BehaviorState`, `BehaviorResult`, `_ActiveCommand`, `BehaviorFSM`, `BehaviorFSM.state`, `BehaviorFSM.submit`, `BehaviorFSM.confirm`, `BehaviorFSM.complete`, `BehaviorFSM.fail`, `BehaviorFSM.safety_override`, `BehaviorFSM.tick`
- [car_control_A/contracts.py](../../../car_control_A/contracts.py) - `_number`, `_integer`, `_text`, `_boolean`, `_payload`, `SignalState`, `RuntimeVehicleState`, `RuntimeVehicleState.to_dict`, `RuntimeVehicleState.from_dict`, `DrivingCommand`, `DrivingCommand.is_expired_at`, `DrivingCommand.requires_confirmation`, `DrivingCommand.to_dict`, `DrivingCommand.from_dict`, `TrafficConstraint`, `TrafficConstraint.to_dict`, `TrafficConstraint.from_dict`, `LongitudinalRequest`, `LongitudinalRequest.to_dict`, `LongitudinalRequest.from_dict`, `ControlOutput`, `ControlOutput.to_dict`, `ControlOutput.from_dict`, `RiskMetrics`, `RiskMetrics.to_dict`, `RiskMetrics.from_dict`, `LongitudinalOutput`, `LongitudinalOutput.to_dict`, `LongitudinalOutput.from_dict`, `ExecutionStatus`, `ExecutionFeedback`, `ExecutionFeedback.is_terminal`, `ExecutionFeedback.to_dict`, `ExecutionFeedback.from_dict`
- [car_control_A/examples/qwen_change_lane_rejected.json](../../../car_control_A/examples/qwen_change_lane_rejected.json) - module/resource/documentation
- [car_control_A/examples/qwen_keep_lane.json](../../../car_control_A/examples/qwen_keep_lane.json) - module/resource/documentation
- [car_control_A/examples/qwen_set_speed_20.json](../../../car_control_A/examples/qwen_set_speed_20.json) - module/resource/documentation
- [car_control_A/examples/qwen_slow_down.json](../../../car_control_A/examples/qwen_slow_down.json) - module/resource/documentation
- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py) - `is_high_level_command`, `HighLevelCommandAdapter`, `HighLevelCommandAdapter.adapt`, `_speed_parameters`, `_direction_parameters`, `_source_text`, `_required_text`, `_optional_text`, `_safe_text`, `_confidence`, `_bounded_confidence`, `_nonnegative_number`, `_positive_number`, `_optional_timestamp`, `_optional_timestamp_lenient`, `_confirmation_requested`
- [car_control_A/maneuver_fsm.py](../../../car_control_A/maneuver_fsm.py) - `ManeuverEvent`, `ManeuverUpdate`, `ManeuverFSM`, `ManeuverFSM.current_step`, `ManeuverFSM.replan_count`, `ManeuverFSM.start`, `ManeuverFSM.update`, `ManeuverFSM.request_replan`, `ManeuverFSM.fail`, `_time`, `_precondition_satisfied`, `_completion_satisfied`
- [car_control_A/README.md](../../../car_control_A/README.md) - module/resource/documentation
- [car_control_A/routing.py](../../../car_control_A/routing.py) - `RouteReference`, `LateralController`, `LateralController.steer`
- [car_control_A/RUN.md](../../../car_control_A/RUN.md) - module/resource/documentation
- [car_control_A/simulator.py](../../../car_control_A/simulator.py) - `_clone_world_settings`, `SensorFrameBuffer`, `SensorFrameBuffer.pending_frames`, `SensorFrameBuffer.push`, `SensorFrameBuffer.callback`, `SensorFrameBuffer.pop_aligned`, `SensorFrameBuffer.pop_aligned_optional`, `ActorRegistry`, `ActorRegistry.track`, `ActorRegistry.release`, `ActorRegistry.cleanup`, `ActorRegistry.dispose`, `SynchronousWorld`, `SynchronousWorld.tick`, `CarlaSession`, `CarlaSession.track_actor`, `CarlaSession.tick`, `CarlaSession.spawn_ego`, `CarlaSession.attach_sensor`
- [car_control_A/telemetry.py](../../../car_control_A/telemetry.py) - `LatencyTrace`, `LatencyTrace.mark`, `LatencyTrace.segment_ms`, `LatencyTrace.end_to_end_ms`, `LatencyTrace.to_dict`, `LatencyTrace.append_jsonl`
- [car_control_A/watchdog.py](../../../car_control_A/watchdog.py) - `RuntimeWatchdog`, `RuntimeWatchdog.heartbeat`, `RuntimeWatchdog.pause`, `RuntimeWatchdog.resume`, `RuntimeWatchdog.check`, `RuntimeWatchdog.module_failed`
- [integration/voice_adapter.py](../../../integration/voice_adapter.py) - `VoiceDiagnostic`, `VoiceCommandMetadata`, `AdaptedVoiceCommand`, `VoiceCommandAdapter`, `VoiceCommandAdapter.adapt`, `_speed_command_fields`, `_required_text`, `_nonnegative_number`, `_positive_number`, `_confidence`, `_optional_bool`, `_diagnostic_tuple`, `_diagnostic_tuple_lenient`, `_safe_text`, `_optional_timestamp`, `_optional_timestamp_lenient`

## Dependencies and coordinated changes


## Validation entry points

`python -m pytest car_control_A/tests integration/tests/test_voice_adapter.py integration/tests/test_voice_compound_routing.py integration/tests/test_voice_qwen_semantic_coverage.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [car_control_A/__init__.py](../functions/car_control_A--__init__--py.md)
- [car_control_A/behavior_fsm.py](../functions/car_control_A--behavior_fsm--py.md)
- [car_control_A/contracts.py](../functions/car_control_A--contracts--py.md)
- [car_control_A/high_level_command.py](../functions/car_control_A--high_level_command--py.md)
- [car_control_A/maneuver_fsm.py](../functions/car_control_A--maneuver_fsm--py.md)
- [car_control_A/routing.py](../functions/car_control_A--routing--py.md)
- [car_control_A/simulator.py](../functions/car_control_A--simulator--py.md)
- [car_control_A/telemetry.py](../functions/car_control_A--telemetry--py.md)
- [car_control_A/watchdog.py](../functions/car_control_A--watchdog--py.md)
- [integration/voice_adapter.py](../functions/integration--voice_adapter--py.md)

## 诊断与维护交接

本模块证据：授权、step、feedback、terminal原因；单步成功不等于任务完成。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_A/tests/test_ac_integration.py`

来源 SHA256：`1151052543e8735a3af5ed653f56e206f63a9ccc5095344bbb1756602a212796`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_behavior_fsm.py`

来源 SHA256：`fc85a3fc22b65a40e479ae54ea2763195f41d2cb2cf716d61652183416355230`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_contracts.py`

来源 SHA256：`2e545d58d2c7de079f5df165255bd1b1714d91f3ca402c7bfc48d21514bf66c2`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_high_level_command.py`

来源 SHA256：`be9afb03bfdd979db698bf66eb92174990e81070fbeb79dd86afe7038a9a1c89`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_maneuver_fsm.py`

来源 SHA256：`a6c27950fa22c1891f0fd9032cf4a5b0b532053d2bf27723204e2914b3d9bb26`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_routing.py`

来源 SHA256：`f6c7557a6f03fa53210de0554740f1868cdd13247c4173d292226ee39a1afe3c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_simulator.py`

来源 SHA256：`a9ee20724d0ee7c6361817727c90197c34b75d06dd0bfbd5592b689d60fe9b39`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_world_settings_restore_even_if_traffic_manager_restore_fails.FailingRestoreTrafficManager.set_synchronous_mode` / 88 | `enabled is False` | `raise RuntimeError('TM unavailable')` |
| `test_world_and_tm_restore_when_tm_enable_changes_state_then_raises.FailingEnableTrafficManager.set_synchronous_mode` / 104 | `enabled is True` | `raise RuntimeError('TM enabled then failed')` |
| `test_exit_clears_sync_state_when_world_restore_raises_and_preserves_business_error` / 143 | `本地无直接if；检查上下文` | `raise ValueError('business failure')` |
| `test_exit_clears_sync_state_when_world_restore_raises_and_preserves_business_error.FailingRestoreWorld.apply_settings` / 124 | `self.fail_restore` | `raise RuntimeError('restore failed')` |
| `test_attach_sensor_validates_before_spawn_and_immediately_releases_listen_failure.FailingSensor.listen` / 203 | `本地无直接if；检查上下文` | `raise RuntimeError('listen failed')` |
| `test_actor_registry_cleans_every_actor_when_one_destroy_fails.BrokenActor.destroy` / 231 | `本地无直接if；检查上下文` | `raise RuntimeError('network lost')` |
### `car_control_A/tests/test_simulator_smoke.py`

来源 SHA256：`54219e701114d4817cf90fceaad22fa2fde63bc8e486e1861517539c8c8e38cb`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_telemetry.py`

来源 SHA256：`183be80c6f2f9996d113ab72da98f63c8dcf18bc5e04d1e55a33e73ad41b1ac2`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_trace_rejects_non_monotonic_and_duplicate_stage` / 27 | `本地无直接if；检查上下文` | `raise AssertionError('expected duplicate stage rejection')` |
| `test_trace_rejects_non_monotonic_and_duplicate_stage` / 33 | `本地无直接if；检查上下文` | `raise AssertionError('expected non-monotonic rejection')` |
### `car_control_A/tests/test_watchdog.py`

来源 SHA256：`aef4d6383111acfe32ae67dd35b3b465b4767f6bf18f795bfce7e6356effcef2`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `car_control_A/tests/test_simulator_smoke.py:10` | `'CARLA_SMOKE'` | `None（未传默认）` |
