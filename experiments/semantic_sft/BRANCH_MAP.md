# Qwen语义适配分支总览

盘点日期：2026-10-29。后续本项工作统一在`qwen_semantic_adaptation`开展。

## 分支边界

| 分支 | 当前用途 | 本次处理 |
| --- | --- | --- |
| `main` | 基础赛道冻结版本；远端a05c8b76 | 不修改，不将新语义实验合入 |
| `main_optimization` | 原驾驶控制优化及此前的离线Qwen实验；远端f92ac6fcc | 保持原样，不重写已有提交或切换服务 |
| `qwen_semantic_adaptation` | 原始指令多步理解、数据审核和未来独立Qwen adapter实验 | 本项唯一新增开发分支 |
| `challenge`及A1/A2/A3/A4/B2等分支 | Student蒸馏、量化、部署和评测 | 与Qwen本体语义适配分开，不混入 |

本分支从f92ac6fcc完整继承原仓库，**不是只有实验文件的空仓库**。此前相关实现已经在祖先提交中，
无需重复cherry-pick。它们同时留在main_optimization的历史里，不代表语义适配训练已部署。
“以后集中在本分支”不通过改写原分支历史来实现，也不撤回已有驾驶修复。

## 按职责找代码

| 内容 | 路径（相对仓库根目录） | 状态 |
| --- | --- | --- |
| 完整原驾驶方案 | `integration/`、`runtime/`、`car_control_A/`至`car_control_D/`、`scenarios/`等 | 继承基线，不在本阶段改动 |
| 现有Qwen HTTP服务及受限决策后端 | `qwen_service/server.py`、`qwen_service/service.py` | 现有服务路径，不是新多步理解接管 |
| 模型贡献审计 | `qwen_service/planner_audit.py` | 原提交中的可选审计；默认关闭，不删除 |
| 离线结构化规划 | `qwen_service/shadow_planner.py` | 研究对照，不接车辆执行 |
| 多步指令提取与原标签契约 | `qwen_service/task_understanding.py` | 本实验复用校验器；不可随意搬走 |
| 分句策略消融 | `qwen_service/clause_understanding.py` | 未晋升候选，保留复现实验 |
| 离线实验入口 | `tools/qwen_planner_experiment.py` | 贡献分析、回放、多步理解；非驾驶入口 |
| 既有开发/探针题 | `config/qwen_task_understanding_dev.jsonl`、`config/qwen_task_understanding_probe.jsonl` | 旧评测材料，不可混作新Train/Val |
| 对应软件测试 | `integration/tests/test_qwen_planner_experiment.py`、`test_qwen_task_understanding.py`、`test_qwen_clause_understanding.py` | 保留，不删失败案例来提升分数 |
| 历史报告 | `docs/reports/main_optimization_qwen_{attribution,slot_constraints,multistep,semantic_followup}_20261028.md` | 记录局限，不是新的通过证明 |

以上既有文件在本分支保留原路径，避免破坏imports、测试、复现实验与保护集来源。
新的准备工作统一位于`experiments/semantic_sft/`，新增文件不得散落到生产目录。

## 准备区目录索引

| 类别 | 文件 | 内容 |
| --- | --- | --- |
| 总入口 | `README.md`、本文件 | 命令、工作边界、代码去向 |
| 进度与部署盘点 | `STATUS.md`、`SERVER_CODE_INVENTORY.md`、`SERVER_LAYOUT.md` | 最新审核/测试结果、初次盘点与整理后的实际目录 |
| 策略与契约 | `plan.json`、`record.schema.json`、`ANNOTATION_GUIDE.md` | 固定2B身份、独立adapter策略、记录格式、人工审核要求 |
| 原始材料与AI建议 | `seeds.jsonl`、`draft_labels.jsonl` | 24条原句及草稿；AI建议不等于人工真值 |
| 数据和隔离保护 | `data.py` | 路径、原方案保护、来源/标签哈希、泄漏、split、审核及导出检查 |
| 草稿构造 | `proposals.py` | 原句与候选绑定，不生成批准 |
| 准备入口 | `prepare.py` | review/draft/hashes/preflight/export/environment；没有训练命令 |
| 审核与整批诊断 | `review.py` | 首轮真实批准记录、只读CPU tokenizer检查 |
| 环境只读检查 | `environment.py` | 依赖、候选LoRA索引、模板/assistant loss mask；不加载模型权重 |
| 软件测试 | `tests/` | 独立路径、泄漏、审批、契约隔离、mask及拒绝导出检查 |

## 成果放置约定

- 代码、说明和匿名种子材料：只提交本分支。
- 真实人工审核队列、授权收据、诊断报告：独立工作区的`artifacts/semantic_sft/`，不提交GitHub。
- 历史驾驶/离线实验日志：保留原main_optimization的`artifacts/`和`outputs/`，不移动活动日志。
- 未来训练结果：只能保存独立adapter；没有授权前不合并基础权重、不切换服务、不共享生产GPU训练。

当前可用人工审核快照是`artifacts/semantic_sft/first_review_20261029/review_queue.jsonl`：
21条有用户首轮批准，3条契约缺口隔离；仍未完成最终双人批准和独立split。尚无新LoRA成品。

## 哪些方案不再作为推进方向

| 方案 | 已有证据 | 去向 |
| --- | --- | --- |
| sequence_first分两次提取 | 开发集4/12，未改善完整标签 | 不作为默认，留作消融 |
| clause_focused分句提取 | 开发集7/12，真实长句被拒绝 | 不晋升，留作消融 |
| 中文动作名协议 | 开发集7/12 | 不晋升，留作协议对照 |
| 2048输出token的受限thinking诊断 | 两条诊断均长度截断，无有效最终答案 | 不作为当前有效方案；不宣称其他预算也无效 |
| 直接把当前多步理解接管车辆 | joint仅9/12开发题、1/4新探针，仍有错误 | 不部署；转向独立监督适配准备 |

这些是“小规模实验未晋升”，不是已经充分证明在任何条件下都无用。
保留代码和证据，避免反复重做负面实验；不将旧结果包装为新模型成绩。

## 本轮整理不做什么

不删除其他分支、不强推、不改变基线、不移动活动权重或venv、不重启端口8000/18005、不丢弃未提交scene修改。
用户批准后的历史工作区整体归档、缓存删除、7B保留与恢复路径见[整理后布局](SERVER_LAYOUT.md)。
历史A3权重随旧工作区归档，不影响当前生产模型或测试环境。
