# 训练恢复、纯权重候选与晋级是三种不同交付

上级：[训练模块](../modules/challenge-training.md)。

## 三种对象的用途

| 对象 | 实现 | 内容与消费者 |
|---|---|---|
| checkpoint | [checkpoint.py](../../../challenge/distillation/checkpoint.py) | model/optimizer/scheduler 状态、epoch/global_step/best_metric、metadata、extra_state、Python/Torch/CUDA RNG；供训练恢复 |
| candidate weights | [artifacts.py](../../../challenge/distillation/artifacts.py) | 纯 model state_dict 与候选 manifest；供 A1 backend 加载，不带优化器 |
| promoted manifest | [promote.py](../../../challenge/distillation/promote.py)、artifacts | 将独立评测与阈值结论写入身份清单；不是训练 checkpoint 的别名 |

checkpoint 使用临时文件再 replace。恢复会检查 format_version，加载权重及可选 optimizer/scheduler，并恢复 RNG；即使 map_location=cuda，CPU RNG 状态也转回 CPU。删掉这个 `.cpu()` 看似简化，实际会破坏 GPU 恢复。

## 当前 Gate 约束与缺口

mock/integration smoke 不能晋级生产。旧的 pinned Teacher 流程核验 Teacher 身份、候选权重 hash、Validation 类型和指标；D2 mixed-cohort 正式训练有独立策略，目前文档明确不授权晋级。

已确认缺口：`_validate_evaluation_identity` 未绑定 Student 评测的 weights_sha256/model_id/config_id，故当前 Gate 不能充分证明分数属于当前候选。这个问题仅记录，尚未修复。后续不能用手工写 `A3_FP32_GATE_PASSED` 来弥补证据关联。

## 修改建议的阅读顺序（不是本轮已实施行为）

改 checkpoint：先读 train 的 resume 调用及元数据兼容检查，再改 save/load，最后验证连续训练与恢复训练一致性。
改晋级：先明确评测文件的 Student/Validation 身份字段，再改 evaluate 生产端、promote 消费端、backend 的清单检查与测试。不能只在消费者要求一个上游从未生成的字段。

验证：[test_artifacts.py](../../../challenge/distillation/tests/test_artifacts.py)、[训练测试目录](../../../challenge/distillation/tests)、[test_delivery.py](../../../challenge/tests/test_delivery.py)。生产接入还需要真实 Student 权重，而 DummyStudent 测试只证明流程。
