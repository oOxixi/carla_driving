# 多 Head 蒸馏的标签、mask 与 loss

上级：[训练模块](../modules/challenge-training.md)。

## 训练到底在优化什么

[label_encoder](../../../challenge/distillation/label_encoder.py) 将 Teacher ManeuverPlan 编为定长监督；[MultiHeadDistillationLoss](../../../challenge/distillation/losses.py) 消费模型输出和标签字典，返回 total 与每个 component。A1 plan_length 实际 1..4，分类标签为 0..3；不要将实际长度直接送 CE。

| Head | 当前损失 | 有效区域 |
|---|---|---|
| behavior、target_pointer、target_lane、completion、on_failure | 分类交叉熵 | step_mask，并应用 sample_weight |
| target_speed | Smooth L1 | `target_speed_mask & step_mask`，不是所有有效步骤都有速度监督 |
| confidence | Smooth L1 | 按样本权重，全计划 |
| replan | 多标签 BCE | 全计划的各重规划条件 |
| plan_length | 分类交叉熵 | 每个样本 |
| requires_confirmation | BCE with logits | 每个样本 |

total 按 LossWeights 加权求和。默认 behavior=2.0、target_pointer=1.5；其余权重在类与训练配置中明确给出。class_balance 是额外类别权重，不等于 sample_weight，且应该只从 Train 估计。

## Soft teacher 的具体范围

当前仅 behavior 与 target_pointer 可通过 `_mix_soft` 加 KL；缺 Teacher soft_probs 或 soft_alpha≤0 时回到 hard loss。概率 Shape 必须与 logits 一致，Teacher 概率先裁剪、归一化，KL 带 temperature²，并以 soft_alpha 混合。不能在报告中笼统声称十个 Head 都做 soft distillation。

## 改动时不能遗漏

- padding Head 值是中性占位，mask 才决定是否参加训练；不能“预测 PAD 正确”提高指标。
- 新增 Head 要同时改 model/contract、label_encoder、loss、evaluate/metrics 与 Adapter；仅加 Linear 不会自动被训练。
- 速度单位始终 m/s；把 km/h 标签直接送 loss 会得到系统性偏差。
- 训练 loss 的下降与有效计划、闭环成功、B2/B3 Gate 是不同证据。

验证入口：[distillation tests](../../../challenge/distillation/tests)、[A1 training contract](../../../challenge/student/training_contract.py)。调整 mask/权重时应验证 padding 不贡献梯度、无速度标签步骤不计速度误差、类别权重维数正确，以及 train/val 统计互不污染。
