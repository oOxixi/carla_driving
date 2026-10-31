# 独立的Qwen 2B语义微调准备区

本目录负责业务数据准备，并提供用户明确批准的**仅合成协议单元**Qwen+LoRA训练smoke。
业务数据正式训练入口仍未启用；不得把合成smoke当作语义准确率或正式Gate。
这是Qwen本体的任务适配准备，不是challenge里的Student/A3蒸馏训练。

统一入口：[分支与文件索引](BRANCH_MAP.md) · [排除清单与负责人说明](EXCLUSION_HANDOFF.md) · [服务器整理后目录及恢复](SERVER_LAYOUT.md) · [最新进度](STATUS.md)。
后续本项新增开发只在`qwen_semantic_adaptation`；此前相关实现已随f92基线完整继承，不重复迁移或重写原分支。

## 与原方案隔离

- 分支：`qwen_semantic_adaptation`，从 `f92ac6fcc8e8c55e3b3a63825b6f4386d49b6d78` 创建。
- 本机目录：`C:/Users/17733/Documents/Codex/2026-08-06/du/work/carla_driving_qwen_semantic_adaptation`。
- 服务器目录：`/home/tiaozhansai/carla-driving-qwen-semantic-adaptation`。
- 原 `main_optimization`、`main`、`challenge` 不切换、不合并本阶段修改。
- 新代码仅允许位于 `experiments/semantic_sft/`；CLI检查相对原提交是否有目录外改动。
- 输出只能写入新工作区的 `artifacts/semantic_sft/<新目录>`，不允许覆盖已有文件。
- 不安装或升级原环境，不重启8000/18005服务；仅授权smoke在物理GPU1读取基础模型，GPU0服务不动。
- 不覆盖、合并或发布基础权重；未来候选仅保存独立LoRA adapter。
- 不在生产服务占用的GPU上同时训练。新.venv只读复用原Torch/Transformers，新增PEFT/Accelerate安装在新环境中。

固定基础模型：`Qwen/Qwen3.5-2B`；revision：
`15852e8c16360a2fea060d615a32b45270f8a8fc`；期望artifact fingerprint：
`4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`。
这只是版本约束，环境预检不会伪称已经重新核验全部权重fingerprint。

## 已准备什么

| 文件 | 内容 |
| --- | --- |
| `seeds.jsonl` | 24条新编写的待标注文本，6类问题、12个同义改写组；不是训练成品 |
| `batches/negative_v1/` | 独立追加的8条禁止类候选、4组；已记录用户批准及B2复核 |
| `draft_labels.jsonl` / `proposals.py` | AI编写的24条待审标签及原句绑定；不是Qwen推理结果或人工真值 |
| `record.schema.json` | 单条数据、来源、分组、split、负责人审核记录；兼容历史双人记录 |
| `ANNOTATION_GUIDE.md` | 任务拆解、条件、否定、目标和歧义的人工标注说明 |
| `data.py` | 原方案保护、数据泄漏检查、审批哈希校验、SFT消息格式 |
| `environment.py` | 依赖/权重索引、真实meta结构目标层核验、CPU tokenizer和loss mask检查；不读取权重 |
| `review.py` | 记录有直接人工授权的第一轮审核；CPU逐条token诊断，不启动训练或导出待批准样本 |
| `prepare.py` | review / draft / hashes / preflight / export / environment / split-preview；没有train命令 |
| `split_preview.py` | 已复核记录的固定种子分组划分预览；保留隔离记录，不冻结正式split |
| `plan.json` | 尚未批准的候选LoRA配置与工程数据门槛，不是比赛正式Gate |
| `tests/` | 路径隔离、泄漏、双人审批、失效审批、mask等软件测试 |
| `synthetic_smoke.py` | GPU1真实2B+LoRA合成单元训练、参数更新、adapter保存/重载；不接受业务数据输入 |
| `build_exclusion_registry.py` | 从真实冻结集合生成文本哈希；严格区分FROZEN_TEST和INDEPENDENT_VALIDATION |
| `batches/paraphrase_v1/build.py` | 12条新词面/参数变体草稿，沿用相关旧组，不能伪装成12个新独立模板 |
| `evaluation/test_candidate_v1.py` | 12条独立存放的Test候选及预期草稿，负责人确认后另行冻结；不能作为训练输入 |

