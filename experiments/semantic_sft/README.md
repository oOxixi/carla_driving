# 独立的Qwen 2B语义微调准备区

本目录只做数据复核、导出和只读预检，**没有训练入口，也不会启动训练**。
这是Qwen本体的任务适配准备，不是challenge里的Student/A3蒸馏训练。

## 与原方案隔离

- 分支：`qwen_semantic_adaptation`，从 `f92ac6fcc8e8c55e3b3a63825b6f4386d49b6d78` 创建。
- 本机目录：`C:/Users/17733/Documents/Codex/2026-08-06/du/work/carla_driving_qwen_semantic_adaptation`。
- 服务器目录：`/home/tiaozhansai/carla-driving-qwen-semantic-adaptation`。
- 原 `main_optimization`、`main`、`challenge` 不切换、不合并本阶段修改。
- 新代码仅允许位于 `experiments/semantic_sft/`；CLI检查相对原提交是否有目录外改动。
- 输出只能写入新工作区的 `artifacts/semantic_sft/<新目录>`，不允许覆盖已有文件。
- 不安装或升级原环境，不重启8000/18005服务，不加载基础模型权重到GPU。
- 不覆盖、合并或发布基础权重；未来候选仅保存独立LoRA adapter。
- 不在生产服务占用的GPU上同时启动训练。需要单独确认GPU和新训练环境。

固定基础模型：`Qwen/Qwen3.5-2B`；revision：
`15852e8c16360a2fea060d615a32b45270f8a8fc`；期望artifact fingerprint：
`4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`。
这只是版本约束，环境预检不会伪称已经重新核验全部权重fingerprint。

## 已准备什么

| 文件 | 内容 |
| --- | --- |
| `seeds.jsonl` | 24条新编写的待标注文本，6类问题、12个同义改写组；不是训练成品 |
| `draft_labels.jsonl` / `proposals.py` | AI编写的24条待审标签及原句绑定；不是Qwen推理结果或人工真值 |
| `record.schema.json` | 单条数据、来源、分组、split、双人复核记录的格式 |
| `ANNOTATION_GUIDE.md` | 任务拆解、条件、否定、目标和歧义的人工标注说明 |
| `data.py` | 原方案保护、数据泄漏检查、审批哈希校验、SFT消息格式 |
| `environment.py` | 依赖/权重索引只读检查、CPU tokenizer和assistant loss mask小测试 |
| `prepare.py` | review / draft / hashes / preflight / export / environment；没有train命令 |
| `plan.json` | 尚未批准的候选LoRA配置与工程数据门槛，不是比赛正式Gate |
| `tests/` | 路径隔离、泄漏、双人审批、失效审批、mask等软件测试 |

## 标注与数据门槛

24条种子全部生成 `DRAFT`、`label=null`、`reviews=[]`、`split=UNASSIGNED`。
程序不自动批准标签，不把旧Qwen输出当正确答案，不把同一模型自评当人工复核。

同组改写必须保持在同一split。语义类别用于分布检查，不能代替真实标签质量审核。
两个不同reviewer必须独立确认**原句和标签**，记录两者SHA256和真实时间。
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

# 人工填写review_queue.jsonl中的label，再生成签审用哈希；此命令不生成审批记录。
python -m experiments.semantic_sft.prepare hashes \
  --input artifacts/semantic_sft/<人工填写批次>/review_queue.jsonl \
  --output-dir artifacts/semantic_sft/hashes_<批次>

python -m experiments.semantic_sft.prepare preflight \
  --input <人工复核后的JSONL> \
  --external-protected-registry <负责人提供的哈希清单.json> \
  --output-dir artifacts/semantic_sft/preflight_<批次>

# 只有同一数据预检通过才会导出train.jsonl/val.jsonl；失败只输出报告。
python -m experiments.semantic_sft.prepare export \
  --input <人工复核后的JSONL> \
  --external-protected-registry <负责人提供的哈希清单.json> \
  --output-dir artifacts/semantic_sft/export_<批次>

python -m experiments.semantic_sft.prepare environment \
  --model-path /home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B \
  --tokenizer-smoke --output-dir artifacts/semantic_sft/env_<批次>
```

哈希排除清单格式：`normalization="nfkc_casefold_remove_whitespace_v1"`、真实`publisher`、
非空`text_sha256`数组。来源真实性仍需负责人确认，不得自行填假publisher来绕过排除检查。

## 当前服务器只读检查结果

- 原服务环境具有Torch 2.11.0、Transformers 5.14.1，缺PEFT、Datasets、Accelerate、TRL等。
  未安装任何依赖；正式训练必须另建环境并冻结兼容版本。
- 模型架构为`Qwen3_5ForConditionalGeneration`。
- 候选正则仅在语言主干的6层全局attention中匹配12个q/v模块，排除了visual和MTP。
  这不是“所有24层都做了LoRA”，更不是已经验证的最佳配置。
- 只读tokenizer小测试可验证当前chat模板前缀和assistant结束token。
  单条单元样例通过不代表真实数据全部通过，更不代表完整Trainer已跑通。
- 目前缺少实际模型实例上的PEFT模块匹配、数据级token长度/mask审计、独立GPU安排与训练入口。

PEFT支持正则形式的target_modules，但后续仍须检查实例化模块与可训练参数：
[官方LoRA配置说明](https://huggingface.co/docs/peft/main/package_reference/lora)。
assistant-only loss依赖正确的chat模板边界，不能仅设一个开关就假定mask正确：
[TRL官方SFT说明](https://huggingface.co/docs/trl/v0.26.0/en/sft_trainer)。

## 后续顺序

人工标注与真实双人复核 → 保护集排除与分组split冻结 → 独立环境和数据级token/mask检查 →
在不共享生产GPU的条件下做小规模训练smoke → 独立adapter离线评测 → 旧方案回归与多模态检查 →
用户确认后才考虑新端口试运行。不得直接替换原服务、权重目录或将候选合并到生产分支。
