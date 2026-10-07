# 新候选 v3（robust closeout）仿真复测（2026-10-07）

> ⚠️ 门禁仍是 `PENDING_A3_FP32_GATE` / `PENDING_B2_INDEPENDENT_VALIDATION`，
> 跑在 X86（官方镜像）上，无板卡。所有结论 `DIAGNOSTIC_ONLY`，**不是精度或达标结论**。

## 0. 这一轮测的是"新模型"

`challenge` 新增 6 个提交，其中 A3 发布 **`a3_b1_closeout_robust_fp32_candidate_v3`**：

| 项 | v1（10-02） | v2（10-02 晚） | **v3（本次）** |
|---|---|---|---|
| 权重 sha256 | `eaee4402…` | `6b6ec1d8…` | **`7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`** |
| 训练视图 | 累计视图 | governed closeout | governed closeout（robust） |
| train / dev | 5826 / 1104 | 5856 / 1108 | 5856 / 1108 |
| 门禁 | PENDING | PENDING | PENDING |

包校验 **PASS**（9 文件、权重摘要与 `candidate_identity` 一致）。

同时 A2 在 10-06 更新了交接说明（`challenge/quantization/A2_HANDOFF_UPDATE_20261006.md`）：
由于没有 `A3_FP32_GATE_PASSED`，他们的三份包（A3/B2/A4）仍是 **PRE_GATE_ONLY**；
并记录了 B1 的"历史模板身份不可恢复"证明，B2 的 contract 对此是
`FAIL_CLOSED_IF_TEMPLATE_IDENTITY_MISSING`——也就是说**核心指标衰减这一项的阻塞原因已变成可校验证据**，
但 Gate 仍未通过。

## 1. 行为复测：v1 / v2 / v3 对照（真实权重，留出队列，各 3 轮）

| 队列 | 例次 | v1 | v2 | **v3** |
|---|---:|---:|---:|---:|
| D3 Wave2 val | 168 | 1.0000 | — | **1.0000** |
| D2 v1.1 val | 1617 | 0.9518 | — | **0.9518** |
| **targeted-gap val** | 297 | 0.9192 | — | **1.0000** ⬆ |
| gap300 val | 369 | — | 0.7073 | **0.7073** |
| turn-gap val | 87 | 0.6897 | 0.6897 | **0.6897** |
| ms34 val | 12 | 0.3333 | 0.7083 | **0.7083** |

**结论**：v3 的"robust"训练在 **targeted-gap 上从 0.9192 提升到 1.0000**（该队列此前是缺口），
其余队列与 v2 持平。**`TURN_LEFT` 依旧从不产出**——v3 在 turn-gap 27/27、gap300 108/108 上
仍把 TURN_LEFT 答成 `SLOW_DOWN`（v1 是 `SET_SPEED`，v2/v3 是 `SLOW_DOWN`）。
这已经是**连续三个候选**同一个缺口，建议把"转弯族补数与训练目标"列为最高优先级。

（`ms34` 的多步：v3 与 v2 相同——能出全长 3/4 步序列，但**最后一步错**：
teacher 的 `KEEP_LANE` 被答成 `RETURN_TO_LANE` 或 `YIELD`。）

## 2. v3 的数值仿真：FP32 ↔ 编译后的 BPU 产物（6 队列 850 例）

流程：用仓库导出器（**已合并且支持 `--weights`**）导出 v3 的 FP32 ONNX
（sha256 `b76b5a32dfde16d52b34ad553bce9e899eaf4220142a8ddd6e9b4aea4fc808e5`）→
在官方镜像里用 **A2 的 1200 个校准张量**编译（`cal_config_v3.yaml`）→
对全部 6 个留出队列逐例 `hb_verifier`（FP32 ONNX ↔ 编译产物 `.bc`）。

| 队列 | 例次 | 离散头 min | 速度头 min | 骨干最差 |
|---|---:|---:|---:|---:|
| d2_v1_1_val | 539 | 0.9999 | **0.9991** | 0.9958 |
| gap300_val | 123 | 0.9999 | 0.9996 | 0.9965 |
| targeted_gap_val | 99 | 0.9999 | 0.9995 | 0.9958 |
| d3_wave2_val | 56 | 1.0000 | 0.9996 | 0.9947 |
| turn_gap_val | 29 | 1.0000 | 0.9998 | 0.9967 |
| ms34_val | 4 | 1.0000 | 0.9997 | 0.9960 |
| **合计** | **850** | — | — | 0.9947 |

