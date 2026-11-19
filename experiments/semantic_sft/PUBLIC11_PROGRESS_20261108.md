# 公开Train原句补充：内部数据发布、真实2B诊断与V14启动

日期：2026-11-08。工作分支：qwen_semantic_adaptation。

本文件保留启动时记录。2026-11-09任务已完成，最终结果见`V14_PUBLIC11_RESULT_20261109.md`；不是仍在训练。

## 已连续完成

1. 保留第10条`requires_confirmation=true`审批版本；按用户明确选择，不进入Train/Val。
2. 其余11条采用已批准标签；仅追加Train，原370条记录不改、旧Val文件逐字节不改。
3. 固定内部研究数据`semantic_text_sft_v8_public11_20261108`：Train306、Val75。
4. 新版本同时存放本机及tiaozhansai；381条CPU tokenizer/loss-mask检查全部通过，最长1025 tokens，无截断。
5. 原始2B与V13 epoch6在新增11条上完成22次真实生成，输入逐条同prompt-token哈希，无语法修复、无重试，无控制器或安全层参与。
6. 启动独立2B V14候选；不合并adapter、不替换生产、不修改7B。

## 来源许可处理：纠正不必要的阻塞，但不伪造确定性

检查固定作者仓库commit `d1055a58d673468b4471e020626e8306ae6e4cb6`的完整归档，
根MIT许可证存在；README明确同时提供MIVS数据和代码；可见归档仅一个许可证文件，
没有找到额外数据例外说明。归档中的aispeech.zip与已审计数据SHA256一致。

本次依据**发布者公开根许可证适用于随仓库发布资源的推断**，完成内部研究候选数据准备，
保留许可证、作者引用、固定来源、原始空标注与人工再标注关系。
这不是作者额外授权，不保证上游所有权或对外提交/再分发权利；风险写入`source_license_review.json`。
没有把“未见单独声明”写成“禁止训练”，也不再要求用户为每个工程步骤重新确认。
对外再分发和正式比赛许可仍不在本次认证范围内；没有对作者发信或发issue。

来源：

- https://github.com/X-LANCE/MIVS_BIRGAT
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

## 真实诊断结果

这11条是新Train候选诊断，不是独立Test、正式比赛成绩或CARLA执行成功率。

| 严格计数 | 原始2B | 冻结V13 epoch6 |
| --- | ---: | ---: |
| JSON/schema合法 | 11/11 | 11/11 |
| 动作顺序完全匹配 | 10/11 | 7/11 |
| 整条语义精确匹配 | 0/11 | 3/11 |
| target_text逐字段匹配 | 0/11 | 10/11 |
| condition逐字段匹配 | 1/11 | 6/11 |

动作及整条匹配必须分开报告：LoRA改善了目标/空槽格式，却在部分基础短指令上变得过度请求确认。
这些是模型直接输出，不是SafetySupervisor覆盖造成的现象。

V13严格未匹配8条的复核：

- 001“向左转”、002“嗯向右转”、005“走到底右转”、012行人礼让，共4条输出HOLD/confirmation=true。
  其中001/002/012是相对原始2B新增的动作退化；005原始2B也没有正确完成。
- 004/006/011共3条遗漏距离或路口前提。
- 009输出“在前方路口”，已批准参考为“前方路口”：这是严格连续片段边界差异，可能语义等价，
  **不能与前述动作错误同样解释为危险决策**。保留原始严格得分，不根据模型答案重写已批准标签或放宽评分。

首轮诊断完成11条BASE后，汇总脚本因缺`semantic_family`报错；保留失败日志与全部原输出。
续跑补齐元数据、重算核对旧得分，仅新生成V13的11条；没有重跑BASE11。

## V14候选边界

- 模型：Qwen/Qwen3.5-2B，revision `15852e8c16360a2fea060d615a32b45270f8a8fc`。
- 指纹：`4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`。
- 从固定base重新训练独立LoRA，不覆盖/续写旧V13 adapter。
- 数据：新增11条Train；旧Val75不改。第10条及Frozen Test/已评测holdout不用于训练或选型。
- 沿用V13配方：10 epochs、lr5e-5、weight_decay0.01、accumulation4、clip1、warmup8、seed20261101。
- 沿用group-action weighting、gradient checkpointing、action-only字段loss（action值权重4，其余1）。
- 计划在3/6/10轮输出Train诊断和Dev语义；Train诊断不用于挑最佳模型。
- 同10轮但Train295增加到306，更新次数及LR时间跨度预计740变770；不是固定更新数的纯单因子消融。
- 只占用空闲GPU2；GPU0保护，既有服务不停止。
- 源码为服务器干净提交`ee3f1e8adf6242f9b0f3c44630bf6d325dbab1df`，本轮不改运行时实现。
- 训练入口默认会生成本轮BASE Dev用于自身guard；V13的比较使用缓存原始结果，不重新跑V13 Dev。
- 尚未完成训练，不宣称已提高准确率或通过Gate；后续需核对旧Dev正确样本的新增退化，绝不自动部署。

## 关键路径

本机相对于语义工作区：

- 新数据：`artifacts/semantic_sft/releases/semantic_text_sft_v8_public11_20261108/`
- 分词审计：`artifacts/semantic_sft/public11_token_audit_20261108/report.json`
- 完成的2B对比：`artifacts/semantic_sft/public11_diagnostic_resumed_20261108/`
- 训练启动记录快照：`artifacts/semantic_sft/v14_public11_launch_20261108/launch.json`

服务器工作区：`/home/tiaozhansai/carla-driving-qwen-semantic-adaptation`。
训练动态状态：`artifacts/semantic_sft/semantic_text_lora_v14_public11_20261108_01/report.json`。
训练日志：`artifacts/semantic_sft/v14_public11_launch_20261108/training.log`。

本轮语义实验测试215 passed、1 skipped；没有运行ASR/CARLA/延迟/正式部署基准，没有推送GitHub。
