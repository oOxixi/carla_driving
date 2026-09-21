# strategy_config：功能记录

上级模块：[模块说明](../modules/support-config-scenarios.md) · 实现：[config/strategy_config.yaml](../../../config/strategy_config.yaml)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [具体参数的装载和覆盖](policy-precedence.md)
- [场景配置与控制/评分分工](scenario-evidence-contract.md)

## 功能职责与范围

strategy_config

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `schema_version`：'1.0'。
- `common`：对象，直接字段：command_confidence_threshold, standstill_speed_mps, comfortable_decel_mps2, max_decel_mps2, hold_brake, emergency_brake, caution_ttc_s, emergency_ttc_s。
- `safety_distance`：对象，直接字段：standstill_gap_m, reaction_time_s, emergency_reaction_time_s, sensor_base_margin_m, sensor_uncertainty_time_s, curvature_margin_gain, vru_distance_factor, vru_emergency_distance_factor, vru_minimum_emergency_distance_m, large_vehicle_distance_factor, unknown_actor_distance_factor, minimum_emergency_distance_m。
- `perception_safety`：对象，直接字段：visual_confidence_threshold, max_observation_gap_s, vru_caution_speed_cap_mps, vru_caution_hold_s。
- `longitudinal`：对象，直接字段：max_lateral_accel_mps2, command_accel_mps2, command_decel_mps2, max_accel_mps2, max_control_delta_per_s, creep_speed_mps, stop_hold_distance_m, pid_kp, pid_ki, pid_kd, pid_integral_limit, pid_target_step_reset_mps。
- `lateral`：对象，直接字段：wheel_base_m, base_lookahead_m, speed_gain_s, min_lookahead_m, max_lookahead_m, curvature_lookahead_gain, error_lookahead_gain, max_steer_angle_rad, steer_gain, max_steer, min_steer_limit, high_speed_steer_reduction_per_mps, curvature_steer_gain, base_steer_delta_per_step, min_steer_delta_per_step, max_steer_delta_per_step, low_speed_steer_gain, curvature_rate_gain, error_rate_gain, stanley_gain, stanley_softening_speed_mps, stanley_curvature_gain, steer_sign。
- `supervisor`：对象，直接字段：stop_line_guard_m, max_lane_offset_m, minimum_lane_offset_m, severe_route_deviation_m, minimum_severe_route_deviation_m, route_speed_sensitivity, route_curvature_sensitivity, route_recovery_max_speed_mps, route_recovery_throttle, route_recovery_steer_limit, route_deviation_brake, caution_brake。
- `sensor_fault`：对象，直接字段：single_sensor_speed_cap_mps, speed_cap_tolerance_mps, speed_cap_base_brake, speed_cap_brake_gain。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-config-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `config/strategy_config.yaml`

来源 SHA256：`455c0c826e43f62c11998b1b8acfb200cfa95e6d7f746dcf7c9ad28d89a5600f`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。
