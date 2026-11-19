# V3：条件口径、协议与Train组平衡

本轮只在`qwen_semantic_adaptation`实验目录改动，不接入CARLA控制、生产服务或7B历史方案。
仍使用固定revision的Qwen/Qwen3.5-2B和417792个语言q/v LoRA参数；不合并基础权重、不自动部署。

## 为什么重训

V2已完成3 epochs、192次更新。其Dev动作26/75→54/75、完整语义0/75→31/75，
但仍丢失1条基座原本正确的动作序列，结论为`NO_ADMISSIBLE_CANDIDATE_KEEP_BASELINE`。
完整语义的基座0分不等于完全不理解指令：旧短prompt下存在大量协议错误。
V2权重保留为诊断材料，不能称为已晋升或正式Gate。

## 已完成的修订

用户明确答复“批准上述18条条件口径修订并重训”。只修改18条的19个condition槽位：

- 16条旧路口转弯记录补上原文“在前方路口”。
- 2条状态加路口约束的记录引用包含两者的连续原文；其中1条的转弯与并列设速共享条件。
- 原句、动作、顺序、目标、方向、速度、距离、group和split不变；保留旧proposal和review，追加本次批准。
- 不增加合成句子，不假称采集了真实口语，不把Dev错误改写后放入Train。

数据：`artifacts/semantic_sft/releases/semantic_text_sft_v3_20261102/`。
Train254、Dev75，原3条契约缺口继续隔离；旧v1/v2及其成绩不覆盖。
manifest SHA256：`59e8913f1a6e7d108c53547e324525eb51325673bb78fa0cef33a5245295f1d8`。
修订前后Dev严格标签不同，不能拿新完整语义分数直接减旧分数作为提升；须在同一V3协议和标签上重测基座。

`revision.py draft`只产生待审候选；`freeze`要求绑定proposal哈希的真实负责人批准，拒绝顺带修改动作或split。
授权字段本身不是身份签名；实际用户答复保留在当前对话，审批文件记录的是登记时间，不猜测消息时间。

## 训练改进及兼容边界

1. 新prompt完整写明动作含义、JSON形状、方向枚举、禁止事项对象、单位、条件范围。
   无Dev/Test few-shot、无关键词动作分类或输出修补；同一prompt同时用于训练、基座生成和候选生成。
2. prompt全文与SHA写入新manifest，CPU token报告绑定该prompt；不能沿用旧短prompt的token报告。
   `chat_record`、token审计和训练验证保留旧默认值，因此旧版发布仍可复验。
3. `--group-action-weighting`仅统计Train：按动作出现的组数取逆平方根，按组内条数平衡；
   权重先相对均值截到0.5–2，再归一为均值1，实际数值保存在`train_weights.json`。
   同一组内重复模板不当作新的动作覆盖；每条Train每轮仍恰好访问一次，不丢弃常见动作。
4. `--gradient-checkpointing`使用非重入激活重算节省显存，默认关闭，旧运行不受影响。
5. 其余仍为3 epochs、lr5e-5、累计4、192次更新；本轮是联合改进实验，不用于分离各项贡献。

## 启动检查及命令

必须先运行真实tokenizer全量审计，通过后才能启动；检查source已提交且干净、文件哈希、排除集、GPU空闲、
基础模型实际fingerprint和生产READY。GPU0禁止；不得停止或共享其他人的GPU任务。

```bash
.venv/bin/python -m experiments.semantic_sft.review token-audit \
  --input artifacts/semantic_sft/releases/semantic_text_sft_v3_20261102/reviewed_rows.jsonl \
  --system-prompt-file artifacts/semantic_sft/releases/semantic_text_sft_v3_20261102/system_prompt.txt \
  --model-path /home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B \
  --output-dir artifacts/semantic_sft/frozen_329_v3_token_audit_20261102

.venv/bin/python -u -m experiments.semantic_sft.train \
  --release-dir artifacts/semantic_sft/releases/semantic_text_sft_v3_20261102 \
  --release-manifest-sha256 59e8913f1a6e7d108c53547e324525eb51325673bb78fa0cef33a5245295f1d8 \
  --token-audit artifacts/semantic_sft/frozen_329_v3_token_audit_20261102/report.json \
  --model-path /home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B \
  --gpu-index 6 --semantic-validation --group-action-weighting --gradient-checkpointing \
  --output-dir artifacts/semantic_sft/semantic_text_lora_v3_20261102_01
```

## 什么才算结果

先生成75条基座Dev，再在每轮后生成75条候选，共300次；开始加载/基座生成不代表已经反向更新。
严格保留逐条不退化检查：任一基座正确动作或整条语义退化，则该轮不入候选池，不降低门槛挑权重。
仍按完整语义、动作序列、引用有效性、loss排序，全部不合格就保留基座。
应查看目标、条件、禁止事项、确认、数值及六类分项，不能只看schema或loss。

旧12题已经曝光，仅保留已知回归/排除角色。新独立Final Test与CARLA真实路况下执行验证尚未完成，
本轮只能给开发候选及诊断，不是闭环、视觉能力或正式性能Gate证明。
