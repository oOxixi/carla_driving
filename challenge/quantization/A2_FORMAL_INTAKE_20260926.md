# A2 正式任务入口检查（2026-09-26）

## 结论

`a3_d2_d3_fp32_candidate_handoff_v3.zip` 文件完整，可继续作为候选预演输入；当前不能进入正式 A2 PTQ。

## 已核对

- ZIP SHA256：`923a0e1797b44c0a776366c84939dacb7edc967b8642c22e501958c005ad49f1`。
- 包内 9 个签名文件全部通过校验。
- 权重 SHA256：`1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c`。
- Student 候选身份、模型、配置和数据集版本与 B2 配置一致。
- GitHub `challenge` 最新提交 `02beca8` 已合并至 A2 分支。

## 正式门禁结果

- 包内 `gate_status`：`PENDING_A3_FP32_GATE`。
- 包内 `package_status`：`PENDING_B2_INDEPENDENT_VALIDATION`。
- B2 readiness：`BLOCKED`。
- A2 正式 ONNX 导出：按安全门禁拒绝，要求 `gate_status=A3_FP32_GATE_PASSED`。

B2 readiness 的六项阻塞：

1. 独立 Validation benchmark 尚未冻结。
2. 独立 Validation case manifest 缺失。
3. 正式 B2 policy 尚未冻结。
4. `policy_version` 缺失。
5. 各 slice 最小分母要求缺失。
6. 多轮结果合并规则缺失。

## A2 下一输入

A2 需要 B2/A3 提供与上述权重 SHA256 完全一致的晋级 manifest，至少包含：

- `gate_status=A3_FP32_GATE_PASSED`；
- B2 独立 Validation 与正式 policy 的版本和摘要绑定；
- 模型、配置、数据集版本及权重 SHA256；
- 可复核的 verification/evidence 引用。

同时需要 B1/B2 签发的 300～500 条正式 Calibration release。收到两项后可直接运行正式 ONNX 导出、PTQ、漂移 Gate 和 OpenExplorer 输入准备；无需重新训练该权重。
