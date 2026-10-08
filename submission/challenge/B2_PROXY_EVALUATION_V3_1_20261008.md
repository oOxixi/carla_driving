# B2 代理执行评测报告（V3.1，2026-10-08）

## 结论

A2 已代理执行当前仓库中能够完成的 B2 测试流程。代码合同测试为
`184 passed / 0 failed / 0 errors`；V3.1 FP32 在 B1 Independent Validation v1 的
240 条上再次实际回放，240/240 成功，预测文件与上一轮逐字节一致，
聚合指标按仓库当前阈值的投影结论为 **PASS**。

本结果不是独立 B2 签发，正式状态仍为 `BLOCKED_NOT_FINAL`。该 240 条标签在
Adapter V3.1 修订前已暴露给 A2，因此这次只能作为可复算的 post-hoc 回归证据，
禁止改名为 `A3_FP32_GATE_PASSED`。

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

结果：`184 passed / 0 failed / 0 errors / 0 skipped`。JUnit 证据 SHA256：
`89a75935dd9da97763f3ef417af3c24674d93b355794c70c5137cd065bb3f07e`。

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

## 为什么还不能正式签 PASS

1. 执行人是 A2，不是独立 B2 评测方。
2. 该 240 条标签在 Adapter V3.1 修订前已暴露，盲测性已丢失。
3. 仓库 `benchmark_config.yaml` 仍是等待状态：Independent Validation 路径、
   formal policy version、slice minimum denominator 和 multi-run rule 没有正式冻结。
4. B1 240 条没有 Seen/Variant/Unseen cohort 标注，不满足最终 B2 完整切片合同。
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

