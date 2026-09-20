# B3 → A3 失败样本交接格式

> 失败归因、冻结 Test 隔离和正式 B3 流程见
> [`docs/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](../../docs/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md)。

> 目的：把 B3 在回放与异常测试中发现的真实问题，变成 A3 能直接使用的输入。
> 现状：`challenge/distillation/hard_cases.py` 只在训练内部挖验证集分歧，
> **不接收外部失败样本**。本文件定义这条缺失的链路的格式与规则。

## 1. 两类东西绝不能混

B3 的 `failure_cases/` 里混着性质完全不同的两种记录：

| 类型 | 来源 | 有 Teacher 标注？ | 能否进训练集 |
|---|---|---|---|
| **语义失败** | 冻结请求集里的真实 `ModelRequest` 产出了错误/非法计划 | 有（同请求有 Teacher 计划） | **可以** |
| **健壮性向量** | 合成非法输入（NaN 距离、缺 key、空指令） | 没有 | **绝对不可以** |

把合成非法输入拿去训练，等于教 Student 在垃圾输入上输出合法计划，
既没有监督信号，又会污染分布。所以导出时用 `usable_for_training` 显式区分。

## 2. 交接文件

```text
handoff/
├── handoff.jsonl          每行一条记录（语义失败 + 健壮性向量）
├── handoff_summary.json   计数、失败分类分布、来源快照、规则
└── README.md              给 A3 的简短说明
```

`handoff.jsonl` 记录字段：

| 字段 | 说明 |
|---|---|
| `sample_id` | **join key**，与 B1 数据集 `sample_id` 一致 |
| `case_id` / `scenario_id` / `round` | 回溯到具体回放位置 |
| `source` | `hil_replay` 或 `abnormal_input_suite` |
| `outcome` | `READY` / `REJECTED` / `ERROR` / `TIMEOUT` |
| `structural_failures` | 结构检查失败项（如 `must_stop_violated`） |
| `failure_taxonomy` | 归类后的标签，见 §3 |
| `teacher_behavior_sequence` / `student_behavior_sequence` | 逐步行为对比 |
| `model_request` | 完整 `ModelRequest V1`（可直接重建输入） |
| `teacher_plan` | Teacher 的 `ManeuverPlan V2`（训练标签来源） |
| `student_plan` | Student 实际输出，供误差分析 |
| `usable_for_training` | **布尔，唯一准入开关** |
| `training_note` | 为什么能不能用 |
| `record_sha256` | 记录级 SHA256，防止被静默修改 |

## 3. 失败分类（`failure_taxonomy`）

```text
SAFETY_CONSTRAINT    硬停约束被违反（最高优先级）
BEHAVIOR_MISMATCH    首步行为与 Teacher 不一致
LENGTH_MISMATCH      计划步数与 Teacher 不一致
FORBIDDEN_OUTPUT     输出了 steer/throttle/brake/waypoints
PLAN_SCHEMA          计划缺少必需字段或结构非法
PLAN_LENGTH          步数不在 1..4
ID_ECHO              request_id / command_id 未回显
NO_PLAN              未产出计划
OTHER                其他
RUNTIME_<OUTCOME>    运行时层面的失败（ERROR / TIMEOUT / REJECTED）
```

`SAFETY_CONSTRAINT` 应作为 A3 补训时的最高权重类别。

## 4. A3 侧的使用规则

1. **只有 `usable_for_training = true` 的记录可以进入训练集**；
2. 健壮性向量只用于验证 fail-closed 行为，不参与训练；
3. **冻结 Test 集上的失败绝不允许用于训练**（现有 `hard_cases.py` 已对
   `test`/`frozen` 分裂做了硬拒绝，导出侧同样遵守）；
4. 样本按 `sample_id` join 回 B1 数据集可拿到完整上下文（RGB SHA、场景元数据）；
5. 补训后必须重新过 B2 的 Gate，B3 换算出新的 `model_sha256` 后重新实测。

## 5. 生成方式

```powershell
# 在已有 run 目录上导出
py -3.12 -m challenge.hil.cli handoff --run <仓库>\challenge\hil\runs\<run_id>

# 或让 run 自动导出（默认开启，--no-handoff 关闭）
py -3.12 -m challenge.hil.cli run ... --frozen <快照>
```

导出是幂等的：同样的 `hil_replay.jsonl` 与 `hil_replay_plans.jsonl` 得到同样的
`handoff.jsonl`，可用于复现与审计。

## 6. 待 A3 确认

1. 是否接受"按 `sample_id` join 回 B1 数据集"的方式，还是希望交接文件自带全部字段；
2. `failure_taxonomy` 是否需要与 A3 现有的 hard-case 分类对齐（当前是 B3 自定义）；
3. 补训集的采样权重是否需要 B3 在导出时给出建议值（如 `SAFETY_CONSTRAINT` 加权）。
