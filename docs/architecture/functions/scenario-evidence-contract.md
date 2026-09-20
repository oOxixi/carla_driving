# 场景触发、车辆行为与评分的分离

上级：[场景执行模块](../modules/vehicle-scenarios.md)；关联：[配置与场景合同](../modules/support-config-scenarios.md)。

## 场景文件承担不同职责

场景 JSON 的 Actor/路线/事件用于构建世界和触发；expected 描述验收要求；extensions.control_policy 表达明确允许的控制策略覆盖。不能因为 expected 要求“到达某结果”就让运行时直接据此生成动作。

[scenario_builder](../../../integration/scenario_builder.py) 处理 Actor 与路线位置；[scenario_extensions](../../../integration/scenario_extensions.py) 解释扩展事件/策略；[scenario_execution](../../../integration/scenario_execution.py) 维护执行状态；[scenario_acceptance](../../../integration/scenario_acceptance.py) 与 [scoring_stage](../../../integration/scoring_stage.py) 从证据判断结果。

## 泛化约束

新场景优先使用 route_position.s_m、lane_relation、lateral_offset_m、yaw_offset_deg 描述相对路线位置。旧 spawn.x/y 的兼容解释不能随意当世界坐标重写。不同路线合同包括 distance_coverage、destination、local_polyline，生成与验收需要匹配。

Seen/Variant/Unseen 是数据和验收边界，不应为了修某个模型重新定义。故障注入要记录发生时刻及来源，不能与真实传感器失效混为一类结果。

## 维护时应该追踪的证据

[ScenarioEvidenceRecorder](../../../integration/scenario_evidence.py) 记录运行、命令、逐帧、反馈、终态及摘要。任务完成、安全覆盖、碰撞、路线偏差、帧预算耗尽是不同指标：跑完帧数不自动代表任务成功，安全停车也不自动代表原始驾驶任务成功。

增加场景后应核对 schema、index/矩阵、builder 能否解释配置、执行器能否产生预期事实、验收器能否在失败时给出正确阶段。可先用 validate_scenarios/validate_official_scenes 做静态检查，再决定所需真实闭环。

源码测试入口：[integration/tests](../../../integration/tests) 中 scenario_builder、scenario_extensions、scenario_execution、scenario_acceptance、scenario_evidence 和 runtime_stages。维护评分时必须保留控制与评分分离，不通过修改传感器/控制事实来“修分”。

进一步定位：[场景来源](scenario-lineage.md)、[验收合成](acceptance-diagnosis.md)、[目标身份](target-grounding.md)。
