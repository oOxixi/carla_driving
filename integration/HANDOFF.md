# 车辆侧全流程交接说明

## 1. 范围与数据流

车辆侧不修改 `voice_group/`。入口接收语音组产生的命令对象，随后按固定顺序执行：

```text
语音命令对象
  -> VoiceCommandAdapter（校验、单位转换、异常 NO_OP）
  -> ControlRuntime / BehaviorFSM（确认态、命令终态、持续安全状态）
  -> RouteReference + B 横向控制
  -> C 纵向规划与控制
  -> D 最终安全仲裁
  -> CARLA VehicleControl（每帧只下发一次）

CARLA RGB + LiDAR + 事件传感器
  -> CarlaPerceptionBridge（严格同帧）
  -> PerceptionFrame -> C / D

全链路事件 -> ScenarioEvidenceRecorder -> JSONL + summary.json
```

车辆侧当前可独立证明定速、普通停车、紧急停车、跟车、红灯停止和异常输入安全降级。
复杂转弯、变道和绕障的语音意图会进入确认/安全停车；没有具体多模态决策结果时不会擅自生成动作。

## 2. 核心模块与函数

| 文件 | 核心入口 | 功能 |
|---|---|---|
| `voice_adapter.py` | `VoiceCommandAdapter.adapt(envelope, now_s)` | 兼容诊断字符串和 `{code,message}`；单位转换；非法协议返回未授权 `NO_OP + REJECTED` |
| `runtime_loop.py` | `submit_voice()`、`confirm_voice()`、`step()`、`reset_safety_latch()` | 持有命令/FSM，组合 B/C/D，产生唯一终态；故障锁存全制动 |
| `carla_perception.py` | `attach_default_sensors()`、`CarlaPerceptionBridge.acquire()` | 挂载 RGB、LiDAR、碰撞、压线传感器；严格获取指定帧；LiDAR 前向走廊测距 |
| `route_planner.py` | `build_route_reference()` | 沿 CARLA waypoint 生成局部路线，首次岔路可选左/右/直行并计算曲率 |
| `scenario_evidence.py` | `ScenarioEvidenceRecorder` | 记录 run/command/frame/feedback/terminal，生成分数和延迟摘要 |
| `official_scenario_runner.py` | `verify_checkout()`、`build_command()`、`run()` | 校验并启动固定提交的官方 ScenarioRunner 0.9.16 |
| `carla_runner.py` | `run()` | 唯一同步 tick、Actor 清理、watchdog、场景验收和自动日志 |

CARLA 使用左手坐标系：Ego 局部 `+Y` 与正 `steer` 都指向右侧。横向控制不得再次反转符号。
验收入口使用 3.5 m 最小前视、0.60 最大归一化舵量和每帧 0.04 最大舵量变化，防止路线异常时瞬间满舵。

## 3. 语音输入协议

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 当前只接受 `1.0` |
| `command_id` | string | 非空唯一 ID |
| `source_text` | string | ASR 文本，只用于审计 |
| `intent` | string | `SET_SPEED/STOP/EMERGENCY_STOP/.../UNKNOWN` |
| `parameters` | object | `SET_SPEED` 需要 `speed`、`unit`；兼容 km/h、m/s 及对应中文单位 |
| `confidence` 或 `intent_confidence` | number | `[0,1]`；真实的 `0.0` 不会被替换成 1 |
| `status` | string | 只有 `valid` 且无 errors 才可授权 |
| `ambiguity_type` | string | 非 `NONE` 进入确认态 |
| `confirm_required` | bool | 显式确认门 |
| `errors`、`warnings` | list | 每项可为非空字符串，或 `{code: string, message: string}` |
| `valid_duration_s` | number | 正数，换算为 CARLA 仿真时间截止点 |
| `t_audio_start_ns/t_asr_end_ns/t_intent_end_ns` | int/null | 同一单调时钟的延迟时间戳 |

非法顶层 JSON、缺字段、未知版本、非法单位、非有限数、错误状态或错误诊断都转换成：

- `DrivingCommand.action = NO_OP`
- `control_authorized = false`
- `ExecutionFeedback.status = REJECTED`
- 不替换已有合法命令，也不把异常对象交给 D 当作紧急语音动作

## 4. 运行时、确认和终态

`ControlRuntime.submit_voice()` 只接纳授权命令。新合法命令会让旧命令以 `FAILED` 终结。
低于 0.80 的置信度、歧义命令或显式确认请求进入 `CONFIRMING`，C 执行舒适减速直到停车。

外部确认 UI 可调用：

```python
runtime.confirm_voice(command_id, approved=True, now_s=carla_sim_time_s)
```

