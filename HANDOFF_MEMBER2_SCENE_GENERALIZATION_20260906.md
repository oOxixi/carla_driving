# 成员2 Actor / 场景泛化交接

- 日期：2026-09-07
- 目标分支：`scene_organized`
- 泛化同步提交：`9a4747d`
- 固定运行环境：Python 3.12、CARLA 0.9.16

## 当前结论

成员2负责的 Actor 路线坐标生成、生成合法性检查与确定性重采样、场景参数化、S2 长路线 Actor 生命周期以及 Variant / Unseen 样本生成已同步到 `scene_organized`。实现与验证数字以 [`docs/scenario_generalization_report.md`](docs/scenario_generalization_report.md) 为准。

## 接手入口

| 内容 | 位置 |
|---|---|
| Actor 路线坐标、合法性检查、重采样 | `integration/scenario_builder.py` |
| Actor 生成和 `activation_trigger` 接入 | `integration/carla_runner.py` |
| Variant / Unseen 参数变换 | `integration/generalization_gate.py` |
| 参数矩阵与固定 seed | `config/generalization_matrix.json` |
| 样本生成命令 | `tools/run_generalization_gate.py` |
| 8 类 Variant + 8 类 Unseen | `scenarios/generalization/member2/` |
| 最新 S2 长路线场景 | `scenarios/official_competition/S2_complex_avoidance_8km.json` |

核心约定：Actor 使用 `route_s + lane_relation + lane_offset` 定位；旧配置中的横向 `±3.5m` 映射到真实相邻车道。位置不合法时按固定 seed 重采样，仍无合法位置则明确失败，不强行生成。

## 已验证

- Python 3.12 编译检查通过。
- Python 3.12 全仓场景校验：151/151 通过。
- Actor、泛化门禁、runner 辅助逻辑和场景扩展测试：155/155 通过。
- S2：7 个同地图 Variant 与 20 个跨地图 Unseen 均可加载。
- 固定交付样本：8 个 Variant + 8 个 Unseen，全部由 `scene_organized` 最新源场景重新生成。

```powershell
py -3.12 -m pytest integration/tests/test_scenario_builder.py integration/tests/test_generalization_gate.py integration/tests/test_carla_runner_helpers.py integration/tests/test_scenario_extensions.py -q
py -3.12 tools/validate_scenarios.py

py -3.12 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind variant
py -3.12 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind unseen
```

## 验收边界和下一步

- `--spawn-all-scenario-actors` 仅检查 Actor 布置；正式运行按 `activation_trigger` / `deactivation_trigger` 管理生命周期。
- 配置校验和 Actor 冒烟检查不能替代完整路线驾驶、Qwen 正确率和端到端延迟。
- 下一步只需各抽一组 Seen、Variant、Unseen 做可视化闭环；失败时按路线、Actor、控制、安全、感知、Qwen 分类，只修通用根因，不增加场景 ID 特判。

