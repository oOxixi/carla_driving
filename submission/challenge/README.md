# 挑战赛道预提交入口

本目录用于 Final Freeze 之前的全赛道文件盘点，不是 `final_submission/`，也不表示任何
模型或 Gate 已经通过。最新快照为 2026-10-08：

- `RC_V3_FREEZE_20261008.json`：唯一候选身份和 `BLOCKED_NOT_FINAL` 冻结决议；
- `V3_INDEPENDENT_DIAGNOSTIC_20261008.md`：240 条一次性回放、指标和证据边界；
- `V3_FIELD_SEMANTIC_NORMALIZATION_20261008.md`：`null/CURRENT` 统一后的并行诊断；
- `PRE_SUBMISSION_LEDGER_20261008.md`：A1–B4 最新产物、缺口和外置包路径；
- `SUBMISSION_COLLECTION_CHECKLIST_20261008.md`：最终收件与晋级清单。

2026-10-07 历史快照保留用于追溯：

- `PRE_SUBMISSION_INVENTORY_20261007.json`：角色、Gate、证据和外置大文件台账；
- `PRE_SUBMISSION_LEDGER_20261007.md`：面向成员的缺口、收件顺序和整理规则；
- `SUBMISSION_COLLECTION_CHECKLIST_20261007.md`：A1–B4 逐项收件、身份核验和 Final
  staging 白名单。

只有 B2、A2、A4、B3 的正式 Gate 全部绑定同一 RC，且完成干净环境复现后，才能依据
`docs/architecture/modules/B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md` 建立
`final_submission/`。当前禁止把 Candidate、X86 预验证、BPU 估算或本地外置包改名为 Final。
