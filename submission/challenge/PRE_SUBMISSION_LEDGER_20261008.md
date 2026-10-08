# 挑战赛道预提交总台账（2026-10-08）

## 总结论

当前可以冻结和打包的是**唯一候选 RC 与全部已有证据**，不是可提交的 Final。
V3 在 240 条 B1 Independent Validation v1 上的一次性阈值投影为 `FAIL`，因此
FP32 Gate 不能签发，INT8、A4 Final Runtime、B3 J6P 和 B4 Final 包都不能越过该门禁。

冻结状态见 `RC_V3_FREEZE_20261008.json`，完整指标见
`V3_INDEPENDENT_DIAGNOSTIC_20261008.md`。

## 唯一候选身份

| 项目 | 冻结值 | 状态 |
|---|---|---|
| A3 release | `a3_b1_closeout_robust_fp32_candidate_v3` | 唯一候选 |
| FP32 weights SHA256 | `7f379c78...6e805` | `PENDING_A3_FP32_GATE` |
| A2 FP32 ONNX SHA256 | `681a5d4b...b4286` | 诊断候选 |
| A2 Full INT8 SHA256 | `275dce5c...836c3` | `DIAGNOSTIC_ONLY` |
| A2 Mixed Top-3 SHA256 | `9a08a03c...132d3` | `DIAGNOSTIC_ONLY` |
| B1 Independent Validation | 240 samples / 240 groups | `FROZEN` |
| FP32 阈值投影 | `FAIL` | 不允许升级 Final |

## 新增的实测事实

- 240/240 条 Student 推理成功，schema validity = 1.0；
- safety-critical behavior recall = 1.0000，达到当前零下降阈值；
- behavior accuracy = 0.942748，下降 5.73%；
- target pointer accuracy = 0.984733，下降 1.5267%，略超 1.5% 阈值；
- target lane accuracy = 0.171756，下降 82.82%；
- completion accuracy = 0.927481，下降 7.25%；
- plan sequence accuracy = 0.108333，下降 89.17%。

B3 已补交本机 Teacher 路线 A 的否证实测：RTX 4060 Laptop 8 GB 上
Qwen2.5-VL-3B FP16 单次完整计划生成耗时 42.3–58.2 s，严格解析 0/4 通过，
无法满足 12–15 s TTL。该证据排除了当前笔记本直接复跑完整 Teacher 的路线，
但没有消除既有 Teacher/Student 对比的跨机器注脚。

低 lane/sequence 结果与 B3 850 例已报告的字段约定差异相符：Teacher 常对
`KEEP_LANE/STOP` 填 `CURRENT`，Student Adapter 按设计留空。这可解释部分差距，
但不能在已查看独立集结果后直接改 Adapter 并把同一集合当作独立重测。

已增加不覆盖原结果的字段语义归一化诊断：仅把非 lane-critical 行为中的 Student
`target_lane=null` 在评分副本中映射为 `CURRENT`，共调整 204 步/201 样本。
target lane 从 17.1756% 升至 **89.3130%**，plan sequence 从 10.8333% 升至
**86.6667%**，分别恢复 189 个 step 和 182 个完整 plan。这证明表示差异是主要因素，
但归一化结果仍低于 98.5% 门槛，且 behavior/completion 仍失败，所以总投影仍为 FAIL。

## A1–B4 全员当前交付

