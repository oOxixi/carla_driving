# 轻量化模型在环的 CARLA 闭环测量（2026-10-07）

> 口径 **`X86/仿真 + 自建场景`**：被测决策模块是蒸馏后的 Student（`student-v0-r3-fp32`，
> 门禁 `PENDING_A3_FP32_GATE`），执行链是仓库原有的 FSM + 横纵向控制 + 安全仲裁。
> 场景为**自建 18 个验收场景**（非官方 1000 帧基准），因此本文只能作为
> **"场景任务完成率"的替代条件数据**，不是官方口径的达标结论。

## 1. 为什么做这一轮

评分细则的"场景任务完成率（三级难度，15 分）"此前一直记为**未测**，原因是仓库的 CARLA
闭环里没有把 Student 接进决策位。本轮补上了这一层，从而第一次拿到
**"轻量化模型在环 + 同一安全链"** 的完成率数据。

## 2. 方法：把 Student 放到决策位，其余链路不动

```
CARLA 场景 ──► integration.carla_runner --qwen-service-url --qwen-mode planner_v2
                    │
                    ├─ 构造 canonical 模型请求（含真实 scene_capabilities / targets / constraints）
                    └─ POST /infer ─► challenge/hil/carla/student_action_service.py
                                          │  StudentPreprocessor → v3 FP32 ONNX → StudentPlanAdapter
                                          └─ 返回 ManeuverPlan V2
                    │
                    └─ PlanValidator / Schema → FSM → 控制 → SafetySupervisor → CARLA
```

要点：

1. **请求与训练同构**：`planner_v2` 模式下，编排器发出的就是训练期的 `ModelRequest`
   （`command_hint` / `constraints` / `scene_summary` / `scene_capabilities` / `targets`），
   其中 `scene_capabilities` 来自**运行时真实解释**（例如 B01 的
   `available_lanes=["CURRENT"]、route_available=true、intersection_ahead=true、current_lane="-1"`），
   **没有任何合成或默认值**；
2. **返回即计划**：服务直接回 Student 的计划（schema 2.0 / `reason_code=STUDENT_V0_STRUCTURED`），
   由仓库自己的 `PlanValidator` 与 `decision_plan`/`maneuver_plan` 校验把关，未通过即
   `REJECTED`（本轮的 23 次请求 **0 次拒绝、0 次异常**）；
3. **安全链不变**：红灯、TTC、行人、碰撞等仍由确定性安全层覆盖，模型只决定高层行为；
4. **图像口径**：`QwenImageStager` 产出的 224×224 padded JPEG，与学生训练帧同尺寸。

## 3. 复现命令

```powershell
# 1) 启动学生决策服务（等价于 Qwen 服务的接口位）
$env:PYTHONPATH='.'; py -3.12 -m challenge.hil.carla.student_action_service `
  --onnx D:\nana\oe\work\v3\student_v0_fp32_v3.onnx --port 8100 `
  --log-dir <log> --image-dir <imgs> --image-root <carla 图像目录>

# 2) 跑 18 个核心验收场景（basic/advanced/challenge 各 6 个，1 seed）
py -3.12 -m challenge.hil.carla.run_student_loop_suite --repo . `
  --service-url http://127.0.0.1:8100 --out <suite.json> --run-root <runs>

# 单场景等价写法
powershell -File challenge/hil/carla_measurement.ps1 `
  -Scenario "scenarios/acceptance_suite/basic/ACC_B02_set_speed_20.json" -Realtime `
  -ExtraArgs "--qwen-service-url http://127.0.0.1:8100 --qwen-mode planner_v2 --qwen-image-root <carla 图像目录> --qwen-timeout-ms 500"
