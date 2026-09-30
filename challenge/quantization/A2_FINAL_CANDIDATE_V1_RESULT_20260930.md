# A2 Final FP32 Candidate v1 量化预演结果（2026-09-30）

## 结论

A3 发布的真实 Final FP32 Candidate v1 已完成 A2 候选阶段全链路：handoff 校验、
真实权重 ONNX 导出、PyTorch/ONNX 一致性、Calibration v1 Full INT8 PTQ、300 样本
逐 Head 漂移、25 个命名节点的逐节点敏感性实验、Top-3 混合精度候选和
OpenExplorer 3.9.1 输入包准备。

该候选仍为 `PENDING_A3_FP32_GATE`。以下结果均是诊断证据，不是
`A3_FP32_GATE_PASSED`、`A2_INT8_GATE_PASSED` 或 J6P 部署通过声明。

## 身份绑定

| 项目 | 值 |
|---|---|
| FP32 model | `student-v0-r3-fp32` |
| FP32 config | `student-v0-r3-structure-20260911` |
| A2 workflow Git SHA | `816849af353b104e9c6e598f6bdc1a97c4495688` |
| FP32 weights SHA256 | `eaee4402197fb3fed53ed82bc2fbaceef62e5ed2d4cde86e8aa1a55dc6d46515` |
| FP32 ONNX SHA256 | `25bb87a05c885de5ea77bd8c00e34b73d195f1245ac6d1f5ae5327ac705ccdd9` |
| Calibration JSONL published SHA256 | `e7520afc683b4545ca0981c549d0aebef50a90962a0d95378d89c1ca4bfbe8cc` |
| Calibration manifest published SHA256 | `659c5e8210ee95cf835be685da1deb55bc1990874ba3e120955d6bdf392d8059` |
| Quant config SHA256 | `1f27acc689e7fbfc5927bfa6fa3e130394f1442e564a8180969082ad5e17da7c` |

Handoff 的 9 个签名文件、权重字节和嵌套身份均已验证。Calibration v1 的
300 样本/300 组、Train/Dev 零重叠、300 张 RGB 和四输入张量合同均通过。

## FP32 导出一致性

在完整 300 条 Calibration v1 上比较真实 PyTorch 权重与导出的 FP32 ONNX：

- 状态：`PASS`；
- 容差：`atol=1e-4`、`rtol=1e-4`；
- 十个 Head 全部通过；
- 全局最大绝对误差：`1.52587890625e-05`。

这证明后续量化误差来自量化本身，而不是错误权重或 ONNX 导出偏差。

## Full INT8 PTQ

| 项目 | 值 |
|---|---|
| quantization_id | `a2-ptq-a17da9f4f284f252` |
| status | `A3_CANDIDATE_PRE_PTQ` |
| INT8 SHA256 | `560a616619d922431e9e603f68406e131b5eafe264b9e96d7ef80d7fa2586bb1` |
| INT8 size | 23,273,279 bytes |
| FP32 ONNX size | 92,041,007 bytes |
| size reduction | 74.7142% |
| QuantizeLinear / DequantizeLinear | 57 / 107 |

量化策略为 QDQ、QInt8 对称激活、QInt8 对称逐通道权重、MinMax，并使用完整
Calibration v1。ORT QDQ 字节仅用于精度诊断，不是 OpenExplorer BPU 产物。

## 300 样本逐 Head 漂移

| Head | Mean absolute error | P95 | Argmax agreement |
|---|---:|---:|---:|
| plan length | 0.057201 | 0.131405 | 1.0000 |
| behavior | 0.051167 | 0.111529 | 0.9708 |
| target pointer | 0.054990 | 0.119245 | 0.9800 |
| target lane | 0.047313 | 0.104894 | 0.9808 |
| target speed | 0.263653 m/s | 0.769152 m/s | N/A |
| completion | 0.046591 | 0.102786 | 0.9667 |
| on failure | 0.056250 | 0.117518 | 0.9842 |

最大单样本漂移为 target speed `1.389767 m/s`。因此速度 Head 是需要 B2
真实标签评测重点确认的风险，但不能仅凭原始输出漂移判定精度 Gate 失败。

## 逐节点敏感性与 Mixed Precision

完成 25 个 `Conv/Gemm/MatMul` 节点的单节点 FP32 恢复。诊断改善前三名出现明显断层：

敏感层报告 SHA256：`b6403a33ecfda795bfc6803c179a748891ae87cf77a18384f1e2ea8a47c9d1eb`。

1. `/model/target_pointer_head/Gemm`：`0.147460`；
2. `/model/behavior_head/Gemm`：`0.142012`；
3. `/model/target_lane_head/Gemm`：`0.130396`；
4. `/model/state_encoder/layers/layers.0/Gemm`：`0.008463`。

据此生成 Top-3 Head FP32 混合精度候选：

| 项目 | 值 |
|---|---|
| quantization_id | `a2-ptq-1a449fab1ef58309` |
| INT8 SHA256 | `02c600d41fc041cd512ca652320661bf8764c45514a40b5a374942f97af9d790` |
| size | 23,622,446 bytes |
| 相对 Full INT8 体积增加 | 1.5003% |
| 相对 FP32 体积减少 | 74.3349% |

| Head | Full INT8 MAE | Mixed MAE | MAE 变化 | Argmax agreement 变化 |
|---|---:|---:|---:|---:|
| behavior | 0.051167 | 0.022101 | -56.8050% | 0.9708 → 0.9925 |
| target pointer | 0.054990 | 0.022555 | -58.9841% | 0.9800 → 0.9925 |
| target lane | 0.047313 | 0.022635 | -52.1583% | 0.9808 → 0.9950 |
| target speed | 0.263653 | 0.263653 | 0% | N/A |

Top-3 混合精度候选以 1.5% 体积代价显著降低三个离散关键 Head 的漂移；它没有改善
速度 Head。单独恢复 `/model/target_speed_head/Gemm` 的综合改善分为负，说明速度误差主要
来自共享上游量化而非该输出层本身。最终白名单必须由 B2 精度和 A4 部署代价共同决定。

## OpenExplorer 输入包

已生成完整 300 组四输入 NPY、`student_j6p_oe391.yaml` 和输入 manifest：

- 状态：`A3_CANDIDATE_OPENEXPLORER_INPUT_READY`；
- OpenExplorer：3.9.1；
- march：`nash-p`；
- manifest SHA256：`cc942b59fe93c8ea6749175c98024e47555d11046e1b68e7930bec14eb158da6`。

该包可以交给 A4 做候选工具链检查，但必须继续保持非正式状态。

## 产物位置

全部生成产物位于：

```text
artifacts/a2/a3_final_fp32_candidate_v1_816849af/
├── student_v0_fp32_candidate.onnx
├── export_consistency.json
├── ptq_int8/
├── sensitivity_full/
├── mixed_precision_top3/
└── openexplorer_oe391/
```

## 剩余 Gate

1. B2 对精确权重 SHA 做独立 Validation，并决定是否签发 `A3_FP32_GATE_PASSED`；
2. Gate 通过后，用通过状态的 manifest 重新导出/核验正式 FP32 ONNX并正式 PTQ；
3. B2 对 Full INT8 与 Mixed Precision 使用同一冻结基准做精度比较；
4. A4 在官方 OpenExplorer 3.9.1 环境检查算子、CPU fallback 和编译结果；
5. 只有 B2/A4 均接受后，才能绑定 `A2_INT8_GATE_PASSED`。

