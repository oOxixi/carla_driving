# B2 独立评测与 A3 FP32 Gate

## 1. 模块目标

本模块定义 A3 Student 候选如何接受独立评价、如何生成可审计的 FP32 Gate 结论，以及
B2 如何在不泄露 Frozen Benchmark 的前提下给出最终验收结果。

它不负责 A3 训练、不允许用 Frozen Test 选择 checkpoint，也不把 A3 FP32 Gate、B2
最终评测、A2 INT8 一致性和 B3 HIL 混成一个“通过”。

相关模块：

- [`A3_TRAINING_AND_HARD_CASES.md`](A3_TRAINING_AND_HARD_CASES.md)：候选训练与开发 Val。
- [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md)：权重身份和状态机。
- [`B1_TO_A3_DATA_PIPELINE.md`](B1_TO_A3_DATA_PIPELINE.md)：数据发布与 split 边界。
- [`challenge/distillation/HANDOFF.md`](../../challenge/distillation/HANDOFF.md)：交接字段。

## 2. 当前状态快照

核对日期：2026-09-21。代码基线：`challenge` 提交
`a17428a84aad82252ea60e961fb735146b1f20aa`。

| 能力 | 当前状态 | 证据/限制 |
|---|---|---|
| A3 逐 Head 开发 Val | 已实现 | `challenge/distillation/evaluate.py`、`metrics.py` |
| FP32 candidate 导出 | 已实现 | 状态保持 `PENDING_A3_FP32_GATE` |
| FP32 promotion 判定器 | 已实现基础规则 | `artifacts.py`、`promote.py`，目前只在合成测试中证明规则可执行 |
| B2 独立评价生成器 | 未实现 | 仓库没有生成 Teacher/Student evaluation JSON 的 B2 入口 |
| 真实独立评价 JSON | 未交付 | 仓库中没有实际 `evaluation_id` 结果文件 |
| B2 Frozen Benchmark | 未冻结 | Seen/Variant/Unseen case 清单和正式判分策略缺失 |
| 真实 FP32 Gate manifest | 未交付 | 仓库没有可部署的 `A3_FP32_GATE_PASSED` 产物 |

`challenge/hil/frozen/d2_v1_1_val/` 只是将 539 条 **开发 Val** 冻结成可重复回放快照；
“frozen”描述文件字节不可变，不表示它是 B2 Frozen Test。D2 的 540 条
`reserved_test_candidates` 也只是候选池，`challenge/reports/D2_DATASET_DELIVERY.md`
明确说明它不是最终 D3 Frozen Test。

## 3. 必须分开的三个验证层级

| 层级 | 数据所有者 | 是否参与模型选择 | 输出 | 当前状态 |
|---|---|---:|---|---|
| A3 development Validation | B1 发布，A3 可见 | 是 | best checkpoint、逐 Head 指标、hard cases | 已运行，但模板/场景高度重合 |
| A3 FP32 independent Validation gate | B2/独立评测方签发；A3 只收聚合证据 | 否 | `A3_FP32_GATE_PASSED/FAILED` manifest | 判定器存在，真实证据缺失 |
| B2 Frozen Benchmark | B2 封存 | 否 | Seen/Variant/Unseen 最终报告与 PASS/FAIL | 数据、执行器和策略均未交付 |

A3 promotion 代码明确拒绝 split 名称含 `test` 或 `frozen` 的评价证据，因此它的输入
必须是独立 Validation，而不是最终 Frozen Test。B2 最终 Benchmark 是后续独立结论，
不得为了复用 promotion CLI 而把 Test 改名成 `validation`。

## 4. A3 向 B2 交付的候选

A3 至少交付以下不可分割的两项：

1. `student_v0_fp32_candidate.pt`：纯 `state_dict`；
2. `student_v0_fp32_candidate.json`：候选身份 manifest。

候选 manifest 当前包含：

- 训练 Git SHA 和工作区是否干净；
- Teacher Git SHA、model ID、exact revision、artifact fingerprint 和 identity policy；
- Student `model_id`、`config_id`；
- weights SHA256、源 checkpoint SHA256；
- dataset version、release manifest SHA、A3 view manifest SHA；
- A3 development Validation 指标；
- `PENDING_A3_FP32_GATE` 状态。

B2 接收时必须重新计算权重 SHA256，并核对候选来自干净、已提交的工作区。Development
Val 指标只用于解释训练过程，不能直接复制成独立评价结果。

## 5. promotion 当前接受的评价合同

`promote.py` 接收 Teacher 与 Student 两个 JSON object。当前代码真正校验的最小结构为：

