# 模型与权重生命周期

## 1. 模块目标

本模块统一挑战赛道从 Qwen Teacher、A1 Student 结构、A3 FP32 训练、A2 INT8 量化到
A4/B3 Runtime 验收的模型身份和权重状态。目标是让每一个可执行模型都能回答：它由什么
代码生成、用什么数据训练、权重字节是否一致、通过了哪一级门禁。

本模块不负责定义驾驶业务逻辑，不把模型输出直接转换为油门、刹车或方向盘，也不替代
B2 独立评测。

A2 的 Calibration、PTQ、敏感层、QAT 和 INT8 交付细则见
[`A2_INT8_QUANTIZATION_AND_QAT.md`](A2_INT8_QUANTIZATION_AND_QAT.md)。
A4 的 OpenExplorer 转换、Runtime 身份、J6P 产物和性能证据门禁见
[`A4_OPENEXPLORER_J6P_RUNTIME.md`](A4_OPENEXPLORER_J6P_RUNTIME.md)。
B4 的 Candidate 登记、Final Freeze、Release Manifest 和提交包身份门禁见
[`B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md`](B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md)。

## 2. 模型角色

| 层级 | 所有者 | 输入与输出 | 权威身份 | 当前状态 |
|---|---|---|---|---|
| Qwen Teacher | B1 | `ModelRequest V1 → ManeuverPlan V2` | `Qwen/Qwen3.5-2B` + exact revision + artifact fingerprint | 已固定并完成服务健康验证 |
| Student 结构 | A1 | 四路固定 Shape 输入 → 10 个结构化 Head | `student-v0-r3-fp32` + `student-v0-r3-structure-20260911` | 结构、Shape、随机 ONNX 已就绪 |
| Student FP32 | A3 | 使用 B1 标签训练同一 A1 结构 | weights SHA + dataset/view SHA + checkpoint SHA | 基线候选存在于外部 artifacts，未 Gate 通过 |
| Student INT8 | A2 | 从 Gate 通过 FP32 量化 | FP32 来源 SHA + 校准集/配置 SHA + INT8 SHA | 未交付 |
| Runtime 产物 | A4 | 固定 Student 输入输出合同 | 模型 SHA + Runtime Git SHA + config/dataset ID | X86 工具链部分完成，J6P 未完成 |
| 独立实测 | B3 | 相同 Runtime 入口 | 五标识 + 原始测量证据 | 等待真实 A3/A2/A4 产物 |

## 3. 固定身份

### 3.1 Teacher

| 字段 | 值 |
|---|---|
| `model_id` | `Qwen/Qwen3.5-2B` |
| `model_revision` | `15852e8c16360a2fea060d615a32b45270f8a8fc` |
| `artifact_fingerprint_sha256` | `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa` |
| 输出模式 | `planner_v2` |
| 精度 | bfloat16，未量化 |

`challenge/teacher_baseline_manifest.json` 记录冻结基线代码 SHA
`a05c8b76efcd4c176965223c661f40b153cb1836`；B1 v4 采集器使用
`95e97b00def8ec36f12937da34ce8bb9082c4a04`。前者是冻结 Teacher 基线身份，后者是
采集代码身份。二者不能共用一个含义不清的 `teacher_git_sha` 字段，派生训练视图必须同时
保留 baseline 与 collector provenance。

### 3.2 Student

| 字段 | 值 |
|---|---|
| `model_id` | `student-v0-r3-fp32` |
| `config_id` | `student-v0-r3-structure-20260911` |
| 参数量 | 23,006,581 |
| 输入 | RGB `[1,3,224,224]`、text `[1,32]`、targets `[1,8,14]`、state `[1,64]` |
| 输出 | 10 个结构化 Head，最多 4 步计划 |
| ONNX | opset 17、batch 1、无动态轴 |

`challenge/student_v0_fp32.onnx` 的 `weights_status` 是
`random_initialization_for_export_smoke_only`。其 SHA 只证明结构产物未漂移，不证明训练
精度。

## 4. 权重状态机

```text
A1_STRUCTURE_READY_A3_WEIGHTS_PENDING
  -> A3 training checkpoint
  -> PENDING_A3_FP32_GATE
  -> A3_FP32_GATE_FAILED 或 A3_FP32_GATE_PASSED
  -> A2 INT8 candidate
  -> INT8 accuracy/consistency gate
  -> A4 Runtime artifact
  -> B3 X86_PRE_VALIDATED
  -> J6P/HIL final evidence
```

禁止跳级。例如随机 ONNX 不能直接进入 A2 正式量化，`PENDING_A3_FP32_GATE` 不能标记
production-ready，X86 工具链通过也不能写成 J6P 通过。

## 5. A3 候选产物

正式训练应输出：

```text
student_fp32_best.pt                 # 完整训练 checkpoint
student_fp32_last.pt                 # 最后 epoch checkpoint
student_v0_fp32_candidate.pt         # 纯 state_dict
student_v0_fp32_candidate.json       # 候选身份和指标
training.jsonl
training_summary.json
training_report.md
hard_cases/
```

候选 manifest 至少绑定：

- 训练代码完整 Git SHA 与工作区是否干净；
- Teacher baseline、model ID、revision 和 artifact fingerprint；
- Student `model_id/config_id`；
- 数据集版本、release manifest SHA、A3 view manifest SHA；
- best checkpoint SHA 和纯权重 SHA；
- Validation 指标与 `PENDING_A3_FP32_GATE` 状态。

