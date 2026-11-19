# S2 短程泛化闭环报告（2026-10-23）

## 范围与基线

- 分支：`main_optimization`
- 测试基线：`dc877ff8697351145df437de2e61f8d3cda8a76e`
- 地图：`Town03_Opt`
- 模型：`Qwen/Qwen3.5-2B`，`planner_v2`，生产服务健康检查通过
- 仿真扰动：控制周期由官方 `0.05 s` 改为 `0.10 s`，并组合 actor 纵向位置、横向位置、速度、行人启动时刻和传感器条件扰动
- 方法：只恢复到目标事件前，验证真实 Actor、RGB/LiDAR/Radar 感知、Qwen 请求、ManeuverPlan V2、控制、安全仲裁和事件后恢复；不将未运行的后续里程计为当前事件失败

## 发现和通用修复

### 1. 传感器量程与车身净距参考不一致

LiDAR/Radar 返回的是传感器原点到目标的量程，纵向控制和评分需要的是 ego 前车身边界到目标的净距。旧实现直接使用量程，使安装在车身内部的传感器把 ego 前悬长度错误计入安全间距。

修复后，感知桥根据传感器前向安装位置和 ego `bounding_box.extent.x` 统一换算为车身净距，再进入融合、跟车控制和证据记录。边界框缺失或非法时保持保守兼容，不产生负距离。

### 2. 转向变化率依赖控制帧率

横向控制的转向变化上限原先按“每帧”固定。控制周期从 `0.05 s` 变成 `0.10 s` 后，每秒可用转向变化率减半，连续弯道会切弯并触发横向安全停车。

修复后，Pure Pursuit 使用 `VehiclePose.sim_time_s` 将转向变化上限归一化到官方 `0.05 s` 基准；无时间戳调用保持原行为，异常或倒退时间戳回退到 1 倍，缩放限制在 `0.5~4.0`。官方 `0.05 s` 路径不改变。

## CARLA + Qwen2B 证据结果

| Variant / 目标事件 | 扰动重点 | Qwen 计划与终态 | 关键安全结果 | 结论 |
|---|---|---|---|---|
| GEN-001 / 自行车 | 横向偏移、RGB 降级、0.10 s | `SLOW_DOWN → KEEP_LANE`，`SUCCEEDED` | 净距 `3.27 m`，恢复 `36.58 km/h`，路线偏差 `0.78 m`，碰撞 0 | 目标段通过 |
| GEN-005 / 自行车 | 速度 1.2 倍、纵向偏移、稀疏 LiDAR、0.10 s | `SLOW_DOWN → KEEP_LANE`，`SUCCEEDED` | 净距 `5.79 m`，恢复 `37.85 km/h`，路线偏差 `0.75 m`，碰撞 0 | 目标段通过 |
| GEN-009 / 交叉口切入 | 速度 0.8 倍、横向/纵向偏移、0.10 s | `SLOW_DOWN → KEEP_LANE`，`SUCCEEDED` | 切入车净距 `8.04 m`，恢复 `35.09 km/h`，路线偏差 `0.79 m`，碰撞 0 | 目标段通过 |
| GEN-017 / 行人 | 速度 1.2 倍、启动延后、稀疏 LiDAR、0.10 s | `YIELD → KEEP_LANE`，`SUCCEEDED` | 行人净距 `3.05 m`；修复前路线偏差 `1.24 m`，用于定位帧率问题 | 诊断证据 |
| GEN-021 / 行人 | 速度 0.8 倍、启动提前、0.10 s | `YIELD → KEEP_LANE`，`SUCCEEDED` | 净距 `3.35 m`，恢复 `38.80 km/h`，路线偏差 `0.78 m`，碰撞 0 | 扩展门禁全部通过 |

最终三类事件均满足目标段合同：Qwen 请求存在、无缺失请求、行为在允许集合内、命令具有唯一成功终态、Actor 在规定窗口激活、指令在规定里程触发、路线偏差不超过 `1.0 m`、无碰撞。

## 服务器证据位置

服务器根目录：`/home/tiaozhansai/carla-driving-main-optimization`

- 距离修复前失败：`artifacts/logs/S2_generalization_20261022/bike_gen001_retry/`
- 自行车快速扰动：`artifacts/logs/S2_generalization_20261022/bike_gen005/`
- 行人帧率问题复现：`artifacts/logs/S2_generalization_20261022/ped_gen017/`、`ped_gen021/`
- 转向归一化后行人通过：`artifacts/logs/S2_generalization_20261023/ped_gen021_time_normalized/`
- 转向归一化后切入通过：`artifacts/logs/S2_generalization_20261023/cutin_gen009_time_normalized/`
- 两项修复共同回归自行车：`artifacts/logs/S2_generalization_20261023/bike_gen001_time_normalized/`

短程恢复运行会因为未继续执行后续阶段而在文件末尾输出整场景 `FAILED`。判断目标事件时必须查看 `scenario_extension_acceptance` 中当前阶段对应的检查和证据，不能把未运行的未来命令当作回归失败。GEN-021 最终运行只剩一个阶段，因此其 `scenario_extension_acceptance` 为完整 `passed=true`。

## 验收边界

本报告证明五组可复现扰动下三类目标事件的闭环稳定性，不替代官方 S2 全 8 km 终验。代码提交前仍执行全量 pytest、场景静态校验和官方场景合同校验；正式版本的完整 8 km 结果继续沿用独立长程证据。