- 拒绝：命令 `REJECTED`，持续停车保持。
- 批准简单定速/停车：清除确认门后执行。
- 批准复杂多模态动作但没有具体决策：命令 `FAILED`，持续停车；确认文本不等于运动决策。

终态只有 `SUCCEEDED/FAILED/REJECTED/EXPIRED/TIMED_OUT`。定速需连续三帧进入
`±0.25 m/s`；停车在速度不大于静止阈值时成功，之后持续保持制动。
若场景帧预算结束时命令仍未完成，该命令以 `FAILED` 终结，场景不会仅因跑满帧数而虚报成功。

watchdog 或控制集成异常会锁存安全状态并全制动。故障排除后只能显式调用
`reset_safety_latch()`，正常帧不会自动解锁。

## 5. 感知接口字段

| `PerceptionFrame` 字段 | 单位/类型 | 当前来源 |
|---|---|---|
| `frame`, `sim_time_s` | int, s | CARLA snapshot |
| `lead_distance_m` | m/null | LiDAR 前向走廊点云的保守距离 |
| `lead_speed_mps` | m/s/null | 与 LiDAR 距离匹配的 CARLA actor 速度；无法关联时保守假设静止 |
| `traffic_light` | enum string | Ego 当前 CARLA 信号灯状态 |
| `distance_to_stop_line_m` | m/null | stop waypoint；不可用时为明确标注的 trigger-volume 近似 |
| `speed_limit_mps` | m/s/null | CARLA 地图限速 |
| `lane_offset_m` | m/null | CARLA waypoint 横向偏移 |
| `route_deviation_m` | m/null | Ego 到当前路线最近距离 |
| `collision/lane_invasion` | bool | CARLA 事件传感器 |
| `red_light_violation` | bool | 红灯越过停止线且仍在运动的车辆侧判定 |

日志的 `perception_sources` 会标出字段来源。当前 RGB 数据已真实挂载并严格对齐，
但尚未接入图像目标检测；交通灯和前车速度关联仍使用 CARLA 真值。这一边界必须在答辩中如实说明。

## 6. 运行方式

从仓库根目录执行。默认 `--perception-mode sensors` 是正式传感器模式：

```powershell
python -m integration.carla_runner --host 127.0.0.1 --port 2000 `
  --timeout-s 60 --warmup-frames 40 --frames 600 --realtime `
  --perception-mode sensors --command-json artifacts/command.json
```

RTX 50 系列笔记本运行 UE4.26 版 CARLA 时，如 `-dx11` 在创建相机传感器后产生
`EXCEPTION_ACCESS_VIOLATION`，应改用 `CarlaUE4.exe ... -dx12`。这是 CARLA 服务端原生
渲染崩溃，Python 侧无法捕获；可在 `%LOCALAPPDATA%\CarlaUE4\Saved\Crashes` 验证。

调试模式不能作为真实感知成绩：

- `--perception-mode world`：读取 CARLA world actor 真值。
- `--perception-mode virtual`：确定性注入前车/停止线，仅用于控制算法验收。

每次运行自动产生 `artifacts/logs/<scenario>_<timestamp>.jsonl` 和同名
`.summary.json`。除非只调试控制台，否则不要使用 `--no-log`。

## 7. 日志与评分

JSONL 顺序为 `run_start -> command -> frame/feedback -> run_complete|run_failed`。frame 记录包括原始控制、
D 最终控制、纵向输出、FSM 状态、场景事实、感知来源和分段延迟。summary 包括停止误差、最终速度、
最小间距/TTC、碰撞/闯红灯/路线偏离、安全覆盖次数、延迟统计、命令终态与 D 组评分。

当前评分是仓库 D 组规则的可重复实现，不应宣称等同主办方未公开的最终计分器。

## 8. 官方 ScenarioRunner

首次准备固定依赖：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fetch_scenario_runner.ps1
```

运行官方内置场景：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_scenario_runner.ps1 `
  -Scenario FollowLeadingVehicle_1
```

固定版本记录在 `external/scenario_runner.lock`。ScenarioRunner 运行时拥有场景时钟；不要同时启动
`integration.carla_runner` 控制同一 world。若要让官方场景驱动本项目 Ego，仍需提供符合其 `--agent`
协议的 agent；`ScenarioRunnerInvocation` 已预留 `agent_path/agent_config`，但当前不虚构此接入已完成。

## 9. 验证与改动边界

```powershell
conda run --no-capture-output -n carla python -m pytest `
  car_control_A/tests car_control_B/tests car_control_C/tests car_control_D/tests integration/tests -q
git diff --name-only -- voice_group
```

第二条命令输出必须为空。`CARLA_0.9.16/`、地图、日志和 `external/scenario_runner/` 是本地依赖或产物，
不提交 Git；只提交 lock、脚本、车辆侧源码和测试。
