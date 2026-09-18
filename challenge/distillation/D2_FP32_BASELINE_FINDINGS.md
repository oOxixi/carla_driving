# A3 D2 v1.1 首轮 FP32 基线：结果与不能宣称的结论

训练证据：独立服务器工作目录 `/home/tiaozhansai/carla-driving-challenge-a3-prep`，
干净代码提交 `f188264ee2fe90612631f3db530e10d2d8d8edda`，配置
`d2_v1_1_formal_config.yaml`，A3 视图 manifest SHA
`f797725014f297bf1ca43444b95a9aa43bf566abb4fcaebfc1841b4851cd8fcf`。
运行产物为
`artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v2/`。

本轮使用严格正样本 Train 2332、Val 489，Qwen/Qwen3.5-2B pinned Teacher 标签，
3 epoch、876 更新。最佳权重 SHA256 为
`bafade09d155af34ec0b394b8d56c9f7481a36e09a341782bc93d0830fefb681`；
候选状态仍为 `PENDING_A3_FP32_GATE`。被选中 checkpoint 的 Val 类别计划
`plan_sequence_accuracy=1.0`，`target_speed_mae=0.642 m/s`；速度误差大于
1 m/s 的 Val 难例仍有 109 条。以上均为**开发 Val**，不是独立 Test、真实闭环或
比赛成绩。最佳 checkpoint 与最后 epoch 指标可能不同，后续产物应使用
`best_validation`，不得把最后 epoch 的指标误归给最佳权重。

## 模板捷径诊断

只读脚本 `shortcut_probe.py` 发现：

- Val 489/489 的精确 `source_text` 均在 Train 出现；489/489 的 `scenario_id` 也在 Train 出现。
- 不读 RGB、只按 Train 中同文本最常见的计划类别签名查表，就能在 Val 匹配 477/489（97.55%）。此签名覆盖 `plan_sequence_accuracy` 的离散字段，不覆盖数值速度。
- 只用 `allowed_behaviors`/`command_hint` 等请求字段的规则可猜中 Val 首步 Behavior 438/489（89.57%）。

这**不证明 B1 的 group-aware route/seed 划分错误**；它证明当前 Val 无法检验未见指令模板或未见场景的泛化。模型的 100% 不能解释为“多模态真实驾驶能力已达标”。B1 后续需发布真实新增、模板/场景独立的评测组，B2 冻结独立评价口径；详见 [B1_D2_COVERAGE_REQUEST.md](B1_D2_COVERAGE_REQUEST.md)。

## 模态遮蔽（同一 v2 最佳权重、同一 Val）

| 输入 | 类别计划准确率 | 速度 MAE (m/s) |
| --- | ---: | ---: |
| 全部模态 | 100.00% | 0.642 |
| RGB 置零 | 97.96% | 2.375 |
| 文本置零 | 99.39% | 1.233 |
| 目标置零 | 90.39% | 1.070 |
| 状态置零 | 46.22% | 4.992 |

遮蔽会制造训练分布外输入，仅能作敏感性诊断，不是模态因果贡献或安全评测。
RGB 对速度回归和少数计划确实有影响，但状态与模板提示足以解释当前 Val
的大部分离散计划成绩。不能据此移除 RGB，也不能宣称模型已经学到视觉避障。

## 可复现性与后续 Gate

在同一服务器、同一固定数据/种子下，确定性设置开启后的两次独立两步 Smoke
产生逐字节相同的 `training.jsonl` SHA
`746d13742053b389ec350e4fb8b048080d26669adfcec6636cbb9e621f094b74`
和权重 SHA
`d64c85dcb31e4a6fdd26c5361b0d3b4a8ec071e556199b7ab78e15fbf5779af0`。
这证明短跑重复性；完整 3 epoch 仍需在同一新代码提交上复跑比对。

在 B2 提供独立、模板/场景不重合的评测与 Teacher 对照之前，A3 不提交
`A3_FP32_GATE_PASSED`，也不使用 Reserved/Frozen Test 调参。下一轮 A3
可以在固定数据上分析 109 条速度难例，但应优先得到真正可测泛化的新数据，
不要针对这个高重合 Val 的 100% 继续调参。
