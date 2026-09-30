# A2 上游最新提交检查（2026-09-27）

## 检查范围

- 远程 `challenge@4cbae9adafb1a3e5939e1c8a0cf8c02c040566cf`
- 本地 A2 分支 `a2-quantization`
- A3 v3 标准交接包 `handoff_manifest.json` 与真实 FP32 权重

## 可以直接用于 A2 的新增内容

1. A3 已明确冻结当前 v3 身份：权重 SHA256 为
   `1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c`。
2. A3 新增 `A2_REAL_WEIGHT_EXPORT_HANDOFF.md`，要求 A2 直接读取标准嵌套
   `candidate_identity`，不得制作临时扁平清单。
3. B3 已用同一真实权重证明 FP32→ONNX→INT8 技术链可运行，并确认
   `target_speed_mps` 是跨分布最敏感输出头。正式校准集应覆盖多个部署分布并单独报告该头。
4. targeted-gap 的 Teacher provenance 已补齐并通过 A3 intake；turn-gap release 和恢复累积视图
   也已通过完整性检查。它们可以支持 A3 后续训练新候选，但不会自动替换当前 v3。
5. A4 已补充 X86 runtime contract，可供 A2 正式产物完成后做下游接口检查。

## 本次完成

- A2 导出器改为复用 `challenge.hil.identity.identity_from_weight_manifest`。
- 同时支持扁平清单和 A3 标准嵌套 `candidate_identity`。
- 导出元数据新增训练 Git SHA 和实际采用的身份布局。
- 使用未改写的 v3 `handoff_manifest.json` 和真实权重完成候选 ONNX 导出。
- PyTorch↔ONNX 一致性：`PASS`，10 个真实预处理样本，10 个输出头全部通过；
  全局最大绝对误差 `5.7220458984375e-06`。
- 候选 ONNX SHA256：
  `95bddcd1eb0da38ba7d080c008cddf120ffaea960fb88cbca85681ac2fcad842`。

本次产物位于忽略目录：

```text
artifacts/a2/candidate_v3_canonical_manifest/
  student_v0_fp32_candidate.onnx
  model_structure.json
  flops_report.json
  export_consistency.json
```

## 正式 A2 仍然阻塞

当前 v3 仍为：

```text
gate_status    = PENDING_A3_FP32_GATE
package_status = PENDING_B2_INDEPENDENT_VALIDATION
```

B2 配置仍缺六项正式输入：

1. 冻结的独立 Validation benchmark；
2. 独立 Validation case manifest；
3. 冻结的正式 policy；
4. `policy_version`；
5. 各 slice 最小分母；
6. 多轮结果合并规则。

GitHub 中仍未出现当前 v3 对应的正式 Teacher/Student 成对评测、B2 PASS 或
`A3_FP32_GATE_PASSED` manifest。正式 Calibration release 也未出现。

因此当前可以继续做候选链路验证和校准策略准备，不能把候选 ONNX/INT8 标为正式交付。
正式 PTQ 的最小剩余输入仍是：

1. 与当前权重 SHA256 完全一致的 `A3_FP32_GATE_PASSED` manifest；
2. 300～500 条 Train-only、多分布覆盖、已冻结并签发的正式 Calibration release。
