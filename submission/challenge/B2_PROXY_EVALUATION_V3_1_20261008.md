# B2 代理执行评测报告（V3.1，2026-10-08）

## 结论

A2 已代理执行当前仓库中能够完成的 B2 测试流程。代码合同测试现为
`197 passed / 0 failed / 0 errors`；V3.1 FP32 在 B1 Independent Validation v1 的
240 条上再次实际回放，240/240 成功，预测文件与上一轮逐字节一致，
聚合指标按仓库当前阈值的投影结论为 **PASS**。

本结果不是独立 B2 签发，正式状态仍为 `BLOCKED_NOT_FINAL`。该 240 条标签在
Adapter V3.1 修订前已暴露给 A2，因此这次只能作为可复算的 post-hoc 回归证据，
禁止改名为 `A3_FP32_GATE_PASSED`。

在这份历史回放之后，A2 又先冻结了新的 240 槽 Seen/Variant/Unseen 采集与 policy，
并在另一批 308 条候选未使用的 Seen 硬负样本上执行固定规则压测。新压测 308/308
成功但阈值投影为 **FAIL**；所以旧 240 条 post-hoc PASS 不能作为当前候选晋级结论。
完整新增证据见 `B2_PROSPECTIVE_FREEZE_AND_SEEN_STRESS_20261008.md`。

## 冻结身份

- Student model/config：`student-v0-r3-fp32` /
  `student-v0-r3-structure-20260911`；
- FP32 weights SHA256：
  `7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`；
- FP32 ONNX SHA256：
  `681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286`；
- Adapter：`student-plan-adapter-v3.1-semantic-contract`；
- B1 case-set digest：
  `da1d032f7d20147a26e4426c10a97def8b470a780b854ea852143697292f7dec`；
- Student predictions SHA256：
  `75148883dbcaee1a661989136ed4685ee03d56b8327ecebfa811a070e40d3285`；
- Teacher stored-reference predictions SHA256：
  `96d8545b129bf32cd1ae15787ad1f53aa735324eb659c6ea7ae77f4f3d024bdd`。

## B2 代码合同测试

执行范围为 `challenge/benchmark/tests`，覆盖：

- case manifest 与泄漏检查；
- Teacher/Student 原始 predictions 覆盖、失败样本零分保留分母、哈希绑定；
- evaluation artifact/package、Teacher baseline、comparison 与 accuracy report；
- policy-bound Gate decision、篡改拒绝、fail-closed readiness；
- formal bundle/package/publication 的构建与验证；
- V3.1 字段语义归一与 INT8 三方对比计算。

结果：`197 passed / 0 failed / 0 errors / 0 skipped`。JUnit 证据 SHA256：
`f702574b61515d1dcad821e64868f11a1f5d028937c720ffbe4cebd70ac57c35`。

## 真实 240 条指标

| Gate 指标 | Teacher | Student V3.1 | 下降 | 聚合阈值 | 投影 |
|---|---:|---:|---:|---:|---|
| behavior accuracy | 1.000000 | 0.992366 (260/262) | 0.007634 | 0.015 | PASS |
| target pointer accuracy | 1.000000 | 1.000000 (262/262) | 0 | 0.015 | PASS |
| target lane accuracy | 1.000000 | 0.992366 (260/262) | 0.007634 | 0.015 | PASS |
| completion accuracy | 1.000000 | 0.992366 (260/262) | 0.007634 | 0.015 | PASS |
| plan sequence accuracy | 1.000000 | 0.991667 (238/240) | 0.008333 | 0.015 | PASS |
| safety-critical behavior recall | 1.000000 | 1.000000 (28/28) | 0 | 0 | PASS |

Student schema validity = 1.0，推理成功 240/240。重跑得到的 Teacher 与 Student
predictions SHA256 与已冻结 V3.1 证据完全相同，可重复性检查为 `PASS`。

## 必须保留的切片告警

聚合 Gate 投影通过，但不等于每个切片都通过。如果把相同 1.5% 阈值试投影到
切片，有 8 个指标告警：

- `sample_class:complex`：behavior/lane/completion 均为 66/68，下降 2.9412%；
  plan sequence 为 56/58，下降 3.4483%；
- `scenario_family:safety_D`：behavior/lane/completion 和 plan sequence 均为
  91/93，下降 2.1505%。

