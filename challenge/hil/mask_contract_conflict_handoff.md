# 行为差额归因交接：契约/掩码 vs 模型（B3 → B1 / B2 / A1 / A3）

> 状态 `DIAGNOSTIC_ONLY`：权重仍是 `PENDING_A3_FP32_GATE` 候选，跑在 X86，无板卡。
> 本文不是精度结论，只回答一个问题：**学生行为匹配率上的差额，有多少来自模型、多少来自解码器的可行性掩码。**

## 1. 为什么要发这份东西

B3 此前三轮一直记录"学生**从不产出 `TURN_LEFT`**（v1/v2/v3 在 turn-gap 27/27、gap300 108/108
全部答成 `SLOW_DOWN`/`SET_SPEED`）"，并据此建议 A1/A3 **补转弯族训练数据**。

2026-10-07 做了逐例逐步归因，**这个建议是错的**：模型在这些步上的**未受限 argmax 就是教师的行为**，
是被解码器（`challenge/planner/student_adapter.py` 的 `_feasible_behaviors`，非 B3 文件）
按请求字段剔掉的。再补数据解不了，**必须先对齐字段/策略**。

## 2. 数字（v3 候选，6 个留出队列，850 例）

| 队列 | 教师行为步 | 解码后匹配 | 未受限 argmax 匹配 | 被掩码挡掉的教师步 |
|---|---:|---:|---:|---:|
| d2_v1_1_val | 593 | 564 (95.1%) | **593 (100%)** | 29 |
| d3_wave2_safe_short | 73 | 73 (100%) | **73 (100%)** | 0 |
| d3_targeted_gap_strict | 99 | 99 (100%) | **99 (100%)** | 0 |
| d3_turn_gap_60_strict | 29 | 20 (69.0%) | **29 (100%)** | 9 |
| d3_gap300_strict | 123 | 87 (70.7%) | **123 (100%)** | 36 |
| b1_ms34_supplement | 14 | 10 (71.4%) | **14 (100%)** | 4 |
| **合计** | **931** | **853 (91.6%)** | **931 (100%)** | **78** |

**78/78 步里，模型的未受限 argmax 与教师完全一致**——差额 100% 来自掩码。

## 3. 两条规则，覆盖全部 78 步

### 规则 A：`scene_capabilities.intersection_ahead = false` → 剔掉 `TURN_LEFT`/`TURN_RIGHT`（73 步）

| 队列 | 步数 | 教师行为 | 模型未受限 argmax | 解码结果 | `route_available` |
|---|---:|---|---|---|---|
| d3_turn_gap_60_strict | 9 | `TURN_LEFT` | `TURN_LEFT` | `SLOW_DOWN` | true |
| d3_gap300_strict | 36 | `TURN_LEFT` | `TURN_LEFT` | `SLOW_DOWN` | true |
| d2_v1_1_val | 29 | `TURN_LEFT` 7 / `TURN_RIGHT` 22 | 同教师 | `SLOW_DOWN` / `SET_SPEED` 等 | true |

也就是说：**数据这边** `route_available=true`，却把 `intersection_ahead` 标成 `false`；
**教师（Qwen）那边**在这批场景里标了转弯；**模型**学会了教师的标签；**解码器**按字段把转弯判成不可行。

### 规则 B：请求的 `allowed_behaviors` 不含 `KEEP_LANE`（ms34 的"恢复"步，4 步）

`b1_ms34_supplement` 的 4 个用例，教师最后一步是 `KEEP_LANE`（避让后回到本车道），
但请求的 `allowed_behaviors` 是

```
["SLOW_DOWN","STOP","CHANGE_LANE","AVOID_OBSTACLE","RETURN_TO_LANE"]      # 2 例
["SLOW_DOWN","STOP","YIELD","CHANGE_LANE","AVOID_OBSTACLE","RETURN_TO_LANE"]  # 2 例
```

——**都没有 `KEEP_LANE`**，于是模型即使把 `KEEP_LANE` 排在第一位也会被改写成
`RETURN_TO_LANE`/`YIELD`。这正是此前记录的"多步计划最后一步错"。

## 4. 需要谁做什么决策（这是本交接的实质）

三选一，选定后 B3 可按同一脚本重算，请**不要**在没有结论前安排转弯族补数据：

1. **改数据**（B1）：让 `scene_capabilities.intersection_ahead` 与教师标签一致；
   同时把 `allowed_behaviors` 补齐到覆盖教师用到的行为（`KEEP_LANE` 等）；
2. **改契约/掩码**（B2 + 仓库 owner）：放宽"无路口 → 禁止转弯"的硬掩码（例如只在
   `route_available=false` 时才禁），并明确 `allowed_behaviors` 与教师标签不一致时的优先级；
3. **保留现状**（A1/B2）：承认"教师标签可能超出可执行域"，那么在评测口径里必须写明
   **这部分不计入模型误差**，否则同一份数字会被两个口径各算一遍。

## 5. 复现

```powershell
# 6 队列 850 例，消融 + 归因一次跑完（宿主）
$env:PYTHONPATH='.'; py -3.12 challenge/hil/harness/x86_sim/cohort_diagnostics.py `
  --onnx <student_v0_fp32_v3.onnx> --work <dumps 根目录> --out <out.json>

# 单队列（含逐案清单）
py -3.12 challenge/hil/harness/x86_sim/turn_left_attribution.py `
  --onnx <v3.onnx> --dumps <dumps_turn> --frozen challenge/hil/frozen/d3_turn_gap_60_strict_v1_val
```

逐案清单（`case_id` / `step` / 教师行为 / 模型 argmax / 掩码后选择 / 被挡原因 / 模型是否与教师一致）
在 `evidence/a3_v3_simulation_20261007/08_cohort_diagnostics_v3.json` 的
`turn_left_attribution.<队列>.mask_blocked_teacher_steps`。

## 6. 口径与限制

- 比的是**行为 token（逐步、按步序号对齐）**，不含 target / lane / speed / completion / timeout 字段；
  整份计划的逐字段等价性仍由 `evidence/a3_v3_simulation_20261007/02_behaviour_replay_v3.json`
  与 `consistency` 覆盖；
- 教师 `teacher_plan` 来自 Qwen 计划，不是 CARLA 真值；"谁对"需要 B1/B2 判定，
  B3 只负责把"差额来自哪一层"量出来；
- 全部结论 `X86_MEASURED` + `DIAGNOSTIC_ONLY`，无板卡、无 A4 Runtime、无 B2 冻结基准。
