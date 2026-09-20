# driving_policy：功能记录

上级模块：[模块说明](../modules/support-config-scenarios.md) · 实现：[config/driving_policy.json](../../../config/driving_policy.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [具体参数的装载和覆盖](policy-precedence.md)
- [场景配置与控制/评分分工](scenario-evidence-contract.md)

## 功能职责与范围

driving_policy

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `schema_version`：'1.0'。
- `perception`：对象，直接字段：visual_confidence_threshold, caution_distance_floor_m, emergency_distance_floor_m, vru_caution_distance_floor_m, vru_emergency_distance_floor_m, vru_caution_speed_cap_mps, vru_caution_hold_s, caution_ttc_s, emergency_ttc_s, max_observation_gap_s, untracked_approach_speed_margin_mps, reaction_time_s, emergency_reaction_time_s, comfortable_deceleration_mps2, emergency_deceleration_mps2, range_uncertainty_buffer_m。
- `safety`：对象，直接字段：minimum_front_distance_floor_m, low_ttc_s, caution_ttc_s, stop_line_guard_m, maximum_lane_offset_m, severe_route_deviation_m, route_recovery_max_speed_mps, low_confidence_threshold, emergency_reaction_time_s, emergency_deceleration_mps2, range_uncertainty_buffer_m。

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

### `config/driving_policy.json`

来源 SHA256：`9918fcfbf9c8c8dfd96917f1ab47f65921e7e07a548c6a685578110c3de4ec27`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。
