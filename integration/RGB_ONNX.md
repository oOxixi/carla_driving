# RGB ONNX 与 C 组 LiDAR 保守融合

本地已兼容 GitHub `oOxixi/carla_driving` 的 `ef7950a` 检测改进，并保留当前分支的场景驱动验收链路。传感器桥可以在每个严格对齐的 CARLA RGB 帧上运行 Ultralytics 风格 COCO ONNX 模型；保留 `person/bicycle/car/motorcycle/bus/truck`，再与同帧前向 LiDAR 距离融合。

## 安装与模型

```powershell
python -m pip install -r requirements.txt
```

把兼容模型放在 Git 忽略的路径，例如 `artifacts/models/yolo11n.onnx`。模型权重不随仓库提交；打包前需要确认第三方模型许可和比赛分发规则。

## 真实传感器运行

```powershell
python -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --scenario-file scenarios/safety_D/D03_front_vehicle_brake.json `
  --scenario-facts-mode perception --perception-mode sensors `
  --rgb-detector-model artifacts/models/yolo11n.onnx `
  --rgb-detector-confidence 0.35 `
  --rgb-detector-iou 0.45 `
  --realtime
```

## 数据与安全语义

- `scene.detected_objects`：RGB 类别、置信度、归一化框，以及与同帧 LiDAR 关联后的距离。
- `c_safety_state`：`visual_valid/lidar_valid/fused_valid`、前向距离、闭合速度、TTC、融合模式、建议动作、原因和各字段来源。
- RGB 缺失或低置信度时不编造类别；LiDAR 仍可独立触发减速/制动。
- 已配置 ONNX 模型但加载/推理失败时，正常推进被抑制并输出全制动。
- RGB 检出中央走廊危险物、LiDAR 却没有可用距离时，C 输出 `FULL_BRAKE / visual_hazard_without_range`。
- LiDAR 检出障碍而 RGB 漏检时，障碍保留为 `LIDAR_ONLY`，并按静止障碍保守处理。

当前关联策略是中央图像走廊启发式，不冒充车道分割。正式验收必须保留 `source_by_field` 和 `c_safety_state`，并明确区分 `scenario-facts-mode perception`、`scenario` 与 `fuse`。
