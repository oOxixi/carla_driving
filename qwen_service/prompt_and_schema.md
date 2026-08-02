# Qwen 提示词与 Schema

正式 Qwen3.5 主线提示词是 `integration.qwen_vl_adapter.build_action_choice_prompt()`。它只要求模型输出一个 `A/B/C/D/E` 代码，不让模型自回归生成完整 JSON。`build_strict_qwen_prompt()` 仅供旧 Transformers/AWQ JSON 后端复查历史证据。

远端主线把完整场景与最多两个结构化目标裁剪组合成固定 256×256 图像，即 Qwen3.5 的 64 个合并视觉 token；没有目标时下半区使用道路关注区域。

`POST /infer` 输入严格等于 A 已冻结的 `QwenInputContext`。实时 CARLA 适配器只传距离优先的 Top-8 目标，并把 COCO 道路参与者归一为 `vehicle`/`pedestrian`：

```json
{
  "schema_version": "1.0",
  "request_id": "req-001",
  "frame": 1,
  "sim_time_s": 0.05,
  "voice_command": "减速",
  "rgb_ref": "req-001.jpg",
  "scene_state": {},
  "perception": {"detected_objects": []},
  "safety_state": {}
}
```

模型原始响应只能是一个代码。仓库根据代码 logprob、语音速度、结构化目标和安全状态组装最终响应。最终响应仍必填 `action`、`confidence`、`requires_confirmation`；可选 `target_speed_mps`、`target_track_id`、`reason_zh`、`decision_source`、`visual_valid`。未知字段和 `throttle/brake/steer/steering_angle/wheel_angle` 一律拒绝。

允许动作沿用冻结协议：`START`、`STOP`、`SLOW_DOWN`、`SET_SPEED`、`EMERGENCY_STOP`。目标 ID 必须来自 `perception.detected_objects`；目标缺失或不唯一时要求确认或安全停车。服务输出仍会经过 A 的 high-level adapter 和 D 的安全仲裁，不能直接下发 VehicleControl。
