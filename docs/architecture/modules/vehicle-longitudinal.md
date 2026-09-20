# Longitudinal control and conservative sensing

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [目标速度、跟车风险与D交接](../functions/longitudinal-safety-contract.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

LongitudinalController combines speed planning, following, stopping, traffic rules and PID. Inputs include target speed, lead gap/speed, stop line, traffic light and curvature. Units are m, m/s, m/s^2 and TTC seconds; throttle/brake are normalized. FuzzyCommandPolicy handles local command constraints; ConservativeSensorFusion handles missing frames, TTC and vulnerable road users. C sensor_adapter/rgb_pipeline/fusion_tracker are delivery helpers distinct from perception package. Parameters mostly inherit config.strategy.DEFAULT_STRATEGY. SafetySupervisor arbitrates downstream.


## 模块接口与参数核对（2026-09-20）

LongitudinalController.step(LongitudinalRequest,dt_s)返回LongitudinalOutput：control、目标加速度/速度、state/reason和risk。调用者为ControlRuntime；下游D仍可覆盖C控制。归一化throttle/brake不是m/s²。

### 参数语义与生效边界

FollowingController.desired_gap_m=standstill_gap+time_gap*速度+sensor_base_margin+sensor_uncertainty_time*速度。风险计算在距离/接近速度缺失或接近速度<=0时TTC为None、emergency为False；这只是此函数的输出，不代表整个系统确认安全。speed_cap在测量缺失时返回None。

### 上下游与修改影响

跟车速度上限为max(0,ego-closing)+sqrt(2*comfortable_decel*max(0,gap-desired))，再取非负。参数验证要求有限值，time_gap/emergency_ttc/comfortable_decel为正。修改PID/风险需检查speed planner、停车保持、D及目标切换。

### [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py) 的入口与声明

```python
LongitudinalController.__init__(self, parameters: LongitudinalParameters | None=None) -> None
LongitudinalController.step(self, request: LongitudinalRequest, dt_s: float) -> LongitudinalOutput
LongitudinalController.reset(self) -> None
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `LongitudinalParameters.max_lateral_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.max_lateral_accel_mps2` |
| `LongitudinalParameters.command_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.command_accel_mps2` |
| `LongitudinalParameters.command_decel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.command_decel_mps2` |
| `LongitudinalParameters.max_accel_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.max_accel_mps2` |
| `LongitudinalParameters.max_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.max_decel_mps2` |
| `LongitudinalParameters.max_control_delta_per_s` | `float` | `DEFAULT_STRATEGY.longitudinal.max_control_delta_per_s` |
| `LongitudinalParameters.hold_brake` | `float` | `DEFAULT_STRATEGY.common.hold_brake` |
| `LongitudinalParameters.emergency_brake` | `float` | `DEFAULT_STRATEGY.common.emergency_brake` |
| `LongitudinalParameters.standstill_gap_m` | `float` | `DEFAULT_STRATEGY.safety_distance.standstill_gap_m` |
| `LongitudinalParameters.time_gap_s` | `float` | `DEFAULT_STRATEGY.safety_distance.reaction_time_s` |
| `LongitudinalParameters.emergency_ttc_s` | `float` | `DEFAULT_STRATEGY.common.emergency_ttc_s` |
| `LongitudinalParameters.comfortable_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.comfortable_decel_mps2` |

### [car_control_C/following_controller.py](../../../car_control_C/following_controller.py) 的入口与声明

```python
FollowingController.__init__(self, parameters: FollowingParameters | None=None) -> None
FollowingController.desired_gap_m(self, ego_speed_mps: float) -> float
FollowingController.risk(self, *, ego_speed_mps: float, lead_distance_m: float | None, closing_speed_mps: float | None) -> RiskMetrics
FollowingController.speed_cap_mps(self, *, ego_speed_mps: float, lead_distance_m: float | None, closing_speed_mps: float | None) -> float | None
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `FollowingParameters.standstill_gap_m` | `float` | `DEFAULT_STRATEGY.safety_distance.standstill_gap_m` |
| `FollowingParameters.time_gap_s` | `float` | `DEFAULT_STRATEGY.safety_distance.reaction_time_s` |
| `FollowingParameters.emergency_ttc_s` | `float` | `DEFAULT_STRATEGY.common.emergency_ttc_s` |
| `FollowingParameters.comfortable_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.comfortable_decel_mps2` |

### [car_control_C/speed_pid.py](../../../car_control_C/speed_pid.py) 的入口与声明

```python
SpeedPID.__init__(self, kp: float=DEFAULT_STRATEGY.longitudinal.pid_kp, ki: float=DEFAULT_STRATEGY.longitudinal.pid_ki, kd: float=DEFAULT_STRATEGY.longitudinal.pid_kd, integral_limit: float=DEFAULT_STRATEGY.longitudinal.pid_integral_limit, accel_min_mps2: float=-DEFAULT_STRATEGY.common.max_decel_mps2, accel_max_mps2: float=DEFAULT_STRATEGY.longitudinal.max_accel_mps2, target_step_reset_mps: float=DEFAULT_STRATEGY.longitudinal.pid_target_step_reset_mps) -> None
SpeedPID.reset(self) -> None
SpeedPID.step(self, target_speed_mps: float, speed_mps: float, dt_s: float) -> float
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `PIDParameters.kp` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_kp` |
| `PIDParameters.ki` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_ki` |
| `PIDParameters.kd` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_kd` |
| `PIDParameters.integral_limit` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_integral_limit` |
| `PIDParameters.accel_min_mps2` | `float` | `-DEFAULT_STRATEGY.common.max_decel_mps2` |
| `PIDParameters.accel_max_mps2` | `float` | `DEFAULT_STRATEGY.longitudinal.max_accel_mps2` |
| `PIDParameters.target_step_reset_mps` | `float` | `DEFAULT_STRATEGY.longitudinal.pid_target_step_reset_mps` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [car_control_C/__init__.py](../../../car_control_C/__init__.py) - module/resource/documentation
- [car_control_C/config.py](../../../car_control_C/config.py) - `_finite`, `FuzzyCommandPolicyConfig`, `FuzzyCommandPolicyConfig.to_dict`, `FuzzyCommandPolicyConfig.from_dict`
- [car_control_C/fault_injection.sh](../../../car_control_C/fault_injection.sh) - module/resource/documentation
- [car_control_C/following_controller.py](../../../car_control_C/following_controller.py) - `FollowingParameters`, `FollowingController`, `FollowingController.desired_gap_m`, `FollowingController.risk`, `FollowingController.speed_cap_mps`
- [car_control_C/fusion_tracker.py](../../../car_control_C/fusion_tracker.py) - `PerceptionTarget`, `PerceptionTarget.to_dict`, `StableTargetTracker`, `StableTargetTracker.update`
- [car_control_C/fuzzy_command_policy.py](../../../car_control_C/fuzzy_command_policy.py) - `FuzzyCommandDecision`, `FuzzyCommandPolicy`, `FuzzyCommandPolicy.evaluate`
- [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py) - `LongitudinalParameters`, `LongitudinalController`, `LongitudinalController.step`, `LongitudinalController.reset`
- [car_control_C/perception_state.json](../../../car_control_C/perception_state.json) - module/resource/documentation
- [car_control_C/README.md](../../../car_control_C/README.md) - module/resource/documentation
- [car_control_C/rgb_pipeline.py](../../../car_control_C/rgb_pipeline.py) - `RgbDetection`, `RgbDetection.to_dict`, `RgbPipelineSummary`, `RgbPipelineSummary.to_dict`, `_nearest_rank_p95`, `summarize_rgb_pipeline`
- [car_control_C/safety_state.py](../../../car_control_C/safety_state.py) - `_optional_non_negative`, `_source`, `VisualObservation`, `VisualObservation.unavailable`, `SafetyStateParameters`, `SafetyStateSummary`, `SafetyStateSummary.fail_closed`, `SafetyStateSummary.to_dict`, `ConservativeSensorFusion`, `ConservativeSensorFusion.reset`, `ConservativeSensorFusion.update`, `ConservativeSensorFusion.fail_closed_control`
- [car_control_C/sensor_adapter.py](../../../car_control_C/sensor_adapter.py) - `SensorFrameStamp`, `SensorFrameStamp.to_dict`, `SensorAudit`, `SensorAudit.to_dict`, `build_sensor_audit`
- [car_control_C/speed_pid.py](../../../car_control_C/speed_pid.py) - `PIDParameters`, `SpeedPID`, `SpeedPID.reset`, `SpeedPID.step`
- [car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py) - `SpeedPlannerParameters`, `SpeedPlan`, `SpeedPlan.to_dict`, `SpeedPlanner`, `SpeedPlanner.plan`, `SpeedPlanner.reset`
- [car_control_C/stop_controller.py](../../../car_control_C/stop_controller.py) - `StopState`, `StopParameters`, `StopController`, `StopController.state_for`, `StopController.speed_cap_mps`, `StopController.required_decel_mps2`
- [car_control_C/traffic_rules.py](../../../car_control_C/traffic_rules.py) - `TrafficRulePlanner`, `TrafficRulePlanner.stop_required`, `TrafficRulePlanner.speed_limit_mps`, `TrafficRulePlanner.stop_distance_m`
- [car_control_C/validation/README.md](../../../car_control_C/validation/README.md) - module/resource/documentation
- [car_control_C/validation.py](../../../car_control_C/validation.py) - `finite`

## Dependencies and coordinated changes


## Validation entry points

`python -m pytest car_control_C/tests integration/tests/test_role_c_perception.py integration/tests/test_perception_bridge.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [car_control_C/__init__.py](../functions/car_control_C--__init__--py.md)
- [car_control_C/config.py](../functions/car_control_C--config--py.md)
- [car_control_C/fault_injection.sh](../functions/car_control_C--fault_injection--sh.md)
- [car_control_C/following_controller.py](../functions/car_control_C--following_controller--py.md)
- [car_control_C/fusion_tracker.py](../functions/car_control_C--fusion_tracker--py.md)
- [car_control_C/fuzzy_command_policy.py](../functions/car_control_C--fuzzy_command_policy--py.md)
- [car_control_C/longitudinal_controller.py](../functions/car_control_C--longitudinal_controller--py.md)
- [car_control_C/rgb_pipeline.py](../functions/car_control_C--rgb_pipeline--py.md)
- [car_control_C/safety_state.py](../functions/car_control_C--safety_state--py.md)
- [car_control_C/sensor_adapter.py](../functions/car_control_C--sensor_adapter--py.md)
- [car_control_C/speed_pid.py](../functions/car_control_C--speed_pid--py.md)
- [car_control_C/speed_planner.py](../functions/car_control_C--speed_planner--py.md)
- [car_control_C/stop_controller.py](../functions/car_control_C--stop_controller--py.md)
- [car_control_C/traffic_rules.py](../functions/car_control_C--traffic_rules--py.md)
- [car_control_C/validation.py](../functions/car_control_C--validation--py.md)

## 诊断与维护交接

本模块证据：速度/距离/TTC、C/D输出；核对单位和最终执行值。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/tests/test_c_deliverables.py`

来源 SHA256：`ff83ecb5190a12612c2acbcb414afae3d0d3895431bc3554125bec5a1480e454`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_C/tests/test_fuzzy_command_policy.py`

来源 SHA256：`4e98f57795c07bf9bb15d9b67e90354f238192dcba7a9298c57e4da745e82209`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_C/tests/test_longitudinal.py`

来源 SHA256：`007a7f6bcebd8f0df2494b4bd2b46ee0004859024ecc26f62650e65858b935d3`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_C/tests/test_safety_state.py`

来源 SHA256：`1fde6f1596d35a79d819f5c2de8ba532fc8409b5fc4307ef914be7a947fa7a04`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_C/tests/test_strategy_generalization.py`

来源 SHA256：`8ef0b768c40df7533f6e47dacd9caa141ba18a634f5f14442f9f3185f039c39e`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
