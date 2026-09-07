# 第一轮官方 S1/S2/S3 泛化测试结果

## 1. 记录范围与职责

- 本文记录第一轮官方 `S1/S2/S3` 测试结果。
- 记录依据：已下载并分析的 6 个官方日志文件（每个场景包含 `.jsonl` 和 `.summary.json`）。
- 按《车辆控制组_泛化优化分工.md》的成员4职责，本文只负责运行结果留档、成功/失败标记、失败样本证据整理和错误初步分类；不对代码根因或修复方案作越权判断。
- `map`、`seed`、`owner` 及运行命令在当前已提供证据中未确认的，均标记为“待从场景配置/团队负责人确认”。
- 此处不混入此前 Windows AMD 780M 环境中的 `D3D Lost` 问题；本表仅记录 AutoDL 上的官方 `S1/S2/S3` 结果。

## 2. 总览

| 场景 | 结果 | 分数 | 运行帧数 | 完成情况 | 成员4初步分类 |
|---|---|---:|---:|---|---|
| S1 基础语音控制 5 km | FAILED | 20 | 12000 | `route_finished=false` | 控制流程 / Watchdog / Qwen流程 |
| S2 复杂避障 8 km | FAILED | 20 | 0 | `completion_basis=runtime_failure` | 评分契约 / 运行前失败 |
| S3 极端紧急 6 km | FAILED | 20 | 18000 | `route_finished=false` | 控制流程 / 安全接管 / 未完成后续阶段 |

## 3. S1 记录

### 基本字段

| 字段 | 记录 |
|---|---|
| scenario | `OFFICIAL_S1_BASIC_VOICE_CONTROL_5KM` |
| map | 待从场景配置/团队负责人确认 |
| seed | 待从场景配置/团队负责人确认 |
| result | `FAILED`，`score=20` |
| owner | 待从场景配置/团队负责人确认 |
| 运行命令 | 待从运行记录/团队负责人确认 |
| 证据文件 | `OFFICIAL_S1_BASIC_VOICE_CONTROL_5KM_20260907_194947_312848.jsonl`；`OFFICIAL_S1_BASIC_VOICE_CONTROL_5KM_20260907_194947_312848.summary.json` |

### 已确认事实

- `frames=12000`。
- `route_finished=false`，`route_remaining=5063.16 m`。
- `collision_count=0`。
- 安全接管原因为 `WATCHDOG_ALERT`，`safety_override_frames=12000`。
- `qwen_request_count=1/5`；`qwen_missing_request_count=4`。
- 路线未完成，指令未按预期全部完成；摘要中相关验收项失败。

### 成员4错误记录

- 主要失败原因：控制流程/Watchdog 触发后车辆未完成路线；同时 Qwen 计划调用不足，后续阶段未完成。
- 错误分类：主要为“控制问题 / Qwen流程问题”，次要为“Watchdog”。
- 备注：日志显示无碰撞、无路线偏离，不能仅凭本轮结果断定为单一 Qwen 模型故障；代码根因留给对应负责人分析。

## 4. S2 记录

### 基本字段

| 字段 | 记录 |
|---|---|
| scenario | `OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM` |
| map | 待从场景配置/团队负责人确认 |
| seed | 待从场景配置/团队负责人确认 |
| result | `FAILED`，score `20` |
| owner | 待从场景配置/团队负责人确认 |
| 运行命令 | 待从运行记录/团队负责人确认 |
| 证据文件 | `OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM_20260907_200115_891324.jsonl`；`OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM_20260907_200115_891324.summary.json` |

### 已确认事实

- `frames=0`。
- `completion=false`，`completion_basis=runtime_failure`。
- 错误阶段/代码：`SCORING` / `SCORING_CONTRACT`。
- 错误信息：`scenario target lane is unavailable for occupancy acceptance`。
- 因为运行帧数为 0，本次没有进入正常驾驶评价阶段；不能据此评价碰撞、路线偏离、Qwen行为或控制质量。

### 成员4错误记录

- 主要失败原因：评分阶段运行时失败，场景目标车道不可用于 occupancy acceptance。
- 错误分类：评分契约 / 场景配置或验收前置条件问题。
- 备注：该条应作为“运行前/评分阶段直接失败”记录，不标记为驾驶过程中的碰撞、避障或控制失败。

## 5. S3 记录

### 基本字段

| 字段 | 记录 |
|---|---|
| scenario | `OFFICIAL_S3_EXTREME_EMERGENCY_6KM` |
| map | 待从场景配置/团队负责人确认 |
| seed | 待从场景配置/团队负责人确认 |
| result | `FAILED`，score `20` |
| owner | 待从场景配置/团队负责人确认 |
| 运行命令 | 待从运行记录/团队负责人确认 |
| 证据文件 | `OFFICIAL_S3_EXTREME_EMERGENCY_6KM_20260907_200705_736275.jsonl`；`OFFICIAL_S3_EXTREME_EMERGENCY_6KM_20260907_200705_736275.summary.json` |

### 已确认事实

- `frames=18000`。
- `collision_count=0`，`pedestrian_collision=0`。
- `route_finished=false`，`route_remaining=5971.98 m`。
- `safety_override_episodes=497`，`safety_override_frames=17245`。
- 安全接管原因为 `EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE`。
- 已完成 `P1/P2`，后续 phase 未完成；摘要验收项 `all_phases_must_complete` 失败。

### 成员4错误记录

- 主要失败原因：前方障碍物过近触发紧急安全接管，车辆未完成路线，P1/P2 后的后续阶段未完成。
- 错误分类：安全接管 / 控制流程 / 阶段完成性问题。
- 备注：本轮确认无车辆碰撞和行人碰撞；不能把“发生安全接管”直接记录为碰撞错误。

## 6. 统一留档备注

- 三个场景均为第一轮官方结果，当前结果均为 `FAILED`，分数均为 `20`。
- 本记录只保留日志明确支持的事实；未确认的配置字段不作猜测。
- 下一步由团队负责人补齐 `map`、`seed`、`owner` 和各场景的完整运行命令，并由相应模块负责人继续定位根因。
- `D3D Lost` 属于此前 Windows AMD 780M 环境问题，不属于本轮 AutoDL 官方 `S1/S2/S3` 结果，故不列入本表失败样本。
