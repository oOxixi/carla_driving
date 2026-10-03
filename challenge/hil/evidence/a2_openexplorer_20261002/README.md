# A2 → A4 OpenExplorer 交接包的独立复核（2026-10-02/03）

> 复核对象是**他人的交付**。B3 只回答"包是否自洽、绑定是否正确、INT8 与 FP32 差多少、
> A2 的 OE 输入能不能被工具链接受"，**不下精度结论、不下板端结论**。

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| 包完整性 | **PASS**：1217/1217 个文件匹配 `SHA256SUMS.txt`；FP32 ONNX、OE 输入清单摘要与 `PACKAGE_MANIFEST.json` 一致 |
| 校准绑定 | A2 声明的 `calibration_jsonl_sha256` / `calibration_manifest_sha256` **与仓库里冻结的 `calibration_v1` 完全一致** → 我之前做的"校准与 6 个 val 划分零重叠"核验**直接覆盖**这次量化 |
| 量化张量 | 4 个输入各 300 个 NPY，共 1200，与清单一致 |
| INT8 产物 | 两份（full / mixed_top3）**都与其 manifest 摘要逐字节一致** |
| **绑定告警** | 该包绑定的是 **A3 候选 v1**（`eaee4402…`），而仓库里最新候选是 **v2**（`6b6ec1d8…`）——需 A2/A4 决定是否在 v2 上重做 |
| FP32↔INT8（留出队列 29 例） | **计划结构完全一致 29/29**；数值有偏差（见 §2） |
| A2 的 OE YAML pre-check | 在 OE 3.9.1（`nash-p`）里**编译成功**：**59/59 节点全在 BPU、零 CPU fallback**，2m09s |
| **编译后的 BPU 产物 ↔ A2 的 INT8 ONNX** | **十头余弦 min ≥ 0.9997**（骨干最差 0.9968），29/29 例次、无一例低于 0.999 → 编译没有引入额外失真 |

## 1. 包完整性（`00`/`01`）

- 1217 个清单文件全部匹配（0 失配、0 缺失、0 需要 EOL 归一——包从 zip 解出，不受 Windows 检出影响）；
- `PACKAGE_MANIFEST.json` 声明的 `fp32_onnx_sha256`（`25bb87a0…`）与随机附带的 ONNX 一致；`openexplorer_input_manifest_sha256` 一致；
- 两份 INT8 manifest 的 `source_fp32_onnx_sha256` 都等于该 FP32 ONNX 摘要，说明**量化确实来自这个 ONNX**；
- 状态如包自述：`PENDING_A3_FP32_GATE`、`gate_status = NOT_FORMAL`、`j6p_ready = false`。

## 2. FP32 ↔ INT8 一致性（`02`–`07`）

默认容差（rtol 1e-4 / atol 1e-5）是给浮点↔浮点设计的，对 INT8 **不适用**，所以 B3 拆成两个问题：

**（a）解码后的计划是否一致？—— 一致。** `consistency --adapter onnx` 在留出队列 29 例上：
两份 INT8（full 与 mixed）对全部 29 例的 `structural_diffs` **均为空**（行为序列、目标 id、完成类型完全相同），
差异只出现在数值字段。

**（b）数值偏差有多大、混合精度有没有用？** 逐头最大绝对偏差（29 例，`07`）：

| 输出头 | full INT8 | mixed_top3 | 是否改善 |
|---|---:|---:|---|
| `target_speed_mps` | **0.9445** | **0.9445** | 未变 |
| `target_pointer_logits` | 0.2154 | **0.1361** | ✅ |
| `replan_condition_logits` | 0.2118 | 0.2118 | 未变 |
| `on_failure_logits` | 0.1920 | 0.1920 | 未变 |
| `plan_length_logits` | 0.1880 | 0.1880 | 未变 |
| `behavior_logits` | 0.1697 | **0.1064** | ✅ |
| `target_lane_logits` | 0.1576 | **0.1169** | ✅ |
| 其余头 | ≤0.174 | 同值 | 未变 |

（各头余弦均 ≥0.9997，即"方向一致、幅度有差"。）

