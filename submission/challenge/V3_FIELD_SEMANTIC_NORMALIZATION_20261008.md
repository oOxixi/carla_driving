# V3 字段语义归一化诊断（2026-10-08）

## 结论

可以对齐字段约定后重算，而且结果证明原始极低的 lane/sequence 指标大部分来自
`target_lane=null` 与 `target_lane=CURRENT` 的表示差异，而不是同等规模的驾驶行为错误。

在不修改原始预测、不修正任何换道/转向/避障动作、也不改变其他字段的前提下：

| 指标 | 原始严格口径 | 语义归一化口径 | 提升 | 归一化后阈值投影 |
|---|---:|---:|---:|---|
| behavior accuracy | 94.2748% | 94.2748% | 0 | FAIL |
| target pointer accuracy | 98.4733% | 98.4733% | 0 | FAIL（仅超限 0.0267 个百分点） |
| target lane accuracy | 17.1756%（45/262） | **89.3130%（234/262）** | **+72.1374 个百分点** | FAIL |
| completion accuracy | 92.7481% | 92.7481% | 0 | FAIL |
| plan sequence accuracy | 10.8333%（26/240） | **86.6667%（208/240）** | **+75.8333 个百分点** | FAIL |
| safety-critical behavior recall | 100% | 100% | 0 | PASS |

归一化恢复了 189 个正确 lane step 和 182 个完整正确 plan；仍有 28 个 lane step、
32 个完整 plan 不一致。因此，字段约定解释了主要差距，但不能把 V3 改判为 PASS。

## 固定规则

工具：`tools/analyze_v3_field_normalization.py`。

仅当 Student 预测步骤满足以下两个条件时，评分副本把
`target.target_lane=null` 映射为 `CURRENT`：

1. 预测行为属于固定集合
   `KEEP_LANE/SET_SPEED/SLOW_DOWN/STOP/YIELD/FOLLOW/HOLD`；
2. 原预测的 `target_lane` 确实为 `null`。

本次共调整 204 个步骤、涉及 201 个样本：`SET_SPEED=88`、`STOP=44`、
`KEEP_LANE=38`、`FOLLOW=29`、`SLOW_DOWN=5`。

`CHANGE_LANE_LEFT/RIGHT`、`TURN_LEFT/RIGHT`、`AVOID_OBSTACLE`、
`RETURN_TO_LANE`、`PULL_OVER` 等 lane-critical 行为完全不修正。behavior、target
pointer、completion、原始预测文件和冻结标签均不修改。

## 输入绑定

- 数据集：`b1_independent_validation_v1`，240 条；
- case-set digest：`da1d032f7d20147a26e4426c10a97def8b470a780b854ea852143697292f7dec`；
- Student raw predictions SHA256：
  `07e8f33dd6e3a8f0234c875efb8c9a58f307f625de08cc0afad5e5f7bcba5e58`；
- Teacher reference SHA256：
  `96d8545b129bf32cd1ae15787ad1f53aa735324eb659c6ea7ae77f4f3d024bdd`；
- 输出目录：`artifacts/b2_role_exception_v3_20261008_semantic_normalized/`。

工具重新计算原始严格指标并与既有诊断逐项绑定，只有绑定一致后才执行归一化；
同时断言除 target lane 和由其参与的 plan sequence 外，其余指标不得变化。

## 使用边界

该结果是 `POST_HOC_DIAGNOSTIC_ONLY`，不能覆盖原始严格结果，也不能直接签发 B2 Gate。
原因是规则在独立集标签已经暴露后才进行验证。正式使用时必须由 B2 在评估前冻结
同一语义等价规则，并在新的未暴露 benchmark 上评估新候选。禁止用这 240 条结果
进行训练、校准或逐样本修正。
