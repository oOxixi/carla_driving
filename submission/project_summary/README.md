# 项目汇报与证据索引 · 2026-11-19

我们完成了 CARLA 多模态驾驶闭环，以及 Qwen Teacher → 轻量 Student 的结构化规划蒸馏与仿真复核。正式运行入口保持不变；语义 LoRA、辅助目标融合与旧量化实验作为独立交付，不替换已经复核的运行链。

## 汇报可引用的实测

| 范围 | 可引用结果 | 不代表什么 |
| --- | --- | --- |
| [Teacher / Student FP32，项目固定 83 场](../../challenge/distillation/CARLA83_FP32_HANDOFF.md)，作业 38 | [166/166 次有效判定](closure/carla83_paired_report.json)；分别通过 76/83、74/83。按基础/进阶/挑战 30/40/30 加权为 **92.17% / 90.83%**，FP32 相对衰减 **1.4467%**，在本矩阵的 3% 线内；双方碰撞、闯红灯、严重路线偏离均为 0 | 不是盲测、官方长里程、INT8、实板或语音效果 |
| [额外四场闭环与计分合同](../../scenarios/development/CARLA83_NEW_VALIDATION.md)，作业 39/40 | Teacher **4/4**、FP32 Student **2/4**，零碰撞、零闯红灯；Student 1 次严重路线偏离。[同次日志归因](../../challenge/distillation/CARLA_GENERALIZATION_HANDOFF_20261116.md)表明：一例是多步解码掩码把设速替换成额外停车；一例已理解回道，但间隙守卫导致停滞超时 | 不与原 83 场相加计算衰减，不能据此把问题统归于量化或蒸馏 |
| [干净语音 ASR 主模型](voice/asr_clean_250_primary_only.md)，11 月 13 日 UTC | 五语言各 50 条，实际音频 250 条。逐句完全匹配 **95.60%**，字符 **99.24%**，意图 **99.60%**，槽位 **99.20%**；端到端 P95 **105.17 ms** | 不代表 2,598 条扩充版、带噪、车控闭环或 ONNX 快路径 |
| [扩充音频配套的文本回归](voice/GROUP1_TASK5_6_SUMMARY.md) | clean / noisy 各 **2,598** 条 reference text，意图 **99.54% / 99.54%**；[ONNX 快路径 clean 50 条](voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.md)和[带噪 50 条](voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.md)实际音频的 ASR 逐句仅 **4% / 4%**、意图 **76% / 78%**、槽位 **36% / 38%** | 文本回归不证明扩充音频的识别准确率；没找到同口径全量音频实测，样本的 50 dBA 来源说明不等于现场声学标定 |
| [Qwen 2B 文本语义 LoRA V14 / V15](../../experiments/semantic_sft/V15_RECAP_20261109.md) | 306 Train / 75 Dev 固定对照，第 6 轮语义全字段 **53/75（70.67%）/ 51/75（68.00%）**，动作顺序 **73/75 / 71/75**；V15 未晋级，保留 V14 内部候选。[额外三场跟车对照](../../experiments/server_sensor_20261117/runs/lora_compare_20261116/README.md)两边 **0/3** | 不是 Student 蒸馏分数、不是独立语义 Gate，不能宣称改善视觉识别 |
| [感知与三维目标诊断](../../experiments/server_sensor_20261117/README.md) | 留出 **21 帧、35 个目标机会**；原阈值 YOLO 匹配 **10/35**，基线定位 **1/35**，三个阶段定位候选各 **4/35**（未验证）；辅助通道新增 9 个候选，**0/9** 达到可信三维/FOLLOW 条件 | 不是生产检测召回率；没有把低置信候选接到车辆执行 |

## 样本扩充记录

