# v2语义覆盖修复：329条冻结数据

版本`semantic_text_sft_v2_20261101`，不是Student/A3数据，不是新Final Test。
负责人对新增72条原句、候选标签和跨批分组明确回复“已逐条复核，全部通过”，已另存真实审批快照。
登记时间是2026-11-01 21:10:12 +08:00，不反推原消息发送时间，不代签第二人。

## 数据与划分

| 内容 | 数量与边界 |
| --- | --- |
| 原v1 | 257条及206/51划分逐字段保留，不覆盖 |
| 新72条 | 18个四句对照组；2个旧Train组留在Train，16个拟定新组按已审核分组处理 |
| 新Train / 新Dev | 48 / 24；每类按固定哈希选择1个完整新组进Dev，不看标签内容或模型成绩 |
| 累计Train / 开发Val | 254 / 75，六类均覆盖，Train/Val组交集0 |
| 隔离 | 原3条契约缺口按原字节保留，不进入Train/Dev |
| 真实tokenizer检查 | 329/329通过、最长374 tokens，prompt loss屏蔽、无跳过或静默截断 |

分组规则：固定seed20261101，以SHA256(`extension_v1|seed|family|group`)最小的新组为每类Dev组。
两个沿用组不参与重新选择，也不移动任何旧组。函数`release.plan_extension_groups`不读label或预测，
只是分配已有批准记录，不会创建审批；发布前仍复验完整标签、哈希和保护集合。
该规则在新一轮训练/预测前声明；不得改seed反复挑好看的划分。

新72条属于看过旧12题结果后的开发补充，不能把Dev或旧Test称为独立最终成绩。
旧12题仍在排除清单中、不进入训练，今后只作已知回归；最终晋升需要新独立测试。
工具不能证明语义模板绝对独立；负责人审核记录和结构相似提示均保留。

## 两端实际文件

相对本机/服务器独立实验仓库根目录：

- 冻结发布：`artifacts/semantic_sft/releases/semantic_text_sft_v2_20261101/`。
- 72条审批：`artifacts/semantic_sft/semantic_contrasts_v1_approved_20261101/`，原草稿不覆盖。
- 划分收据：`artifacts/semantic_sft/semantic_contrasts_release_20261101/planning/`。
- 全量token报告：`artifacts/semantic_sft/frozen_329_token_audit_20261101/report.json`。
- 服务器预检：`artifacts/semantic_sft/frozen_329_preflight_20261101/`。

Train SHA256：`450ba6e464e29cac5c894336a9e9108b56f599fa68fac87301e644b792d53378`。
Dev SHA256：`dbd6f88de20338ea1d245d65a3c3fa7e842262fa0e63098ddb29cb88184f599a`。
发布manifest逐文件记录SHA256并链接父版本和审批输入（不是数字签名）；新token报告input SHA绑定新reviewed_rows文件。
原v1、已训v1 adapter、旧Test材料和生产服务保持原样，真实语料/审批不直接上传GitHub。

## 新一轮选模要求

新训练必须使用`--semantic-validation`，不要直接用默认旧loss模式声称已完成语义修复。
新模式先让未适配基座对全部75条Dev真实生成，再在每轮训练后对相同Dev生成一次。
输入仅为已审计的prompt前缀，不含assistant/金标；贪心解码、1536新token上限，不用语法约束、重试或答案修正。

预先固定规则：

1. 原始动作序列单独从raw JSON读取，不因其他字段schema失败而记为零。
2. 完整语义须全部动作、顺序、目标、条件、方向、速度、距离、禁止事项及确认标志一致，并通过引用校验；
   evidence允许合法的不同摘录边界，数字容差1e-6。
3. 基座原本做对的任何Dev动作序列或完整语义案例，新候选不能丢失。否则该轮只作诊断，不参与候选选择。
4. 合格候选按完整语义正确数→原始动作序列正确数→引用契约通过数→较低loss排序，不按Test选模。
5. 若无合格候选，报告NO_ADMISSIBLE_CANDIDATE_KEEP_BASELINE，不静默回退到最低loss；
   留存的diagnostic_adapter不是晋升权重，即使保存重载通过也不能混称best_adapter。

默认旧模式仍保留用于原训练复现，不改变生产方案。新模式软件测试已覆盖评分、配对和筛选逻辑，
截至本次发布尚未完成新模式的完整GPU训练验证，不能把测试通过当作模型修复有效。
75条是开发选模数据；即使得到候选也不是比赛Gate或最终独立验证通过，不自动部署。
