# A 运行时交付说明

成员 A 负责 CARLA 运行主线：命令入口、FSM 终态、同步 tick、Actor 生命周期、watchdog 故障降级，以及把 B/C/D 的输出编排成唯一 `apply_control()`。A 不直接做视觉识别、横向算法、纵向 PID 或最终安全规则，但必须保证这些模块只能通过固定顺序进入车辆控制链。

## 完成状态

当前 A 已完成 7 月 24 日演示所需的最小闭环：

- 固定 `DrivingCommand`、`ExecutionFeedback`、车况、纵向请求、控制输出等 A/C 契约。
- `BehaviorFSM` 保证每个 `command_id` 只有一个终态：`SUCCEEDED`、`FAILED`、`REJECTED`、`EXPIRED` 或 `TIMED_OUT`。
- `ControlRuntime` 固定执行顺序：命令/FSM -> B 横向 -> C 纵向 -> D 安全仲裁 -> runner 唯一 apply。
- `VoiceCommandAdapter` 支持 `SET_SPEED`、`SLOW_DOWN`、`STOP`、`EMERGENCY_STOP`、`KEEP_LANE`。
- `HighLevelCommandAdapter` 支持 Qwen 高层 JSON，禁止 `throttle/brake/steer` 等低层字段。
- `integration.carla_runner --command-json` 可自动识别旧 voice envelope 或新 Qwen high-level JSON。
- CARLA 0.9.16 Linux 环境下，`Town03` 自动使用稳定的 `Town03_Opt` 地图契约等价路径。

## 代码位置

```text
car_control_A/
  contracts.py              # A/C 共享严格数据契约
  behavior_fsm.py           # 命令生命周期和唯一终态
  command_adapter.py        # 基础中文文本快路径
  high_level_command.py     # Qwen 高层 JSON 冻结入口
  simulator.py              # CARLA 同步 session、Actor 清理、传感器帧缓冲
  telemetry.py              # 延迟 trace 与 JSONL 写入
  watchdog.py               # 运行时健康检测与 fail-closed
  examples/                 # 可直接传给 --command-json 的 Qwen 示例
```

正式车辆闭环入口仍是：

```bash
conda run -n carla312 python -m integration.carla_runner
```

## Qwen 高层命令协议

Qwen 只能输出高层动作 JSON，不能输出底层控制量。

```json
{
  "schema_version": "1.0",
  "command_id": "qwen-demo-set-speed-20",
  "action": "SET_SPEED",
  "target_speed_mps": 5.5555555556,
  "confidence": 0.95,
  "reason": "clear lane, cruise at 20 km/h",
  "visual_valid": true,
  "timestamp_ns": 0,
  "valid_duration_s": 30.0
}
```

可直接执行的动作：

|action|A 侧处理|
|---|---|
|`SET_SPEED`|转换为目标速度命令，C 控速，速度稳定后 `SUCCEEDED`|
|`SLOW_DOWN`|转换为较低目标速度；缺少 `target_speed_mps` 时使用保守默认值|
|`STOP`|C 舒适停车，停车后保持制动|
|`EMERGENCY_STOP` / `EMERGENCY_BRAKE`|D 拥有立即全制动权|
|`KEEP_LANE`|保持当前 route 与目标速度，连续健康帧后给终态|
|`START`|兼容旧 Day22 输出，归一化为 `KEEP_LANE`|

复杂动作不会直接执行：`TURN*`、`CHANGE_LANE*`、`AVOID*`、`PULL_OVER`、`FOLLOW_ROUTE`、`SPEED_UP` 会进入 confirmation-gated `MULTIMODAL_DECISION`，车辆侧 fail-closed 减速/停车，直到未来决策模块给出可验证的具体命令。

示例文件：

```text
car_control_A/examples/qwen_set_speed_20.json
car_control_A/examples/qwen_slow_down.json
car_control_A/examples/qwen_keep_lane.json
car_control_A/examples/qwen_change_lane_rejected.json
```

## 运行

启动 CARLA 服务端：

```bash
cd /home/abc/projects/simulator/carla0916
./CarlaUE4.sh -RenderOffScreen -nosound -quality-level=Low -carla-port=2000
```

固定场景契约测试：

```bash
conda run -n carla312 python -m integration.carla_runner \
  --host 127.0.0.1 \
  --port 2000 \
  --scenario-file scenarios/smoke/S01_set_speed_20.json \
  --scenario-facts-mode scenario \
  --perception-mode world \
  --realtime
```

Qwen JSON live 命令测试：

```bash
conda run -n carla312 python -m integration.carla_runner \
  --host 127.0.0.1 \
  --port 2000 \
  --command-json car_control_A/examples/qwen_set_speed_20.json \
  --perception-mode world \
  --scenario cruise \
  --frames 160 \
  --realtime
```

退出时用 `Ctrl-C` 停 CARLA 服务端；runner 内部会清理本次创建的 ego、传感器和同步设置。

## 验收结果

已完成的关键验证：

```bash
conda run -n carla312 python -m pytest \
  car_control_A/tests \
  integration/tests/test_voice_adapter.py \
  integration/tests/test_runtime_loop.py \
  integration/tests/test_carla_runner_helpers.py \
  -q
```

结果：`147 passed, 1 skipped`。

完整固定场景已在本机通过：

```text
scenario_id: S01_set_speed_20
status: SUCCEEDED
score: 25.0
frames: 600
command_count: 1
command_terminal_statuses: {"scenario_cmd_000": "SUCCEEDED"}
completion: true
completion_basis: explicit_expected_contracts
```

证据日志示例：

```text
artifacts/logs/S01_set_speed_20_20260723_193644_891622.jsonl
```

## 故障降级

- 命令 JSON 非对象、未知动作、低层控制字段、无效速度单位或无效 schema 都不会获得控制权。
- 命令过期、超时、被抢占、确认拒绝或 runtime 外层失败时，FSM 会写终态并清除活跃命令。
- 传感器超时、watchdog 失联或集成异常会让 `ControlRuntime` 请求 `ControlOutput(0, 1, 0)`。
- D 永远在 apply 前最后仲裁；A/B/C 输出不能绕过 D。
- `world` / `scenario` 模式只用于契约验证；真实传感器验收必须标注 `--perception-mode sensors` 和 `--scenario-facts-mode perception`。

## 交付总结

A 的内容现在已经收口为一个可复现运行时边界：上游可以给 voice envelope 或 Qwen high-level JSON；A 统一转换为 `DrivingCommand`，交给 FSM 管理生命周期；每帧由 runner 唯一 tick，`ControlRuntime` 编排 B/C/D，并保证每条命令和每个场景都有可查证结果。后续如果继续扩展转弯、变道或绕障，应新增可验证的 route/actor/安全契约，而不是让 Qwen 直接输出底层控制。

