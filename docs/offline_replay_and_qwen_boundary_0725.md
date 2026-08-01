# 离线回放验收与 Qwen 正式接入边界

## 目的

这套链路不启动 CARLA，可用队友保存的 RGB、LiDAR、车辆状态和 Qwen 输出重复运行：

```text
记录数据
  → RGB 检测（可选 ONNX）
  → LiDAR 前方距离
  → 严格 Qwen 输入/输出边界
  → A/B/C/D 正式控制链
  → 每帧验收结果与 JSON 报告
```

离线通过不能替代 CARLA 实跑，但可以区分“算法/协议错误”和“CARLA/显卡环境错误”。

## 快速验证

```powershell
python tools/replay_acceptance.py examples/replay_acceptance_sample.jsonl `
  --output artifacts/replay_acceptance_sample_report.json
```

返回码：

- `0`：所有帧的期望条件通过。
- `1`：回放完成，但至少一个验收条件失败。
- `2`：数据格式、依赖或运行异常。

## JSONL 数据格式

每行是一帧，必填字段：

```json
{
  "schema_version": "1.0",
  "frame": 1,
  "sim_time_s": 0.05,
  "vehicle": {
    "speed_mps": 0.0,
    "x_m": 0.0,
    "y_m": 0.0,
    "z_m": 0.0,
    "yaw_deg": 0.0,
    "lane_id": "1"
  }
}
```

可选传感器字段：

- `rgb_path`：相对 JSONL 所在目录的 `.npy`、PNG 或 JPEG。`.npy` 必须为 `uint8 (H,W,3)` RGB。
- `lidar_path`：相对目录的 `.npy`，形状为 `(N,3)` 或 `(N,4)`。
- `lidar_points`：直接内嵌的点列表，适合小型单测。
- `perception.detected_objects`：没有 ONNX 模型时使用的已记录检测框。

所有文件路径必须位于数据集目录内，禁止 `../` 跳出目录。

使用 ONNX 重新检测 RGB：

```powershell
python tools/replay_acceptance.py dataset/replay.jsonl `
  --rgb-detector-model models/yolo11n.onnx `
  --output artifacts/replay_report.json
```

未指定模型时仍会读取并校验 RGB，但使用 JSONL 中记录的 `detected_objects`。

## Qwen 输入边界

`integration.QwenInputContext` 固定以下内容：

- `request_id`、`frame`、`sim_time_s`
- `voice_command`
- `rgb_ref`（图像引用，不把二进制塞入日志）
- `scene_state`
- `perception`
- `safety_state`

所有结构化字段必须能被严格 JSON 序列化，拒绝 NaN、无限值、非字符串键和不可序列化对象。

## Qwen 输出边界

模型只允许返回单个 JSON 对象：

```json
{
  "action": "SET_SPEED",
  "target_speed_mps": 3.0,
  "confidence": 0.95,
  "requires_confirmation": false,
  "reason_zh": "道路清晰",
  "decision_source": "QWEN_VL",
  "visual_valid": true
}
```

规则：

- 禁止 Markdown 围栏和 JSON 外额外文字。
- 禁止 `throttle`、`brake`、`steer` 等底层控制。
- 禁止未知字段。
- `requires_confirmation` 和 `visual_valid` 必须是真正的 JSON 布尔值。
- `SET_SPEED` 必须提供 `target_speed_mps`。
- 速度范围限制为 `0–50 m/s`，置信度限制为 `0–1`。

## 超时和安全降级

`AsyncQwenDecisionBridge` 同时具有：

- 仿真时间 TTL：结果过期变为 `STALE`。
- 墙钟推理截止时间：模型长期不返回变为 `TIMEOUT`。
- 最新请求覆盖：旧推理完成后不能覆盖新请求。

`PENDING`、`TIMEOUT`、`STALE`、`ERROR` 都不产生可执行 Qwen 命令。回放器把这些状态转换为 `QWEN_*` watchdog 告警，由正式 D 安全链输出零油门、全制动。模型失败不会伪装成一个模型生成的 `STOP`。

## 每帧验收字段

`expected` 可包含：

- `qwen_status`
- `safety_override`
- `safety_reason`
- `min_brake`
- `max_throttle`
- `min_detection_count`
- `lead_distance_range_m`
- `rgb_loaded`
- `lidar_loaded`

报告会保存每帧检测数量、前方距离、Qwen 状态、watchdog、最终油门/制动/转向和失败原因。
