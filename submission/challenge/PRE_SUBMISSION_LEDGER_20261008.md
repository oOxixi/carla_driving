# 挑战赛道预提交总台账（2026-10-08）

## 总结论

当前可以冻结和打包的是**V3 权重/ONNX + Adapter V3.1 复合候选与全部已有证据**，
不是可提交的 Final。原始 V3 严格回放为 `FAIL`；落地固定语义合同后的 V3.1 在同一
240 条上的回归投影为 `PASS`，Full/Mixed INT8 也通过投影。但这次修订发生在旧集合
结果已暴露之后，不能由 A2 自签正式 Gate，仍需 B2 用新的未暴露集合独立复核。

最新补充结果：新的 240 槽 Seen/Variant/Unseen 采集设计和 policy 已在模型运行前冻结，
但尚未在 CARLA + 精确 Teacher v4 上采集；另有 308 条 sample/group/RGB/seed 均未被
候选使用的 Seen 硬负样本压测，308/308 推理成功但严格阈值投影为 **FAIL**。因此当前
候选仍为 `BLOCKED_NOT_FINAL`，不能用旧 240 条 post-hoc PASS 覆盖新失败证据。

冻结状态见 `RC_V3_FREEZE_20261008.json`，完整指标见
`V3_INDEPENDENT_DIAGNOSTIC_20261008.md`；V3.1 实现和结果见
`V3_1_ADAPTER_INT8_POSTHOC_20261008.md`；A2 代理执行的 B2 全套合同测试与真实
回放审计见 `B2_PROXY_EVALUATION_V3_1_20261008.md`。

## 唯一候选身份

| 项目 | 冻结值 | 状态 |
|---|---|---|
| A3 release | `a3_b1_closeout_robust_fp32_candidate_v3` | 唯一候选 |
| FP32 weights SHA256 | `7f379c78...6e805` | `PENDING_A3_FP32_GATE` |
| A2 FP32 ONNX SHA256 | `681a5d4b...b4286` | 诊断候选 |
| Adapter contract | `student-plan-adapter-v3.1-semantic-contract` | 已实现；308 条候选未暴露 Seen 压测 FAIL，待新三队列正式复核 |
| A2 Full INT8 SHA256 | `275dce5c...836c3` | `DIAGNOSTIC_ONLY` |
| A2 Mixed Top-3 SHA256 | `9a08a03c...132d3` | 下一轮 Gate 首选，仍为 `DIAGNOSTIC_ONLY` |
| B1 Independent Validation | 240 samples / 240 groups | `FROZEN` |
| 原始 V3 / V3.1 回归投影 | `FAIL` / `PASS` | 后者为 post-hoc，不允许直接升级 Final |

## 新增的实测事实

- 新 prospective freeze：Seen/Variant/Unseen 各 80，共 240 个固定槽；240 个唯一 seed，
  240/240 场景 schema-valid；与 7,735 条历史治理数据 seed/场景 ID 重叠为 0；
- 新 308 条 Seen 压测：sample/group/RGB/seed 重叠均为 0，scenario 16/16、文本 15/15
  已见；308/308 推理成功；两次 predictions 逐字节一致；
- 新 308 条严格指标：behavior 0.921512、pointer 1.000000、lane 0.816860、completion
  0.921512、sequence 0.795455、安全召回 1.000000，投影 **FAIL**；
- 63 条 Gate 字段差异全部集中在 36 条避障 lane 表达和 27 条阻挡变道 STOP 安全收紧；
  它们均来自以安全接管终止的硬负样本，不能结果后删样本或改分。

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

随后把固定规则真正实现为 Adapter V3.1，而不是继续对评分结果做后处理，并补齐了转弯
方向约束、路口前 FSM 等待、避障车道存在性、SLOW_DOWN 指针/completion 与不安全换道
fail-closed 测试。干净提交 `2900258a` 上重跑 240 条：behavior/lane/completion 均
260/262，pointer 262/262，完整计划 238/240，安全召回 28/28，阈值投影为 **PASS**。
仅余两条 `left_gap_safe=false` 的换道样本，Student 安全地输出 STOP。

