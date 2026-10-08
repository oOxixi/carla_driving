# V3 独立集一次性诊断（2026-10-08）

## 结论

robust v3 已在 B1 冻结的 `b1_independent_validation_v1` 240 条样本上完成一次性回放，
240/240 条均成功输出合法 ManeuverPlan，schema validity = 1.0。但按仓库当前 Gate 阈值
做的投影判定为 **FAIL**，因此本轮只冻结 V3 为唯一候选，不签发
`A3_FP32_GATE_PASSED`，不允许进入 `FINAL_SUBMISSION`。

| 核心指标 | Teacher reference | Student | 绝对下降 | 允许下降 | 投影结果 |
|---|---:|---:|---:|---:|---|
| behavior accuracy | 1.000000 | 0.942748 | 0.057252 | 0.015000 | FAIL |
| target pointer accuracy | 1.000000 | 0.984733 | 0.015267 | 0.015000 | FAIL |
| target lane accuracy | 1.000000 | 0.171756 | 0.828244 | 0.015000 | FAIL |
| completion accuracy | 1.000000 | 0.927481 | 0.072519 | 0.015000 | FAIL |
| plan sequence accuracy | 1.000000 | 0.108333 | 0.891667 | 0.015000 | FAIL |
| safety-critical behavior recall | 1.000000 | 1.000000 | 0.000000 | 0.000000 | PASS |

Student 分母为 262 个有效步、240 个完整计划与 28 个 safety-critical 有效步。

## 身份与完整性

- FP32 weights SHA256：`7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`
- FP32 ONNX SHA256：`681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286`
- Independent Validation case-set digest：`da1d032f7d20147a26e4426c10a97def8b470a780b854ea852143697292f7dec`
- 评估基线 Git SHA：`bd72fb96a25420a15b1cf83fa4d9bf5c7f754c6f`
- Student raw predictions SHA256：`07e8f33dd6e3a8f0234c875efb8c9a58f307f625de08cc0afad5e5f7bcba5e58`
- Stored Teacher reference SHA256：`96d8545b129bf32cd1ae15787ad1f53aa735324eb659c6ea7ae77f4f3d024bdd`
- 完整诊断报告 SHA256：`8e155001739857f7976be98aceec4099ce284ef63d7476d5dbe270783bfb6dae`
- 外置证据目录：`artifacts/b2_role_exception_v3_20261008_final/`

工具对 240 张 RGB 的 SHA256 和字节数、B1 `SHA256SUMS`、case manifest、dataset identity
和 case-set digest 全部做了绑定检查。

## 证据边界

这不是 B2 正式签发，原因有四个：

1. 本次由 A2 角色代执行，不具备 B2 独立性；
2. Teacher 侧是冻结数据内已存的 Teacher plan，不是当次重跑 Teacher service；
3. B1 已证明历史 `template_id` 无法恢复，不允许从 `scenario_id` 或文本推断；
4. B2 formal policy 的 policy version、slice 最小分母和 multi-run merge rule 仍未冻结。

因此这里的 `FAIL` 是阈值投影结果，不是伪造的正式 Gate decision；它已足以证明
现有 V3 不能被包装为 Final。

## 后续规则

- 禁止用这 240 条的标签做训练、量化校准、阈值选择或逐错调参；
- 如修改模型、Adapter 或训练策略，必须产生新版本候选，并由 B2 用新的、未暴露的
  template-valid 独立集重新评估；
- FP32 未通过前，Full INT8 和 Mixed Top-3 只保留为 A2 诊断产物，不发
  `A2_INT8_GATE_PASSED`。
