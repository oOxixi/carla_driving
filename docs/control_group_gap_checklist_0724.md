# 控制组缺口清单与完整测试门槛

本文基于当前仓库状态、A 运行时收口结果、已有场景/单测和 CARLA 实跑记录整理。目标不是继续扩功能，而是判断控制组距离“7 月 24 日可稳定演示和验收”还缺什么，以及什么时候才有资格跑完整测试。

## 当前结论

控制组现在已经具备模块骨架、固定场景闭环、单场景 sensors 闭环、离线 Qwen high-level JSON live 闭环和一个 D 安全接管闭环；但还没有完成“全量完整验收闭环”。

已经能够证明：

- A/B/C/D 与 integration 纯 Python 回归通过：`267 passed, 1 skipped`。
- 34 个场景 JSON 静态校验通过：`checked=34, failed=0`。
- `S01_set_speed_20` 在 `world + scenario facts` 固定场景契约模式下实跑成功：
  - `status=SUCCEEDED`
  - `score=25.0`
  - `command_terminal_statuses={"scenario_cmd_000": "SUCCEEDED"}`
  - `completion=true`
- `S01_set_speed_20` 在 `sensors + perception facts` 真实传感器模式下完整 600 帧实跑成功：
  - `status=SUCCEEDED`
  - `score=25.0`
  - `command_terminal_statuses={"scenario_cmd_000": "SUCCEEDED"}`
  - `completion=true`
- A 已支持 Qwen high-level JSON 输入，且禁止模型输出底层 `throttle/brake/steer`。
- 离线 Qwen high-level JSON `qwen_set_speed_20.json` 已进入 CARLA live runner 并成功：
  - `command_terminal_statuses={"qwen-demo-set-speed-20": "SUCCEEDED"}`
  - `status=SUCCEEDED`
  - `score=25.0`
- D08 红灯/冲突命令安全接管场景已实跑成功：
  - `status=SUCCEEDED`
  - `score=25.0`
  - `safety_override_frames=410`
  - `override reason=RED_LIGHT_STOP_LINE_GUARD`
  - 注意：该场景中原始命令终态为 `FAILED` 是预期结果，因为 D 必须压过冲突命令；场景级验收成功。

还不能完整证明：

- 真实 RGB/LiDAR sensors 链路已完成单场景首轮闭环，但还没有多场景/多轮稳定性证据。
- Qwen 离线 high-level JSON 已跑通；真实模型调用到车辆动作的端到端稳定性还缺证据。
- 红灯/冲突命令 D 接管已首轮通过；前车/行人/低 TTC 安全场景还缺正式实跑证据。
- B/C/D 在真实 CARLA 场景中的指标表、证据包和失败归因已经封板。
- 30 分钟稳定性和批量回归已经跑完。

一句话：现在已经能证明关键链路分层跑通，但还不能宣称“全量真实多模态完整测试完成”。下一步不是大改功能，而是补多轮复现、前方风险场景、真实 Qwen 链和统一证据表。

## 最新实跑证据

截至 2026-07-23 20:55，已经产生并检查过以下证据：

|层级|场景/命令|模式|结果|关键指标|日志|
|---|---|---|---|---|---|
|L0|A/B/C/D/integration tests|纯 Python|PASS|`267 passed, 1 skipped`|-|
|L0|scenario JSON validation|静态校验|PASS|`checked=34, failed=0`|-|
|L1|`S01_set_speed_20`|`world + scenario facts`|PASS|score `25.0`, command `SUCCEEDED`, frames `600`|`artifacts/logs/S01_set_speed_20_20260723_205052_835135.jsonl`|
|L2|`S01_set_speed_20`|`sensors + perception facts`|PASS|score `25.0`, command `SUCCEEDED`, frames `600`, final speed `5.00 m/s`|`artifacts/logs/S01_set_speed_20_20260723_205337_664031.jsonl`|
|L3|`qwen_set_speed_20.json`|`command-json + world`|PASS|score `25.0`, command `SUCCEEDED`, frames `260`|`artifacts/logs/cruise_20260723_205255_622674.jsonl`|
|L4 partial|`D08_command_conflict_red_light_continue`|`world + scenario facts`|PASS|score `25.0`, D override `410` frames, stopped before red line|`artifacts/logs/D08_command_conflict_red_light_continue_20260723_205458_086458.jsonl`|

一次失败也有价值：