## 标注与数据门槛

初始24条种子全部生成 `DRAFT`、`label=null`、`reviews=[]`、`split=UNASSIGNED`。
程序不自动批准标签，不把旧Qwen输出当正确答案，不把同一模型自评当人工复核。
最新累计快照29条（原21条+negative_v1新增8条）已记录用户批准及用户转述的B2复核，另3条隔离。
批准的是标签与分组，不是训练Gate；仍缺样本规模、正式Test排除、独立split及训练环境/资源，见STATUS.md。
各源文件仍保留AI草稿，真实批准记录在私有artifact，不把源文件自动升级为金标；命令见[batches/negative_v1/README.md](batches/negative_v1/README.md)。

同组改写必须保持在同一split。语义类别用于分布检查，不能代替真实标签质量审核。
按用户2026-11-01确认的新策略，由用户作为唯一负责人最终审核原句、标签与分组，记录哈希和真实确认时间。
不再等待B2或第二位审核；历史双人记录不删除。其他人的审核不能冒充负责人批准。
原句或标签修改后，原审批失效。JSON中的身份字段不是数字签名：负责人必须另有真实复核记录。
`source_sha256`绑定原句UTF-8原始字节；排重与保护集排除另用NFKC/大小写/空白规范化哈希，二者不可混用。

旧12条开发题、4条复核题、已用提示示例、之前已检查的行人超车长指令均列入排除清单。
它们仍可用于原方案回归，但不能混入新训练/验证集来宣称独立提升。
还需要数据/评测负责人提供正式Frozen Test的**文本哈希排除清单**，不需要其标签。
原B1/Student数据不自动导入：输出契约、来源和split需要另行审核。

`plan.json`暂定200条Train、50条Val，且两侧覆盖6类。这只是建议的工程data-smoke门槛，
不是样本足够、训练有效或比赛通过的证明。当前24条未标注数据显然不满足要求。
即使数据通过预检，也仅是 `data_ready_for_tokenization`，`ready_for_training`仍为false。

## 命令

在独立仓库根目录运行。Python可先使用既有解释器做只读预检，不在该环境安装训练依赖。
所有输出目录必须是新目录。

```bash
python -m experiments.semantic_sft.prepare review \
  --output-dir artifacts/semantic_sft/review_<批次>

# 可选：生成包含AI候选标签、逐步表格和复核提示的待审包；不会填写label或批准。
python -m experiments.semantic_sft.prepare draft \
  --output-dir artifacts/semantic_sft/ai_drafts_<批次>

# 明确收到真实人工批准后，才可记录首轮审核。以下占位符必须替换为真实信息。
# first-review仅用于尚无人工标签/记录的草稿；3条契约缺口不会被批准。
python -m experiments.semantic_sft.review first-review \
  --input <原草稿队列JSONL> --reviewer-id <真实审核人标识> \
  --reviewed-at <实际记录时间含时区> \
  --approval-reference <实际人工授权出处> --approval-quote <原批准内容> \
  --output-dir artifacts/semantic_sft/first_review_<批次>

# 可在审核后做长度/mask诊断，但这不等于训练数据导出或训练准入。
python -m experiments.semantic_sft.review token-audit \
  --input artifacts/semantic_sft/first_review_<批次>/review_queue.jsonl \
  --model-path /home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B \
  --output-dir artifacts/semantic_sft/token_audit_<批次>

# 人工填写review_queue.jsonl中的label，再生成签审用哈希；此命令不生成审批记录。
python -m experiments.semantic_sft.prepare hashes \
  --input artifacts/semantic_sft/<人工填写批次>/review_queue.jsonl \
  --output-dir artifacts/semantic_sft/hashes_<批次>

python -m experiments.semantic_sft.prepare preflight \
  --input <人工复核后的JSONL> \
  --external-protected-registry <负责人提供的哈希清单.json> \
  --output-dir artifacts/semantic_sft/preflight_<批次>

# 只有同一数据预检通过才会导出train.jsonl/val.jsonl；失败只输出报告。
# 划分预览另用以下命令，仅生成候选和quarantine，不改原审核快照，不生成训练文件。
python -m experiments.semantic_sft.prepare split-preview \
  --input artifacts/semantic_sft/second_review_b2_20261101/review_queue.jsonl \
  --output-dir artifacts/semantic_sft/split_preview_<新批次>

python -m experiments.semantic_sft.prepare export \
  --input <人工复核后的JSONL> \
  --external-protected-registry <负责人提供的哈希清单.json> \
  --output-dir artifacts/semantic_sft/export_<批次>

python -m experiments.semantic_sft.prepare environment \
  --model-path /home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B \
  --tokenizer-smoke --output-dir artifacts/semantic_sft/env_<批次>

# 只用config在meta设备构建真实模型结构，不加载权重、创建adapter或初始化CUDA。
python -m experiments.semantic_sft.prepare environment \
  --model-path /home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B \
  --module-audit --output-dir artifacts/semantic_sft/meta_modules_<批次>
```

