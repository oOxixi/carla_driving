# Qwen 正式运行边界

正式链路统一使用单个高层 `action`、`target_speed_mps` 和
`requires_confirmation`。

`car_control_A.HighLevelCommandAdapter` 负责将该协议转换为运行时命令，并拒绝
任何 `throttle`、`brake`、`steer` 字段。

## 非阻塞要求

当前真实 Qwen2.5-VL 验证的平均推理耗时约为 1.8 秒，因此模型推理不得运行在
CARLA 同步控制线程。

`integration.AsyncQwenDecisionBridge` 提供以下状态：

- `PENDING`：推理仍在进行，不产生车辆命令；
- `READY`：只允许消费 TTL 内最新结果；
- `STALE`：结果过期，不产生车辆命令；
- `ERROR`：模型或协议失败，不产生车辆命令。

新请求会覆盖队列里尚未执行的旧请求。已经在运行的旧推理即使完成，也不能覆盖
更新请求的结果。

## 控制所有权

Qwen 只生成高层候选动作。A 负责命令适配和 FSM，B/C 负责确定性控制，D 保留
最终安全否决权。正式车辆只允许 `integration.carla_runner` 的控制循环调用一次
Ego `apply_control()`。

## 历史 Day20 协议

Day20 的 `actions` 列表和 `target_speed_kmh` 仅保留用于历史演示。进入正式
runner 前必须转换成单动作、m/s 协议。不能让 Day20 独立 world tick 或控制 Ego
与正式 runner 同时运行。

## 后续联机门槛

1. 将实时 RGB 与 C 组 SafetyState 构造成 Day22Context；
2. 低频提交 Qwen 请求；
3. 仅把新鲜 `READY` 结果提交给 ControlRuntime；
4. `PENDING/STALE/ERROR` 由 watchdog 和 D fail-closed；
5. 日志同时记录 Qwen 原始输出、高层命令、最终控制和安全覆盖原因。
