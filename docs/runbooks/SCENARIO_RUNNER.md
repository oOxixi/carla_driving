# scenario_runner接入约定

## A需要读取的字段

- `scenario_id`
- `map`
- `weather`
- `seed`
- `runtime.sync_mode`
- `runtime.fixed_delta_seconds`
- `runtime.duration_s`
- `ego_spawn`
- `route.points_xy_m`
- `commands`
- `actors`
- `sensors`
- `expected`

## A运行时流程

```text
读取场景JSON
→ 加载CARLA地图和天气
→ 设置同步模式和fixed_delta_seconds
→ 生成ego车辆和传感器
→ 生成或转换route reference
→ 按commands时间注入DrivingCommand
→ 每帧构建VehicleState
→ 调B输出steer
→ 调C输出throttle/brake
→ 合成raw_control
→ 调D安全仲裁
→ A唯一apply_control
→ 写frame/event/result/score日志
```

## 坐标说明

当前场景里的`route.points_xy_m`是局部路线模板，不是最终CARLA地图世界坐标。A需要负责转换。

## actor说明

- `vehicle`：前车、静态障碍物、跟车目标
- `walker.pedestrian`：行人横穿
- `traffic_light`：红灯/黄灯/绿灯和停止线距离

如果A当前暂时不能生成actor，可以先将actor字段作为风险桩输入D，完成接口联调。
