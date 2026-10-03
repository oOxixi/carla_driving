# A2 B1 Closeout FP32 Candidate v2 量化诊断结果（2026-10-03）

## 结论

A2 已对 A3 的 B1 closeout FP32 candidate v2 完成候选阶段全链路：上游治理审计、
真实权重 ONNX 导出、300 样本 PyTorch/ONNX 一致性、冻结 Calibration v1 Full INT8、
25 个命名节点的逐节点敏感性实验、Top-3 Mixed Precision，以及 OpenExplorer 3.9.1
四输入交接包准备。

该候选仍为 `PENDING_A3_FP32_GATE` / `PENDING_B2_INDEPENDENT_VALIDATION`。
本文全部结果都是 `DIAGNOSTIC_ONLY`，不是 `A3_FP32_GATE_PASSED`、
`A2_INT8_GATE_PASSED`、OpenExplorer 编译通过或 J6P 板端通过声明。

## 身份与治理边界

| 项目 | 值 |
|---|---|
| A2 workflow Git SHA | `20c80d7cde2ca8ca651f383ca06b8bc06e0acaa3` |
| model / config | `student-v0-r3-fp32` / `student-v0-r3-structure-20260911` |
| dataset view | `b1_governed_closeout_v1_a3_strict_positive_v1` |
| governed source counts | Train `6037` / Dev `1158` |
| optimizer view counts | Train `5856` / Validation `1108` |
| FP32 weights SHA256 | `6b6ec1d8e815866aaccb3981d7a7a74efaa971e2a0d0bf8a9b42cbf7af0b8546` |
| A3 handoff manifest SHA256 | `738f0101816cd2ee4585057c5b5a56aa395b25fc179f0713502374185fd92104` |
| B1 governed release SHA256 | `07d3a82502005646d8f29d0c493fa8a5b0270a5194fd5c802a04b4870ba7d37d` |
| Calibration manifest published SHA256 | `659c5e8210ee95cf835be685da1deb55bc1990874ba3e120955d6bdf392d8059` |

上游审计确认权重字节、governed counts、B1 closeout 与 Calibration 身份全部匹配。
唯一阻塞项为 `A3_FP32_GATE_NOT_PASSED:PENDING_A3_FP32_GATE`。B1 的 240 条
Independent Validation 继续严格归 B2 所有，A2 没有读取其标签用于校准、白名单选择或
误差驱动迭代。

## FP32 ONNX 导出一致性

| 项目 | 值 |
|---|---|
| FP32 ONNX SHA256 | `a946fc361d09780cc50723d2800495802ba84db1324810e011403263a03cfbf3` |
| 文件大小 | `92,041,414` bytes |
| 样本数 | `300`（完整 Calibration v1） |
| 容差 | `atol=1e-4`、`rtol=1e-4` |
| 结果 | `PASS`，十个 Head 全部通过 |
| 全局最大绝对误差 | `9.5367431640625e-06` |

因此后续 FP32/INT8 差异来自量化候选，而不是错误权重或 ONNX 导出偏差。

## Full INT8

| 项目 | 值 |
|---|---|
| quantization id | `a2-ptq-fa31c3bdb4ad793c` |
| status / gate | `A3_CANDIDATE_PRE_PTQ` / `NOT_FORMAL` |
| INT8 SHA256 | `1e2572a5ef0d0d799db3730670e6dc2cb306c48756ac1b151db5fa97b9c64a01` |
| 文件大小 | `23,273,686` bytes |
| 相对 FP32 体积减少 | `74.7139%` |
| QuantizeLinear / DequantizeLinear | `57 / 107` |

量化策略仍为 QDQ、QInt8 对称激活、QInt8 对称逐通道权重、MinMax，使用完整冻结
Calibration v1。

### 300 样本逐 Head 漂移

| Head | Mean absolute error | P95 | Max | Argmax agreement |
|---|---:|---:|---:|---:|
| plan length | `0.032451` | `0.073485` | `0.120130` | `1.0000` |
| behavior | `0.037297` | `0.081812` | `0.146164` | `0.9992` |
| target pointer | `0.038619` | `0.084233` | `0.141579` | `1.0000` |
| target lane | `0.037055` | `0.080287` | `0.141685` | `1.0000` |
| target speed | `0.124153 m/s` | `0.378047 m/s` | `0.702583 m/s` | N/A |
| completion | `0.034764` | `0.077432` | `0.137693` | `0.9925` |
| on failure | `0.034714` | `0.077575` | `0.140667` | `1.0000` |

相同 Calibration v1 口径下，v2 的速度 Head 最大漂移由旧 v1 的 `1.389767 m/s`
下降到 `0.702583 m/s`；behavior argmax 由 `0.9708` 提升到 `0.9992`。这只是原始
输出诊断改善，不能替代 B2 的真实标签精度 Gate。

## 敏感层与 Top-3 Mixed Precision

25 个单节点 FP32 恢复实验完成。前三名仍为三个离散输出 Head，且与第四名存在明显断层：

