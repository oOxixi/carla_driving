# 东风赛道 CARLA 高质量验收场景套件

版本：`acceptance-suite-2026.08-v2`

本目录按《acceptance_suite 补充场景与统一复杂场景实施方案》构建 84 个场景，继续使用
`schema_version=1.0`、`scenario_local_xy_m` 路线和仓库既有 `category`。v2 在原 43 个场景
基础上新增 41 个补充场景，并将 `CX06_multi_command_full_trip` 升级、重命名为唯一主综合
场景 `CX_MAIN_01_safe_urban_mission`。

## 目录与数量

| 目录 | 数量 | 用途 |
|---|---:|---|
| `basic/` | 6 | 原有 P0 基础核心验收 |
| `advanced/` | 6 | 原有 P0 进阶核心验收 |
| `challenge/` | 6 | 原有 P0 挑战核心验收 |
| `variants/` | 18 | 原有 P1 基础、进阶、挑战变体 |
| `supplemental/basic/` | 6 | v2 新增基础评分场景 |
| `supplemental/advanced/` | 18 | v2 新增进阶评分场景 |
| `supplemental/challenge/` | 12 | v2 新增挑战评分场景 |
| `supplemental/system/` | 5 | v2 新增 Qwen 与系统压力场景 |
| `complex/` | 6 | 5 个组合回归 + 1 个唯一主综合场景 |
| `stability/` | 1 | 60 分钟稳定性场景 |
| **总计** | **84** | 18 基础 + 30 进阶 + 24 挑战 + 6 综合 + 6 系统/稳定性 |

完整路径、能力标签、分组和运行支持状态见 `matrix.json`；本次具体构建内容及最终 84 个
场景索引见 [BUILD_SUMMARY.md](BUILD_SUMMARY.md)。

## 唯一主综合场景

`complex/CX_MAIN_01_safe_urban_mission.json` 是唯一正式完整复杂场景合同，包含九个阶段：

```text
启动 → 定速 → 多目标跟随 → 前车急刹 → 行人横穿
→ 红灯冲突 → 绿灯重启 → 施工绕行 → 紧急停车
```

其中 7 条语音均要求独立 Qwen 请求；红灯、低 TTC、行人和紧急停车仍由本地安全链立即
抢占，不等待远端模型。该场景当前标记为 `extension_required`，在矩阵所列事件触发、命令
队列、目标绑定和 Qwen 验收扩展完成前，不得宣称全链路通过。

## 运行支持边界

所有 84 个 JSON 都能被 `ScenarioSpec.load()` 加载。`matrix.json` 使用两种状态：

- `current`：当前运行器具备该 JSON 声明的必要 Actor、路线、命令和验收能力；
- `extension_required`：JSON 可加载，但完整语义仍依赖 `runtime_support.requirements` 中的扩展。

尚未落地的事件触发、故障注入、全语音 Qwen、目标绑定、动作空间、命令队列和新增验收
指标均保存在 `extensions`，没有伪装成已经执行的 `expected` 条件。

## 正式运行约束

正式结果必须使用：

```bash
--perception-mode sensors \
--scenario-facts-mode perception
```

Qwen 只允许输出高层动作，不得输出 `steer/throttle/brake`。每条语音调用一次 Qwen，不按帧
调用；紧急安全动作本地立即执行并与 Qwen 记录并行。

## 验证

在仓库根目录运行：

```bash
python tools/build_acceptance_suite.py --check
python tools/validate_scenarios.py
python -m pytest integration/tests/test_acceptance_suite_contracts.py -q
```

单场景只加载配置：

```bash
python -m integration.carla_runner \
  --scenario-file scenarios/acceptance_suite/supplemental/basic/SUP_B06_right_offset_recovery.json \
  --validate-scenario-only
```

## 生成与维护

场景、`matrix.json` 和 `BUILD_SUMMARY.md` 均由 `tools/build_acceptance_suite.py` 确定性生成。
修改定义后重新运行脚本，再执行 `--check` 和场景验证器。运行器尚未支持的验收字段必须
保留在 `extensions.proposed_acceptance`；未知字段不得直接加入 `expected`。