**读法**：A2 的敏感层 top-3 恢复（pointer / behavior / lane）**确实且只在这三个头上生效**——
其余头逐字节不变。但**当前最大绝对偏差在 `target_speed_mps`（0.9445 m/s）**，而它不在 top-3 里。
建议 A2 的敏感层排序把**物理量纲**（速度 m/s、计划内数值）纳入评分，而不只用 head 漂移分——
否则"最该恢复的层"会被漏掉。这条是 B3 能给出的、最直接可执行的反馈。

## 3. A2 的 OpenExplorer 输入 pre-check（`08`–`10`）

用包里 **原封不动的** `student_j6p_oe391.yaml` + 1200 个校准 NPY，在
`openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`（`hb_compile 3.5.16` / `HBDK 4.11.11`）里运行：

| 项 | 值 |
|---|---|
| 结果 | **成功**，2m09s，0 warning / 0 error |
| 算子落点 | **59/59 节点全在 BPU**，`cpu_fallback_nodes = 0` → **无 CPU fallback** |
| 校准 | 4 输入各 300 例，全部读取成功 |
| 产物 | `student_v0_j6p.hbm` 23,579,816 B；`.bc` 23,179,259 B |
| 内存口径 | input 603,136 / output 2,560 / static 23,579,816 / dynamic 605,696 / temporary 0，**min requirement 24,185,512 B** |

**口径声明（必须随数字引用）**：这是 **`BPU_ESTIMATED` 类**的工作站工具链预检——算子落点、fallback、
内存来自 X86 上的 `hb_compile`，**不是 J6P 实测、也不是板端时延估计**。
A4 仍负责正式的 `artifacts/a4/<runtime_id>/`（含 `bpu_performance_estimate.json` 与 `estimation_method.md`），
届时由 B3 的 `bpu-verify` 逐项核验。

### 3.1 编译后的 BPU 产物是否仍等价于 A2 的 INT8 模型？（`11`–`13`）

这是此前**没人验过**的一环：A2 只报了 ORT QDQ 的漂移，A4 还没回传编译结果，所以
"编译成 nash-p 产物之后，模型还是不是那个 INT8 模型"没有数据。B3 用刚编出的
`student_v0_j6p_quantized_model.bc` 对 A2 的 `models/student_int8.onnx` 逐例 `hb_verifier`：

| 输出头 | min | p50 | 低于 0.999 |
|---|---:|---:|---:|
| `plan_length_logits` | 0.9999 | 1.0000 | 0 |
| `behavior_logits` | 0.9997 | 0.9998 | 0 |
| `target_pointer_logits` | 0.9998 | 0.9999 | 0 |
| `target_lane_logits` | 0.9998 | 0.9999 | 0 |
| `target_speed_mps` | 0.9997 | 0.9999 | 0 |
| `completion_type_logits` | 0.9997 | 0.9998 | 0 |
| `on_failure_logits` | 0.9998 | 0.9999 | 0 |
| `confidence` / `requires_confirmation_logits` / `replan_condition_logits` | 1.0000 | 1.0000 | 0 |

骨干 6 个中间张量最差 min 0.9968。**29/29 例次全部通过，十头 min ≥ 0.9997**——
说明"编译到 nash-p"这一步**没有引入超出 INT8 量化本身的额外失真**：
目前模型侧的误差主要来自 FP32→INT8（§2），而不是 BPU 编译。
口径仍是 `BPU_ESTIMATED`（X86 仿真的数值等价性），**不是板端时延或精度结论**。

### 3.2 全队列 X86 仿真矩阵（`14`）

把上面的检查扩到**所有留出队列**（6 个队列、**850 例次**），产物仍是 A2 YAML 编出的
`student_v0_j6p_quantized_model.bc`，参考仍是 A2 的 `models/student_int8.onnx`：

| 队列 | 例次 | 最差头（min） | 骨干最差 | 低于 0.99 |
|---|---:|---|---:|---:|
| `d2_v1_1_val` | 539 | behavior_logits 0.9991 | 0.9945 | 0 |
| `gap300_val` | 123 | target_speed_mps 0.9996 | 0.9961 | 0 |
| `targeted_gap_val` | 99 | behavior_logits 0.9995 | 0.9955 | 0 |
| `d3_wave2_val` | 56 | completion_type 0.9996 | 0.9923 | 0 |
| `turn_gap_val` | 29 | behavior_logits 0.9997 | 0.9968 | 0 |
| `ms34_val` | 4 | behavior_logits 0.9996 | 0.9922 | 0 |
| **合计** | **850** | **全局最低 0.999125** | 0.9922 | **0** |