排除清单v2必须包含实际集合角色、frozen=true、精确source_revision、test_version、真实publisher及非空text_sha256。
Normalization固定为nfkc_casefold_remove_whitespace_v1。Validation清单不能替代Frozen Test，来源真实性仍须负责人确认。
完整生成与交接步骤见EXCLUSION_HANDOFF.md。

## 当前服务器只读检查结果

- 原服务环境具有Torch 2.11.0、Transformers 5.14.1，缺PEFT、Datasets、Accelerate、TRL等。
  原环境未安装/升级任何依赖。新.venv已安装PEFT 0.21.2和Accelerate 1.15.0，复用原Torch/Transformers只读文件。
- 模型架构为`Qwen3_5ForConditionalGeneration`。
- 候选正则仅在语言主干的6层全局attention中匹配12个q/v模块，排除了visual和MTP。
  这不是“所有24层都做了LoRA”，更不是已经验证的最佳配置。
- 2026-10-30用真实meta模型核对这12个模块与权重索引一致：q_proj形状4096x2048，
  v_proj形状512x2048。r=8时A/B矩阵参数估算417792；不是实际PEFT注入结果或模型效果。
- 只读tokenizer小测试可验证当前chat模板前缀和assistant结束token。
  单条单元样例通过不代表真实数据全部通过，更不代表完整Trainer已跑通。
- 累计29条标签已通过真实tokenizer逐条诊断；B2确认未改标签，哈希逐项匹配；仍缺完整训练数据上的正式mask审计。
- PEFT实际注入、仅LoRA可训练、GPU1前后向、独立adapter保存/重载已通过合成协议单元smoke。
  这不等于完整业务数据训练、语义评测或正式训练环境已冻结。
- 预检额外报告首轮审核数据的改写组覆盖。新增8条获批后禁止类已有5组，六类满足最低组数；
  这不等于已证明跨批独立或数量充足。诊断不会自动划分数据、拆散同组或降低门槛。

PEFT支持正则形式的target_modules，但后续仍须检查实例化模块与可训练参数：
[官方LoRA配置说明](https://huggingface.co/docs/peft/main/package_reference/lora)。
assistant-only loss依赖正确的chat模板边界，不能仅设一个开关就假定mask正确：
[TRL官方SFT说明](https://huggingface.co/docs/trl/v0.26.0/en/sft_trainer)。

## 后续顺序

当前29条已审核记录的划分预览为Train 18 / Val 11，3条隔离另存。固定seed=20261101，
每类按SHA256(seed,family,group)排序取一个完整组作Val，不看标签或模型成绩，也不强凑80/20。
两侧覆盖6类、组无交集，但这只是小样本候选：没有正式Test排除清单，数量未到200/50，不能作为训练准入或泛化证明。
新数据加入后分组选择可能变化，不能将此视为已经冻结的分配；旧审核快照始终保留。

后续数据补充/审核 → 保护集排除与分组split冻结 → 独立环境和完整数据token/mask检查 →
在不共享生产GPU的条件下做小规模训练smoke → 独立adapter离线评测 → 旧方案回归与多模态检查 →
用户确认后才考虑新端口试运行。不得直接替换原服务、权重目录或将候选合并到生产分支。
