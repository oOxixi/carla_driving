# Day22 多模态决策问题清单

## 1. 凭空编造目标
没有可靠视觉类别却声称“发现行人”。

解决：仅当 `visual_valid=true`、`object_class=PEDESTRIAN/PERSON` 且置信度达阈值时，允许使用行人原因。LiDAR-only 不猜类别。

## 2. 用户命令覆盖安全
红灯或低 TTC 时仍输出 `START`。

解决：安全状态优先；红灯 `STOP`，低 TTC `EMERGENCY_STOP`。

## 3. 只有距离没有语义
把 LiDAR 距离解释成车辆或行人。

解决：只输出“前方距离不足”或“TTC风险”。

## 4. 低置信度仍执行
解决：
```text
action=STOP
requires_confirmation=true
```

## 5. 输出底层控制量
禁止 `throttle`、`brake`、`steer`。

## 6. 解释过长
`reason_zh` 保持一句话，建议不超过 20 个汉字。

## 7. 停止线信息不足
需要第二组提供 `distance_to_stop_line_m`。

## 8. TTC 不稳定
需要 `closing_speed_mps`、连续帧距离和 `ttc_s`。