```json
{
  "evaluation_id": "独立且非空的评价运行 ID",
  "split": "validation",
  "dataset_version": "必须与 candidate 一致",
  "teacher_git_sha": "必须与 candidate 一致",
  "teacher_model_id": "必须与 candidate 一致",
  "teacher_model_revision": "必须与 candidate 一致",
  "teacher_artifact_fingerprint_sha256": "必须与 candidate 一致",
  "schema_validity": 1.0,
  "metrics": {
    "behavior_accuracy": 0.0,
    "target_pointer_accuracy": 0.0,
    "target_lane_accuracy": 0.0,
    "completion_accuracy": 0.0,
    "plan_sequence_accuracy": 0.0,
    "safety_critical_behavior_recall": 0.0
  }
}
```

其中 `schema_validity` 是 Student evaluation 的强制字段；Teacher evaluation 可以不含该
字段。其余身份字段和六项指标两边都必须提供。

Teacher 和 Student 必须在同一份不可变 case manifest 上、用同一 label encoder 和指标
实现运行。当前代码尚未校验 case manifest SHA、样本数或 evaluator Git SHA，因此 B2
正式交付不能只满足上述“最小结构”，还必须补充第 8 节的证据字段。

## 6. 当前 Gate 规则

默认规则来自 `challenge/distillation/artifacts.py`：

| 指标 | 默认规则 |
|---|---|
| `behavior_accuracy` | Student 相比 Teacher 下降不超过 0.015 |
| `target_pointer_accuracy` | 下降不超过 0.015 |
| `target_lane_accuracy` | 下降不超过 0.015 |
| `completion_accuracy` | 下降不超过 0.015 |
| `plan_sequence_accuracy` | 下降不超过 0.015 |
| `safety_critical_behavior_recall` | 不允许下降 |
| Student `schema_validity` | 必须严格等于 1.0 |

CLI 返回码：PASS 为 `0`，指标不达标并成功写出 FAILED manifest 为 `2`；输入身份、数值
范围、文件哈希或合同非法时抛错，不得把异常当成普通 FAIL。

### 6.1 指标解释限制

- `plan_sequence_accuracy` 不包含 target speed、confidence、confirmation 或 replan。
- target speed MAE、failure accuracy、plan length、confirmation 和 replan 当前不参与晋级。
- `safety_critical_behavior_recall` 实际是 safety-critical 样本有效步骤上的 Behavior
  micro accuracy，不是碰撞检出率或闭环安全通过率。
- 所有 Gate accuracy 必须在 `[0,1]` 且为有限数；没有有效分母时不能用 0 或 1 填充。
- 1.5 个百分点是仓库当前默认工程阈值，不是比赛评分细则中的官方阈值。

## 7. 已实现的 fail-closed 项与缺口

| 检查 | 当前实现 | 仍需补足 |
|---|---|---|
| candidate 状态 | 只接受 `PENDING_A3_FP32_GATE` | 无 |
| Git 清洁性 | 要求 `source_worktree_dirty=false` | 未复核远端 commit 可达性 |
| 权重身份 | 重新计算并比对 weights SHA256 | evaluation 未绑定该 SHA |
| Teacher 身份 | 比对四项 Teacher 字段 | 多 cohort policy 尚未统一 |
| split 防泄露 | 拒绝 Test/Frozen，只接受 Val/Dev 别名 | 未绑定具体 split manifest SHA |
| 数据身份 | 比对 `dataset_version` | 未比对 release/view/case-set digest |
| 评价运行 | 要求非空 `evaluation_id` | 未校验 evaluator Git/config/env/时间/样本数 |
| 指标合法性 | 六项必需、有限且在 `[0,1]` | 没有 denominator、置信区间或切片覆盖门禁 |
| 阈值 | 输出实际使用的 drop threshold | CLI 可任意放宽，未绑定 B2 policy manifest |
| 结果 | 原子写出 PASS/FAILED manifest | 没有签名/批准人和原始预测哈希 |

## 8. B2 正式评价包的完成合同

为了关闭上述缺口，B2 每次独立评价至少应交付：

```text
b2_evaluation/<evaluation_id>/
├── benchmark_manifest.json
├── policy_manifest.json
├── teacher_evaluation.json
├── student_evaluation.json
├── slice_metrics.json
├── predictions.sha256
├── environment.json
└── evaluation_report.md
```

### 8.1 `benchmark_manifest.json`

至少记录 benchmark ID/version、用途（independent-val 或 frozen-test）、case-set digest、
样本数、RGB 集合哈希、split/group 规则、Seen/Variant/Unseen 数量、各风险类别分母和
冻结时间。公开给 A3 的 independent-val 与 B2 封存的 final-test 必须是两个身份。

### 8.2 `policy_manifest.json`

固定指标实现 Git SHA、macro/micro 口径、空分母规则、Gate 指标、阈值、切片最低分母、
多次运行合并规则和失败处理。阈值一旦用于比较候选就不能通过 CLI 临时放宽；修改策略
必须产生新 policy version，并对所有候选重评。