这些不能直接称为正式切片 Gate FAIL，因为 B2 尚未冻结切片判分政策；但必须在
B2 冻结 policy 时明确是否要求切片同样满足 1.5%。

8 个告警全部由两条 `SUP_A15_lane_change_blocked` 样本造成：

- `td_82f0f6ef99214f0140c5c3e9`；
- `td_8a507cff191360afaf5c3a63`。

两条都是 `left_lane_exists=true` 但 `left_gap_safe=false`。存储的 Teacher plan 输出
`CHANGE_LANE_LEFT`，Student V3.1 按 fail-closed 安全规则输出 `STOP`。因此严格字段评分
判错，但 Student 行为是安全收紧，不建议为追分改回不安全换道。

## 新 240 槽冻结与 308 条 Seen 压测

新冻结 ID 为 `b2-proxy-prospective-unseen-v1-20261008`，规则提交为 `2d59d928`。
它固定了 Seen/Variant/Unseen 各 80 个槽、240 个唯一新 seed、1.5%/0% 门槛、失败零分
保留分母及禁止结果后换样规则。240/240 场景合同有效，并对 7,735 条既有治理记录完成
暴露审计；但 CARLA 与精确 Teacher v4 当前不可达，实际 case set 尚未采集。

固定规则的 308 条候选未暴露 Seen 压测结果为：behavior 0.921512、pointer 1.000000、
lane 0.816860、completion 0.921512、sequence 0.795455、安全召回 1.000000，严格投影
**FAIL**。两次完整运行的 Student predictions SHA256 均为
`c4568227c5f0063aad1362f3d933d1a9f7930466ee8a5b16d4e937b6ba2950dd`。

该 308 条与 Train/Dev/Calibration/旧 IV 的 sample/group/RGB/seed 均零重叠，但场景与
文本模板已见，并且来源是 `HARD_NEGATIVE`；所以它是可复算压力证据，不是新的正式
三队列 Gate。

## 为什么还不能正式签 PASS

1. 执行人是 A2，不是独立 B2 评测方。
2. 该 240 条标签在 Adapter V3.1 修订前已暴露，盲测性已丢失。
3. 新 prospective policy、最小分母和 multi-run rule 已冻结，但对应 240 条实际 cases、
   RGB、Teacher 输出、case manifest 和 case-set digest 尚未采集或签发。
4. 历史 B1 240 条没有 Seen/Variant/Unseen cohort 标注；新三队列目前只有采集槽，
   还不是可评分数据集。
5. Teacher 列使用冻结的 stored plan，未在当前环境重跑 Teacher service。
6. 当前 formal readiness 仍为 `BLOCKED`，不能生成真实 Final promotion。

## 交付位置

- 完整审计目录：`artifacts/b2_proxy_audit_v3_1_20261008/`；
- 可直接发送 ZIP：
  `artifacts/submission/B2_PROXY_AUDIT_V3_1_20261008.zip`；
- ZIP SHA256：
  `9d1975473b5035e75384af98ba0705709d315064de1081022f607f4fe7cab9a5`；
- 核心 audit JSON SHA256：
  `e5ee85f9c35c804f3f061ca2c58d4c7154c7d935108c3ec5abc212b705285c11`；
- ZIP 验证：21 entries，CRC PASS，20 个受管成员逐文件 SHA256 PASS。

包内含实际 Teacher/Student raw predictions、240 条 cases、B1 身份、候选身份、JUnit、
Teacher/Student proxy evaluation、policy/benchmark proxy manifest、Gate 投影、readiness、差异分析与
`SHA256SUMS`。包内明确带有 `A2_ASSISTED_B2_PROXY` 和 `formal_gate_eligible=false`，
不会被误当成正式签发。

新增可发送包：

- `artifacts/submission/B2_PROSPECTIVE_BENCHMARK_FREEZE_V1_20261008.zip`，SHA256
  `a84c66134cc1880db78a2d971192e19603e251db8096b56e88b8f211b224f778`；
- `artifacts/submission/B2_CANDIDATE_UNEXPOSED_SEEN_STRESS_V1_20261008.zip`，SHA256
  `bce32f1dc56b95e036c45ea9b716dca7592bbf091bbc50d36e73a85e642f1339`。