同一 Adapter 下 Full INT8 与 Mixed Top-3 均 240/240 成功，Teacher 指标与 FP32 相同，
且相对 FP32 的 behavior/pointer/lane/completion/完整计划核心字段全部 100% 一致；109 个
带速度目标步骤的绝对差为 mean 0.150893、P95 0.395727、max 0.597761 m/s。两份 INT8
在本集合上的解码 predictions 字节相同。依据此前 Calibration v1 的无标签逐 Head 漂移，
Mixed Top-3 以约 1.50% 体积代价降低三个离散头误差，故作为下一轮未暴露 Gate 首选；
Full INT8 保留为体积优先备选。

## A1–B4 全员当前交付

| 角色 | 已有产物 | 当前结论 | Final 前还缺 |
|---|---|---|---|
| A1 | `A1_正式模型与FLOPs交接_20261008/` | Student 0.498640896 GFLOPs；Teacher 固定样例 892.929605632 GFLOPs | 团队/评审认可原始模型与计数范围 |
| B1 | closeout、Calibration v1、Independent Validation v1、泄漏检查 | 数据治理完整；历史 template lineage 不可恢复 | 新建 template-valid 未暴露独立集，不能伪造旧 `template_id` |
| A3 | robust v3 权重、训练证据和 handoff | 权重继续冻结；Adapter V3.1 复合候选旧集投影 PASS | 确认复合候选身份；如未暴露集失败，只能用 Train/Dev 产生新版本 |
| B2 | 评估/Gate 工具与 fail-closed 逻辑；A2 代理完成 197 项合同测试、240 条历史复跑、240 槽新冻结和 308 条 Seen 压测 | 新 policy/采集槽已冻结；308 条压力投影 FAIL；正式 decision 仍阻塞 | 在 CARLA + 精确 Teacher v4 上采集冻结 240 槽，关闭 case manifest/digest 后一次性评估 exact weights+ONNX+Adapter |
| A2 | FP32 ONNX、Full/Mixed INT8、1200 NPY、Adapter V3.1、三方回放证据 | FP32/两份 INT8 旧集投影均 PASS；Mixed 为下一轮首选；不能自签 Gate | B2 未暴露 FP32 PASS 后签正式 INT8 manifest，再由 B2 签 INT8 decision |
| A4 | OpenExplorer 预编译证据 | 59/59 BPU、0 fallback，0.615 ms 为估算 | 绑定 A2 exact ONNX/INT8 的 `.hbm/.bc`、Runtime、fallback 和环境证据 |
| B3 | 850 例衰减、83 场景学生闭环、BPU 估算、X86 证据、本机 Teacher 路线 A 否证 | 诊断证据已齐；完整 Teacher 本机复跑不可行；不是最终 J6P | exact Final RC 的 X86 重跑和 J6P latency/memory/stability/utilization；如需同机 Teacher，另走受约束单 token 路线并声明口径差异 |
| B4 | 规范和预提交目录 | `BLOCKED_NOT_FINAL` | Gate 链、Docker、干净复现、技术报告、演示视频、最终 manifest |

## 当前可直接发送的外置文件