Mock 或 integration smoke 只能输出 `MOCK_ONLY`，永远不能进入正式晋级。

## 6. FP32 晋级门禁

`challenge/distillation/promote.py` 只接受独立 Validation 的 Teacher/Student 同口径结果，
明确拒绝 Frozen Test。当前默认门槛：

| 指标组 | 门槛 |
|---|---|
| behavior、target pointer、target lane、completion、plan sequence | Student 相对 Teacher 下降不超过 1.5 个百分点 |
| safety-critical behavior recall | 不允许下降 |
| Student schema validity | 必须为 100% |
| 输入身份 | dataset version 与四项 Teacher 身份必须一致 |
| 候选来源 | 干净、已提交的 Git 工作区 |

运行形式：

```bash
python -m challenge.distillation.promote \
  --candidate artifacts/run/student_v0_fp32_candidate.json \
  --weights artifacts/run/student_v0_fp32_candidate.pt \
  --teacher-evaluation artifacts/eval/teacher_validation.json \
  --student-evaluation artifacts/eval/student_validation.json \
  --output artifacts/run/weights_manifest.json
```

### 正式D2多cohort门禁

`promote_fp32_candidate()` 现同时接受 `frozen_manifest` 和
`signed_d2_release_formal`。正式D2策略必须使用固定多cohort Teacher标识，并验证完整
model revision、artifact fingerprint、release manifest SHA和A3 view manifest SHA；
Teacher/Student独立评价还必须绑定相同的benchmark manifest、policy manifest、case-set
digest、evaluator Git SHA和样本数，并逐端绑定predictions SHA；Student评价必须绑定candidate
权重SHA，正式对照Teacher必须是冻结v4。Smoke策略继续被拒绝。

该兼容只解决“合法正式候选无法进入判定器”的代码问题，不产生评价证据。没有B2签发的
independent Validation包时，所有候选继续保持 `PENDING_A3_FP32_GATE`；仍禁止手工改
identity policy或使用Reserved/Frozen Test制造PASS。

## 7. Runtime 就绪语义

`challenge/planner/student_backend.py` 实施 fail-closed：

- 无权重：加载随机结构，`production_ready=false`；
- 有权重但无 manifest：可用于诊断，`production_ready=false`；
- manifest 缺字段、Git SHA 非 40 位、模型/config 不匹配或权重 SHA 不匹配：拒绝；
- manifest 未标记 `A3_FP32_GATE_PASSED`：拒绝；
- 权重和 Gate manifest 全部一致：才报告 Student Planner ready。

这里的 ready 只表示 A3 权重身份通过；B2、A2、A4 和 B3 仍有各自门禁。

## 8. 本地存储与版本库边界

- `models/`：服务器本地大模型目录，Git 仅跟踪 README。
- `artifacts/`：训练 checkpoint、候选权重、运行日志和临时报告，默认不提交。
- `challenge/`：可复现结构、配置、manifest、随机初始化 ONNX 和测试。
- `weights/`：下载脚本，不保存正式挑战赛道模型 artifact。

本地目录名不构成模型身份。复制到新服务器后必须重新生成或核对 artifact manifest，不能
只比较文件夹大小。

Teacher 指纹命令：

```bash
python -m challenge.dataset.teacher_model_fingerprint \
  --model-dir /absolute/path/to/Qwen3.5-2B \
  --model-id Qwen/Qwen3.5-2B \
  --revision 15852e8c16360a2fea060d615a32b45270f8a8fc
```

A1 结构验证：

```bash
python -m challenge.export.export_onnx --output challenge/student_v0_fp32.onnx
python -m challenge.export.validate_artifacts --root .
python -m pytest -q challenge/tests/test_a1_student.py challenge/tests/test_delivery.py
```

## 9. 旧路线与当前路线隔离

以下文件仍包含基础赛道历史 Qwen3-VL-2B GPTQ/FP8 配置：

- `tools/run_qwen3vl_2b_vllm_cu132.sh`
- `tools/run_qwen_latency_gate.py`
- `tools/repro_cli.py`
- `submission/current/technical_solution.md`

它们不是挑战赛道正式 Teacher 入口，其模型 ID、revision、量化方式和历史延迟不能进入
B1/A3/B2/B3 的挑战赛道证据。后续整理这些文件时应明确标注 basic-track/legacy，或将仍
需要的挑战赛道功能迁移到独立入口；在完成前不要直接删除，以免破坏基础赛道复现。

## 10. 当前完成度

| 项目 | 状态 |
|---|---|
| Teacher exact revision 与 artifact fingerprint | 已完成 |
| A1 Student 结构与随机 ONNX | 已完成 |
| D2 FP32 基线训练及确定性复跑 | 已完成，但仅为候选 |
| 独立 Validation Teacher/Student 对比 | 未交付 |
| promotion identity policy 与证据身份对齐 | 已完成代码与测试；真实B2评价包未交付 |
| 真实 `A3_FP32_GATE_PASSED` 权重与 manifest | 未交付 |
| A2 INT8 正式产物 | 未交付 |
| A4 J6P Runtime | 未交付 |
| B3 正式板端/HIL 证据 | 未交付 |

仓库中出现的 `A3_FP32_GATE_PASSED` 目前只存在于测试构造和规则说明中，不是可部署的
真实权重证据。