- `qwen_set_speed_20.json` 用 `--frames 160` 失败，原因是帧预算结束前还没连续 3 帧进入目标速度容差。不是命令未进入 FSM，而是完成判据时间不足。重跑 `--frames 260` 后成功。

## 完整测试的分层定义

为了避免大家把不同测试混在一起，先把“完整测试”拆成 5 层。

|层级|名称|目的|当前状态|
|---|---|---|---|
|L0|静态/纯 Python 回归|证明模块契约、FSM、B/C/D 纯逻辑没有坏|已可跑，已通过|
|L1|固定场景契约测试|证明场景 JSON、命令 FSM、终态、runner 控制链、D apply 前仲裁|已可跑，`S01` 已通过|
|L2|真实 sensors 闭环测试|证明 RGB/LiDAR/事件传感器帧对齐、感知来源、watchdog 和控制链可跑|单场景已通过，缺多场景/多轮|
|L3|Qwen high-level 闭环测试|证明 Qwen 输出经过 A 适配、C/B/D 执行，非法/慢/低置信度输出可降级|离线 JSON 已通过，缺真实模型链和负例 live 证据|
|L4|批量回归与稳定性测试|证明 3 个演示场景、多组 safety/regression 和长稳测试可重复|D08 首轮通过，缺批量和长稳|

“完整测试”应至少指 L0 + L1 + L2 + L3 + 选定 L4 子集全部通过。否则只能说通过了某一层。

## 什么时候才能跑完整测试

完整测试不是等所有代码写完才开始，而是满足下面 P0 条件后才能正式跑。否则跑出来的失败很可能是环境、模型、场景、日志口径混杂，无法判断责任。

### 最早可跑完整测试的 P0 条件

- [x] CARLA 服务端可连接，当前运行窗口命令为 `CarlaUE4.sh -quality-level=Low -nosound -windowed -ResX=1280 -ResY=720 -carla-rpc-port=2000`。
- [x] 当前运行环境确认使用 `carla312`。
- [x] 当前机器明确使用 `Town03_Opt` 作为 `Town03` 契约等价地图，避免非优化 Town03 崩溃。
- [ ] 3 个主演示场景确定，不再临时换：
  - [x] 正常巡航/定速：建议 `scenarios/smoke/S01_set_speed_20.json`
  - [ ] 前车/行人/低 TTC：从 safety/regression 中选一个真实 sensors 可复现场景
  - [x] 红灯或冲突命令 D 接管：建议 `D08_command_conflict_red_light_continue`
- [ ] 每个主演示场景都有固定运行命令、固定 `spawn_index`、固定 perception/facts 模式。当前 S01 与 D08 已固定，前方风险场景未固定。
- [x] sensors 模式至少一个场景能跑到 summary，而不是只用 world/scenario truth。
- [ ] Qwen 输出路径确定：
  - [x] 离线 high-level JSON 文件
  - [ ] 或真实 Qwen adapter 输出
  - [x] 且不能输出底层控制字段
- [ ] 结果目录标准确定：每次运行保留 config、frame log、command log、feedback、summary、score。当前已有 JSONL 和 `.summary.json`，还缺统一总表和 config 快照。
- [x] D 的 override reason 可以从日志里追到最终控制。
- [ ] 失败时能分类：环境 / 感知 / Qwen / A FSM / B 横向 / C 纵向 / D 安全。

如果只求“能开始跑完整测试”，上述 P0 满足即可。

如果要“完整测试结果可用于演示/答辩”，还需要：

- [ ] 3 个主演示场景各连续通过至少 2 次。
- [x] 至少一次故意触发红灯冲突，D 明确接管。
- [ ] 至少一次传感器失效或 Qwen 非法输出，车辆 fail-closed。
- [ ] 输出总表：场景、命令、模式、结果、终态、D 接管、最终速度/距离/CTE、日志路径。

## 时间判断

以当前进度判断：

- L0 和 L1：现在就能跑。
- L2 单场景 sensors 测试：已跑出第一份有效日志；下一步是前方风险场景 sensors/fuse 或 sensors/perception 复现。
- L3 Qwen high-level 闭环：离线 JSON 已完成 live 通过；真实 Qwen 模型链仍需要确认模型调用耗时、输出格式和 fallback，预计 0.5 到 1 天。
- L4 三场景批量复现：S01 与 D08 已首轮通过；还需要至少半天到 1 天跑多轮、补前方风险、整理证据和修小问题。

