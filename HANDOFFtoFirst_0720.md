# 7 月 20 日第二组向第一组交接

> 文档状态：截至 7 月 22 日回填。RGB + LiDAR 保守融合、异常降级和确定性故障注入已经完成。

## 今日交付结论

第二组向第一组提供统一的“融合后安全状态”。分工原则如下：

- RGB 负责目标类别、置信度和图像位置等语义信息。
- LiDAR 负责前向距离，并参与闭合速度和 TTC 计算。
- 控制模块根据融合状态生成车辆请求。
- D 安全仲裁拥有最终否决权，任何 Qwen 或用户命令都不能绕过。

## 已确定的视觉输入接口

每个视觉结果必须与 LiDAR 使用相同 `frame`，并至少包含：

```json
{
  "frame": 1200,
  "valid": true,
  "object_class": "VEHICLE",
  "confidence": 0.92,
  "source": "RGB_ONNX"
}
```

要求：

- `valid=false` 时不得携带猜测的类别和置信度。
- 当前有效置信度阈值为 `0.60`；低于阈值按视觉无效处理。
- 类别建议统一为 `PERSON/PEDESTRIAN/VEHICLE/CAR/TRUCK/BUS/BICYCLE/MOTORCYCLE/OBSTACLE/UNKNOWN`。
- 第一组如输出交通灯状态，应另外给出置信度与来源，不能把 `UNKNOWN` 转成 `GREEN`。

## 第二组返回的融合安全状态

```json
{
  "schema_version": "1.0",
  "frame": 1200,
  "sim_time_s": 60.0,
  "front_distance_m": 7.0,
  "closing_speed_mps": 6.0,
  "ttc_s": 1.17,
  "object_class": "VEHICLE",
  "object_confidence": 0.92,
  "visual_valid": true,
  "lidar_valid": true,
  "fused_valid": true,
  "fusion_mode": "RGB_LIDAR",
  "recommended_action": "EMERGENCY_BRAKE",
  "reason": "low_ttc",
  "source_by_field": {
    "visual": "RGB_ONNX",
    "lidar": "LIDAR_FRONT_CORRIDOR",
    "closing_speed_mps": "LEAD_TRACKER",
    "ttc_s": "FRONT_DISTANCE_DIVIDED_BY_CLOSING_SPEED"
  }
}
```

中文解释：RGB 确认前方是车辆，LiDAR 给出 7 m 距离，自车正在快速接近，TTC 约 1.17 s，因此车辆侧要求紧急制动。即使 Qwen 输出“继续行驶”，D 仍应覆盖该动作。

## 融合与安全优先规则

| 情况 | 融合结论 | 车辆侧动作 |
|---|---|---|
| RGB、LiDAR 均有效且同帧 | 使用 RGB 类别和 LiDAR 距离/TTC | 按距离和 TTC 输出保持、减速或紧急制动 |
| RGB 漏检、LiDAR 发现障碍 | `LIDAR_ONLY`，不丢弃障碍 | 仍按距离/TTC 减速或制动 |
| RGB 发现危险目标、LiDAR 无可靠距离 | `RGB_ONLY`，距离未知 | `FULL_BRAKE`，原因是危险目标无量程 |
| LiDAR 帧无效 | `FAIL_CLOSED` | `FULL_BRAKE` |
| RGB 低置信度 | 不采用类别，不虚构语义 | 继续使用 LiDAR 几何风险 |
| RGB 与 LiDAR 不同帧 | 拒绝融合 | 安全降级，不允许正常推进 |

当前默认阈值：提醒距离 10 m、紧急距离 5 m、提醒 TTC 2.5 s、紧急 TTC 1.5 s。

## 当日验收记录

- 同帧 RGB/LiDAR 融合：已通过单元与集成测试。
- RGB 漏检但 LiDAR 发现障碍：已验证不会漏掉障碍。
- LiDAR 无效：故障注入验证为全制动。
- RGB 危险目标但无 LiDAR 距离：故障注入验证为全制动。
- 视觉检测器不可用但 LiDAR 有效：保留 LiDAR 独立判断，不伪造类别。
