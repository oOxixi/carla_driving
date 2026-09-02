# 成员4：S3 极限应急闭环交付

## 范围与固定配置

- 场景：`OFFICIAL_S3_EXTREME_EMERGENCY_6KM`
- 配置：`scenarios/official_competition/S3_extreme_emergency_6km.json`
- 地图/天气/种子：Town04 / HardRainNight / 20260303
- 模型：继续使用项目现有 7B Qwen Planner V2 服务；不切换模型、不修改权重。
- 路由：雨夜安全车速、施工绕行共 2 次 `QWEN_PLAN`；加塞、行人共 2 次
  `FAST_LOCAL`，紧急制动不能等待 Qwen。

## 最终阈值

| 项目 | 阈值 |
|---|---:|
| 加塞触发距离 | 32 m（Actor 动作），30 m（紧急指令） |
| 行人紧急指令距离 | 42 m |
| 完整制动生效 | `brake >= 0.5` 且 `throttle <= 0.03` |
| 应急响应 P95 | ≤100 ms |
| 应急响应最大值 | ≤120 ms |
| 路线横向误差 | ≤1.0 m |
| 碰撞/交通违规/决策失败 | 0 |
| 多模态语义对齐 | ≥97% |
| 停车保持与恢复 | 加塞至少 2 s、行人至少 6 s；危险窗口后恢复 18 km/h |

## 应急事件与验收证据

| 事件 | 预期处理 | 必须记录 |
|---|---|---|
| 雨夜低光 | 视觉不稳定时继续使用 LiDAR/Radar 硬约束，不加速冒险 | 感知来源、TTC、逐帧 sensor-to-control |
| 施工锥桶/车道收窄 | Qwen 高层减速绕行，控制器完成合法并道并回归路线 | Qwen request/plan/route/terminal、最小距离、路线误差 |
| 车辆加塞 | 本地快速链抢占，立即撤销油门并制动 | 五阶段时间戳、TTC、最小距离、安全原因 |
| 横穿行人 | 本地快速链抢占，停车并保持 | 五阶段时间戳、TTC、最小距离、停车保持 |

每个动态危险均须生成：`danger_timestamp_s`、`perception_timestamp_s`、
`decision_timestamp_s`、`safety_override_timestamp_s`、`control_effect_timestamp_s` 和
`response_ms`。缺任一字段即失败，不能用画面主观判断替代。

## 最短执行流程

```bash
export QWEN_SERVICE_URL=http://127.0.0.1:18000
export QWEN_MODEL=Qwen/Qwen2.5-VL-7B-Instruct-AWQ

bash scripts/run_official_s3_member4.sh --validate
bash scripts/run_official_s3_member4.sh --smoke
bash scripts/run_official_s3_member4.sh --run
```

正式运行结束后脚本自动从原始 JSONL 和 summary 生成同名 `.member4.json`。只有
`.member4.json` 中 `passed=true` 才算成员4完成。运行器只会在配置的保持时间结束、没有活动
指令且没有安全锁存时恢复行驶，从而同时满足停车保持和 6 km 路线完成。`--smoke` 只用于发现启动、Actor、传感器
或服务问题，不能作为正式成绩。

演示视频使用同一个正式运行的 `scenario_id / seed / code_version`，至少保留施工障碍、车辆
加塞和横穿行人三段，并与 `.member4.json` 一起交付。视频是辅助证据，判定仍以日志为准。

## 问题复现

- 服务模型不是 7B：脚本在启动 CARLA 前拒绝运行。
- 行人或加塞未被感知：`required_emergency_event_ids` 或五阶段时间戳检查失败。
- 制动超过 100/120 ms：报告分别标记 P95 或最大延迟失败。
- 未完成停车保持、发生碰撞或违规：报告直接失败。

当前代码侧未解决问题：无。正式成绩和视频必须在 CARLA 0.9.16 + 7B 生产服务机器上生成，
仓库不伪造实机结果。
