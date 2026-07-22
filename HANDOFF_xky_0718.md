# HANDOFF xky 0718

## 今日完成

- 在昨日融合版基础上继续吸收并完善 `carla_driving_rstar` 的场景驱动执行链路。
- 新增严格场景验收器，按场景预期检查碰撞、停车、路线偏差、安全接管和事件证据。
- 修复 B 类道路与 B06 左转：优化场景路线生成/重采样，路口优先使用安全路线偏差判断。
- 修复 D04 车道偏离恢复及安全接管逻辑，并补充相关单元测试。
- 完善传感器模式，接入 RGB ONNX 车辆/行人检测，并与前向 LiDAR 做保守融合；检测异常时保持 fail-closed。
- 保存今天的场景验收、回归、传感器和 RGB ONNX 仿真实跑日志到 `artifacts/`。

## 验证结果

- 单元/集成测试：`232 passed, 1 skipped`。
- B06 传感器实跑通过：完成左转，无碰撞，最大横向误差约 `1.44 m`。
- RGB ONNX 实跑：前车场景 119/120 帧检测到车辆；行人场景 99/100 帧检测到行人，均安全停车并通过验收。
- 当前完整提交：`ef7950a`（已推送到 `carla_driving_1/main`）。

## 关键位置

- 场景执行：`integration/scenario_execution.py`
- 场景验收：`integration/scenario_acceptance.py`
- CARLA 入口：`integration/carla_runner.py`
- 传感器融合：`integration/carla_perception.py`
- ONNX 检测：`integration/rgb_detector.py`
- ONNX 使用说明：`integration/RGB_ONNX.md`
- 正式运行证据：`artifacts/acceptance_*`、`artifacts/regression_*`、`artifacts/sensor_*`、`artifacts/rgb_onnx_v1`

## 注意与下一步

- 仓库未提交本地 Python 运行环境和 `yolo11n.onnx` 权重；使用者需按 `integration/RGB_ONNX.md` 自行准备模型。
- 当前 ONNX 是快速目标检测层，不是视觉语言大模型；复杂多模态决策仍需接入 Qwen2.5-VL/OpenVLA 类模型。
- 建议下一步先实现严格的多模态决策 JSON 接口和 CARLA 数据采集器，再做 VLM 零样本验证及 LoRA/QLoRA。
