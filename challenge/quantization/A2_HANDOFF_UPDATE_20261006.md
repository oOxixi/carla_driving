# A2 交接更新与 A4 输入缺口（2026-10-06）

## 当前结论

截至 integration evidence Git SHA
`3c10b121d7d1dda169a873df76dc80bc8a226e26`，仓库没有新增
`A3_FP32_GATE_PASSED` 或 B2 exact-weights Gate decision。因此 A2 不能把现有
FP32 ONNX、INT8 或 OpenExplorer YAML 改名为正式产物，也不需要重复运行相同权重的
量化实验。

本次可推进内容已经完成：把正式 Calibration v1 identity 补入交接包，把 B1 新发布的
旧模板身份恢复证明补入 B2/A3 交接证据，并重新生成 A3、B2、A4 三份哈希锁定包。

## 截图所列 A4 输入逐项核对

| A4 所需输入 | 当前仓库状态 | A2 已提供 | 还需要谁行动 |
|---|---|---|---|
| `A3_FP32_GATE_PASSED` | **缺失** | exact weights SHA 和全部候选证据 | B2 给出独立 Gate decision，A3 对同一权重签发 |
| 正式 FP32 ONNX | **缺失** | Candidate ONNX，SHA `a946fc36...3cfbf3` | A3 Gate 通过后 A2 重新正式导出 |
| 正式 INT8 / 最终 Mixed Precision | **缺失** | Full INT8 与 Top-3 Mixed 候选 | B2 对同一 Frozen Benchmark 比较后决定 |
| `A2_INT8_GATE_PASSED` | **缺失** | 候选量化证据和 manifest | B2 签发 INT8 decision，A2 绑定结果 |
| 正式 `int8_manifest.json` | **缺失** | 两份 `NOT_FORMAL` manifest | FP32 Gate 与 INT8 Gate 完成后生成 |
| 正式 OpenExplorer YAML | **缺失** | `PRE_GATE_ONLY` YAML、模型和 1200 NPY | A2 正式化后 A4 重跑官方工具链 |
| 正式 Calibration identity | **已具备** | 已放入新版三份交接包 | 无；继续保持该 SHA |

正式 Calibration identity 状态为 `FROZEN_CALIBRATION`，300 samples / 300 groups，
文件 SHA256 为
`2ec6c85473e49b0be5dab308919e559cc0d6bdc3784d37fdbf8c5a8fff2a0b51`；其绑定的
Calibration manifest SHA256 为
`659c5e8210ee95cf835be685da1deb55bc1990874ba3e120955d6bdf392d8059`。

## 新增 B1 证据对 B2 Gate 的影响

B1 新增
`challenge/dataset/attestations/b1_legacy_template_identity_recovery_v1/`。其结论是：

- 状态为 `HISTORICAL_TEMPLATE_LINEAGE_UNRECOVERABLE`；
- 无法签发正式 sample-to-template sidecar；
- 不允许从 `scenario_id` 或 source text 推断 template identity；
- Independent Validation cases 和历史 release 均未被修改；
- 当前 B2 contract 对缺失 template identity 的行为仍是
  `FAIL_CLOSED_IF_TEMPLATE_IDENTITY_MISSING`。

所以这次更新不是 Gate PASS，而是把阻塞原因变成了可校验的正式证据。B2 下一步必须明确
选择并记录：按现有 contract 给出 BLOCKED/FAIL、经批准修改 Gate policy，或请求 B1
重新采集带显式 template identity 的数据。A2 无权替 B2 选择。

## 2026-10-06 分成员交接包

本机目录：`artifacts/a2/handoff_20261006_3c10b121/`。

| 接收方 | 文件 | 大小 | SHA256 | 用途 |
|---|---|---:|---|---|
| A3 | `A2_to_A3_gate_feedback_3c10b121.zip` | 36,487 bytes | `cc1bc1c4c258f466490dfafa77749942fb88822fe3ba38f607d8386e1e53f9f2` | 接收量化反馈、Calibration identity 与 B1 新阻塞证明 |
| B2 | `A2_to_B2_evaluation_3c10b121.zip` | 215,358,886 bytes | `e3d8be14358a6307104aa9d003b0b8011e45263362e9d915f41c16cab4468622` | exact weights、FP32/INT8、量化证据及完整 B1 恢复证明 |
| A4 | `PRE_GATE_ONLY_A2_to_A4_openexplorer_3c10b121.zip` | 154,097,294 bytes | `fb085f4aaa99f7b8de02becb6bedae3e99ebdbfdcc61c13f079c93b2f224b0e1` | 仅用于预编译、算子映射、fallback 扫描和诊断估算 |

三个包逐文件 SHA256 均为 0 mismatch，ZIP CRC 全部通过且时间戳已规范化。A4 包经 B3
独立验证器复核：1221/1221 文件匹配、四输入各 300 个 NPY、两份 INT8 均匹配其
manifest，0 error、0 warning，状态 `PASS`。这里的 `PASS` 仅表示包自洽，不表示模型 Gate
通过。

## 上传与发送边界

可以提交 Git：本报告、打包工具、B1/A2/A3/B2 的 JSON/Markdown/YAML 配置与 SHA 证据。

不提交 Git、改用群文件或网盘：`.pt`、`.onnx`、1200 个 `.npy` 以及三份 ZIP。发送前必须
用 `DELIVERY_SHA256SUMS.txt` 核验，A4 包必须保留 `PRE_GATE_ONLY` 文件名。

## 现在谁可以继续

1. B2 立即使用新版 B2 包，对权重 SHA
   `6b6ec1d8e815866aaccb3981d7a7a74efaa971e2a0d0bf8a9b42cbf7af0b8546`
   给出正式 Gate 处置，并明确模板身份缺口如何处理。
2. A4 可以使用 `PRE_GATE_ONLY` 包完成工具链预演，但不得写成正式编译或板端结论。
3. A3 等 B2 decision；若权重字节不变且获得 PASS，再签发同一 SHA 的
   `A3_FP32_GATE_PASSED` manifest。
4. A2 收到上述 manifest 后立即重新导出正式 FP32 ONNX、生成正式候选 INT8，并交 B2
   执行 INT8 Gate；当前不得提前签发 `A2_INT8_GATE_PASSED`。