### 8.3 Teacher/Student evaluation

除第 5 节字段外，至少增加：

- `benchmark_manifest_sha256`、`policy_manifest_sha256`；
- evaluator Git SHA、配置 SHA、环境指纹和运行时间；
- Student `model_id/config_id/weights_sha256`；
- 总样本数、每项指标 denominator、无效/失败样本数；
- 原始预测文件 SHA256 和 schema error 分类；
- Seen/Variant/Unseen、normal/complex/safety-critical 逐切片结果。

Teacher 与 Student 的 case digest、policy digest 和 evaluator 代码必须逐项相同。若某次
推理失败，必须按预先冻结的 policy 计入，不能从分母中静默删除。

## 9. Benchmark 治理

### 9.1 Seen / Variant / Unseen

- **Seen**：能力类别和训练域已见，但具体 route/seed/frame 与训练隔离。
- **Variant**：同类任务的新地图、天气、交通密度、语言等价表达或组合变化。
- **Unseen**：未参与 A3 设计和调参的新 scenario family/组合，仍受合同能力边界约束。

最终定义和最小数量由 B2 policy manifest 固定，不能由 A3 根据结果事后移动样本类别。
三个集合均需按 group key 隔离，并审计 RGB、规范化 request、source text 和 scenario ID
与 Train/Val 的重复情况。

### 9.2 防泄露与冻结

1. A3 只拿 independent-val 聚合结果，不拿 Frozen Test label 或逐样本 Teacher plan。
2. 冻结后任何增删都生成新 benchmark version 和完整变更清单。
3. 看过 Frozen Test 结果的候选不能针对该结果重训后继续声称同一测试集为盲测。
4. 同一 RGB、相邻帧、同一 supervision event 或仅改 sample ID 的副本不得跨 split。
5. `reserved_test_candidates` 在正式冻结、去重和 policy 签发前不得称为 Frozen Test。
6. `official_like_1000` 目前只有设计说明、没有实际发布文件，不能写成已完成。

## 10. A3 FP32 Gate 与 B2 最终结论的状态机

```text
PENDING_A3_FP32_GATE
  -> independent Validation evidence complete
  -> A3_FP32_GATE_FAILED
     或 A3_FP32_GATE_PASSED
  -> B2 Frozen Benchmark（只评，不调）
  -> B2_FINAL_FAILED
     或 B2_FINAL_PASSED
  -> 才能与 A2/A4/B3 的独立门禁组合成挑战赛道交付结论
```

FP32 Gate FAILED 后应回到新候选、新权重 SHA 和新 evaluation ID；不得覆盖旧 manifest。
B2 final FAILED 也不能通过手改 A3 Gate manifest 消除。

## 11. 当前可执行命令

只有在 B2 已提供合规的两个 independent Validation JSON 后才能运行：

```bash
python -m challenge.distillation.promote \
  --candidate artifacts/run/student_v0_fp32_candidate.json \
  --weights artifacts/run/student_v0_fp32_candidate.pt \
  --teacher-evaluation artifacts/b2/teacher_validation.json \
  --student-evaluation artifacts/b2/student_validation.json \
  --output artifacts/run/student_v0_fp32.manifest.json
```

不得在没有 B2 policy 的情况下使用 `--max-core-drop` 或 `--max-safety-drop` 放宽默认值。
当前 D2 正式 candidate 还会先因 `signed_d2_release_formal` 与 promotion 只接受
`frozen_manifest` 的策略不一致而失败。

## 12. 当前阻塞与完成定义

| 阻塞 | 关闭条件 |
|---|---|
| 没有 B2 独立评价入口 | 提交可复现的 Teacher/Student 成对 evaluator、schema 和测试 |
| 没有真实评价包 | 按第 8 节签发 independent Validation 包 |
| policy 可由 CLI 临时改变 | 阈值与指标绑定不可变 policy manifest，并由 Gate 校验哈希 |
| evaluation 身份校验不足 | 绑定 case/policy/evaluator/weights/release/view SHA 和样本分母 |
| Teacher identity policy 不一致 | 支持并严格验证正式 signed multi-cohort policy，加入端到端测试 |
| Reserved 与 Frozen 术语混用 | B2 签发独立 benchmark ID；旧候选池继续明确标为 candidate |
| 没有最终 Benchmark | 冻结 Seen/Variant/Unseen、执行正式评测并只交付批准范围的证据 |

模块完成的标准是：相同候选和相同不可变评价包可复算出同一 Gate 结论；失败不会生成
PASS；A3 无法接触或调参 Frozen Test；每个数字都有分母和来源；真实
`A3_FP32_GATE_PASSED` 能追溯到权重、代码、数据、Teacher、benchmark 和 policy 的完整
哈希链。当前仓库尚未达到该完成状态。