因此，真正能称为“完整测试”的时间点仍不是现在，而是在“前方风险场景 + 真实 Qwen 或明确离线替代 + 多轮复现 + 统一证据表”完成后。2026-07-24 前应只做复现、证据整理和小修，不应再扩动作或大改接口。

## 模块缺口清单

### A：运行时与命令边界

当前状态：基本完成，但还要补正式证据。

- [x] 命令 FSM 有唯一终态。
- [x] `command_id` 进入日志和 summary。
- [x] Qwen high-level JSON 入口已补。
- [x] `SLOW_DOWN`、`KEEP_LANE` 已有车辆侧可执行语义。
- [x] 非法 low-level 字段会被拒绝。
- [x] `Town03` 到 `Town03_Opt` 兼容已补。
- [x] 用 `--command-json car_control_A/examples/qwen_set_speed_20.json` 跑一次真实 CARLA live 命令。
- [ ] 形成一张“5 条命令到终态”对照表：
  - [x] `SET_SPEED`
  - `SLOW_DOWN`
  - `STOP`
  - `KEEP_LANE`
  - `CHANGE_LANE_LEFT` 或非法字段，确认 fail-closed
- [ ] 固化演示启动和清理命令，避免现场手动摸索。

验收标准：

- 每个命令都有 `ExecutionFeedback`。
- active command 不会跨场景残留。
- runner 失败时 active command 写 `FAILED`。
- D 仍然是唯一 apply 前最终仲裁。

### B：横向控制

当前状态：代码和单测存在，S01 的真实 CARLA 横向证据已首轮通过，但多路线/多轮证据仍不足。

- [ ] 固定 3 个演示路线的 route 生成方式。
- [x] 记录 S01 最大横向误差 `max_cross_track_error_m`：sensors 模式约 `0.0025 m`，world/scenario 模式约 `0.0027 m`。
- [x] 在 S01/D08 上确认 Town03_Opt 直道 `steer_sign`、yaw 单位、路径点顺序没有明显反向问题。
- [x] 验证 S01/D08 直道不蛇形。
- [ ] 明确哪些动作暂不演示：变道、绕障、复杂路口。
- [ ] 对每个主演示场景跑至少 2 次并记录：
  - 场景名
  - spawn_index
  - max CTE
  - 是否压线
  - 是否路线偏离
  - 日志路径

验收标准：

- 主演示场景无严重路线偏差。
- `max_cross_track_error_m` 满足场景 expected。
- B 只输出 steer，不改 throttle/brake。

### C：纵向控制

当前状态：定速、停车、跟车、TTC 能力较完整；S01 定速和 D08 停车已有首轮实跑证据，但还缺正式曲线化证据和前方风险曲线。

- [ ] 整理 `SET_SPEED 20 km/h` 的速度曲线。当前已有原始日志，可从 `S01_set_speed_20_20260723_205337_664031.jsonl` 提取。
- [ ] 整理 `STOP` 的减速和 brake hold 曲线。
- [ ] 整理前车/行人/低 TTC 的距离、相对速度、TTC 曲线。
- [ ] 明确 slow speed、emergency TTC、caution TTC、hold brake 参数。
- [x] 在 S01/D08 实跑 summary 中未出现碰撞、路线偏离；D08 最终控制为 `throttle=0, brake=1`，体现安全覆盖。仍需全量自动检查 throttle/brake overlap。
- [ ] 验证传感器无效、TTC 缺失、距离突变时不会继续加速。
- [ ] 给 D 的 `RiskMetrics` 字段在日志里可追溯。

验收标准：

- 速度达到目标容差。
- 停车无明显过冲。
- 低 TTC 或近距离时减速/停车。
- 异常输入时保守制动。

### D：安全仲裁

当前状态：规则存在，D08 红灯/冲突命令已实跑通过；仍需要低 TTC、非法控制、路线偏差等 safety regression 的正式证据包和批量结果。

- [x] 确认 D 在 apply 前执行：D08 日志包含 raw control 与 final control，最终控制覆盖为 `throttle=0, brake=1`。
- [x] 红灯场景：即使命令继续前进，D 最终停车。
- [ ] 低 TTC 场景：D 能覆盖 C/B 原始控制。
- [ ] 非法控制场景：NaN、油门刹车冲突被覆盖。
- [ ] 路线偏差场景：严重偏离触发降速或停车。
- [ ] 每个 override 都写明：
  - `override_reason`
  - raw control
  - final control
  - vehicle state
  - risk metrics
