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

## 第5模块逐项精读结论（2026-09-21）

本轮按当前 `challenge` 实现逐入口复核了 `car_control_C` 的13份有实际声明的功能页，原来的83处“需阅读函数体”占位说明均已替换为可检查的参数消费、返回值、状态变化、异常和调用关系。这里只记录代码已经具备的语义；没有把静态阅读写成 CARLA 闭环通过。

### 生产调用链和控制权

1. `integration.perception_bridge.longitudinal_request` 要求车辆与场景的 `frame`、`sim_time_s` 完全一致，并把交通灯、停止线和限速整理为 `TrafficConstraint`。只有距离而没有前车速度时，它保守地按前方物体静止处理，即 `closing_speed_mps = ego_speed_mps`；只有速度没有距离则拒绝。
2. `ControlRuntime.step` 先把命令速度、交通灯接近速度和感知 `speed_cap_mps` 合并，再从局部路线窗计算曲率。需确认的命令先经过 `FuzzyCommandPolicy`；其余请求直接进入 `LongitudinalController.step`。
3. `SpeedPlanner` 同时计算弯道、道路限速、停止点和前车间距四类硬上限，再与命令速度舒适斜坡取最小值。硬上限不会被命令斜坡抬高；`last_plan` 保留实际限制来源供日志解释。
4. `LongitudinalController` 的优先顺序是停止线 `HOLD`、不可达停止点紧急制动、TTC 本地紧急制动、PID 与执行器变化率限制。油门和制动互斥，切换时先撤销另一执行器；输出仍是 C 的原始控制，不是最终车辆权限。
5. `ControlRuntime` 可追加停车保持，随后把 C 的控制和 `RiskMetrics` 交给 D 的 `SafetySupervisor`。D 仍能覆盖最终油门/制动，因此诊断必须同时看 C 的 `state/reason/last_plan`、D 的 `reason_category` 以及最终实际 control。

### 多约束速度规划

| 约束 | 实际公式/条件 | 缺失时语义 |
|---|---|---|
| 弯道 | `sqrt(max_lateral_accel / abs(curvature))`；曲率近零为无穷上限 | 不限制目标速度，且无穷值不写入 `constraint_caps_mps` |
| 道路限速 | 来自 `TrafficRulePlanner.speed_limit_mps` | 不加入硬上限 |
| 停止点 | 舒适制动公式预留 `hold_distance + speed * dt`；近线切到 `CREEP/HOLD` | 无需停车时不限制 |
| 前车 | `lead_speed + sqrt(2 * comfortable_decel * max(0, gap-desired_gap))` | 距离或接近速度缺失时不生成此 cap |
| 命令速度 | 相对上一目标按 `command_accel/decel * dt` 斜坡 | 首帧以当前车速为斜坡起点 |

`StopController` 的状态边界是：无停止距离为 `CRUISE`；距离不大于 `hold_distance` 且速度不大于 `hold_speed` 才 `HOLD`；距离不大于 `max(2 m, 3 * hold_distance)` 为 `CREEP`；否则 `DECELERATE`。当 `v² / (2 * usable_distance) >= max_decel` 时，外层控制器不再只依赖舒适速度上限，而返回满制动的 `stop_unreachable_fallback`。

### 跟车、TTC 与缺测语义

期望间距为 `standstill_gap + time_gap * ego_speed + sensor_base_margin + sensor_uncertainty_time * ego_speed`。只有距离和接近速度都存在且接近速度大于0时才计算 `TTC = distance / closing_speed`；`TTC is None` 的含义是当前局部函数无法计算，不等于已确认安全。生产桥接在“有距离、无速度”时采用静止障碍假设，因此该路径通常仍能给 C 生成保守 TTC；`FollowingController` 被单独调用时则保留 `None` 语义。

