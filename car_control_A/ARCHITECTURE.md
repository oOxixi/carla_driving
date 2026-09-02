# A：CARLA 运行时、语音命令闭环与行为状态

## 1. 职责与边界

成员 A 是运行时的唯一编排方：维护同步 CARLA 世界和 Actor 生命周期、将语音组的识别文本转为受限命令、维护命令终态和高层行为状态、记录延迟，并向 C、B、D 提供稳定的协议边界。

不属于 A 的工作：RGB/LiDAR 感知与场景理解、复杂语句的多模态决策模型、横向控制算法（B）、最终安全仲裁/官方评分（D）、CARLA 服务或地图的安装和启动。`CARLA_ROOT` 与 CARLA 服务均由使用者手工启动和管理；本目录不会启动、停止或加载地图。

## 2. 目录与模块图

```text
语音 ASR 文本
  -> command_adapter.CommandAdapter
     ├─ FAST_PATH -> contracts.DrivingCommand -> behavior_fsm.BehaviorFSM
     └─ NEEDS_DECISION -> DecisionProvider.submit(异步多模态模块)

CARLA World -> simulator.CarlaSession/SynchronousWorld -> tick(frame)
  -> SensorFrameBuffer(RGB/LiDAR 同帧数据) -> 感知/决策（外部）
  -> routing.RouteReference -> B: LateralController.steer()
  -> C: LongitudinalController.step(LongitudinalRequest, dt_s)
  -> D: 最终安全仲裁（外部） -> CARLA VehicleControl

telemetry.LatencyTrace -> JSONL
watchdog.RuntimeWatchdog -> 故障时 ControlOutput(0, 1, 0)
```

|文件|实际职责|
|---|---|
|`contracts.py`|版本化、严格 JSON 的 A/C 共享数据契约|
|`simulator.py`|同步 World、Actor 反序清理、RGB/LiDAR 帧对齐、Ego/Sensor 生成|
|`command_adapter.py`|基础中文命令快路径；复杂命令转异步决策请求|
|`behavior_fsm.py`|命令唯一终态、确认、过期、超时、抢占和高层状态|
|`routing.py`|路线参考和 B 的最小横向控制协议，不含横向算法|
|`telemetry.py`|单调时间戳、分段/端到端延迟和 JSONL 写入|
|`watchdog.py`|运行时健康检测与局部全制动故障回退|
|`tests/`|无 CARLA 单测、A/C 假模块集成、门控 CARLA 烟测|

## 3. 环境、运行与验证

项目使用 Conda 环境 `carla`（Python 3.12）和 CARLA 0.9.16。常规回归不需要启动 CARLA：

```powershell
conda run --no-capture-output -n carla python -m pytest car_control_A/tests car_control_C/tests -q
```

仅用户确认服务器已经启动后才运行烟测。用户应在独立 PowerShell 中自行设置并启动：

```powershell
$env:CARLA_ROOT = 'F:\carla_driving_rstar\CARLA_0.9.16'
cd $env:CARLA_ROOT
.\CarlaUE4.exe -quality-level=Low -carla-port=2000
```

服务稳定后，在仓库根目录执行：

```powershell
$env:CARLA_SMOKE = '1'
conda run --no-capture-output -n carla python -m pytest car_control_A/tests/test_simulator_smoke.py -q
```

烟测只连接 `127.0.0.1:2000` 和 Traffic Manager 端口 `8000`，在当前地图临时生成一个 Ego，退出时销毁该 Actor 并恢复 World/Traffic Manager 设置；它不启动服务也不调用 `load_world()`。

## 4. 核心执行流程与实现要点