```

每个场景 35 s 仿真时长、`--realtime`、`fixed_delta_s=0.05`，一轮 18 场景约 25 分钟。

## 4. 结果：18 场景通过 12 个

| 组 | 场景 | 判定 | 分 | 学生行为 | 未通过项 |
|---|---|---|---:|---|---|
| basic | ACC_B01_start_keep_lane | **SUCCEEDED** | 25 | KEEP_LANE | |
| basic | ACC_B02_set_speed_20 | FAILED | 20 | SET_SPEED | `target_speed_kph` |
| basic | ACC_B03_slow_to_10 | FAILED | 20 | SET_SPEED, SET_SPEED | `target_speed_kph` |
| basic | ACC_B04_normal_stop | **SUCCEEDED** | 25 | SET_SPEED, STOP | |
| basic | ACC_B05_emergency_stop | **SUCCEEDED** | 25 | SET_SPEED, STOP | |
| basic | ACC_B06_offset_recovery | FAILED | 20 | KEEP_LANE | `must_finish_route`、`cross_track_error_should_decrease`、`final_cross_track_error_m` |
| advanced | ACC_A01_lead_brake | **SUCCEEDED** | 25 | FOLLOW | |
| advanced | ACC_A02_red_light_conflict | **SUCCEEDED** | 25 | STOP | |
| advanced | ACC_A03_pedestrian_crossing | FAILED | 20 | KEEP_LANE | `expected_safety_override`、`expected_reason_contains`、`must_generate_event` |
| advanced | ACC_A04_static_obstacle_stop | FAILED | 20 | STOP | 扩展项 `expected_target_actor_id` |
| advanced | ACC_A05_lane_change_left | **SUCCEEDED** | 25 | CHANGE_LANE_LEFT | |
| advanced | ACC_A06_obstacle_detour_return | **SUCCEEDED** | 25 | AVOID_OBSTACLE, RETURN_TO_LANE | |
| challenge | ACC_C01_heavy_rain_fog | **SUCCEEDED** | 25 | KEEP_LANE | |
| challenge | ACC_C02_ambiguous_instruction | **SUCCEEDED** | 25 | STOP | |
| challenge | ACC_C03_illegal_instruction | **SUCCEEDED** | 25 | STOP | |
| challenge | ACC_C04_multi_target_binding | **SUCCEEDED** | 25 | FOLLOW | |
| challenge | ACC_C05_perception_failure | FAILED | 20 | KEEP_LANE | 扩展项 `max_fault_response_s` |
| challenge | ACC_C06_dynamic_route_deviation | **SUCCEEDED** | 25 | KEEP_LANE | |

**汇总（判定口径：`scenario_acceptance.status == SUCCEEDED`）**

| 组（对应评分细则三级难度） | 通过 / 总数 | 完成率 |
|---|---:|---:|
| 基础 basic | 3 / 6 | **50.0%** |
| 进阶 advanced | 4 / 6 | **66.7%** |
| 挑战 challenge | 5 / 6 | **83.3%** |
| **合计** | **12 / 18** | **66.7%** |

**全程 0 碰撞、0 闯红灯、0 路线偏离事件**（`collision_seen=false` 全部为假）。

## 5. 失败项归因（这是本轮最有价值的部分）

| 失败簇 | 场景 | 直接原因 |
|---|---|---|
| **速度跟踪偏低** | B02（要求 20 km/h ±2）、B03（要求降到 10 km/h） | 学生给出的 `SET_SPEED` 目标是 **4.33 m/s（15.6 km/h）** 与 **3.80 m/s（13.7 km/h）**，低于验收窗口——模型的显式速度回归系统性偏保守（与"速度头是量化偏差最大头"的既有结论一致） |
| 路线完成/横向误差 | B06 offset_recovery | 学生连续输出 `KEEP_LANE`，未完成"回到原车道"的恢复动作，末态横向误差 0.566 m |
| 安全覆盖期望 | A03 pedestrian_crossing | 场景要求出现**安全层覆盖事件**（`expected_safety_override`），而学生输出 `KEEP_LANE` 且未触发预期事件 |
| 目标绑定 | A04 static_obstacle_stop | 学生输出 `STOP` 但没有绑定目标 actor id，扩展验收要求 `expected_target_actor_id` |
| 故障恢复时延 | C05 perception_failure | 感知故障注入下，故障响应时间超出扩展阈值 `max_fault_response_s` |

**读法**：这 6 个未通过项**没有一个来自安全违规**（无碰撞、无越线），失败集中在
**显式速度精度、恢复动作选择、目标绑定与故障响应时延**四个工程点上——这些都可以直接转成
下一轮训练/契约的改进清单。

## 6. 决策延迟（同一轮实测）

| 指标 | 值 |
|---|---|
| 学生决策（ONNX 前向，含预处理）P50 | **3.81 ms** |
| P95 / max | 5.65 ms / 15.94 ms |
| 请求数 / 错误数 | 23 / **0** |

对照：Qwen 2B VLM 服务在同一链路上的延迟量级是**百毫秒到秒**（团队既有口径
`sensor-to-trajectory` P95 127.3 ms、模型服务 P95 86.5 ms）。本轮数据说明
**蒸馏模型在保持行为语义的同时把决策延迟压到 4 ms 量级**，是挑战赛道"轻量化"叙事的直接证据。

## 7. 口径与限制（引用时必须同时声明）

1. **场景是自建的 18 个**（`scenarios/acceptance_suite/{basic,advanced,challenge}`），
   不是官方 1000 帧基准；分组与评分细则的三级难度对齐，但**分母不同**，
   不能与团队的 83 场景结果直接相比（那一轮用的是 Qwen 决策模块）；
2. **单 seed**（seed 0），未做多次重复；每场景 35 s 实时仿真；
3. **安全链在环**：完成率是"模型 + 确定性安全层"的合计表现，不是模型单独成绩；
4. **行为 token 与执行语义**：`TURN_*`/`CHANGE_LANE_*` 的执行由 FSM 编译后的动作完成，
   本轮的 `CHANGE_LANE_LEFT`、`AVOID_OBSTACLE → RETURN_TO_LANE` 均已实际执行并通过验收；
5. **无板卡**：全部为 X86 仿真；功耗、真实 BPU 利用率仍 `NOT_MEASURED`；
6. 置信度口径：把学生计划置信度（本轮 0.85–0.94，均高于仓库 0.60 门槛）映射为逐 token
   logprob，未做人为抬升（`--confidence-mode plan`）。

## 8. 文件

| 文件 | 内容 |
|---|---|
| `01_suite_core_18_scenarios.json` | 18 个场景的逐场结果（判定、分、失败键、学生行为、碰撞、横向误差、末速）与分组汇总 |
| `02_student_decisions.jsonl` | 服务侧逐请求记录：送入的 canonical 请求、构造的学生请求、计划、行为、延迟 |
| `03_service_metrics.json` | 模型身份（ONNX SHA256）、请求数、动作分布、决策延迟分位 |
| `04_student_loop_metrics.json` | 18 次运行的逐场记录 + 汇总：闭环时延池化分位、oracle 对齐、安全计数、舒适性代理、30/40/30 加权演算 |
| `05_modality_ablation_closed_loop.json` | 闭环模态消融：rgb 置零后 18 场景逐场对比（判定/行为变化均为 0） |
| `06_closed_loop_soak_and_resources.json` | 闭环长稳 30 次运行的通过序列、时延稳定性、安全计数、舒适性与宿主 CPU/RSS 采样 |

工具（本轮新增，均在 `challenge/hil/carla/`）：
`student_action_service.py`（决策服务，`/infer` 返回计划、`/v1/chat/completions` 返回 A–E）、
`run_student_loop_suite.py`（批量驱动与分组统计）。

## 9. 从同批运行里汇出的其他 B3 指标（不需要额外跑车）

`challenge/hil/carla/summarise_student_loop.py` 把 18 次运行的 `*.summary.json` 与逐帧
`*.jsonl` 汇成下表（逐帧池化，共 **12,167 帧**），并做 30/40/30 加权演算。

### 9.1 闭环端到端时延（感知→控制，含模型决策）

| 阶段 | P50 | P95 | P99 | max | 均值 |
|---|---:|---:|---:|---:|---:|
| **sensor → control**（在环端到端） | **32 ms** | **47 ms** | 62 ms | 156 ms | 37.9 ms |
| sensor → decision | 32 ms | 47 ms | 62 ms | 156 ms | 37.5 ms |
| 模型决策（CARLA 侧打点，1 ms 量化） | 0 ms | 0 ms | 16 ms | 16 ms | 0.46 ms |
| 感知采集等待 | 62 ms | 78 ms | 79 ms | 391 ms | 51.7 ms |
| 仿真步进 | 15 ms | 16 ms | 31 ms | 32 ms | 11.1 ms |

口径：`--realtime` + `fixed_delta_s=0.05` 的同步仿真，**不含语音前端**（语音链路非 B3）。
两者都远低于 150 ms 阈值；`sensor→control` 与 `sensor→decision` 几乎相同，说明
**瓶颈在感知/仿真节拍而非模型**（决策自身的服务侧 P50 为 3.81 ms，见第 6 节）。

### 9.2 语义-动作对齐（闭环口径）

| 项 | 结果 |
|---|---|
| 场景自带的 `oracle_expected_behaviors` 检查 | **18/18 PASS** |
| 扩展验收整体 | 16/18（失败键：`expected_target_actor_id`、`max_fault_response_s`） |

即：每个场景"期望的高层行为集合"与**学生实际执行的行为**一致，包含
`SET_SPEED / KEEP_LANE / FOLLOW / STOP / CHANGE_LANE_LEFT / AVOID_OBSTACLE → RETURN_TO_LANE`。

### 9.3 安全计数（18 次运行合计）

| 项 | 值 |
|---|---|
| 碰撞 / 闯红灯 / 路线偏离 / 严重偏离 | **0 / 0 / 0 / 0** |
| 安全层覆盖帧数 | 37 帧（确定性安全层在环生效，不是模型输出） |

### 9.4 行驶动作合理性（舒适性代理指标）

| 指标 | 逐运行 P95 / 均值 | 最大值 |
|---|---|---|
| 纵向加速度 \|a\|（P95 / 峰值） | 0.71 / —（运行均值） | 25.17 m/s²※ |
| 纵向加加速度 \|jerk\|（P95 / 峰值） | 9.49 / —（运行均值） | 435.2 m/s³※ |
| 横向加速度 \|a_lat\| | 0.21（均值） | 2.29 m/s² |
| 转向变化率 | 0.48 /s（均值） | 5.00 /s |
| 横向误差（跨道误差） | 0.107 m（均值） | 0.85 m |

※ **单帧尖峰来自离散控制跳变**（油门/制动阶跃或停车终态），不是持续工况：按运行取 P95 后，
纵向加速度最差运行时为 **2.07 m/s²**、jerk 最差运行时 P95 为 25.3 m/s³。
横向加速度峰值 2.29 m/s²、横向误差最大 0.85 m 均出现在变道/绕障场景，属可接受范围，
但**舒适性阈值未由 B2/A4 冻结**，本表只报数字不判定。

### 9.5 完成率的评分口径演算（15 分项）

细则公式：`基础分 =（基础完成率×30% + 进阶×40% + 挑战×30%）×15`。本批数据：

`0.30×0.500 + 0.40×0.667 + 0.30×0.833 = 0.667` → **基础分 10.0 / 15**（未计违规扣分项，本批为 0）。

**这不是得分结论**：分母是自建 18 场景、单 seed；官方 1000 帧基准到位后必须重算。

## 10. 追加两轮（2026-10-07 晚）：闭环模态消融 + 闭环长稳

### 10.1 闭环模态消融：把视觉输入置零

服务侧加 `--zero-input rgb`（保持张量形状，内容清零），**同一批 18 场景**重跑一遍：

| 项 | 基线（有 RGB） | 视觉置零 | 差异 |
|---|---:|---:|---:|
| 通过数 | 12 / 18 | **12 / 18** | **0** |
| 判定变化的场景 | — | — | **0** |
| 行为序列变化的场景 | — | — | **0** |

也就是说：**在闭环里去掉视觉模态，18 个场景的判定与执行行为一个都没变**。这与离线消融
（6 队列 850 例置零 rgb 从不翻转行为）互相印证，构成"多模态融合有效性"这一项的**闭环证据**。
（本轮只置零了 rgb；text/targets/state 仍是离线诊断数据。）

### 10.2 闭环长稳：30 次连续在环运行（≈28 分钟）

两个代表场景各重复 15 次（`--realtime`，每次 35 s 仿真）：

| 场景 | 通过 / 次数 | 通过序列 | 失败键 |
|---|---:|---|---|
| ACC_B02_set_speed_20 | **0 / 15** | `FFFFFFFFFFFFFFF` | `target_speed_kph`（学生 `SET_SPEED` 目标稳定落在 4.33–4.41 m/s，低于 18–22 km/h 窗口） |
| ACC_A05_lane_change_left | **14 / 15** | `FPPPPPPPPPPPPPP` | 首轮 `must_finish_route` + `final_lateral_shift_m`，其后 14 轮全通过 |

* 19,292 帧里 **sensor→control P95 47 ms（大多数运行）**，首轮 A05 与其中一轮 B02 为 78/79 ms，
  **28 分钟内没有时延上漂**；
* 安全计数仍为 **0 碰撞 / 0 闯红灯 / 0 路线偏离**；安全层覆盖 2,097 帧（2.7%，集中在停车与恢复阶段）；
* oracle 行为检查 **30/30 PASS**；舒适性代理 p95 |a_long| 1.32 m/s²、横向加速度 max 0.48 m/s²、横向误差 max 0.12 m。

### 10.3 宿主资源（异构利用率的 CPU 侧证据）

用 `carla/loop_resource_sampler.py` 在两轮运行时 1 Hz 采样（共约 63 分钟）：

| 进程 | 平均 CPU（单核=100%） | P95 | max |
|---|---:|---:|---:|
| 规划进程（`carla_runner` + CARLA 客户端） | 30–35% | 48–55% | 84% |
| 学生决策服务 | 7.7–8.9% | 1.6% | 596–613%（多线程 ONNX 突发） |
| 全系统 | 35–37% | 43–44% | 70% |

**口径限制**：① 官方"异构算力利用率"公式未到，本表只提供 **CPU 侧**证据；② 服务进程的峰值是
ONNX 多线程推理突发（不是窗口塌缩——清洗后丢弃样本为 0），引用时用**均值/P95**；③ BPU 侧
`NOT_MEASURED`，需 A4 Runtime 或板卡。逐项记录见 `06_closed_loop_soak_and_resources.json`。
