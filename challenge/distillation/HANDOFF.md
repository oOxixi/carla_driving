# A3 上下游交接合同

本文只定义跨成员交接时必须稳定的接口。训练、评测、断点恢复和 Hard-case 细节见
[`docs/architecture/modules/A3_TRAINING_AND_HARD_CASES.md`](../../docs/architecture/modules/A3_TRAINING_AND_HARD_CASES.md)。

## A1 → A3：Student 结构

当前 A3 factory 入口是 `challenge.distillation.a1_student:build_a1_student`，输入
packer 是同一模块的 `build_a1_input_packer`；二者复用 A1 的
`challenge.student.StudentPlannerV0` 与 `StudentPreprocessor`。A3 配置通过
`model.factory` 指定 `module:callable`；factory 接收模型选项以及固定的
`max_steps=4`、`max_targets=8`，返回 `torch.nn.Module`。

Student 输入必须只使用 A1 packer 的固定张量合同，不得在 A3 内重新发明 token、
target 排序或图像预处理。输出必须包含以下浮点张量，其中 `B` 为 batch size：

| Head | Shape |
|---|---|
| `plan_length_logits` | `[B, 4]` |
| `behavior_logits` | `[B, 4, 14]` |
| `target_pointer_logits` | `[B, 4, 9]` |
| `target_lane_logits` | `[B, 4, 6]` |
| `target_speed_mps` | `[B, 4]` |
| `completion_type_logits` | `[B, 4, 8]` |
| `on_failure_logits` | `[B, 4, 4]` |
| `confidence` | `[B, 1]` |
| `requires_confirmation_logits` | `[B, 1]` |
| `replan_condition_logits` | `[B, 7]` |

Target pointer `0..7` 是当前 `ModelRequest.targets` 的零基槽位，`8` 表示 `NONE`。
Student 不得学习 Actor ID 字符串。Target-lane 索引固定为 A1 定义的
`CURRENT, LEFT_ADJACENT, RIGHT_ADJACENT, ROUTE_BRANCH, SHOULDER, NONE` 顺序。

A1 修改 head 数量、shape、枚举顺序、TopK、图像规格或 packer 时，必须同时提供：

1. 新 schema/配置版本；
2. packer 与 forward 合同测试；
3. 旧 checkpoint 不兼容声明或迁移器；
4. A3 可执行的 20～50 条真实数据 integration smoke。

## B1 → A3：数据发布

A3 只接收 B1 签发的 release，不接收聊天附件、临时路径或未签名 JSONL。每条记录
至少包含唯一 `sample_id`、`metadata.dataset_version`、`metadata.split`、有效
`ModelRequest V1`、Teacher `ManeuverPlan V2` 和可访问 RGB。

当前状态：

- 正式训练路径：`challenge/dataset/releases/d2_v1_1/`；
- D3 Wave1：additive candidate，完成全部 release/preflight 门禁前不得替换 D2；
- `normal`、`complex`、`safety_critical` 是当前支持的样本风险类别；
- B1 原始字段与 A3 派生 label 可以并存，但派生 label 必须能回溯到原始 plan。

A3 必须拒绝 split/group/RGB overlap、受保护 Test provenance、非法 target 引用、超过
4 步的计划、超过 TopK=8 的目标、非有限数值、未知类别，以及 manifest/hash 不一致。
正式数据版本不得原地改写；修订必须生成新 release 和新 dataset version。

## A3 → B2：独立评测

完整评价层级、JSON 合同、Gate 规则和 Frozen Benchmark 治理见
[`docs/architecture/modules/B2_EVALUATION_AND_FP32_GATE.md`](../../docs/architecture/modules/B2_EVALUATION_AND_FP32_GATE.md)。

A3 向 B2 交付待验 FP32 candidate 与 manifest，至少包括：

- `git_sha`、Student factory/config ID；
- `model_id`、checkpoint SHA256；
- `dataset_version`、Teacher repo/revision/fingerprint；
- Training/Validation 指标、hard-case 汇总和已知限制；
- 明确的 candidate 状态，不得提前写 `A3_FP32_GATE_PASSED`。

使用 `python -m challenge.distillation.candidate_handoff` 生成不可覆盖的待验包；工具会
复算candidate权重与来源checkpoint SHA，核对训练摘要、数据预检和hard-case计数，并从
训练Git提交提取配置快照。当前已冻结候选及服务器持久路径见
[`A3_CANDIDATE_HANDOFF.md`](A3_CANDIDATE_HANDOFF.md)。

B2 独立保管 Frozen Test 并给出最终 PASS/FAIL。A3 只能消费 B2 返回的聚合结果和错误
分类，训练、样本加权、checkpoint 选择与 hard-case mining 都不能读取 Frozen Test。

`signed_d2_release_formal` 与 promotion 的策略不一致已关闭：校验器现在同时支持单一
`frozen_manifest` 和正式 D2 多 cohort 签名策略；后者额外绑定 release/view、B2
benchmark/policy、case-set digest、evaluator Git SHA、样本数、两端 predictions SHA 与
Student 权重 SHA。正式 Gate 的 Teacher 对照强制为冻结的 Teacher v4；历史多 cohort 标识
只描述训练数据 provenance，不会被冒充为新的 Gate Teacher。这个修改只打通候选验证合同；B2 尚未交付
真实独立 Validation 包，因此任何当前 candidate 仍不得写成 `A3_FP32_GATE_PASSED`。

## A3 → A2/A4/B3：下游权重

只有 B2 独立评测通过、身份 manifest 完整并正式标记 FP32 Gate PASS 的 checkpoint
才能交给 A2 量化、A4 导出部署或 B3 HIL。`student_fp32_last.pt`、Smoke checkpoint、
未签名文件和人工改名权重均不得进入下游。

下游回报必须携带上游 FP32 权重 SHA256；否则 INT8、ONNX、OpenExplorer、J6P 或 HIL
结果无法归属到特定 A3 模型。

## B3 → A3：闭环 Hard-case

B3 的回传格式见 [`challenge/hil/hard_cases_handoff.md`](../hil/hard_cases_handoff.md)。
当前仓库已有格式但尚未接入 A3 importer。接入前，B3 样本不能直接追加到 Train。

正式回流必须完成 artifact/模型/场景身份校验、稳定键 join、Frozen Test 排除、Teacher
重标、group-aware 重划分、overlap 检查和新 release 签发。原始失败证据要保留；禁止
只复制修正后的标签而丢掉失败上下文。