| 样本类型 | 数量、来源与可查清单 |
| --- | --- |
| 语音 | 原 250 条是两套扩充清单共同子集。干净和带噪各 [2,598 条 clean](voice/manifests/data_short_clean_manifest.json) / [2,598 条 noisy](voice/manifests/data_short_noisy_50dba_manifest.json)，按条件配对；每套 1,000 个 source ID、957 条不同正文。多音色/方言合成音频，不能当不同真人录音，也不能把配对总数当作独立样本。[数据审计](voice/data_short_dataset_audit.json)、[准备报告](voice/GROUP1_TASK5_6_DATASET_PREP.md)、[历史交付](voice/GROUP1_TASK5_6_FINAL_DELIVERABLE.md)。原始外部音频包没有随 Git 发布。 |
| 文本规划 | [CARLA Language Benchmark](../../CARLA-Language-Benchmark/) 的 6,192 条是文本，不是语音。曾有早期 4,652 条文本版本，不和后来的 6,192 条相加。 |
| 项目仿真 | 冻结 [83 场矩阵](../../scenarios/acceptance_suite/matrix.json)仍为 83 场。新增四个定向闭环变体及对应 JSON，索引共 **162 份场景定义**；不是 162 次闭环通过。另有 11 月 17 日同步感知数据和[施工示意场景](../../experiments/server_roadworks_20261118/)；不混入正式验收。 |
| Qwen 语义 | [早期冻结 v1](../../experiments/semantic_sft/DATASET_RELEASE.md) 206 Train / 51 Dev，[v2](../../experiments/semantic_sft/DATASET_RELEASE_V2.md) 254 / 75，有历史内部 12 条冻结排除；V14/V15 使用 306 / 75，[含 11 条经审查的新 Train](../../experiments/semantic_sft/V14_PUBLIC11_RESULT_20261109.md)，不得报作独立验证。 |
| Teacher 蒸馏数据 | [B1 D2 v1.1](b1/d2_v1_1_README.md) 2,513 Train / 539 Val / 540 Reserved；8 条终态异常隔离。[后续治理关闭交付](b1/B1_HANDOFF.md) 合计 6,037 Train / 1,158 Dev，另有不入训练的 Calibration 300 和 Independent Validation 240；该交付未指定 Frozen Test。阶段版本不能相加，B1 数据治理 PASS 也不是 B2 性能 Gate。 |

## 去哪里取代码和交付

- [正式运行与基础赛道场景](../../README.md)、[项目技术方案](../current/technical_solution.md)、[三场正式长里程配置](../../scenarios/official_competition/README.md)。本次场景校验通过不等于重新跑过 5/8/6 km。
- [当前 83 场 FP32 HANDOFF](../../challenge/distillation/CARLA83_FP32_HANDOFF.md)包含模型哈希、代码身份、运行入口和服务器证据位置。[作业 40 采证代码](../../experiments/server_carla83_diagnostics_20261116/)和[四场预冻结哈希](closure/carla_new4_frozen_inputs.sha256)用于复盘。报告文件后续追加了结果，预冻结哈希绑定的是跑前版。
- [A3 中间实验](a3_history/)保留速度 Head、数值条件、音频桥接和换道/转弯诊断；[Robust V3 训练材料](a3_history/robust_v3_training/)包含配置、训练日志和交接清单，[原始 V3 权重](https://github.com/oOxixi/carla_driving/blob/2da949be62eccade91e62dc081e5776e652e485a/challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/student_v0_fp32_candidate.pt)仍由原分支提供。它与[旧 Features16](../../challenge/distillation/FEATURES16_CANDIDATE_HANDOFF.md)、83 场的 `student_post_turn_explicit_dev.onnx` 不是同一候选，不能共用同一成绩或 Gate。
- [感知源码与回放](../../experiments/server_sensor_20261117/)、[语义 SFT](../../experiments/semantic_sft/)、[main_optimization 源码差分与报告](../../experiments/server_main_optimization_20261028/)、[2B 部署依据](../../experiments/server_qwen2b_deployment/)。
- 语音扩样材料来自 `verify_new_fix@1a87d20ee5e80f4de1a64801107983944cfea4c2`；B1 索引来自 `challenge@2da949be62eccade91e62dc081e5776e652e485a`。表中的历史服务器结果不是本次重新执行。模型权重、冻结测试正文/标签、原始训练数据和全量仿真/ASR 逐条日志不在本交付内；按交接中绑定的路径和 SHA256 到服务器核对。

## 汇报时保留的边界

与基线相比，轻量学生在项目固定矩阵上达到 3% 线，但在定向新场景上仍暴露约束解码和回道执行问题。优先做跨路线、多 seed 的独立泛化验证；语音扩充后还缺全量音频同口径复测；语义改进要继续用独立冻结集合验证，不用 Dev 或少量跟车诊断替代。
