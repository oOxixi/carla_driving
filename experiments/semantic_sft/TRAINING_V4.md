# V4：语义字段loss单因素对照

## V3实际结论

V3完成192/192次更新和300次Dev生成，保存重载logit误差0；没有合格晋升权重。
在相同V3数据、提示和解码下，基座动作45/75，第3轮60/75；完整语义0/75→35/75。
第3轮丢失4条基座正确动作序列，仍为`NO_ADMISSIBLE_CANDIDATE_KEEP_BASELINE`，不部署、不签Gate。

4条退化属于：静止目标通过误判为让行、漏掉前置保持车道、STOP误判PULL_OVER、漏掉变道后的保持车道。
全部15条动作错误还包括条件恢复误判HOLD、否定转弯与同侧变道混淆、矛盾指令未请求确认。
56条动作序列正确且schema合法的记录中，条件错误13条、方向错误11条、目标错误1条、
速度错误1条、间距错误0条、禁止事项错误3条，以上计数重叠，不能相加当失败总数。
另4条动作正确但schema失败，不能混在这56条槽位对照中。

这些是开发集诊断，不是独立测试或因果证明。当前输出显示的不少问题确实是模型误解，
不能全部归咎于评分；不改Dev答案、评分、门槛，也不把Dev错误改写进Train。

## 本轮只改变训练目标

仍使用已批准且冻结的`semantic_text_sft_v3_20261102`，Train254/Dev75、prompt、优化器、
LoRA参数范围、3 epochs、Train组/动作加权、梯度检查点、生成与选模完全沿用V3。
不新增标签或训练文本，无新的人工审核记录。

增加显式参数`--semantic-field-loss`，默认关闭，因此旧入口保留原行为：

- action值token权重4；非空condition值3；非空direction值2；非空prohibited_actions对象3。
- 其余值、null、JSON语法、EOS为1；prompt仍为0，不参与loss。
- 通过结构化JSON序列化定位字段值，再用真实fast tokenizer的offset核验；不靠在原句里搜索关键词。
  跨字段边界token只要与字段值相交即使用该字段权重，不声称存在完全独立的字段token边界。
- 以加权token损失之和除以权重之和，再乘V3原有Train样本权重；不是扩大整个loss/学习率。
- 只计算预测assistant的尾部logits，验证因果位移及最后一个无监督logit，避免创建完整prompt词表张量。
- 每条Train的mask摘要及哈希写入`field_loss_audit.json`；不从Dev/Test统计字段权重。

这是预先固定的工程实验权重，不是已证明的最佳配方。训练侧loss定义已变，不能与V3训练loss直接比较；
验证loss仍为原始未加权token CE，语义评分与基座逐条不退化门槛未变。

V4启动命令在V3命令上追加`--semantic-field-loss`，使用新的输出目录
`artifacts/semantic_sft/semantic_text_lora_v4_20261102_01`，绝不覆盖V3。
先通过本机/服务器软件测试及真实Train254条offset/mask审计，提交并固定源码，再检查GPU6空闲和生产READY。

## 未完成边界

V3新权重并未接管生产服务。新Final Test与CARLA实际路况执行验证仍缺失；
本轮就算Dev提高也不能当作最终独立准确率。若再次出现任一基座正确案例退化，仍拒绝晋升。
