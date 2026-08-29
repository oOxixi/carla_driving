# Qwen 高层决策提示词与输出约束

## 输入裁剪

- 图像只保留道路 ROI，像素预算为 `min_pixels=50176`、`max_pixels=200704`；
- 最多保留距离最近且置信度最高的 8 个目标；
- 输入只包含 `ModelRequest` 中的场景摘要、Top-K 目标和安全约束；
- 不把 CARLA actor、原始点云、完整日志或底层控制状态塞入提示词；
- 服务输出上限为 48 token，温度应固定为 0。

## 系统约束

```text
你是自动驾驶系统的高层多模态决策模块。只输出一个 JSON 对象。
安全约束和交通规则优先于用户命令。目标不唯一、视觉无效、状态过期或
置信度不足时，必须要求确认或输出 HOLD/STOP。禁止输出 throttle、brake、
steer、steering_angle、wheel_angle 等底层控制量。
target_id 只能从输入 targets[].target_id 精确复制，禁止编造。
```

实际完整提示词生成函数位于 `integration/qwen_vl_adapter.py::build_strict_qwen_prompt`。
模型服务随后把其短 JSON 归一化为 `interfaces/decision_plan.schema.json`；两层均为
`additionalProperties: false`。

## 输出示例

模型原始短 JSON 只使用 `START/STOP/SLOW_DOWN/SET_SPEED/EMERGENCY_STOP`。
例如唯一目标跟随先输出：

```json
{"action":"SLOW_DOWN","confidence":0.93,"requires_confirmation":false,"target_track_id":"vehicle-right-01"}
```

服务层随后补上不超过 2 m/s 的确定性保守速度，并转换成严格 `DecisionPlan V1`；
不会让模型输出油门、制动或转向值。当前 D 还不能执行转向/变道，因此相关复杂请求
即使模型给出不兼容计划也会被 A/D 拒绝并保持停车。

Qwen 的输出只能成为 A 校验后的高层计划。D 独立计算并仲裁最终油门、制动和方向。

## Planner V2

复杂机动使用 `--qwen-mode planner_v2`，输出严格的
`interfaces/maneuver_plan.schema.json`，不替换 V1。完整提示词位于
`integration/qwen_plan_adapter.py::PLANNER_V2_SYSTEM_PROMPT`。

- 只允许 14 个受限高层行为，步骤数为 1–4；
- 每步必须声明前置条件、确定性完成条件、超时与失败策略；
- `target_id` 只能复制请求中的可见目标；目标车道必须来自
  `scene_capabilities.available_lanes`；
- 红灯、`must_stop`、紧急风险和限速优先；
- 不确定时 `requires_confirmation=true`，由 A 安全等待；
- 递归拒绝 `throttle/brake/steer/wheel_angle/torque/raw_waypoints`。

本地服务示例：

```bash
python -m qwen_service.server \
  --qwen-mode planner_v2 \
  --model-path /path/to/Qwen2.5-VL-7B-Instruct \
  --image-root /shared/carla_driving \
  --timeout-ms 5000 \
  --max-new-tokens 256
```

`--deterministic-test-backend` 在 Planner V2 下会启用独立的契约 stub；其结果只能
用于接口与故障测试，不能作为真实模型准确率或延迟证据。
