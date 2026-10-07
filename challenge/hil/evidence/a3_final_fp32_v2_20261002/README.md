# B1 closeout FP32 候选 v2：独立校验与留出队列复测（2026-10-02）

> ⚠️ **替代条件演练**：门禁仍是 `PENDING_A3_FP32_GATE` /
> `PENDING_B2_INDEPENDENT_VALIDATION`，跑在 X86 上，无板卡、无 B2 冻结 Benchmark。
> 所有回放结论都是 `DIAGNOSTIC_ONLY`，**不是精度或泛化结论**。

> 🔁 **2026-10-07 更正**：本文"TURN_LEFT 没有修好 / 必须进入下一轮补数与训练目标"（第 45–54 行）
> 是**解码后计划**的结论。归因脚本证明：模型在这些步上的**未受限 argmax 就是 `TURN_LEFT`**，
> 被解码器可行性掩码（`scene_capabilities.intersection_ahead=false`）剔掉；6 队列 931 步上未受限
> argmax **931/931** 等于教师，解码后 78 处差额全部来自掩码。补数建议作废，改为先由 B1/B2/A1
> 决策字段口径——见 [`../a3_v3_simulation_20261007/README.md`](../a3_v3_simulation_20261007/README.md) §6。
> 本文其余内容（包校验、逐步复测记录）作为当时事实存档，不改写。

## 1. 新候选与包校验

| 项 | v1（10-02 上午） | **v2（本次）** |
|---|---|---|
| 权重 sha256 | `eaee4402…` | **`6b6ec1d8…`（实际文件哈希与清单一致）** |
| 训练视图 | d2_v1_1+…+gap300 累计视图 | **`b1_governed_closeout_v1_a3_strict_positive_v1`（治理化 closeout）** |
| train / dev | 5826 / 1104 | **5856 / 1108** |
| hard cases | 81 | 152 |
| 门禁 | 仍 `PENDING_A3_FP32_GATE` | 仍 `PENDING_A3_FP32_GATE` |

包校验 **PASS**：9 个文件全部匹配（8 个文本文件只有 CRLF→LF 归一后才匹配，即 F12 现象延续），
权重摘要与 `candidate_identity.weights_sha256` 一致。

## 2. A3 自报的 dev 指标 vs B3 的留出队列复测

A3 的 `dev_slice_metrics.json` 报告：**所有行为切片准确率 1.0**（含 `TURN_LEFT` 67 步、
`YIELD` 24 步、`PULL_OVER` 6 步），计划长度切片 1/2/3/4 步也全 1.0。

但那是**开发集**（且 3 步/4 步切片各只有 **2 个样本**）。B3 用 v2 权重在**留出队列**上复测：

| 队列 | 例次 | v2 行为匹配 | v1 行为匹配 | 关键观察 |
|---|---:|---:|---:|---|
| TURN-gap val | 87 | 0.6897 | 0.6897 | **TURN_LEFT 仍从不产出**（27/27 → SET_SPEED） |
| Gap300 val | 369 | 0.7073 | 0.7073 | 同上（108/108 → SET_SPEED） |
| **ms34 val（3/4 步）** | 12 | **0.7083** | 0.3333 | **多步已修好方向**：能出全长 3/4 步序列 |

## 3. v1 → v2 到底改了什么

**多步计划：修好方向，尾步仍错。** v1 的每个计划都被截断在 2 步（ms34 0.3333）；
v2 能产出完整长度：

| teacher | v2 student | 匹配 |
|---|---|---:|
| `AVOID_OBSTACLE\|RETURN_TO_LANE\|KEEP_LANE`（3） | `AVOID_OBSTACLE\|RETURN_TO_LANE\|RETURN_TO_LANE` | 0.667 |
| `YIELD\|AVOID_OBSTACLE\|RETURN_TO_LANE\|KEEP_LANE`（4） | `YIELD\|AVOID_OBSTACLE\|RETURN_TO_LANE\|STOP` | 0.75 |

即"**步数对了、最后一步错了**"（teacher 的收尾 `KEEP_LANE` 被答成 `RETURN_TO_LANE` 或 `STOP`）。

**TURN_LEFT：没有修好。** v2 仍然**从不产出 `TURN_LEFT`**——27 个 turn-gap 与 108 个 gap300
的 TURN_LEFT 例次全部被答成 `SET_SPEED`（v1 是答成 `SLOW_DOWN`，替代项变了，符号依旧缺失）。
**这与 A3 开发切片声称的 `TURN_LEFT` 准确率 1.0 直接矛盾**，原因很清楚：开发切片重复同样的模板，
而留出队列含真实转弯场景；而且治理视图里 3 步/4 步计划各只有 **17 条**，转弯族的样本量本身就不足。

**YIELD 保持正确**：6/6（turn-gap）、36/36（gap300）。

## 4. 给 A3/B2 的可执行结论

1. `TURN_LEFT` 必须进入下一轮补数与训练目标——**连续两版候选都从不产出它**，这是当前最大的单一能力缺口；
2. 开发切片对转弯族的 1.0 不能作为证据（模板重复 + 3/4 步各 2 例），建议 A3 用留出队列的
   行为混淆矩阵替代"切片准确率"来自评；
3. 多步已从"截断"进展到"尾步错"，下一步针对**计划收尾行为**（KEEP_LANE）做定向补数即可。

## 文件

| 文件 | 内容 |
|---|---|
| `00_handoff_integrity.log` / `01_handoff_integrity_compact.json` | v2 包独立校验（PASS） |
| `02_replay_behaviour.json` | 三个留出队列的行为匹配、词表与混淆矩阵 |
| `03_v1_v2_comparison.json` | v1↔v2 对比、A3 自评与 B3 复测的差异、可执行结论 |