- [ ] 建立一张 safety regression 结果表。

验收标准：

- 严重安全事件为 0。
- D 接管原因和最终控制一致。
- 失败场景能解释是规则预期、环境问题还是上游输入问题。

### 感知与多模态

当前状态：风险最大，尤其容易把 truth 当 perception。S01 已证明 sensors/perception 单场景能跑到 summary，但前方风险和真实 RGB 模型仍未封板。

- [x] 至少一个 `--perception-mode sensors --scenario-facts-mode perception` 成功。
- [ ] RGB 检测模型路径和加载命令固定。当前 S01 传感器日志里 `visual_object_class=RGB_DETECTOR_UNAVAILABLE`，说明尚未接入固定 RGB detector。
- [x] LiDAR safety state 样例写入日志。当前 S01 记录了 `c_safety_state`、`fusion_mode=NO_OBSTACLE`、`lidar_valid=true`。
- [ ] `perception_sources` 中明确字段来源：
  - CARLA sensor
  - ONNX detector
  - LiDAR projection
  - map truth
  - scenario truth
- [ ] 禁止在真实感知验收中使用 `scenario` 模式冒充。
- [ ] 传感器 warmup 参数固定：
  - `--sensor-warmup-frames`
  - `--sensor-timeout-s`
  - `--sensor-startup-grace-frames`
- [ ] 感知失败时进入 brake 或 D override，并有日志。

验收标准：

- sensors 模式不是只启动传感器，而是能跑到 summary。
- 每个关键字段都有 valid/source。
- 缺失时标记缺失，不编造。

### Qwen 决策

当前状态：A 已接协议，离线 high-level JSON 已 live 通过；真实模型闭环和负例 live 证据不足。

- [x] Qwen 输出只能包含高层动作，A 的 high-level adapter 已限制并有单测。
- [x] Qwen 输出非法底层字段时被拒绝，已有单测；仍缺 live 负例证据。
- [x] Qwen 输出未知动作时被拒绝或确认门控，已有单测；仍缺 live 负例证据。
- [ ] Qwen 慢路径不能阻塞控制主循环。
- [ ] 低置信度输出进入确认/安全停车。
- [ ] 结构化 safety state 与 Qwen 动作一致性有对照表。
- [ ] 至少 5 条命令对照：
  - [x] `SET_SPEED`
  - `SLOW_DOWN`
  - `STOP`
  - `KEEP_LANE`
  - unsupported manoeuvre / illegal low-level output

验收标准：

- Qwen 不直接控制车辆底层。
- Qwen 错误不会造成车辆继续危险行驶。
- A/FSM 仍能给每条命令终态。

### 结果与证据包

当前状态：有 JSONL/summary，且关键首轮日志已产生；仍缺正式统一目录、config 快照和总表。

- [ ] 建立固定结果目录命名：
  - commit
  - scenario_id
  - mode
  - timestamp
- [ ] 每次运行保留：
  - command JSON
  - config used
  - frame log
  - event log
  - summary/result
  - score report
  - failure snapshot
- [ ] 生成总表：
  - scenario_id
  - perception_mode
  - facts_mode
  - status
  - score
  - command terminal statuses
  - collision count
  - route deviation count
  - D override frames
  - log path
- [ ] 失败必须分类，不接受只写“失败”。

验收标准：

- 另一名成员只看 README 和结果目录即可复现。
- 答辩时能从 summary 回溯到关键帧。

### 环境与运行脚本

当前状态：已有说明，现场 CARLA + `carla312` 已验证可跑；仍需把启动、清理、恢复流程写成固定文档。

- [x] 固定 conda 环境名：`carla312`。
- [x] 固定 CARLA 启动命令：`CarlaUE4.sh -quality-level=Low -nosound -windowed -ResX=1280 -ResY=720 -carla-rpc-port=2000`。
- [x] 固定端口：`2000`。
- [x] 固定地图兼容策略：`Town03` -> `Town03_Opt`。
- [ ] 检查端口和进程命令写入 README。
- [ ] 清理 CARLA 残留进程流程写入 README。
- [ ] 如果 CARLA 崩溃，有备用启动和备用场景。

验收标准：

- 重启机器后能按文档恢复。
- 不需要现场临时改 Python 版本、环境变量或地图名。

## 推荐完整测试顺序

