# 挑战赛道预提交入口

本目录用于 Final Freeze 之前的全赛道文件盘点，不是 `final_submission/`，也不表示任何
模型或 Gate 已经通过。最新快照为 2026-10-08：

- `RC_V3_FREEZE_20261008.json`：唯一候选身份和 `BLOCKED_NOT_FINAL` 冻结决议；
- `V3_INDEPENDENT_DIAGNOSTIC_20261008.md`：240 条一次性回放、指标和证据边界；
- `V3_FIELD_SEMANTIC_NORMALIZATION_20261008.md`：`null/CURRENT` 统一后的并行诊断；
- `V3_1_ADAPTER_INT8_POSTHOC_20261008.md`：Adapter V3.1 实现、FP32/INT8 回归
  PASS 投影及正式 Gate 边界；
- `B2_PROXY_EVALUATION_V3_1_20261008.md`：A2 代理执行的 197 项 B2 合同测试、
  240 条真实复跑、切片告警和非独立 Gate 投影；
- `B2_PROSPECTIVE_FREEZE_AND_SEEN_STRESS_20261008.md`：评测前冻结的 240 槽
  Seen/Variant/Unseen 采集与 policy、308 条候选未暴露 Seen 压测 FAIL、重复性和
  两份可发送 ZIP；
- `B2_PROXY_PROSPECTIVE_RECEIPT_20261008.json`：上述冻结、指标、哈希和 Gate 状态的
  机器可读回执；
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

## 2026-10-09 打包代补进度

打包负责人已补齐部署、统计、演示入口与附件说明。最新完成项和仍需收取的实体文件见
[PACKAGING_PROGRESS_20261009.md](PACKAGING_PROGRESS_20261009.md)，机器可读状态见
[PACKAGING_PROGRESS_20261009.json](PACKAGING_PROGRESS_20261009.json)。
新增可安装工程见 [PACKAGING_SUPPLEMENT_20261009](PACKAGING_SUPPLEMENT_20261009/README.md)。
代码与整理完成不代表镜像、同批原始记录或实际演示已经生成；本次不生成最终 ZIP，
也不改变上述候选模型与正式 Gate 状态。

