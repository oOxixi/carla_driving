# B2 新基准冻结与候选未暴露 Seen 压测（2026-10-08）

## 结论

A2 按团队负责人授权代理 B2，已经在读取新 Student 结果前冻结了新的 240 槽
Seen/Variant/Unseen 采集设计和判分 policy，并把精确 V3.1 复合候选绑定到冻结锁。
240 个场景合同全部通过结构校验，但当前机器没有 CARLA，也无法访问精确 Teacher v4
服务，因此这只是 `ACQUISITION_AND_POLICY_FROZEN_AWAITING_COLLECTION`，尚未形成
冻结 case set，更没有正式 Gate decision。

在不替代上述 240 槽的前提下，又对现有 308 条候选未使用的 D3 Wave1 硬负样本执行了
固定规则 Seen 压测。308/308 推理成功且两次运行的原始预测逐字节一致，但严格阈值投影
为 **FAIL**。因此当前候选不能依据该结果进入 FINAL，`A3_FP32_GATE_PASSED=false`。

## 一、评测前冻结的 240 槽新基准

- freeze ID：`b2-proxy-prospective-unseen-v1-20261008`；
- 冻结规则提交：`2d59d9284bfe06b6896bac45b5af75756eb85f31`；
- 角色：`A2_ACTING_AS_B2_PROXY`；
- 独立性：`PROSPECTIVE_TEMPORAL_HOLDOUT`，不是外部 B2 签名；
- 槽数：Seen 80 / Variant 80 / Unseen 80，共 240；
- 唯一 seed：240；唯一场景 ID：240；
- 场景合同：240/240 schema-valid；
- 排除边界：Train、Development、Calibration v1、旧 Independent Validation，
  共审计 7,735 条记录；
- seed 与既有数据重叠：0；场景 ID 与既有数据重叠：0；
- policy：核心指标最大下降 1.5%，安全召回最大下降 0%，schema validity 必须 100%；
- 失败推理：保留参考分母、分子记 0；禁止只统计成功样本；
- 合并规则：每槽只取第一条质量有效结果，只有模型比较前的基础设施故障允许重试，
  禁止看结果后替换或排除样本。

关键绑定：

- weights SHA256：`7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`；
- FP32 ONNX SHA256：`681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286`；
- Adapter contract：`student-plan-adapter-v3.1-semantic-contract`；
- Adapter SHA256：`bb30726b8287b422516820af8e8af21e5d6a205cd81d3f9de6871de9badfcf21`；
- policy manifest SHA256：`b7e45788a8fb54f04233689d8f64c0c9af954d53a22b108dfe5e35fd4f323fa3`；
- acquisition slots SHA256：`2f38f8158b1300ee012c894546bb1db54d50b5008888c2dbdbb34403931efbad`；
- freeze lock SHA256：`b54535a2472596dadfdc0adfe114ec406b925f6b6eb56ba1d4f8215859e5eea9`。

冻结目录共有 248 个文件；外层 247 条 `SHA256SUMS` 已逐项复算通过，无未登记文件。

## 二、308 条候选未暴露 Seen 压测

### 输入边界

运行规则先固定在提交 `ee9e4197be30f3ae1b02f9a3ac8a34ac0f9c86bb`，再启动
Student。输入为 D3 Wave1 发布锁中的全部 308 条 `hard_negative_addition.jsonl`，不按
结果筛选。源文件逻辑 LF SHA256 为
`c0b3a3c5374c9ebfcfe2a0be90bab5fdf52d5b0a754c720a17aa0798232ad585`。

308 条均绑定同一精确 Teacher v4 Git SHA
`95e97b00def8ec36f12937da34ce8bb9082c4a04`。另一个补充发布中的 1 条旧 Teacher SHA
样本在模型运行前因教师身份不一致而未纳入，未发生结果后排除。

相对 7,735 条既有治理数据：

| 身份字段 | 唯一数 | 重叠数 | 解释 |
|---|---:|---:|---|
| sample ID | 308 | 0 | 候选未使用样本 |
| group key | 308 | 0 | 无组泄漏 |
| RGB SHA256 | 308 | 0 | 无图像复用 |
| seed | 308 | 0 | 无运行 seed 复用 |
| scenario ID | 16 | 16 | Seen 场景，不是 Unseen |
| source text SHA256 | 15 | 15 | Seen 文本模板 |
| normalized request SHA256 | 46 | 44 | 大量语义模板已见 |

因此本结果只能叫 `CANDIDATE_UNEXPOSED_SEEN_STRESS`，不能叫新的三队列 Frozen
Benchmark Gate。

### 严格结果

Student coverage 为 308/308，schema validity 为 1.0，无 inference error 或 invalid
output。