### Step 1：静态与纯 Python

```bash
conda run -n carla312 python -m pytest \
  car_control_A/tests \
  car_control_B/tests \
  car_control_C/tests \
  car_control_D/tests \
  integration/tests \
  -q

conda run -n carla312 python tools/validate_scenarios.py
```

通过标准：

- 所有测试通过，允许 CARLA smoke 因未启服务被 skip。
- 34 个场景 JSON 全 OK。

### Step 2：固定场景契约

```bash
conda run -n carla312 python -m integration.carla_runner \
  --host 127.0.0.1 \
  --port 2000 \
  --scenario-file scenarios/smoke/S01_set_speed_20.json \
  --scenario-facts-mode scenario \
  --perception-mode world \
  --realtime
```

通过标准：

- `status=SUCCEEDED`
- `command_count=1`
- `command_terminal_statuses` 非空且成功
- `completion=true`

### Step 3：Qwen high-level JSON live 命令

```bash
conda run -n carla312 python -m integration.carla_runner \
  --host 127.0.0.1 \
  --port 2000 \
  --command-json car_control_A/examples/qwen_set_speed_20.json \
  --perception-mode world \
  --scenario cruise \
  --frames 260 \
  --realtime
```

再分别跑：

```text
car_control_A/examples/qwen_slow_down.json
car_control_A/examples/qwen_keep_lane.json
car_control_A/examples/qwen_change_lane_rejected.json
```

通过标准：

- 可执行动作有终态。
- 不支持动作不直接执行危险动作。
- 非法字段被拒绝。

### Step 4：真实 sensors 单场景

建议先用简单场景，不要一开始就上 Qwen 和复杂 actor。

```bash
conda run -n carla312 python -m integration.carla_runner \
  --host 127.0.0.1 \
  --port 2000 \
  --scenario-file scenarios/smoke/S01_set_speed_20.json \
  --scenario-facts-mode perception \
  --perception-mode sensors \
  --sensor-warmup-frames 30 \
  --sensor-timeout-s 1.0 \
  --realtime
```

通过标准：

- 能跑到 `run_complete`。
- `perception_sources` 不依赖 scenario truth。
- 传感器超时次数可接受，且不会导致危险控制。

### Step 5：三场景演示回归

每个场景至少 2 次：

|演示场景|建议模式|必须证明|
|---|---|---|
|正常巡航/定速|world/scenario 先跑，再 sensors/perception|速度稳定、无接管、命令成功|
|前车/行人/低 TTC|sensors/perception 优先，必要时 fuse 标注|C/D 减速停车、无碰撞|
|红灯/冲突命令|world/scenario 可先证明 D 契约，再补 sensors|D 安全优先、override reason 正确|

### Step 6：长稳测试

```bash
conda run -n carla312 python -m integration.carla_runner \
  --host 127.0.0.1 \
  --port 2000 \
  --scenario-file scenarios/regression/REG_012_challenge_long_run_stability.json \
  --scenario-facts-mode fuse \
  --perception-mode world \
  --realtime
```

通过标准：

- 不崩溃。
- 无 active command 残留。
- D 没有无故持续接管。
- summary 可读。

## 最小封板标准

如果时间紧，至少做到以下内容才能算控制组可演示：

- [x] L0 通过。
- [x] `S01_set_speed_20` L1 通过。
- [x] `S01_set_speed_20` sensors/perception 单场景通过。
- [x] 一个 Qwen high-level JSON live 命令通过。
- [x] 一个 D 接管场景通过。
- [ ] 一个前方风险场景通过。
- [ ] 三个场景都有日志路径和 summary 摘要。
- [ ] README 写清楚启动、运行、清理、失败恢复。

## 不建议继续做的事

7 月 24 日前不建议继续投入：

- 新增复杂变道/绕障执行。
- 让 Qwen 输出 steer/throttle/brake。
- 训练或替换新模型。
- 大改 B/C/D 接口。
- 扩充大量新场景。
- 为了“看起来多模态”把 scenario truth 写成视觉结果。

这些事情会显著增加演示当天的不确定性。

## 最终风险判断

当前最大风险已经从“关键链路能不能跑”转为“证据能不能稳定复现并讲清楚”。`world/scenario`、`sensors/perception`、离线 Qwen high-level、D 接管都已有首轮成功证据；剩余重点是前方风险场景、真实 Qwen 链、多轮复现、统一结果总表和 README 固化。
