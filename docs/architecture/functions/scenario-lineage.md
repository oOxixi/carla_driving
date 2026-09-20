# 场景来源与泛化漂移

上级：[配置与场景](../modules/support-config-scenarios.md)、[数据治理](../modules/challenge-data.md)。基线fe1ba839，2026-09-20。

base JSON → [perturb_scenario](../../../integration/generalization_gate.py) → GEN JSON → collector selection → [runner](../../../integration/carla_runner.py) → evidence → release。生成器不是自动同步机制，base修改不会更新已提交GEN。

生成器deepcopy base，改变地图、天气、seed、步长、actor位置/速度/密度与传感条件，保留语义commands/oracles。extensions.generalization_case.base_scenario_id关联base；参数记录不等于完整版本来源。

## 核对字段与来源

先按base_scenario_id唯一匹配；缺失时去掉__GEN_后缀仅作候选。比较commands的文本、intent、参数和trigger，以及expected、qwen_expected、oracle、proposed_acceptance。actor角色与引用变化需要检查，但合法密度克隆和位置扰动不能直接报stale。

来源链需要base路径/SHA、生成代码SHA及参数、GEN哈希、selection哈希、collector与实际runner SHA。未保存的身份从Git/运行记录恢复，不能补造。差异查历史确认设计意图，再决定重生成。

修改影响：base → 全部GEN → selection → 静态检查 → 同seed probe → 新cohort。历史冻结样本与manifest保持原身份。Schema合法不等于语义一致，parity检查需说明比较字段。

回归入口：[integration tests](../../../integration/tests)。已发现实例见[Wave2记录](wave2-audit.md)。