1. 上游以同一 `now_s`（仿真秒）调用 `CommandAdapter.adapt(text, command_id, now_s, confidence, expires_at_s)`。快路径仅支持“停车/停止/停下/请停车/请停止”、紧急刹车词，以及“设置到/速度… + km/h”的限速表达；未知组合动作绝不猜测，返回 `DecisionRequest` 交给实现 `DecisionProvider.submit()` 的异步模块。
2. 将 `DrivingCommand` 交给 `BehaviorFSM.submit()`。低置信度（`<0.80`）、歧义或显式确认命令进入 `CONFIRMING`；通过 `confirm()` 后才执行。新命令会以 `FAILED: superseded by a newer command` 结束旧活跃命令。
3. 在 `with CarlaSession(world, ...) as session:` 内生成 Ego 并 `attach_sensor()`；**只允许**通过 `session.tick()` 触发世界时钟。传感器 callback 以 CARLA `measurement.frame` 放入 `SensorFrameBuffer`，再以 `pop_aligned(('rgb', 'lidar'), frame, timeout_s=...)` 获取同帧数据；超时必须按安全路径处理，不能混用邻帧。
4. 由外部感知生成 `RuntimeVehicleState`、`TrafficConstraint`、前车观测，构造 `LongitudinalRequest` 给 C。路线仅封装为 `RouteReference`，B 实现 `LateralController.steer(reference)` 并返回 `[-1,1]` 转向；D 应在 C/B 输出合成为 `ControlOutput` 后进行最终仲裁。
5. 在接收、FSM 接纳、纵向规划、控制下发等阶段调用 `LatencyTrace.mark()`，终态/关键指标以 `append_jsonl()` 追加。每帧调用 `BehaviorFSM.tick()` 处理过期/超时；完成时用 `complete()` 或失败时用 `fail()`，任一 `command_id` 只保留首次终态。
6. 对关键模块定期 `RuntimeWatchdog.heartbeat(module, now_s=...)`；`check()` 返回非空时直接使用 `ControlOutput(0.0, 1.0, 0.0)`。这只是运行时故障回退，不能替代 D 的安全仲裁。

`CarlaSession.__exit__()` 先由 `ActorRegistry` 逆序 `stop()`/`destroy()`，随后恢复同步设置；清理为 best-effort，单个 Actor 的析构失败不能阻止其他 Actor 清理。`SynchronousWorld` 进入时复制并改写 World settings，退出时恢复；Traffic Manager 存在时，调用者必须显式给出此前同步状态 `tm_previous_synchronous_mode`。

## 5. 公开接口与字段表

所有 `to_dict()`/`from_dict()` 契约均携带 `schema_version: "1.0"`，拒绝缺失字段、未知字段、错误版本、布尔伪数值、字符串数值和 `NaN/Infinity`。纵向物理量全为 SI；`sim_time_s` 是 CARLA 仿真秒，`LatencyTrace` 使用单调纳秒，不可混用。

|契约/接口|字段或调用|说明|
|---|---|---|
|`RuntimeVehicleState`|`frame`, `sim_time_s`, `speed_mps`, `x_m/y_m/z_m`, `yaw_deg`, `lane_id`|帧对齐车况；速度 m/s、坐标 m、航向 deg|
|`DrivingCommand`|`command_id`, `received_at_s`, `expires_at_s`, `confidence`, `action`, `target_speed_mps?`, `is_ambiguous`, `confirmation_requested`|命令在 `sim_time_s >= expires_at_s` 时过期；置信度范围 `[0,1]`|
|`TrafficConstraint`|`signal_state`, `distance_to_stop_line_m?`, `speed_limit_mps?`|`SignalState` 为 `RED/YELLOW/GREEN/UNKNOWN`；UNKNOWN 是不确定而非绿灯|
|`LongitudinalRequest`|`vehicle`, `requested_speed_mps`, `path_curvature_per_m`, `traffic?`, `lead_distance_m?`, `closing_speed_mps?`|传给 C；前车距离和闭合速度必须成对出现，`closing=ego-lead`，正值才表示接近|
|`ControlOutput`|`throttle`, `brake`, `steer=0`|全部归一化；油门/刹车互斥，转向范围 `[-1,1]`|
|`RiskMetrics`|`ttc_s?`, `desired_gap_m`, `emergency_brake_requested`|C 提供给未来 D 的本地风险信息|
|`LongitudinalOutput`|`control`, `target_accel_mps2`, `target_speed_mps`, `state`, `reason`, `risk`|C 的纵向输出；加速度 m/s²|
|`ExecutionFeedback`|`command_id`, `status`, `completed_at_s`, `detail`|每条命令的唯一终态记录|
|`ExecutionStatus`|`SUCCEEDED/FAILED/REJECTED/EXPIRED/TIMED_OUT`|仅有这五种终态；重复完成返回首个结果|
|`CommandAdapter.adapt`|见第 4 节|返回 `AdaptedCommand(FAST_PATH, command=...)` 或 `NEEDS_DECISION, decision_request=...`，两者恰有一个|
|`BehaviorFSM`|`submit/confirm/complete/fail/tick`|状态包括 `IDLE`、`LANE_FOLLOW`、`APPROACH_STOP`、`STOPPED`、`FOLLOWING`、`YIELDING`、`CONFIRMING`、`EMERGENCY_BRAKE`、`RECOVERING`|
|`SynchronousWorld` / `CarlaSession`|上下文管理器、`tick()`、`spawn_ego()`、`attach_sensor()`|同步生命周期唯一入口；勿直接在会话外 `world.tick()`|
|`RouteReference` / `LateralController`|`points_xy_m`, `curvature_per_m`, `target_speed_mps`；`steer(reference)`|A→B 接口；B 只能回传转向，不接管油门/刹车|

