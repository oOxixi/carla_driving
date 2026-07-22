# 7 月 19 日第二组向第一组交接

> 文档状态：截至 7 月 22 日回填，记录已完成的车辆/雷达状态接口和自动化验证结果。

## 今日交付结论

第二组向第一组提供一版可直接加入 Qwen 输入的“车辆与雷达状态摘要”。摘要覆盖车辆速度、前向距离、前车速度、闭合速度、TTC、期望安全间距、交通灯、停止线距离、路线偏差以及碰撞/压线事件。

第一组只需使用这些状态帮助 Qwen理解场景和输出高层动作，不应让 Qwen 生成方向盘、油门或刹车数值。

## 建议交互字段

| 字段 | 单位/取值 | 给第一组的含义 |
|---|---|---|
| `schema_version` | 当前为 `1.0` | 接口版本，双方变更字段时必须同步升级 |
| `frame` | 非负整数 | CARLA 帧号；视觉、雷达和车辆状态必须同帧 |
| `sim_time_s` | s | 仿真时间，不使用电脑墙钟时间 |
| `speed_mps` | m/s | 自车当前速度 |
| `front_distance_m` | m 或 `null` | 前向走廊最近障碍距离；`null` 表示没有可靠距离，不代表道路安全 |
| `lead_speed_mps` | m/s 或 `null` | 可关联前车时的前车速度 |
| `closing_speed_mps` | m/s 或 `null` | 自车速度减前车速度；正值代表正在接近 |
| `ttc_s` | s 或 `null` | 正闭合速度下的碰撞时间；无可靠计算时为 `null` |
| `desired_gap_m` | m | 当前速度下的建议安全间距 |
| `traffic_light` | `RED/YELLOW/GREEN/UNKNOWN` | `UNKNOWN` 必须按不确定处理，不得当成绿灯 |
| `distance_to_stop_line_m` | m 或 `null` | 到停止线距离；无可靠结果时为 `null` |
| `lane_offset_m` | m 或 `null` | 相对当前车道中心偏移 |
| `route_deviation_m` | m 或 `null` | 相对规划路线偏差 |
| `collision` | 布尔值 | 是否已发生碰撞事件 |
| `lane_invasion` | 布尔值 | 是否触发压线事件 |
| `source_by_field` | 对象 | 每个状态来自 LiDAR、地图、车辆状态、事件传感器或降级估计 |

## 给第一组的状态样例

```json
{
  "schema_version": "1.0",
  "frame": 1200,
  "sim_time_s": 60.0,
  "speed_mps": 8.0,
  "front_distance_m": 20.0,
  "lead_speed_mps": 5.0,
  "closing_speed_mps": 3.0,
  "ttc_s": 6.67,
  "desired_gap_m": 15.0,
  "traffic_light": "GREEN",
  "distance_to_stop_line_m": null,
  "lane_offset_m": 0.08,
  "route_deviation_m": 0.12,
  "collision": false,
  "lane_invasion": false,
  "source_by_field": {
    "front_distance_m": "LIDAR_FRONT_CORRIDOR",
    "traffic_light": "CARLA_TRAFFIC_LIGHT",
    "route_deviation_m": "ROUTE_REFERENCE"
  }
}
```

中文解释：车辆正在以 8 m/s 行驶，前方 20 m 有较慢目标，自车以约 3 m/s 的闭合速度接近，当前 TTC 约 6.67 s，未达到紧急制动条件；Qwen 可以建议保持谨慎或减速，但不能直接输出刹车值。

## 已完成的状态来源与保守规则

可稳定按帧提供：自车速度和位姿、LiDAR 前向距离、碰撞/压线事件、交通灯枚举、路线偏差及最终控制结果。

需要明确来源或安全兜底：

- LiDAR 只能提供几何距离，不能自行确定“车辆/行人”等语义类别。
- 前车速度依赖目标关联；不能可靠关联时不应虚构速度。
- 停止线距离可能来自地图停止点或触发区域近似，第一组展示时须保留来源。
- 任一关键字段为 `null` 或传感器异常时，Qwen 应输出“无法判断/建议减速或停车”，不能推断道路必然安全。

## 当日验收记录

- 离线 smoke 场景定义与契约：5 项全部通过。
- 每帧车辆、感知、安全和最终控制字段：链路已具备。
- 对 `null`、`UNKNOWN`、传感器无效和不同来源字段的保守语义已经明确。
