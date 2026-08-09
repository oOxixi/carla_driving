# CARLA 演示可视化使用说明

正式演示界面已接入 `integration.carla_runner`。展示层只读取语音、Qwen、感知、安全和执行快照，不调用 `world.tick()`，也不修改车辆控制量。绘制使用独立的“最新帧优先”线程；显示跟不上时只丢弃旧画面，不阻塞控制循环。

## 正式演示

在原有运行命令后增加：

```bash
--ui-mode demo --realtime
```

例如红灯冲突场景：

```bash
python -m integration.carla_runner \
  --scenario-file scenarios/acceptance_suite/advanced/ACC_A02_red_light_conflict.json \
  --qwen-service-url http://127.0.0.1:18000 \
  --perception-mode sensors \
  --scenario-facts-mode perception \
  --realtime \
  --ui-mode demo
```

界面固定为 `1920×1080`：左侧约 72% 为真实 CARLA RGB 画面，右侧显示当前任务、用户语音、系统理解、场景感知、AI 决策、安全监督和车辆执行，底部为处理时间线。只有当前决策目标会被高亮。

## 调试模式

```bash
--ui-mode debug
```

调试模式会额外显示帧号、状态机、控制量和内部安全原因。正式录屏使用 `demo`，不要使用 `debug`。

## 录制合成帧

需要后期合成视频时，可让 UI 异步保存已绘制的 PNG 帧：

```bash
--ui-mode demo \
--ui-fps 10 \
--ui-record-dir artifacts/demo_frames/red_light
```

输出帧均为 `1920×1080`，名称按 `frame_000000.png` 递增。保存发生在展示线程，磁盘较慢时会丢弃中间画面，但不会拖慢车辆控制。

## 数据来源

- 用户语音：实际 `CommandTimeline`、文件/麦克风语音结果；
- 系统理解：实际语音 envelope 的 intent 与参数；
- Qwen 状态与决策：实际异步路由和模型结果；
- 场景感知：当前帧对齐的 `PerceptionFrame` 与故障状态；
- 安全监督：D/C 最终 `FrameResult` 的安全接管结果；
- 车辆执行：真实车速、目标速度、执行反馈和终态。

字段缺失时界面显示“暂无/等待”，不会填入测试期望动作或伪造模型结果。快速确定性路径会明确显示“快速路径，无需推理”，不会冒充 Qwen 输出。