| 排名 | 节点 | 诊断改善分 |
|---:|---|---:|
| 1 | `/model/target_pointer_head/Gemm` | `0.140006` |
| 2 | `/model/behavior_head/Gemm` | `0.139176` |
| 3 | `/model/target_lane_head/Gemm` | `0.137286` |
| 4 | `/model/fusion/fusion.2/Gemm` | `0.010226` |

`/model/target_speed_head/Gemm` 的改善分仍为负值，说明速度误差主要来自共享上游量化，
单独恢复速度输出层不能解决问题。

Top-3 Mixed Precision 结果：

| 项目 | 值 |
|---|---|
| quantization id | `a2-ptq-2cf2e6d7fcd452b3` |
| INT8 SHA256 | `8935fb6a611762ac3d851e753062b4dbe2fb8a74a3a4d37bddbb6e6ef28870b9` |
| 文件大小 | `23,622,853` bytes |
| 相对 Full INT8 增加 | `1.5003%` |
| 相对 FP32 体积减少 | `74.3345%` |

| Head | Full INT8 MAE | Mixed MAE | Full argmax | Mixed argmax |
|---|---:|---:|---:|---:|
| behavior | `0.037297` | `0.016534` | `0.9992` | `1.0000` |
| target pointer | `0.038619` | `0.016992` | `1.0000` | `1.0000` |
| target lane | `0.037055` | `0.016707` | `1.0000` | `1.0000` |
| target speed | `0.124153` | `0.124153` | N/A | N/A |

该白名单只基于 Calibration 原始 Head 漂移。最终是否采用必须由 B2 同一冻结基准精度结果
和 A4 部署代价共同决定。

## OpenExplorer 交接输入

- 状态：`A3_CANDIDATE_OPENEXPLORER_INPUT_READY`；
- OpenExplorer：`3.9.1`；march：`nash-p`；
- 300 组四输入，共 1200 个 NPY；
- input manifest SHA256：
  `c6bcf3a09a1e84cf0cee2cad2b11a9c6615ac0353ffee3eca568512a57a51e80`；
- YAML SHA256：
  `299adaa788c8e9fc828d0ac091a91858a5bb3842be22eaa0b6175f89816c4f4f`。

OpenExplorer 正式编译、算子落点、CPU fallback、BPU 性能估算和板端实测仍分别属于 A4/B3。

## 已知 FP32 能力缺口

B3 已在留出队列报告 v2 对 TURN-gap 和 Gap300 的 `TURN_LEFT` 共 135 个例次全部失败，
并且 3/4 步计划虽然恢复完整长度，最后一步仍可能错误。量化结果不能修复 FP32 本身的能力
缺口；在 B2 给出 exact weights Gate decision 前，本候选不得升级为正式 INT8。

## 验证与产物

- A2 单元测试：`16 passed`；
- 敏感层实验：`25/25` 完成；
- 本机产物目录：
  `artifacts/a2/a3_final_fp32_candidate_v2_20c80d7c/`；
- 敏感层报告 SHA256：
  `b7412f48d153545a838baf22931a635ff6610a707079cedeaef747994c39fcd1`。

### 分成员交接包

打包目录为 `artifacts/a2/handoff_20261003_20c80d7c/`：

| 接收方 | 压缩包 | 大小 | SHA256 |
|---|---|---:|---|
| A3 | `A2_to_A3_gate_feedback_20c80d7c.zip` | `28,480` bytes | `f217e8bf030f8ee14c6fdd82f0e2761900a4d3228b6d216b9749d9f4b4c2eda6` |
| B2 | `A2_to_B2_evaluation_20c80d7c.zip` | `215,287,371` bytes | `e69a28d77c4b3b71f1eddcb18add16a70f9469c22f9538b6edf2864af32d0531` |
| A4 | `A2_to_A4_openexplorer_20c80d7c.zip` | `154,091,710` bytes | `8d1ea529376f1615457a9945a9516d7f0711ed05c85e851cd828d9909cb3e4ec` |

A4 包已经 B3 独立校验器复核：`1217/1217` 个台账文件匹配，四输入各300个NPY，
Full INT8 与 Mixed Top-3 均与各自 manifest 匹配并绑定最新
`a3_final_fp32_candidate_v2`，结果为 `PASS`、0 error、0 warning。

## 剩余 Gate

1. B2 对权重 SHA256 `6b6ec1d8...b8546` 执行独立 Validation 并签发 PASS/FAIL；
2. 仅在 B2/A3 将完全相同权重晋级为 `A3_FP32_GATE_PASSED` 后，A2 才能重新生成正式
   FP32 ONNX 与 `PENDING_B2_INT8_GATE` 候选；
3. B2 对 Full INT8 与 Mixed Top-3 使用同一冻结基准比较精度；
4. A4 在 OpenExplorer 3.9.1 中完成编译、算子映射、fallback 与 BPU estimate；
5. B3 对 A4 最终 Runtime 重跑 X86/板端验证；完成前不得写成 `A2_INT8_GATE_PASSED`。
