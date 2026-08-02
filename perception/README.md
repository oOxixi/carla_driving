# C：同步感知、融合跟踪与故障降级

本目录输出唯一 `PerceptionState V1`。坐标统一为 ego 车体坐标：x 向前、y 向左、
z 向上，单位为米；速度为米每秒。RGB、毫米波雷达、LiDAR 和 VehicleState 必须
通过 `SensorSynchronizer` 的帧号和时间容差检查后才能被标记有效。

处理顺序：

```text
SensorSample + Extrinsics
  -> SensorSynchronizer（有界缓存、同帧、stale）
  -> RGBPipeline（道路 ROI、低频检测、高频稳定 ID、Top-K）
  -> FusionTracker（RGB/Radar/LiDAR 关联、TTC、最小距离、风险）
  -> interfaces/perception_state.schema.json
```

故障注入：

```bash
perception/fault_injection.sh input.jsonl output.jsonl camera_blackout
perception/fault_injection.sh input.jsonl output.jsonl radar_dropout
perception/fault_injection.sh input.jsonl output.jsonl lidar_missing
perception/fault_injection.sh input.jsonl output.jsonl sensor_latency --latency-ms 300
perception/fault_injection.sh input.jsonl output.jsonl radar_noise --noise-std-m 2
```

每种失效都会输出明确无效性或错误码，不会将空数据伪造为“正常无目标”。

实时 CARLA 入口位于 `integration/carla_perception.py`：RGB/LiDAR 为必需同帧流，
Radar 为 5 ms 有界可选同帧流。有效 Radar 径向速度与 LiDAR 距离通过 4 m 门限关联；
缺帧或非法 Radar 明确写入 `source_by_field["radar_modality"]`，继续使用 LiDAR 的
保守静态障碍假设。`tools/check_sensor_stability.py --sensor all` 可独立探测三路回调。
