# Strategy configuration and scenario assets

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [具体参数的装载和覆盖](../functions/policy-precedence.md)
- [场景配置与控制/评分分工](../functions/scenario-evidence-contract.md)

Parent: [Support module](../modules/support.md).

## Configuration functions

[config/strategy.py](../../../config/strategy.py) strictly loads strategy_config.yaml (JSON-syntax YAML), validates fields/numbers/relations and exports DEFAULT_STRATEGY and dynamic_safety_distance for A/B/C/D.

[driving_policy.json](../../../config/driving_policy.json), loaded by [integration/driving_policy.py](../../../integration/driving_policy.py), generates perception SafetyStateParameters and final SafetyConfig. CLI overrides can replace visual confidence, route deviation and stop-line guard; some minimum thresholds still come from DEFAULT_STRATEGY. Record effective values and provenance: editing one configuration does not guarantee every consumer changes. generalization_matrix.json owns deterministic scene transformations; repro/*.env contains common, RTX5070 and A800 safe/optimized environments.

## Scenario functions

- smoke: minimal integration; lateral_B: straight/curve/turn/lane-change; safety_D: lights, pedestrians, lead braking, TTC and invalid control arbitration.
- regression: base/weather/interactions/challenge; qwen_routing/fullchain/faults: route selection, plan execution and failure boundaries.
- acceptance_suite: basic/advanced/challenge core tasks, variants, complex missions and supplemental basic/advanced/challenge/system cases. matrix.json and BUILD_SUMMARY.md index the suite.
- official_competition: S1 5km, S2 8km, S3 6km. development: route generalization and targeted S2 pedestrian/bicycle diagnostics. generalization/member2/variant and unseen: generated generalization assets.

## Contracts, validation and failure

[scenario_schema.json](../../../scenarios/scenario_schema.json) describes structure; [validate_scenarios.py](../../../tools/validate_scenarios.py) manually checks a subset rather than executing full JSON Schema. Core fields include scenario_id/map/weather/seed/runtime/ego_spawn/route/commands/expected. scenario_local_xy_m requires runner conversion; do not treat it as CARLA world coordinates.

Run python tools/validate_scenarios.py, then relevant validate_official_scenes.py/validate_route_generalization.py/validate_control_generalization.py, and finally python -m integration.carla_runner --scenario-file PATH with CARLA. Static validation does not prove mission completion. Runtime evidence belongs under artifacts.

Illegal policy values are rejected; scenario validators report errors. Route-generation, actor-spawn and sensor failures must remain runtime failures rather than being hidden by changing expected outcomes. Threshold edits require perception/C/D/effective-policy review; scenario schema edits require validators, runner, generators, metrics, matrices and evidence-index updates. Development/generalization runs cannot replace official-scene evidence.


## 模块接口与参数核对（2026-09-20）

load_strategy_config读取策略并构造DEFAULT_STRATEGY；load_driving_policy读取schema_version=1.0且perception/safety必须为object。DrivingPolicy再生成SafetyStateParameters和SafetyConfig，runner可传明确覆盖。

### 参数语义与生效边界

policy数值拒绝bool、非数、非有限或小于minimum；deceleration下限0.001。route_deviation_override_m和stop_line_guard_override_m优先于policy对应值；maximum_lane_offset还取policy值与route deviation的min，部分最低限取DEFAULT_STRATEGY。

### 上下游与修改影响

不存在一句通用“CLI总覆盖全部配置”的规则，必须按构造函数追最终生效值。base/GEN和generalization_matrix是不同层，具体差异与selection联动见场景来源记录。

### [config/strategy.py](../../../config/strategy.py) 的入口与声明

```python
load_strategy_config(path: str | Path=DEFAULT_STRATEGY_PATH) -> StrategyConfig
SafetyDistanceEnvelope.to_dict(self) -> dict[str, float]
dynamic_safety_distance(*, ego_speed_mps: float, closing_speed_mps: float | None=None, curvature_per_m: float=0.0, actor_type: str | None=None, sensor_margin_scale: float=1.0, config: StrategyConfig=DEFAULT_STRATEGY) -> SafetyDistanceEnvelope
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `CommonStrategy.command_confidence_threshold` | `float` | `无声明默认（构造/赋值方提供）` |
| `CommonStrategy.standstill_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `CommonStrategy.comfortable_decel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `CommonStrategy.max_decel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `CommonStrategy.hold_brake` | `float` | `无声明默认（构造/赋值方提供）` |
| `CommonStrategy.emergency_brake` | `float` | `无声明默认（构造/赋值方提供）` |
| `CommonStrategy.caution_ttc_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `CommonStrategy.emergency_ttc_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.standstill_gap_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.reaction_time_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.emergency_reaction_time_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.sensor_base_margin_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.sensor_uncertainty_time_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.curvature_margin_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.vru_distance_factor` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.vru_emergency_distance_factor` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.vru_minimum_emergency_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.large_vehicle_distance_factor` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.unknown_actor_distance_factor` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceStrategy.minimum_emergency_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSafetyStrategy.visual_confidence_threshold` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSafetyStrategy.max_observation_gap_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSafetyStrategy.vru_caution_speed_cap_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSafetyStrategy.vru_caution_hold_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.max_lateral_accel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.command_accel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.command_decel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.max_accel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.max_control_delta_per_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.creep_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.stop_hold_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.pid_kp` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.pid_ki` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.pid_kd` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.pid_integral_limit` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalStrategy.pid_target_step_reset_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.wheel_base_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.base_lookahead_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.speed_gain_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.min_lookahead_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.max_lookahead_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.curvature_lookahead_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.error_lookahead_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.max_steer_angle_rad` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.steer_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.max_steer` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.min_steer_limit` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.high_speed_steer_reduction_per_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.curvature_steer_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.base_steer_delta_per_step` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.min_steer_delta_per_step` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.max_steer_delta_per_step` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.low_speed_steer_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.curvature_rate_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.error_rate_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.stanley_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.stanley_softening_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.stanley_curvature_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralStrategy.steer_sign` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.stop_line_guard_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.max_lane_offset_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.minimum_lane_offset_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.severe_route_deviation_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.minimum_severe_route_deviation_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.route_speed_sensitivity` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.route_curvature_sensitivity` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.route_recovery_max_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.route_recovery_throttle` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.route_recovery_steer_limit` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.route_deviation_brake` | `float` | `无声明默认（构造/赋值方提供）` |
| `SupervisorStrategy.caution_brake` | `float` | `无声明默认（构造/赋值方提供）` |
| `SensorFaultStrategy.single_sensor_speed_cap_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `SensorFaultStrategy.speed_cap_tolerance_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `SensorFaultStrategy.speed_cap_base_brake` | `float` | `无声明默认（构造/赋值方提供）` |
| `SensorFaultStrategy.speed_cap_brake_gain` | `float` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.schema_version` | `str` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.common` | `CommonStrategy` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.safety_distance` | `SafetyDistanceStrategy` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.perception_safety` | `PerceptionSafetyStrategy` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.longitudinal` | `LongitudinalStrategy` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.lateral` | `LateralStrategy` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.supervisor` | `SupervisorStrategy` | `无声明默认（构造/赋值方提供）` |
| `StrategyConfig.sensor_fault` | `SensorFaultStrategy` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.caution_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.emergency_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.reaction_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.braking_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.sensor_margin_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.curvature_multiplier` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.actor_multiplier` | `float` | `无声明默认（构造/赋值方提供）` |
| `SafetyDistanceEnvelope.emergency_actor_multiplier` | `float` | `无声明默认（构造/赋值方提供）` |

### [integration/driving_policy.py](../../../integration/driving_policy.py) 的入口与声明

```python
DrivingPolicy.perception_parameters(self, *, visual_confidence_override: float | None=None) -> SafetyStateParameters
DrivingPolicy.safety_config(self, *, route_deviation_override_m: float | None=None, stop_line_guard_override_m: float | None=None) -> SafetyConfig
load_driving_policy(path: str | Path | None=None) -> DrivingPolicy
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `DrivingPolicy.source_path` | `Path` | `无声明默认（构造/赋值方提供）` |
| `DrivingPolicy.perception` | `Mapping[str, object]` | `无声明默认（构造/赋值方提供）` |
| `DrivingPolicy.safety` | `Mapping[str, object]` | `无声明默认（构造/赋值方提供）` |

### [integration/generalization_gate.py](../../../integration/generalization_gate.py) 的入口与声明

```python
GeneralizationMatrix.cases(self, scenario_id: str) -> Iterator[PerturbationCase]
load_generalization_matrix(path: str | Path | None=None) -> GeneralizationMatrix
perturb_scenario(raw_scenario: Mapping[str, Any], case: PerturbationCase) -> dict[str, Any]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `PerturbationCase.case_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.map_name` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.weather` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.seed` | `int` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.fixed_delta_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_longitudinal_offset_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_lateral_offset_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_speed_scale` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.brake_time_offset_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.pedestrian_start_offset_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_count_scale` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.target_lane_relation` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.sensor_condition` | `str` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.source_path` | `Path` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.maps` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.weather_profiles` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.seeds` | `tuple[int, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.fixed_delta_seconds` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_longitudinal_offsets_m` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_lateral_offsets_m` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_speed_scales` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.brake_time_offsets_s` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.pedestrian_start_offsets_s` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_count_scales` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.target_lane_relations` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.sensor_conditions` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.samples_per_scenario` | `int` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.holdout_scenarios` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [config/__init__.py](../functions/config--__init__--py.md)
- [config/driving_policy.json](../functions/config--driving_policy--json.md)
- [config/generalization_matrix.json](../functions/config--generalization_matrix--json.md)
- [config/strategy.py](../functions/config--strategy--py.md)
- [config/strategy_config.yaml](../functions/config--strategy_config--yaml.md)
- [scenarios/scenario_schema.json](../functions/scenarios--scenario_schema--json.md)

## 诊断与维护交接

本模块证据：CLI/env/场景覆盖、GEN来源参数；19 GEN发现9项语义差异。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

专项记录：[场景来源与泛化漂移](../functions/scenario-lineage.md)。

### [config/strategy_config.yaml](../../../config/strategy_config.yaml) 配置值快照

这些是此文件的值；只有实际入口选择并装载此文件后才参与生效，不覆盖上文的显式override规则。

| 参数路径 | 文件值 |
|---|---|
| `schema_version` | `"1.0"` |
| `common.command_confidence_threshold` | `0.8` |
| `common.standstill_speed_mps` | `0.15` |
| `common.comfortable_decel_mps2` | `3.0` |
| `common.max_decel_mps2` | `5.0` |
| `common.hold_brake` | `0.55` |
| `common.emergency_brake` | `1.0` |
| `common.caution_ttc_s` | `2.5` |
| `common.emergency_ttc_s` | `1.5` |
| `safety_distance.standstill_gap_m` | `3.0` |
| `safety_distance.reaction_time_s` | `1.0` |
| `safety_distance.emergency_reaction_time_s` | `0.35` |
| `safety_distance.sensor_base_margin_m` | `0.75` |
| `safety_distance.sensor_uncertainty_time_s` | `0.1` |
| `safety_distance.curvature_margin_gain` | `0.35` |
| `safety_distance.vru_distance_factor` | `1.75` |
| `safety_distance.vru_emergency_distance_factor` | `1.2` |
| `safety_distance.vru_minimum_emergency_distance_m` | `8.0` |
| `safety_distance.large_vehicle_distance_factor` | `1.15` |
| `safety_distance.unknown_actor_distance_factor` | `1.1` |
| `safety_distance.minimum_emergency_distance_m` | `1.5` |
| `perception_safety.visual_confidence_threshold` | `0.6` |
| `perception_safety.max_observation_gap_s` | `0.3` |
| `perception_safety.vru_caution_speed_cap_mps` | `2.0` |
| `perception_safety.vru_caution_hold_s` | `4.0` |
| `longitudinal.max_lateral_accel_mps2` | `2.0` |
| `longitudinal.command_accel_mps2` | `1.5` |
| `longitudinal.command_decel_mps2` | `3.0` |
| `longitudinal.max_accel_mps2` | `2.5` |
| `longitudinal.max_control_delta_per_s` | `2.0` |
| `longitudinal.creep_speed_mps` | `0.5` |
| `longitudinal.stop_hold_distance_m` | `0.8` |
| `longitudinal.pid_kp` | `1.2` |
| `longitudinal.pid_ki` | `0.15` |
| `longitudinal.pid_kd` | `0.02` |
| `longitudinal.pid_integral_limit` | `4.0` |
| `longitudinal.pid_target_step_reset_mps` | `3.0` |
| `lateral.wheel_base_m` | `2.8` |
| `lateral.base_lookahead_m` | `2.5` |
| `lateral.speed_gain_s` | `0.45` |
| `lateral.min_lookahead_m` | `2.5` |
| `lateral.max_lookahead_m` | `8.0` |
| `lateral.curvature_lookahead_gain` | `10.0` |
| `lateral.error_lookahead_gain` | `0.3` |
| `lateral.max_steer_angle_rad` | `0.6` |
| `lateral.steer_gain` | `1.0` |
| `lateral.max_steer` | `0.6` |
| `lateral.min_steer_limit` | `0.35` |
| `lateral.high_speed_steer_reduction_per_mps` | `0.018` |
| `lateral.curvature_steer_gain` | `1.5` |
| `lateral.base_steer_delta_per_step` | `0.038` |
| `lateral.min_steer_delta_per_step` | `0.025` |
| `lateral.max_steer_delta_per_step` | `0.038` |
| `lateral.low_speed_steer_gain` | `0.75` |
| `lateral.curvature_rate_gain` | `2.0` |
| `lateral.error_rate_gain` | `0.15` |
| `lateral.stanley_gain` | `0.8` |
| `lateral.stanley_softening_speed_mps` | `1.0` |
| `lateral.stanley_curvature_gain` | `1.5` |
| `lateral.steer_sign` | `1.0` |
| `supervisor.stop_line_guard_m` | `8.0` |
| `supervisor.max_lane_offset_m` | `1.8` |
| `supervisor.minimum_lane_offset_m` | `0.75` |
| `supervisor.severe_route_deviation_m` | `3.0` |
| `supervisor.minimum_severe_route_deviation_m` | `1.5` |
| `supervisor.route_speed_sensitivity` | `0.025` |
| `supervisor.route_curvature_sensitivity` | `2.0` |
| `supervisor.route_recovery_max_speed_mps` | `1.5` |
| `supervisor.route_recovery_throttle` | `0.0` |
| `supervisor.route_recovery_steer_limit` | `0.35` |
| `supervisor.route_deviation_brake` | `0.65` |
| `supervisor.caution_brake` | `0.35` |
| `sensor_fault.single_sensor_speed_cap_mps` | `2.0` |
| `sensor_fault.speed_cap_tolerance_mps` | `0.1` |
| `sensor_fault.speed_cap_base_brake` | `0.35` |
| `sensor_fault.speed_cap_brake_gain` | `0.25` |

### [config/driving_policy.json](../../../config/driving_policy.json) 配置值快照

这些是此文件的值；只有实际入口选择并装载此文件后才参与生效，不覆盖上文的显式override规则。

| 参数路径 | 文件值 |
|---|---|
| `schema_version` | `"1.0"` |
| `perception.visual_confidence_threshold` | `0.6` |
| `perception.caution_distance_floor_m` | `10.0` |
| `perception.emergency_distance_floor_m` | `5.0` |
| `perception.vru_caution_distance_floor_m` | `25.0` |
| `perception.vru_emergency_distance_floor_m` | `8.0` |
| `perception.vru_caution_speed_cap_mps` | `2.0` |
| `perception.vru_caution_hold_s` | `4.0` |
| `perception.caution_ttc_s` | `2.5` |
| `perception.emergency_ttc_s` | `1.5` |
| `perception.max_observation_gap_s` | `0.3` |
| `perception.untracked_approach_speed_margin_mps` | `5.0` |
| `perception.reaction_time_s` | `0.7` |
| `perception.emergency_reaction_time_s` | `0.35` |
| `perception.comfortable_deceleration_mps2` | `3.5` |
| `perception.emergency_deceleration_mps2` | `6.0` |
| `perception.range_uncertainty_buffer_m` | `1.0` |
| `safety.minimum_front_distance_floor_m` | `5.0` |
| `safety.low_ttc_s` | `1.5` |
| `safety.caution_ttc_s` | `2.5` |
| `safety.stop_line_guard_m` | `1.0` |
| `safety.maximum_lane_offset_m` | `1.8` |
| `safety.severe_route_deviation_m` | `3.0` |
| `safety.route_recovery_max_speed_mps` | `1.5` |
| `safety.low_confidence_threshold` | `0.8` |
| `safety.emergency_reaction_time_s` | `0.35` |
| `safety.emergency_deceleration_mps2` | `6.0` |
| `safety.range_uncertainty_buffer_m` | `1.0` |

## 第18模块逐入口精读结论（2026-09-22）

本轮按基线 `4e41f990` 核对5份配置资源页、1份场景Schema页和3份专题语义页，改写14处泛用占位。该模块定义的是“配置怎样生效、场景怎样被解释和验证”，不直接证明车辆完成场景。

### 配置所有权与覆盖顺序

`strategy_config.yaml`（实际为JSON语法YAML）由 `config/strategy.py` 严格装载并形成导入期 `DEFAULT_STRATEGY`；`driving_policy.json` 由 `integration/driving_policy.py` 形成感知与安全配置，runner还可传显式override。最终值不是简单的“后者覆盖前者”：部分安全下限仍从 `DEFAULT_STRATEGY` 取值，lane offset还会取policy与route deviation的较小值。每次run应记录文件hash、CLI/env和最终派生配置，单独修改某个文件不能宣称全链阈值已经改变。

### 场景合同与运行证据

`scenario_schema.json` 描述结构，`validate_scenarios.py` 实现的是项目需要的手工子集检查，不是完整JSON Schema执行器。静态合法只说明字段、有限数值和部分关系通过；地图存在、spawn成功、路线可达、actor时序、传感器同步、Qwen终态与评分都必须由runner证据回答。`scenario_local_xy_m` 需由runner转换，不能当作CARLA world坐标直接使用。

official、development、acceptance、generalization、variant/unseen各自证据等级不同。生成器输出和开发场景通过不能替代S1/S2/S3正式结果；场景ID、route hash、seed、地图、天气和代码SHA必须一起保存，避免以同名JSON覆盖真实运行身份。

### 修改联动与门禁

改策略字段时同步loader、dataclass关系校验、DrivingPolicy派生、实际消费者与测试；改场景Schema时同步validator、runner、生成器、矩阵、评分和证据索引。门禁顺序为通用静态校验、official/泛化专项校验、离线合同测试、指定CARLA smoke、完整任务与冻结证据。任何actor/spawn/route/sensor失败都应保留为运行失败，禁止通过放宽expected或改评分掩盖。