**850/850 通过、零失败**：编译到 nash-p 的产物在所有队列上都与 INT8 模型保持一致。

### 3.3 量化损失（FP32 → INT8）也做了全队列覆盖（`15`/`16`/`20`）

另一个轴是"量化本身损失多少"。逐头统计（FP32 ONNX ↔ INT8 ONNX）：

| 队列 | 例次 | 速度头 max\|Δ\| | 该队列最差头 max\|Δ\| | 头余弦 min |
|---|---:|---:|---|---:|
| `d2_v1_1_val` | 539 | **1.3128 m/s** | target_speed_mps | 0.9994 |
| `targeted_gap_val` | 99 | **1.4071 m/s** | target_speed_mps | 0.9996 |
| `gap300_val` | 123 | 1.3799 m/s | target_speed_mps | 0.9996 |
| `turn_gap_val` | 29 | 0.9445 m/s | target_speed_mps | 0.9998 |
| `d3_wave2_val` | 56 | 0.9255 m/s | target_speed_mps | 0.9998 |
| `ms34_val` | 4 | 0.5150 m/s | target_speed_mps | 0.9999 |

**`target_speed_mps` 在全部 6 个队列里都是最大绝对偏差的头**（0.52–1.41 m/s）——
这独立复现并强化了 §2 的建议（敏感层排序应纳入物理量纲）。

但**原始张量的容差失败不代表计划会变**：解码级对比（`consistency --adapter onnx`）在四个队列上
**合计 747 例、结构失配 0 例**（d2 0/539、gap300 0/123、d3_wave2 0/56、turn-gap 0/29）——
行为序列、目标 id、完成类型**从未因 INT8 而改变**；差异只体现在数值字段。
（注：对"整张量取 argmax"的粗略指标会显示部分离散头有翻转，但解码器并不受影响，
所以那种指标不能单独用来判断行为是否变化。）

## 文件

| 文件 | 内容 |
|---|---|
| `00_package_check.log` / `01_package_check.json` | 包完整性核验（1217 文件、声明的摘要、校准绑定、绑定告警） |
| `02_consistency_full_int8_turn.json` / `03_…mixed_top3…` | 原始张量级对比（默认浮点容差，仅作参考） |
| `04_plan_level_full_int8_turn.json` / `05_…mixed_top3…` | 计划级对比（结构 vs 数值分开） |
| `06_plan_level_summary.json` | 结构一致率与数值偏差汇总 |
| `07_per_head_int8_drift.json` | 逐头最大绝对偏差：full vs mixed_top3 |
| `08_oe_precheck.log` | A2 YAML 在 OE 3.9.1 的编译预检日志（节选） |
| `09_node_placement.csv` | 59 个节点的落点（全部 BPU） |
| `10_oe_precheck_summary.json` | 预检机读摘要（落点、产物、内存、口径） |
| `11_bpuc_vs_int8onnx_summary.json` | 编译后 `.bc` 对 A2 INT8 ONNX 的逐头余弦分布（29 例） |
| `12_bpuc_vs_int8onnx_single_case.log` | 单例的 16 行逐层/逐头余弦明细 |
| `13_bpuc_vs_int8onnx_reading.json` | 该检查的问题、设置、结果与口径 |
| `14_x86_matrix_summary.json` | **全队列 X86 仿真矩阵**（6 队列 × 850 例次，逐头 min/p50、全局最低） |
| `15_quantisation_loss_matrix.json` / `16_quantisation_loss_discrete.json` | FP32↔INT8 逐头最大偏差与离散头 argmax 一致率（全队列） |
| `17`–`19_planlevel_int8_*.json` | 解码级计划对比（d3w2 / gap300 / d2） |
| `20_planlevel_summary.json` | 解码级汇总：**747 例、结构失配 0** |
