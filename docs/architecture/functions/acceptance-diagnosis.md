# 验收合成与failed keys定位

上级：[场景执行](../modules/vehicle-scenarios.md)；关联：[证据职责](scenario-evidence-contract.md)。基线fe1ba839，2026-09-20。

[runner](../../../integration/carla_runner.py)末尾将completion与Qwen monitor.finalize().passed合并，再与extension_runtime.evaluate().passed合并，然后交给[ScenarioEvidenceRecorder.complete](../../../integration/scenario_evidence.py)。complete通过[evaluate_expected](../../../integration/scenario_acceptance.py)取得基础验收，再与已有completion做AND。异常退出等上游状态还需另查，不能仅用末尾路径解释所有失败。

## 原始证据位置

recorder的self.path为记录文件，summary_path由path.with_suffix('.summary.json')得到。目录取决于启动参数/recorder初始化，不假设固定artifacts位置。runner stdout还输出qwen_scenario_acceptance、scenario_extension_acceptance、scenario_acceptance三类record_type。

summary.acceptance包含passed、checks、failed_keys；checks含key/status/actual/required/detail。A03先读failed_keys，再到_acceptance_metrics追actual如何从帧/context聚合，最后查控制/感知/事件生产者。

extension pass不保证base pass；任务完成、动作正确、安全停车与基础指标不同。修改required不能代替修actual；检查单位、时间区间、缺失值与默认context。

联动：scenario expected → evidence metrics/context → acceptance → summary → collector资格 → release/view。回归需覆盖两类验收结果不一致的情况，入口[integration tests](../../../integration/tests)。A03实际failed_keys尚缺，根因未闭合。