| 接收方 | 文件 | SHA256 | 用途/限制 |
|---|---|---|---|
| A3 | `artifacts/a2/handoff_20261008_v31_a2354507/A2_to_A3_gate_feedback_a2354507.zip` | `30474422...793ac` | Adapter V3.1 与 FP32/INT8 post-hoc 反馈；非正式 Gate |
| B2 | `artifacts/a2/handoff_20261008_v31_a2354507/A2_to_B2_evaluation_a2354507.zip` | `7c531ba8...ace5f` | 当前完整评估包：weights、FP32、两份 INT8、Adapter 和三方 raw predictions |
| A4 | `artifacts/a2/handoff_20261008_v31_a2354507/PRE_GATE_ONLY_A2_to_A4_openexplorer_a2354507.zip` | `ebe7626d...03c7d` | 当前 1200 NPY/模型/Adapter 预门禁包；必须保留 `PRE_GATE_ONLY` |
| B2（历史） | `artifacts/a2/handoff_20261007_3ebd0682/A2_to_B2_evaluation_3ebd0682.zip` | `95e05330...a59f` | 旧包，不含 Adapter V3.1 回放，已被上行当前包替代 |
| A4（历史） | `artifacts/a2/handoff_20261007_3ebd0682/PRE_GATE_ONLY_A2_to_A4_openexplorer_3ebd0682.zip` | `543a2ee2...3918` | 旧预门禁包，已被上行当前包替代 |
| 团队/B2 | `artifacts/b2_role_exception_v3_20261008_final/` | report `8e155001...6dae` | 240 条一次性诊断原始 predictions；不是 B2 签发 |
| 团队/B2 | `artifacts/b2_role_exception_v3_20261008_semantic_normalized/` | 见目录 `SHA256SUMS` | `null/CURRENT` 字段对齐诊断；不覆盖严格结果，不是 B2 签发 |
| 团队/B2 | `artifacts/b2_role_exception_v3_1_adapter_20261008_final/` | report `bb9a2e5a...72585` | Adapter V3.1 FP32 实际回放；旧集 PASS 投影，非正式 Gate |
| 团队/B2 | `artifacts/b2_role_exception_v3_1_full_int8_20261008_final/` | report `d970ffb8...b36931` | Full INT8 与 Teacher/FP32 三方诊断；非正式 Gate |
| 团队/B2 | `artifacts/b2_role_exception_v3_1_mixed_int8_20261008_final/` | report `4326f032...141e4b` | Mixed Top-3 三方诊断；下一轮 Gate 首选，非正式 Gate |
| 团队/B2/B4 | `artifacts/submission/B2_PROXY_AUDIT_V3_1_20261008.zip` | `9d197547...ab9a5` | 184 项 B2 测试、240 条复跑、Gate 投影、readiness、切片与差异证据；`A2_ASSISTED_B2_PROXY`，非正式签发 |
| CARLA/Teacher v4 采集方 | `artifacts/submission/B2_PROSPECTIVE_BENCHMARK_FREEZE_V1_20261008.zip` | `a84c6613...4f778` | 240 槽新基准、policy、场景、排除边界和生成器；等待正式采集 |
| 团队/B2/B4 | `artifacts/submission/B2_CANDIDATE_UNEXPOSED_SEEN_STRESS_V1_20261008.zip` | `bce32f1d...f1339` | 308 条两次原始预测、FAIL 指标、差异审计、JUnit 和确定性证明；Seen 硬负压力证据，非正式 Gate |

预提交综合包已生成在 `artifacts/submission/`：

- `CHALLENGE_RC_V3_1_ADAPTER_EVIDENCE_20261008.zip`，SHA256
  `d16c902d986818a91f4ed86e80fd3345981e0884d63d73ab860ac5f1a7ebfce6`，115 个文件，
  ZIP CRC 与逐文件 SHA256 均 PASS；
- `CHALLENGE_SOURCE_RUNTIME_PREVIEW_V3_1_20261008.zip`，SHA256
  `0c0439fcd475d09153903742f9d9512acbf97a360ad12668ed1a51b97c234ed4`，610 个文件，
  ZIP CRC 与逐文件 SHA256 均 PASS。

大模型、1200 NPY、`.hbm/.bc`、Docker 和视频不放入小型综合包；其中现有模型/NPY 已由
上表 A3/B2/A4 收件人专用 ZIP 及 SHA256 外置交付。

## 现在不存在于本工作区的关键原件

- B3 报告所述 SHA 对应的实体 `.bc` 和 `.hbm`；
- A4 最终可运行 Runtime/工程包与完整 OpenExplorer 原始输出；
- J6P 实板时延、内存、稳定性和异构利用率原始记录；
- Bench2Drive 复现记录；
- 真实语音→ASR/NLU→Student→CARLA 最终 RC 全链路录制/工程包；
- 可消除跨机器注脚的同机 Teacher/Student 正式复现；当前完整计划 Teacher 路线已实测不可行；
- 新 240 槽在 CARLA + 精确 Teacher v4 上的实际采集、RGB、case manifest 和 case-set digest；
- 最终 Student/J6P Docker archive、干净环境复现记录、技术报告 PDF 和演示视频。

## 冻结规则

1. 保留 V3 weights/ONNX + Adapter V3.1 作为当前唯一可追溯复合候选，不改名为 Final。
2. 原始 FAIL、字段归一化 FAIL 和 V3.1 post-hoc PASS 三组结果并列保留，不覆盖历史证据，
   不再用 240 条标签做训练、校准或逐错调参。
3. 任何模型/Adapter 变化必须新建版本和全套 SHA，由 B2 在新的未暴露基准上独立签发。
4. 只有 FP32→INT8→A4/B3→B4 同一 RC 门禁链全部通过，才能生成
   `RELEASE_MANIFEST.json` 和 `FINAL_SUBMISSION`。