## 6. 配置、重置与生命周期

- 命令默认 TTL 为 `5.0 s`，FSM 默认执行超时为 `15.0 s`；按场景配置，但不可用过期命令重新激活控制。
- `SensorFrameBuffer(max_frames=32)` 仅缓存最近仿真帧；已经消费或落后于消费帧的 callback 会丢弃。发生 `TimeoutError` 时由上层记录并走 watchdog/D 的安全策略。
- `RuntimeWatchdog` 默认 `timeout_s=1.0`；指定 `required_modules` 后，越过 `startup_grace_s + timeout_s` 仍无心跳即制动。
- 每个 CARLA 重新生成/重置 episode 都应新建 `CarlaSession`、FSM、trace 和 watchdog；结束必须退出上下文，不能只销毁 Ego 而保留传感器或同步设置。

## 7. 测试覆盖、边界与交接

`car_control_A/tests` 已覆盖：严格版本化 JSON、命令元数据和中文快路径、确认/拒绝/过期/超时/抢占/终态唯一性、路线协议、传感器乱序/容量/超时/线程等待、World/TM 恢复、Actor 清理、watchdog、JSONL 延迟；`test_ac_integration.py` 用固定 B 转向桩与透传 D 安全桩验证“ASR→FSM→C→B/D→控制”链路。

已知边界：A 未实现复杂语音的 VLM、实际 RGB/LiDAR 检测、路线规划器、横向控制、D 的最终安全裁决或官方 ScenarioRunner 评分。`RouteReference` 当前仅是数据边界，路线点和曲率必须由接手方接入规划/感知结果。

- **交给 B：** 实现 `LateralController.steer(RouteReference) -> float`，自行验证输出在 `[-1,1]`；不得修改 C 的纵向目标。
- **交给 C：** 使用 `LongitudinalRequest`/`LongitudinalOutput`；共享契约的字段、JSON 版本和 SI 单位不得私改。
- **交给 D：** 提供 `arbitrate(ControlOutput) -> ControlOutput` 之类的最终覆盖层；读取 `RiskMetrics` 与 A 的 watchdog 结果，D 是最终安全责任方。
- **交给感知/决策负责人：** 为每个 `session.tick()` 产生同帧车况、交通/前车约束；复杂命令必须消费 `DecisionRequest` 并返回受约束高层动作，不能绕开 FSM。

## 8. 常见故障定位

|现象|优先检查|
|---|---|
|烟测被跳过|确认 `$env:CARLA_SMOKE='1'`，且用户已在 `127.0.0.1:2000` 启动 CARLA|
|`ModuleNotFoundError: carla`|确认执行命令使用 `conda run --no-capture-output -n carla`，不是系统 Python|
|传感器等待超时|核对只用 `session.tick()`、sensor `listen()` 成功、传入的 `frame` 与 snapshot 相同、sensor ID 唯一|
|World 一直同步或 Actor 残留|确保 `with CarlaSession(...)` 正常退出；不要在会话外重复创建未跟踪 Actor|
|命令立即 `EXPIRED`|检查 `now_s` 和 `expires_at_s` 均为同一 CARLA 仿真时基，且截止线是包含式|
|命令停在 `CONFIRMING`|低置信度、`is_ambiguous` 或 `confirmation_requested` 为真；调用 `confirm(command_id, approved=...)`|
|出现 `RECOVERING`|检查命令是否被新命令抢占、`tick()` 是否报告超时、或未知 action 是否来自未适配的复杂决策|
|没有 JSONL 或时间倒退异常|每个阶段只 `mark()` 一次，使用单调递增的纳秒时间戳，并保证目标目录可写|
