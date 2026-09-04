# 成员2场景泛化结果

## 已解决问题

| 问题 | 处理 |
|---|---|
| `spawn.y=±3.5m` 在弯道/窄路落到车道线 | 按 CARLA waypoint 的真实左右车道关系生成，并拒绝反向车道、路肩和非行驶车道 |
| Actor 生成失败只依赖 `try_spawn_actor` | 生成前检查车道、朝向、高度和重叠；失败后按固定 seed 从近到远重采样 |
| 行人起点随机化但终点未同步 | 起点、终点、Actor 事件和生成触发统一沿 `route_s` 同步偏移 |
| 跨地图仍沿用固定 spawn index | Unseen 样本自动移除地图专用 `route_anchor_spawn_index`，交给拓扑选点 |
| S2 交互集中在前 1.1km | 公交、行人、慢车、自行车改到 0.5/2.3/4.8/7.0km，并在事件前约 150m 延迟生成，避免回环道路上的远期 Actor 提前干扰感知 |
| Variant 只能改少量固定数值 | 同时覆盖距离、横向偏移、速度、制动时机、行人时机、可选车道、NPC 数量、天气和 Sensor 条件 |

## 精简验证结果

| 验证 | 结果 |
|---|---:|
| Actor/场景/触发相关单元测试 | 147/147 通过 |
| S2 同地图 Variant 配置 | 9/9 可加载 |
| S2 跨地图 Unseen 配置 | 18/18 可加载 |
| 8 类核心模板固定输出 | 8 个 Variant + 8 个 Unseen，全部可加载 |
| Town03 S2 实际 CARLA Actor 生成 | 4 辆车 + 3 名行人全部成功；8km 路线实际生成 8001.56m |
| Town04 未见过路线 Actor 生成 | `ACC_A01` 路线 80.0m、前车实距 19.96m，实际 CARLA 生成成功 |

`--spawn-all-scenario-actors` 只用于快速检查 Actor 布置，不作为正式成绩。正式运行默认按 `spawn_trigger` 延迟生成远期事件 Actor。

## 复现命令

```powershell
py -3.13 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind variant
py -3.13 tools/run_generalization_gate.py scenarios/official_competition/S2_complex_avoidance_8km.json --kind unseen

# CARLA 与 Planner V2 服务启动后，仅检查 S2 全部 Actor 是否能合法生成
py -3.12 -m integration.carla_runner `
  --scenario-file scenarios/official_competition/S2_complex_avoidance_8km.json `
  --qwen-service-url http://127.0.0.1:8765 --qwen-mode planner_v2 `
  --perception-mode world --scenario-facts-mode scenario `
  --spawn-all-scenario-actors --max-frames 1
```

完整路线驾驶、Qwen 正确率和延迟属于联合闭环验收，不把本次 Actor 布置冒烟结果冒充完整场景通过。
S2 跨地图 8km 配置已通过静态门禁，但当前成员1路线选择器会为所有候选出生点重复构建 8km 路线，启动过慢；待快速拓扑锚点接口合入后再做该项联合实测。
