# 成员2 Actor / 场景泛化交接

- 日期：2026-09-06
- 目标分支：`carla_driving_rstar`
- 实现提交：`7ce6928fa9065c8a7f76ecd5061323d1d2d5f4e8`
- 固定运行环境：Python 3.12、CARLA 0.9.16

## 当前结论

成员2负责的 Actor 路线坐标生成、生成合法性检查与确定性重采样、场景参数化、S2 长路线事件分布以及 Variant / Unseen 样本生成已经落地。实现和验证结论以 [`docs/scenario_generalization_report.md`](docs/scenario_generalization_report.md) 为准，本文件只说明接手入口、边界和后续联合验收事项。

## 交付入口

| 内容 | 位置 |
|---|---|
| Actor 路线坐标解析、合法性检查、重采样 | `integration/scenario_builder.py` |
| Actor 延迟生成及 CARLA 接入 | `integration/carla_runner.py` |
| Variant / Unseen 参数变换 | `integration/generalization_gate.py` |
| 生成命令 | `tools/run_generalization_gate.py` |
| 参数范围和固定 seed | `config/generalization_matrix.json` |
| 8 类 Variant + 8 类 Unseen 固定样本 | `scenarios/generalization/member2/` |
| S2 长路线事件配置 | `scenarios/official_competition/S2_complex_avoidance_8km.json` |
| 精简验证记录 | `docs/scenario_generalization_report.md` |

核心约定：Actor 优先用 `route_s + lane_relation + lane_offset` 定位；旧配置中的横向 `±3.5m` 会映射到真实相邻车道，不再作为世界坐标硬偏移。位置不合法时按固定 seed 重采样，无法得到合法位置则明确失败，禁止强行生成。

## 已验证

- 相关单元测试：147/147 通过。
- 全仓场景配置校验：148 个通过、0 个失败。
- Town03 S2：实际生成 8001.56m 路线，4 辆车和 3 名行人均可生成。
- Town04 未见路线 `ACC_A01`：80.0m 路线，前车实际距离 19.96m，Actor 生成成功。
- 16 个固定 Variant / Unseen 样本均可加载。

最小回归命令：

```powershell
py -3.12 -m pytest integration/tests/test_scenario_builder.py integration/tests/test_generalization_gate.py integration/tests/test_carla_runner_helpers.py integration/tests/test_scenario_extensions.py -q
py -3.12 tools/validate_scenarios.py
```

生成样本：

```powershell
py -3.12 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind variant
py -3.12 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind unseen
```

## 验收边界

- `--spawn-all-scenario-actors` 仅用于快速检查 Actor 布置，不代表完整闭环通过；正式运行默认按 `spawn_trigger` 在事件前延迟生成。
- S2 跨地图 8km 样本已通过静态门禁，但完整跨地图驾驶需等待成员1的快速拓扑锚点接口合入；当前路线选择器会对候选出生点重复构建长路线，启动较慢。
- Qwen 正确率、端到端延迟、完整任务成功率属于成员1/2/3联合闭环验收，不应由 Actor 冒烟结果代替。
- 默认模型仍保持 Qwen3-7B，本次成员2实现不修改模型路线。

## 下一步只做三件事

1. 合入成员1路线接口后，实跑一次 S2 Unseen 跨地图长路线，确认延迟生成的后续事件顺序正确。
2. 合入成员3通用控制后，各抽取 Seen、Variant、Unseen 一组做可视化闭环，不扩写重复测试矩阵。
3. 若失败，先按路线、Actor、控制、安全接管、感知、Qwen 分类，只修通用根因，不增加场景 ID 特判。

建议下一会话仅在 CARLA 闭环可复现失败时使用 `diagnose` 技能，按“复现—最小化—定位—修复—回归”处理；常规接手无需额外技能。