| 角色 | 已有产物 | 当前结论 | Final 前还缺 |
|---|---|---|---|
| A1 | `A1_正式模型与FLOPs交接_20261008/` | Student 0.498640896 GFLOPs；Teacher 固定样例 892.929605632 GFLOPs | 团队/评审认可原始模型与计数范围 |
| B1 | closeout、Calibration v1、Independent Validation v1、泄漏检查 | 数据治理完整；历史 template lineage 不可恢复 | 新建 template-valid 未暴露独立集，不能伪造旧 `template_id` |
| A3 | robust v3 权重、训练证据和 handoff | V3 候选已冻结，本轮阈值投影 FAIL | 只用 Train/Dev 产生新版本；不得用已暴露 240 标签调参 |
| B2 | 评估/Gate 工具与 fail-closed 逻辑 | 无正式 decision | 冻结新基准与 policy，由独立负责人评估新候选 |
| A2 | FP32 ONNX、Full INT8、Mixed Top-3、300 组/1200 NPY、B2/A4 ZIP、字段语义归一化诊断 | 表示差异已量化，但归一化后仍 FAIL；不能签 INT8 PASS | 先由 B2 预先冻结等价规则并获得新候选 FP32 PASS，再重建并冻结正式 INT8 |
| A4 | OpenExplorer 预编译证据 | 59/59 BPU、0 fallback，0.615 ms 为估算 | 绑定 A2 exact ONNX/INT8 的 `.hbm/.bc`、Runtime、fallback 和环境证据 |
| B3 | 850 例衰减、83 场景学生闭环、BPU 估算、X86 证据、本机 Teacher 路线 A 否证 | 诊断证据已齐；完整 Teacher 本机复跑不可行；不是最终 J6P | exact Final RC 的 X86 重跑和 J6P latency/memory/stability/utilization；如需同机 Teacher，另走受约束单 token 路线并声明口径差异 |
| B4 | 规范和预提交目录 | `BLOCKED_NOT_FINAL` | Gate 链、Docker、干净复现、技术报告、演示视频、最终 manifest |

## 当前可直接发送的外置文件

| 接收方 | 文件 | SHA256 | 用途/限制 |
|---|---|---|---|
| B2 | `artifacts/a2/handoff_20261007_3ebd0682/A2_to_B2_evaluation_3ebd0682.zip` | `95e05330...a59f` | A2 模型与量化证据；旧包，不含本次独立集回放 |
| A4 | `artifacts/a2/handoff_20261007_3ebd0682/PRE_GATE_ONLY_A2_to_A4_openexplorer_3ebd0682.zip` | `543a2ee2...3918` | 1200 NPY 与预门禁模型；必须保留 `PRE_GATE_ONLY` |
| 团队/B2 | `artifacts/b2_role_exception_v3_20261008_final/` | report `8e155001...6dae` | 240 条一次性诊断原始 predictions；不是 B2 签发 |
| 团队/B2 | `artifacts/b2_role_exception_v3_20261008_semantic_normalized/` | 见目录 `SHA256SUMS` | `null/CURRENT` 字段对齐诊断；不覆盖严格结果，不是 B2 签发 |

预提交综合包另生成在 `artifacts/submission/`，其中会包含代码/证据索引和小型
报告，大模型、NPY、`.hbm/.bc`、Docker 和视频通过外置哈希发送。

## 现在不存在于本工作区的关键原件

- B3 报告所述 SHA 对应的实体 `.bc` 和 `.hbm`；
- A4 最终可运行 Runtime/工程包与完整 OpenExplorer 原始输出；
- J6P 实板时延、内存、稳定性和异构利用率原始记录；
- Bench2Drive 复现记录；
- 真实语音→ASR/NLU→Student→CARLA 最终 RC 全链路录制/工程包；
- 可消除跨机器注脚的同机 Teacher/Student 正式复现；当前完整计划 Teacher 路线已实测不可行；
- 最终 Student/J6P Docker archive、干净环境复现记录、技术报告 PDF 和演示视频。

## 冻结规则

1. 保留 V3 作为当前唯一可追溯候选，不把它改名为 Final。
2. 不修改本次诊断结果，不用 240 条标签做调参。
3. 新模型必须新建版本和全套 SHA，由 B2 在新的未暴露基准上独立签发。
4. 只有 FP32→INT8→A4/B3→B4 同一 RC 门禁链全部通过，才能生成
   `RELEASE_MANIFEST.json` 和 `FINAL_SUBMISSION`。
