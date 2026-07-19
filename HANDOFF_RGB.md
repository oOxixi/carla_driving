# RGB目标与交通灯感知模块交付说明

## 1. 职责

本模块接收 CARLA 0.9.16 前视 `sensor.camera.rgb` 图像，输出统一的 `VisionObservation`。
它负责目标类别、置信度、二维框、图像区域、危险区域标记和交通灯观测；不负责精确距离、TTC、变道可行性、油门、刹车、方向盘或最终安全仲裁。

## 2. 对外输出

核心字段：

- `schema_version="1.0"`
- `frame`：CARLA帧号
- `sim_time_s`：CARLA仿真时间
- `objects[].category`：大写统一枚举
- `objects[].bbox_xyxy`
- `objects[].image_region`
- `objects[].in_danger_zone`
- `traffic_light.state`：`RED/YELLOW/GREEN/OFF/UNKNOWN`
- `perception_status`：`OK/DEGRADED/TIMEOUT/ERROR/UNAVAILABLE/STALE`
- `latency_ms`

第二组需要距离、TTC时，必须使用 LiDAR/融合结果，不能使用本模块二维框推断成精确物理量。

## 3. 两种后端

1. `carla_gt`：CARLA仿真Actor投影，只用于接口冻结、场景联调与生成样例。结果必须标记为 `CARLA_GT`，不得作为RGB模型准确率。
2. `onnx`：YOLO风格ONNX检测器。交通灯目标可检测，但普通COCO模型不能判定红黄绿，颜色分类器接入前状态为 `UNKNOWN`。

## 4. 启动

```bash
python demo_rgb_carla.py --backend carla_gt --frames 300
```

ONNX：

```bash
python demo_rgb_carla.py --backend onnx --model models/yolov8n.onnx --frames 300
```

## 5. 输出证据

- `outputs/rgb_demo/vision_observations.jsonl`
- `outputs/rgb_demo/frame_*.jpg`

## 6. 已知边界

- 当前没有专用交通灯颜色分类模型；ONNX后端颜色为`UNKNOWN`。
- `in_danger_zone`是二维图像启发式标记，只能作为融合提示。
- 最终安全决策必须由控制组D仲裁。