| Gate 指标 | Teacher | Student | 下降 | 阈值 | 投影 |
|---|---:|---:|---:|---:|---|
| behavior accuracy | 1.000000 | 0.921512 (317/344) | 0.078488 | 0.015 | FAIL |
| target pointer accuracy | 1.000000 | 1.000000 (344/344) | 0 | 0.015 | PASS |
| target lane accuracy | 1.000000 | 0.816860 (281/344) | 0.183140 | 0.015 | FAIL |
| completion accuracy | 1.000000 | 0.921512 (317/344) | 0.078488 | 0.015 | FAIL |
| plan sequence accuracy | 1.000000 | 0.795455 (245/308) | 0.204545 | 0.015 | FAIL |
| safety-critical behavior recall | 1.000000 | 1.000000 (89/89) | 0 | 0 | PASS |

分类切片：Normal 199 条的全部核心字段为 100%；Complex 56 条的 behavior/lane/
completion/sequence 为 29/56；Safety-critical 53 条中安全行为召回 89/89，但完整计划仅
17/53，目标车道为 53/89。

### 63 条严格差异的根因

245/308 个完整计划的 Gate 字段完全一致。其余 63 条只有两种确定性模式：

1. `QWR_07_visual_avoid_return` 36 条：Teacher 与 Student 都是 `AVOID_OBSTACLE`，
   completion 都是 `TARGET_PASSED`，但 Teacher lane=`CURRENT`，Student
   lane=`LEFT_ADJACENT`。
2. `SUP_A15_lane_change_blocked` 27 条：Teacher 为
   `CHANGE_LANE_LEFT / LEFT_ADJACENT / LANE_CENTERED`，Student 为
   `STOP / CURRENT / STOPPED`。

这不是此前的 `null/CURRENT` 字段约定问题。63 条全部来自 `HARD_NEGATIVE`，原始闭环
记录均以 `SAFETY_OVERRIDE / EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE` 终止；所以它们是有价值
的压力证据，但不是可直接当作正式金标准的正样本。严格冻结口径仍保持 FAIL，不做结果后
改标签、归一化、删样本或调阈值。

差异样本 ID 排序集合 SHA256：
`8541141aace902a741278a957c4b99354aadd5b2edf881d4218da94114c40511`。

## 三、确定性与测试

- 两次完整 308 条运行的 Teacher predictions SHA256 均为
  `f8c1a97db2684082f5ba5fb3088d8d8a39be3eee7e7de1fe8773c5bc84f6f109`；
- 两次 Student predictions SHA256 均为
  `c4568227c5f0063aad1362f3d933d1a9f7930466ee8a5b16d4e937b6ba2950dd`；
- 两次指标逐项一致；CPU 计时不纳入确定性声明；
- `challenge/benchmark/tests`：197 passed / 0 failed；
- JUnit SHA256：`f702574b61515d1dcad821e64868f11a1f5d028937c720ffbe4cebd70ac57c35`。

## 四、可直接发送的 ZIP

1. CARLA/Teacher v4 采集方：
   `artifacts/submission/B2_PROSPECTIVE_BENCHMARK_FREEZE_V1_20261008.zip`
   - SHA256：`a84c66134cc1880db78a2d971192e19603e251db8096b56e88b8f211b224f778`
   - 256 entries；ZIP CRC PASS；255 个受管成员 SHA256 PASS。
2. B2/B4/团队审阅：
   `artifacts/submission/B2_CANDIDATE_UNEXPOSED_SEEN_STRESS_V1_20261008.zip`
   - SHA256：`bce32f1dc56b95e036c45ea9b716dca7592bbf091bbc50d36e73a85e642f1339`
   - 19 entries；ZIP CRC PASS；18 个受管成员 SHA256 PASS；
   - 含两次 raw predictions、完整报告、固定 policy、runner、测试、JUnit、差异审计和
     确定性证明。

## 五、正式 Gate 还缺什么

1. 在可访问 CARLA 和精确 pinned Teacher v4 的机器上，按冻结包采集 240 个槽；
2. 生成实际 case manifest、case-set digest 和 RGB/组/事件级零泄漏审计；
3. case set 完全关闭后，才允许对精确冻结 Student 做一次评测；
4. B2 代理人据相同 policy 出具 decision，但必须继续标注角色豁免，不能冒充外部独立签字；
5. 若根据 308 条结果修改模型或 Adapter，必须产生新候选、新 SHA、新 freeze ID 和新 seed，
   当前 240 槽不得继续被称为该新候选的盲测证据。

当前机器上的硬阻塞是 `CARLA_RUNTIME_NOT_AVAILABLE` 与
`EXACT_TEACHER_V4_SERVICE_NOT_REACHABLE`。因此 `A3_FP32_GATE_PASSED=false`、
`A2_INT8_GATE_PASSED=false`、`final_submission_allowed=false`。
