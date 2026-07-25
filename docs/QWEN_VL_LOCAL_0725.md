# 本地 Qwen2.5-VL 严格接入

## 边界

`integration.qwen_vl_adapter.StrictQwenVLAdapter` 只输出受限高层 JSON。
它不能输出或执行 `throttle`、`brake`、`steer`。输出必须再经过
`validate_qwen_response()`；非法 JSON、Markdown、额外文字、未知字段和底层控制字段都会失败。

正式闭环中把 `adapter.infer` 传给 `AsyncQwenDecisionBridge`。后者负责：

- 墙钟推理超时 `TIMEOUT`；
- 仿真时间过期 `STALE`；
- 非法输出/模型异常 `ERROR`；
- 新请求覆盖旧请求。

这些状态不生成模型控制命令，只产生 `QWEN_*` watchdog，由 D 安全链停车。

## 安装

在单独的 Qwen 环境中安装：

```powershell
python -m pip install -r requirements-qwen.txt
```

最终提交材料必须记录实际 `pip freeze`、GPU/CUDA、checkpoint 名称、许可证和
checkpoint SHA-256。模型目录必须已在本机，加载过程使用 `local_files_only=True`，
不会自动联网下载。

## 单帧真实模型验证

context JSON 使用 `QwenInputContext` 字段：

```json
{
  "schema_version": "1.0",
  "request_id": "req_000001",
  "frame": 1,
  "sim_time_s": 0.05,
  "voice_command": "慢一点",
  "rgb_ref": "rgb/000001.jpg",
  "scene_state": {"traffic_light": "GREEN"},
  "perception": {"lead_distance_m": 8.0},
  "safety_state": {"risk_level": "MEDIUM"}
}
```

运行：

```powershell
python tools/run_qwen_vl_decision.py context.json `
  --model-path D:/models/Qwen2.5-VL `
  --image-root D:/capture `
  --output artifacts/qwen/req_000001.json
```

输出同时保存：

- 原始模型文本；
- 严格校验后的高层动作；
- 推理延迟；
- 实际图片路径；
- `READY` 或错误信息。

单帧通过只能证明模型和协议可用。CARLA 控制循环必须继续使用异步桥和 D 最终安全仲裁。
