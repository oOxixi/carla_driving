# 东风赛道 CARLA 高质量验收场景套件

版本：`acceptance-suite-2026.08-v1`

本目录按《东风赛道 CARLA 高质量场景库建设方案》构建 43 个场景，保持现有
`schema_version=1.0`、`scenario_local_xy_m` 路线和四类兼容 `category`。原有场景未删除。

## 目录与数量

| 目录 | 数量 | 用途 |
|---|---:|---|
| `basic/` | 6 | P0 基础核心验收 |
| `advanced/` | 6 | P0 进阶核心验收 |
| `challenge/` | 6 | P0 挑战核心验收 |
| `variants/` | 18 | P1 基础、进阶、挑战鲁棒性变体 |
| `complex/` | 6 | P2 多风险、多目标、多阶段综合场景 |
| `stability/` | 1 | P3 60 分钟稳定性场景 |
| **总计** | **43** | 18 P0 + 18 P1 + 6 P2 + 1 P3 |

完整路径、难度、能力标签及运行器成熟度见 `matrix.json`。

## 当前可执行边界

所有 43 个 JSON 都能被当前 `ScenarioSpec.load()` 加载。`matrix.json` 将场景分为：

- `current`：当前运行器已具备场景所需的 Actor、路线、命令和验收能力。
- `extension_required`：JSON 可加载，但完整语义还依赖矩阵所列运行器扩展。

下列能力按方案暂存于 `extensions`，不会放入 `expected` 造成假失败：

- 自定义雾参数；
- 多命令逐条提交远端 Qwen；
- 原始模糊文本的受限 Qwen 路由；
- RGB/LiDAR 黑屏、陈旧帧和转向偏置故障注入；
- Qwen 目标绑定、故障恢复和资源增长指标；
- 60 分钟路线循环。

`extensions.runtime_support.status=extension_required` 不代表这些能力已经执行或通过。

## 验证

在仓库根目录运行：

```bash
python tools/build_acceptance_suite.py --check
python tools/validate_scenarios.py
```

单场景只加载配置：

```bash
python -m integration.carla_runner \
  --scenario-file scenarios/acceptance_suite/basic/ACC_B02_set_speed_20.json \
  --validate-scenario-only
```

当前运行器可直接执行的代表场景：

```bash
./run_full_pipeline.sh run \
  --scenario-file scenarios/acceptance_suite/advanced/ACC_A01_lead_brake.json \
  --perception-mode sensors \
  --scenario-facts-mode perception \
  --sensor-profile low \
  --log-dir artifacts/scenario_runs/ACC_A01
```

正式结果必须使用 `--perception-mode sensors --scenario-facts-mode perception`。安全事件由本地
安全链立即处理，不等待 Qwen；Qwen 仅输出高层动作。

## 生成与维护

场景由 `tools/build_acceptance_suite.py` 确定性生成。修改生成定义后重新执行脚本，并运行
`--check` 和场景验证器。新验收字段在 `integration/scenario_acceptance.py` 支持前只能放入
`extensions.proposed_acceptance`。