**十头全局最低余弦 0.999134，低于 0.99 的观测为 0。**
注意口径：v1 那一轮的矩阵参考是 **INT8 ONNX**（只测"编译保真度"），
本轮的参考是 **FP32 ONNX**（把量化损失与编译损失合并测量），
即便如此 v3 的离散头仍全部 ≥0.9999——说明 v3 的预测轨迹对量化**更稳**。

## 3. v3 的 OpenExplorer 编译预检

| 项 | 值 |
|---|---|
| 结果 | 成功，`nash-p`，0 error |
| 算子落点 | **59/59 节点全在 BPU，零 CPU fallback** |
| 产物 | `.hbm` 23,579,544 B；`.bc` 23,179,197 B |
| 内存 | input 603,136 / output 2,560 / static 23,579,544 / dynamic 605,696，**min requirement 24,185,240 B** |

口径：`BPU_ESTIMATED`（工作站工具链预检），不是板端性能。

## 文件

| 文件 | 内容 |
|---|---|
| `00_handoff_integrity.log` / `01_handoff_integrity_compact.json` | v3 包独立校验（PASS） |
| `02_behaviour_replay_v3.json` | v1/v2/v3 行为复测与 teacher→student 混淆矩阵 |
| `03_matrix_summary_v3.json` | 6 队列 × 850 例的逐头余弦矩阵 |
| `04_oe_compile_v3.log` | v3 编译预检日志（节选） |
| `05_node_placement_v3.csv` | 59 个节点落点（全部 BPU） |
| `06_flops_crosscheck_and_modality_ablation.json` | FLOPs 独立复算 + 多模态消融（见下） |

## 4. 追加：评分口径相关的两项可测数据（2026-10-07）

### 4.1 FLOPs：B3 独立复算与仓库报告**完全一致**

用仓库的 `challenge/export/compute_flops.py` 在干净检出上重跑，7 个关键字段
（参数 23,006,581、MACs 249,320,448、FLOPs 498,640,896、教师下界参数/FLOPs、
比值 0.1769125802176339、`ratio_pass=true`）与 `challenge/flops_report.json` **逐项相同**。
说明：同一工具重跑只能证明**可复现**，不构成方法独立；**分母定义仍需团队确认**。

### 4.2 多模态融合有效性：消融实验（v3，D2 val 150 例）

做法：把四个输入之一**置零**，走同一解码器（`StudentPlanAdapter`），与全输入基线比较。

| 置零的输入 | 最差头余弦（min） | 行为 logits 平均最大偏差 | 相对变化（均值） | 行为 argmax 翻转 |
|---|---:|---:|---:|---:|
| **`state`** | **0.4654** | **8.0242** | **71.6%** | **122/150** |
| `targets` | 0.9544 | 0.8701 | 9.8% | 0/150 |
| `rgb` | 0.9637 | 0.5026 | 4.1% | 0/150 |
| `text_tokens` | 0.9930 | 0.3467 | 3.3% | 0/150 |

**读法（重要，含口径限制）**：去掉 `state` 会让模型剧烈变化；而去掉 **rgb / text / targets**
只让 logits 轻微变化，且**从不改变解码后的行为**。也就是说：**这一版候选的计划几乎完全由
state 主导**，视觉、语言、目标三路在决策层面的贡献很小。

⚠️ 口径限制：置零 ≠ 移除证据（全黑图仍是图，零 token 仍是 token 序列），
该数字衡量的是"把某模态替换为其零值后的敏感性"，不是严格的意义上的模态贡献度；
且这是 X86 数值诊断，不是精度结论。这项数据对应评分细则里"多模态信息融合有效性"，
建议 A1/A3 复核（若正式评测也呈现同样形态，"VLA 多模态联合压缩"的创新性叙事会被质疑）。

### 4.3 模糊指令安全策略（代理数据）

异常输入套件 10 例：**9/10 与预期一致**，唯一不符是
`empty_source_text`（预期 `MUST_FAIL_CLOSED`，实际产出了计划）。是否算 Gate 失败由 B2 判定
（套件自带的 `policy_note` 已写明）。
