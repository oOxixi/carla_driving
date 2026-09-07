# 成员2场景泛化结果

## 已解决问题

| 问题 | 处理 |
|---|---|
| `spawn.y=±3.5m` 在弯道/窄路落到车道线 | 按 CARLA waypoint 的真实左右车道关系生成，并拒绝反向车道、路肩和非行驶车道 |
| Actor 生成失败只依赖 `try_spawn_actor` | 生成前检查车道、朝向、高度和重叠；失败后按固定 seed 从近到远重采样 |
| 行人起点随机化但终点未同步 | 起点、终点、Actor 事件和生成触发统一沿 `route_s` 同步偏移 |
| 跨地图仍沿用固定 spawn index | Unseen 样本自动移除地图专用 `route_anchor_spawn_index`，交给拓扑选点 |
| S2 交互集中在路线起点 | 沿约 1.0/2.8/4.3/5.45/7.04km 分布公交、行人、慢车、自行车和路口加塞，并通过 `activation_trigger` / `deactivation_trigger` 控制 Actor 生命周期，避免远期 Actor 提前干扰感知 |
| Variant 只能改少量固定数值 | 同时覆盖距离、横向偏移、速度、制动时机、行人时机、可选车道、NPC 数量、天气和 Sensor 条件 |

## 精简验证结果

| 验证 | 结果 |
|---|---:|
| Actor/场景/触发相关单元测试 | 155/155 通过 |
| 全仓场景配置校验（Python 3.12） | 151/151 通过 |
| S2 同地图 Variant 配置 | 7/7 可加载 |
| S2 跨地图 Unseen 配置 | 20/20 可加载 |
| 8 类核心模板固定输出 | 8 个 Variant + 8 个 Unseen，全部可加载 |

`--spawn-all-scenario-actors` 只用于快速检查 Actor 布置，不作为正式成绩。正式运行默认按 `activation_trigger` 延迟生成远期事件 Actor。

## 复现命令

```powershell
py -3.12 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind variant
py -3.12 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind unseen

# CARLA 与 Planner V2 服务启动后，仅检查 S2 全部 Actor 是否能合法生成
py -3.12 -m integration.carla_runner `
  --scenario-file scenarios/official_competition/S2_complex_avoidance_8km.json `
  --qwen-service-url http://127.0.0.1:8765 --qwen-mode planner_v2 `
  --perception-mode world --scenario-facts-mode scenario `
  --spawn-all-scenario-actors --max-frames 1
```

完整路线驾驶、Qwen 正确率和延迟属于联合闭环验收，不把配置校验或 Actor 布置冒烟结果表述为完整场景通过。
