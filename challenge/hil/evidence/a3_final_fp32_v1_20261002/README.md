# Final FP32 candidate v1（B1 closeout 视图）独立复核与复测（2026-10-02）

> ⚠️ **替代条件演练**：权重虽是 A3 的新 final FP32 候选，但门禁仍是
> `PENDING_A3_FP32_GATE`（包状态 `PENDING_B2_INDEPENDENT_VALIDATION`），跑在 X86 上，
> 没有板卡、没有 B2 冻结 Benchmark。所有结论仍是 `DIAGNOSTIC_ONLY`，
> **不是精度或泛化结论**。

## 1. 新候选是什么（与上一版的区别）

| 项 | 上一版（v3，9/26） | **本版（final v1，10/02）** |
|---|---|---|
| 权重 sha256 | `1afb8ebd…` | **`eaee4402…`（真新权重，实际文件哈希与清单一致）** |
| 数据集 | d2_v1_1 + d3_wave1 | **+ d3_wave2 + targeted_gap + turn_gap + gap300**（全累计视图） |
| 训练/开发样本 | 4079 / 797 | **5826 / 1104** |
| hard cases | 310 | 81 |
| Teacher 政策 | `signed_cumulative_release_formal` | `content_bound_final_cumulative_formal` |
| 门禁 | `PENDING_A3_FP32_GATE` | 仍是 `PENDING_A3_FP32_GATE` |

**包校验（修正后）PASS**：9 个文件全部匹配，权重摘要与 `candidate_identity.weights_sha256` 一致。

### 顺带修掉校验器自己的一个缺陷（F12 的延伸）

首轮校验报了 8 个 `size_mismatch`，差值**恰好等于行数**——又是 F12：清单按 LF 记录大小，
Windows 检出是 CRLF，每行多 1 字节。摘要比对早已归一，但**尺寸没归一**。
现在 `verify_a3_handoff.py` 对"只有 CRLF→LF 归一后才匹配"的文本文件，**尺寸也用同一归一方式比较**
（并记录 `size_via`）。修正后本包 PASS，旧 v3 包回归仍 PASS。

## 2. 复测：转弯族与多步族（本轮核心）

用新权重在三个队列上各跑 3 轮（全部 ready/structural 100%，结论 `DIAGNOSTIC_ONLY`）：

| 队列 | 例次 | 行为匹配 | 学生产出的行为词表 | 关键观察 |
|---|---:|---:|---|---|
| TURN-gap val（29） | 87 | **0.6897**（上一版 0.5517） | SLOW_DOWN / KEEP_LANE / SET_SPEED / FOLLOW / **YIELD** | **YIELD 已修好**；TURN_LEFT 仍缺 |
| Gap300 val（123） | 369 | **0.7073** | +PULL_OVER，**YIELD** | 同上 |
| ms34 val（4） | 12 | **0.3333** | `AVOID_OBSTACLE\|RETURN_TO_LANE` | 能出 2 步，但被截断 |

### 2.1 YIELD 修好了，TURN_LEFT 没有

```
teacher -> student（turn-gap，87 例次）
  YIELD      -> YIELD       x6      ← 上一版是 0/6，全部答成 SET_SPEED
  TURN_LEFT  -> SLOW_DOWN   x27     ← 上一版是 SET_SPEED x27，仍然从不产出 TURN_LEFT
  KEEP_LANE  -> KEEP_LANE   x21
  SET_SPEED  -> SET_SPEED   x21
  FOLLOW/SLOW_DOWN -> 各自正确 x6
```

Gap300 队列同样：**YIELD 36/36 正确**，而 **TURN_LEFT 108 例次全部答成 SLOW_DOWN**。
所以补数确实改变了行为分布（YIELD 从"完全不会"变成"全对"），但 **TURN_LEFT 仍然是词表外的行为**，
只是替代项从 SET_SPEED 变成了 SLOW_DOWN。这条应作为下一轮补数与训练的重点（团队清单 GAP-06）。

### 2.2 多步（3 步/4 步）仍不成立

ms34 的 4 个 val 用例：

| 用例 | teacher（步数） | student | 匹配 |
|---|---|---|---:|
| td_8c17… | `AVOID_OBSTACLE\|RETURN_TO_LANE\|KEEP_LANE`（3） | `AVOID_OBSTACLE\|RETURN_TO_LANE` | 0.667 |
| td_45ad… | 同上（3） | 同上 | 0.667 |
| td_229a… | `YIELD\|AVOID_OBSTACLE\|RETURN_TO_LANE\|KEEP_LANE`（4） | `AVOID_OBSTACLE\|RETURN_TO_LANE` | 0.0 |
| td_13d7… | 同上（4） | 同上 | 0.0 |

读法：候选**能产出 2 步序列**，但**止步于 2 步**——3 步用例丢尾部 `KEEP_LANE`，
4 步用例还丢掉开头的 `YIELD`。注意它**单步时能正确输出 YIELD**，所以这是
**计划长度/顺序的能力限制**，不是符号缺失。样本量只有 4 例（12 例次），
**只作诊断，不足以定量**，但方向明确：多步计划仍是短板。

## 3. 不能说的话

- 权重未过 A3/B2 门禁 → 所有匹配率只是开发集诊断，**不是精度结论**；
- 开发划分本身存在查表捷径（此前测过 100% / 88.9%）→ **不是泛化证据**；
- X86 数值 ≠ 板端数值；本目录不含任何板端或预估数据。

## 文件

| 文件 | 内容 |
|---|---|
| `00_handoff_integrity.log` / `01_handoff_integrity_compact.json` | 新候选包独立校验（PASS；含尺寸归一的修正说明） |
| `02_replay_behaviour.json` | 三个队列的行为匹配、teacher→student 混淆与词表 |
| `03_ms34_multistep_detail.json` | 3 步/4 步用例的逐步对照 |
| `04_vocabulary_change_vs_previous.json` | 与上一版候选在 turn-gap 上的词表变化（YIELD 修好、TURN_LEFT 未修好） |