`ConservativeSensorFusion` 是感知侧的另一套逐帧安全摘要：它强制帧号和仿真时间单调、RGB/LiDAR 同帧，LiDAR 无效却携带距离/速度会被拒绝。没有对齐前车速度时，LiDAR 距离差分必须经过幅值过滤和连续两次确认；目标切换造成的不可能接近速度会标记为 outlier。LiDAR 失效、只有 RGB 危险目标但无测距等情况会 fail closed。VRU 谨慎限速还有 `vru_caution_hold_s` 的时间保持，不能只看当前一帧是否仍有人。

### PID、状态与重置

- `SpeedPID` 校验有限值与正 `dt`，对积分做上下限裁剪；目标速度跳变超过 `pid_target_step_reset_mps` 时只保留原积分的25%，避免旧目标积累直接带入新目标。
- `SpeedPlanner` 保存上一目标，`LongitudinalController` 保存上一油门/制动；两者都是 episode-local 状态。车辆重生或独立运行开始前必须调用 `LongitudinalController.reset()`，否则舒适斜坡和执行器变化率会继承旧 episode。
- `FuzzyCommandPolicy` 对过期、低置信度、模糊或危险确认状态可直接生成纵向输出；它不是绕过 Qwen 的规划快路径，而是已收到命令后的本地安全确认层。

### 当前生效的默认量级

主策略来自 `config/strategy_config.yaml`：舒适/最大减速度为3/5 m/s²，停止保持制动0.55，紧急制动1.0，谨慎/紧急 TTC 为2.5/1.5 s；C 最大横向加速度2 m/s²，命令加减速斜坡1.5/3 m/s²，最大正加速度2.5 m/s²，控制量最大变化率2/s，蠕行0.5 m/s，停止保持距离0.8 m；PID 为 `1.2/0.15/0.02`，积分限幅4，目标跳变阈值3 m/s。跟车静止间距3 m、反应时间1 s，另叠加0.75 m基础传感器裕量和 `0.10 s * speed` 的速度裕量。

这些是默认实例的来源，不代表所有 runner 都使用默认值。`integration.driving_policy` 会为 `ConservativeSensorFusion` 和 D 生成另一组场景策略；运行证据仍应记录实际策略文件及命令行覆盖。

### 已确认边界与保留问题

- **M05-01 / 配置生效缺口，未修复：** `DrivingPolicy.perception_parameters()` 会构造 `reaction_time_s`、`emergency_reaction_time_s`、`comfortable_deceleration_mps2`、`emergency_deceleration_mps2` 和 `range_uncertainty_buffer_m`，`SafetyStateParameters` 也验证这些字段；但 `ConservativeSensorFusion.update()` 调用 `dynamic_safety_distance()` 时没有把它们或等价 `StrategyConfig` 传入。动态包络实际读取模块导入时的 `DEFAULT_STRATEGY`，所以修改上述五个 perception 字段不会改变 `dynamic_caution_distance_m` / `dynamic_emergency_distance_m`。距离 floor、TTC、VRU 阈值等其他字段仍有各自消费路径，不能据此说整个 policy 都无效。
- **A07 / 测试发现缺口继续保留：** `car_control_C/tests/test_safety_state.py` 有重复测试函数名，后定义覆盖前定义；文件中的函数数不等于 pytest 实际收集数。它属于既有审计问题，本轮没有用文档改写冒充修复。
- `fusion_tracker.py`、`sensor_adapter.py`、`rgb_pipeline.py` 是 C 的交付/审计辅助件；生产 CARLA 感知主入口是 `integration/carla_perception.py`。单独辅助件测试通过不能证明生产 runner 使用了同一目标身份和时序。

### 验证范围

相关回归入口包括 `car_control_C/tests/test_longitudinal.py`、`test_fuzzy_command_policy.py`、`test_safety_state.py`、`test_strategy_generalization.py`、`integration/tests/test_perception_bridge.py`、`test_runtime_loop.py` 与 `test_role_c_perception.py`。本轮完成的是源码、逐文件说明、链接与纯 Python 边界核对；当前本机环境没有可用 pytest，因此不声明这些测试已重新执行，也未运行 CARLA、真实传感器或远端模型。


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
