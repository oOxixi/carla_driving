# 第二组需要补充的状态字段

|场景|必须字段|推荐字段|用途|
|---|---|---|---|
|红灯|`traffic_light`、`distance_to_stop_line_m`|`speed_mps`|判断停车时机|
|前车|`front_distance_m`、`closing_speed_mps`|`ttc_s`、`object_class`|跟车减速|
|行人|`object_class`、`object_confidence`、`visual_valid`|`front_distance_m`、`lidar_valid`|语义+距离|
|低 TTC|`ttc_s`|`front_distance_m`、`closing_speed_mps`|紧急停车|
|低置信度|`visual_valid`、`lidar_valid`、`fused_valid`|`input_confidence`|安全降级|
|传感器失败|`recommended_action`、`fusion_mode`、`reason`|`source_by_field`|fail-closed|
|雨天|`weather`|道路附着/限速|保守限速|

缺失处理：
- LiDAR 无效：安全停车；
- 视觉无效但 LiDAR 有距离：允许减速/停车，但不猜类别；
- 视觉确认危险但无距离：安全停车；
- 红灯缺停止线距离：交由 C/D 保守处理。
