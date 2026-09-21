# Final safety, feedback and scoring

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [C/D分工与实时仲裁](../functions/longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](../functions/control-frame.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

SafetySupervisor.arbitrate consumes raw B/C control, vehicle/command/risk state and watchdog alerts; returns SafetyDecision with raw_control, final_control, safety_override and reason. Invalid output, throttle/brake conflict, collision and low TTC trigger overrides. DControlRuntime wraps canonical ControlCommand/PerceptionState validation and feedback but is not used by the live runner, which calls SafetySupervisor through ControlRuntime. A and D feedback objects require mapping. Metrics, benchmark, event logger and official_score supply repository evidence; this score is not proof of unpublished official scoring.


## 模块接口与参数核对（2026-09-20）

SafetySupervisor.arbitrate消费raw control、车辆/命令/风险及告警，生成安全决定；实时链由ControlRuntime调用。DControlRuntime是canonical封装，不能以其测试替代实时入口验收。

### 参数语义与生效边界

SafetyConfig多数默认来自DEFAULT_STRATEGY；emergency_reaction_time_s=0.35、emergency_deceleration_mps2=6、range_uncertainty_buffer_m=1为类声明默认。runner可通过DrivingPolicy重建SafetyConfig，不能把默认表当实际run配置。

### 上下游与修改影响

安全覆盖、制动值和任务终态必须分别记录。低TTC、控制非法、碰撞与watchdog来源不同；先查首次原因，不能只看WATCHDOG_ALERT。修改阈值需联动感知风险、C规划、policy覆盖、反馈映射及场景验收。

## 第7模块逐入口精读结论（2026-09-21）

### 两条接线与控制权边界

当前生产实时链是 `integration.ControlRuntime.step → SafetySupervisor.arbitrate → FrameResult.final_control`，外层负责 safety latch、告警清除、命令 FSM 和 CARLA apply；D 本身逐帧无状态。`DControlRuntime.apply` 是 canonical `ControlCommand/PerceptionState` 的另一层封装：它经 `InterfaceRegistry` 校验输入、生成 execution feedback，并测量仲裁时延/cadence，但当前 live runner 不调用它。两者共享 `SafetySupervisor`，测试其中一条不能替代另一条的闭环验收。

最终安全决定包含 `raw_control` 与 `final_control`，便于证明覆盖前后差异。实时 runner 后仍存在 R05 所列“D 后启动宽限期全制动”执行例外；因此“D 是最后仲裁者”指正常控制授权边界，不应解释为此后绝无任何安全制动写入。

### 输入收敛、单位与 fail-closed 顺序

- control adapter 缺失三轴按 0 处理，但 validator 要求 steer `[-1,1]`、throttle/brake `[0,1]`，并以两者同时大于 `0.03` 判冲突。
- vehicle view 使用 m、m/s、仿真秒和 1/m；距离/速度/传感器裕量不得为负。Risk 的 TTC 为秒、desired gap 为米。dataclass 本身只是容器，直接构造不会执行 adapter/validator 约束。
- command adapter 支持兼容别名，但 command validator 只检查 schema、ID、intent、置信度及 CHANGE_LANE/SET_SPEED 的最低参数形状。UNKNOWN/歧义是 warning，进入 supervisor 后仍会停车等待或拒绝。
- supervisor 的主 reason 按代码首个命中分支确定：非法控制/状态/风险、watchdog、碰撞/闯灯、命令停止或拒绝、风险急停、低 TTC、动态前距、停止线、路线/车道、caution TTC。`risk_metrics` 保存输入与动态阈值；多个风险同帧存在时不能只凭主 reason 推断其他风险未发生。

动态前距取三者最大值：策略 `dynamic_safety_distance` 的 emergency distance、`SafetyConfig.min_front_distance_m`、以及本配置 `range buffer + v*reaction + v²/(2*deceleration)`。路线阈值随速度和曲率收紧；严重偏航分支只允许零油门和受限转向，不消费保留字段 `route_recovery_throttle/route_recovery_max_speed_mps` 来主动推进。

### 命令终态、测量和评分证据等级

`ExecutionFeedbackTracker` 在进程内保证同一 ID 最多一个终态；receipt→apply 使用单调纳秒并输出毫秒。重复终态返回第一次结果，`fail_unfinished` 才会在关停时补 FAILED。完整反馈由 `InterfaceRegistry` 验证；`validate_execution_feedback` 只是“ID + 终态枚举”的浅检查，不能替代 schema Gate。

benchmark 只量测纯 Python 仲裁与无障碍直线 `ControlRuntime.step` 热路径；ScenarioRecorder 的 JSONL 是追加写、JSON 汇总是覆盖写，且没有原子提交或运行身份 manifest。`official_score.py` 实现仓库内 25/10/5 扣分和固定 30/40/30 完成率权重，未绑定赛事发布的评分版本，文件名不能作为官方一致性证明。

### 已复现边界 M07-01（未修复）

对同一 `command_id`，第一次 `DControlRuntime.apply` 因 emergency risk 生成终态 `SAFETY_OVERRIDE`；第二次在风险解除、仲裁 reason=`NONE` 时，`final_control` 可恢复为 throttle=0.2/brake=0，但 tracker 因“最多一个终态”仍返回第一次 `SAFETY_OVERRIDE`，且 unfinished 列表为空。即控制输出已经继续执行，生命周期却保持终态。当前 live runner 不使用该封装，所以不能扩大为已确认 CARLA 实车故障；若 canonical D 接入生产，必须明确安全覆盖是“命令永久终止”还是“帧级事件”，并据此禁止终态后推进或引入新的 command/attempt ID。

### 修改联动清单

改 `SafetyConfig`/优先级需同时核对 `config.strategy`、DrivingPolicy override、C 风险输出、runtime latch/恢复和场景 reason 断言；改 command view 需核对 canonical behavior、目标字段和 Qwen 多步计划；改 feedback 需核对 interface schema、终态监控和评分消费者；改日志/计分必须同步 manifest、原始事件和官方规则版本，不能通过重命名报告提升证据等级。

### [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py) 的入口与声明

```python
SafetySupervisor.__init__(self, config: Optional[SafetyConfig]=None) -> None
SafetySupervisor.arbitrate(self, raw_control: Any, vehicle_state: Any=None, command: Any=None, risk: Any=None, watchdog_alerts: Optional[Iterable[str]]=None) -> SafetyDecision
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `SafetyConfig.min_front_distance_m` | `float` | `DEFAULT_STRATEGY.safety_distance.minimum_emergency_distance_m` |
| `SafetyConfig.low_ttc_s` | `float` | `DEFAULT_STRATEGY.common.emergency_ttc_s` |
| `SafetyConfig.caution_ttc_s` | `float` | `DEFAULT_STRATEGY.common.caution_ttc_s` |
| `SafetyConfig.stop_line_guard_m` | `float` | `DEFAULT_STRATEGY.supervisor.stop_line_guard_m` |
| `SafetyConfig.max_lane_offset_m` | `float` | `DEFAULT_STRATEGY.supervisor.max_lane_offset_m` |
| `SafetyConfig.minimum_lane_offset_m` | `float` | `DEFAULT_STRATEGY.supervisor.minimum_lane_offset_m` |
| `SafetyConfig.severe_route_deviation_m` | `float` | `DEFAULT_STRATEGY.supervisor.severe_route_deviation_m` |
| `SafetyConfig.minimum_severe_route_deviation_m` | `float` | `DEFAULT_STRATEGY.supervisor.minimum_severe_route_deviation_m` |
| `SafetyConfig.route_speed_sensitivity` | `float` | `DEFAULT_STRATEGY.supervisor.route_speed_sensitivity` |
| `SafetyConfig.route_curvature_sensitivity` | `float` | `DEFAULT_STRATEGY.supervisor.route_curvature_sensitivity` |
| `SafetyConfig.route_recovery_max_speed_mps` | `float` | `DEFAULT_STRATEGY.supervisor.route_recovery_max_speed_mps` |
| `SafetyConfig.route_recovery_throttle` | `float` | `DEFAULT_STRATEGY.supervisor.route_recovery_throttle` |
| `SafetyConfig.route_recovery_steer_limit` | `float` | `DEFAULT_STRATEGY.supervisor.route_recovery_steer_limit` |
| `SafetyConfig.route_deviation_brake` | `float` | `DEFAULT_STRATEGY.supervisor.route_deviation_brake` |
| `SafetyConfig.low_confidence_threshold` | `float` | `DEFAULT_STRATEGY.common.command_confidence_threshold` |
| `SafetyConfig.hold_brake` | `float` | `DEFAULT_STRATEGY.common.hold_brake` |
| `SafetyConfig.emergency_brake` | `float` | `DEFAULT_STRATEGY.common.emergency_brake` |
| `SafetyConfig.caution_brake` | `float` | `DEFAULT_STRATEGY.supervisor.caution_brake` |
| `SafetyConfig.standstill_speed_mps` | `float` | `DEFAULT_STRATEGY.common.standstill_speed_mps` |
| `SafetyConfig.emergency_reaction_time_s` | `float` | `0.35` |
| `SafetyConfig.emergency_deceleration_mps2` | `float` | `6.0` |
| `SafetyConfig.range_uncertainty_buffer_m` | `float` | `1.0` |

### [integration/runtime_loop.py](../../../integration/runtime_loop.py) 的入口与声明

```python
ControlRuntime.__init__(self, lateral: LateralController, *, longitudinal: LongitudinalController | None=None, safety: SafetySupervisor | None=None, voice_adapter: VoiceCommandAdapter | None=None, default_speed_mps: float=5.0, command_timeout_s: float=15.0) -> None
ControlRuntime.yellow_clear_committed(self) -> bool
ControlRuntime.submit_voice(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand
ControlRuntime.safety_latched(self) -> bool
ControlRuntime.active_command_id(self) -> str | None
ControlRuntime.confirm_voice(self, command_id: str, *, approved: bool, now_s: float) -> ExecutionFeedback | None
ControlRuntime.reset_safety_latch(self) -> None
ControlRuntime.clear_safety_alerts(self, alerts: tuple[str, ...]) -> None
ControlRuntime.clear_safety_alert_prefix(self, prefix: str) -> tuple[str, ...]
ControlRuntime.release_scenario_stop_hold(self, *, requested_speed_mps: float) -> bool
ControlRuntime.fail_active(self, *, now_s: float, detail: str, resume_speed_mps: float | None=None) -> ExecutionFeedback | None
ControlRuntime.complete_active(self, *, now_s: float, detail: str) -> ExecutionFeedback | None
ControlRuntime.step(self, vehicle: RuntimeVehicleState, scene: PerceptionFrame, route: RouteReference, *, dt_s: float, watchdog_alerts: tuple[str, ...]=(), raw_control_override: object | None=None, speed_cap_mps: float | None=None, safety_override_reason: str | None=None) -> FrameResult
```

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [car_control_D/__init__.py](../../../car_control_D/__init__.py) - module/resource/documentation
- [car_control_D/adapters.py](../../../car_control_D/adapters.py) - `_as_mapping`, `optional_float`, `_get`, `adapt_control`, `adapt_command`, `adapt_vehicle_state`, `adapt_risk`
- [car_control_D/benchmark.py](../../../car_control_D/benchmark.py) - `_percentile_ms`, `_summary`, `_measure`, `run_control_safety_benchmark`
- [car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py) - `FinalControlFrame`, `DControlRuntime`, `DControlRuntime.apply`, `DControlRuntime.complete`, `DControlRuntime.metrics`
- [car_control_D/demo_fake_integration.py](../../../car_control_D/demo_fake_integration.py) - `main`
- [car_control_D/event_logger.py](../../../car_control_D/event_logger.py) - `ensure_dir`, `append_jsonl`, `write_json`
- [car_control_D/execution_feedback.py](../../../car_control_D/execution_feedback.py) - `_Lifecycle`, `ExecutionFeedbackTracker`, `ExecutionFeedbackTracker.received`, `ExecutionFeedbackTracker.executing`, `ExecutionFeedbackTracker.finish`, `ExecutionFeedbackTracker.safety_override`, `ExecutionFeedbackTracker.fail_unfinished`, `ExecutionFeedbackTracker.events`, `ExecutionFeedbackTracker.unfinished_command_ids`
- [car_control_D/metrics.py](../../../car_control_D/metrics.py) - `ScenarioRecorder`, `ScenarioRecorder.log_event`, `ScenarioRecorder.log_frame`, `ScenarioRecorder.log_command`, `ScenarioRecorder.write_result`, `ScenarioRecorder.write_score_report`
- [car_control_D/official_score.py](../../../car_control_D/official_score.py) - `ScoreBreakdown`, `ScoreBreakdown.to_dict`, `calculate_deduction`, `score_scenario`, `weighted_completion_score`, `latency_report`, `OfficialScorer`, `OfficialScorer.score_scenario`, `OfficialScorer.summarize`
- [car_control_D/README.md](../../../car_control_D/README.md) - module/resource/documentation
- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py) - `SafetyConfig`, `SafetySupervisor`, `SafetySupervisor.arbitrate`
- [car_control_D/scenario_runner.py](../../../car_control_D/scenario_runner.py) - `ScenarioRunner`, `ScenarioRunner.run`
- [car_control_D/schemas.py](../../../car_control_D/schemas.py) - `ControlOutput`, `ControlOutput.to_dict`, `CommandView`, `CommandView.to_dict`, `VehicleStateView`, `VehicleStateView.to_dict`, `RiskView`, `RiskView.to_dict`, `SafetyDecision`, `SafetyDecision.to_dict`, `ValidationResult`, `ValidationResult.to_dict`, `ScenarioResult`, `ScenarioResult.to_dict`
- [car_control_D/validators.py](../../../car_control_D/validators.py) - `_finite_number`, `validate_control`, `validate_command`, `validate_execution_feedback`

## Dependencies and coordinated changes


## Validation entry points

`python -m pytest car_control_D/tests integration/tests/test_role_d_control_runtime.py integration/tests/test_basic_track_scorecard.py`

2026-09-21 在工作树根目录执行上述入口：**35 passed in 0.53s**。结果覆盖当前 D 单元、canonical runtime 和基础评分回归，不包含 CARLA、远端模型、真实传感器、跨线程时序或赛事官方评分一致性。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [car_control_D/__init__.py](../functions/car_control_D--__init__--py.md)
- [car_control_D/adapters.py](../functions/car_control_D--adapters--py.md)
- [car_control_D/benchmark.py](../functions/car_control_D--benchmark--py.md)
- [car_control_D/control_runtime.py](../functions/car_control_D--control_runtime--py.md)
- [car_control_D/demo_fake_integration.py](../functions/car_control_D--demo_fake_integration--py.md)
- [car_control_D/event_logger.py](../functions/car_control_D--event_logger--py.md)
- [car_control_D/execution_feedback.py](../functions/car_control_D--execution_feedback--py.md)
- [car_control_D/metrics.py](../functions/car_control_D--metrics--py.md)
- [car_control_D/official_score.py](../functions/car_control_D--official_score--py.md)
- [car_control_D/safety_supervisor.py](../functions/car_control_D--safety_supervisor--py.md)
- [car_control_D/scenario_runner.py](../functions/car_control_D--scenario_runner--py.md)
- [car_control_D/schemas.py](../functions/car_control_D--schemas--py.md)
- [car_control_D/validators.py](../functions/car_control_D--validators--py.md)

## 诊断与维护交接

本模块证据：首次runtime_alerts、锁存/复位、brake；long首故障待证。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

专项记录：[WATCHDOG_ALERT与持续停车](../functions/watchdog-diagnosis.md)。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/tests/test_benchmark.py`

来源 SHA256：`674439120085ab0b7a4838db547719d182e85804e439460e893aaedeb46568cd`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_D/tests/test_official_score.py`

来源 SHA256：`2bb905adca2cd32c5ab11b40b198d22f4054d8b570360d35049c91096481e597`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_D/tests/test_safety_supervisor.py`

来源 SHA256：`c0aa30b411d79d6132629c25f4a81e50bde462be938789011d090ac81464ba40`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_D/tests/test_validators.py`

来源 SHA256：`f0ee2048f156386747c642562577e2d775ba09f0acd9323dba41f161ff91e325`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
