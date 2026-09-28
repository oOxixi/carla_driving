# TURN-gap 队列：真实权重回放与 INT8 复核（2026-09-27）

> ⚠️ 仍然是**替代条件下的可行性演练**：权重是 A3 的候选包（`PENDING_A3_FP32_GATE`），
> 跑在 X86 上，没有板卡、没有 B2 冻结 Benchmark。所有回放结论都是 `DIAGNOSTIC_ONLY`，
> **不是精度或泛化结论**。

## 这轮做的三件事

1. B1 新发的 `d3_turn_gap_60_strict_v1` 用了**第三种通行证格式**，B3 的发布校验器先扩展再复核；
2. 用**真实权重**在这个新队列上跑回放（第一次看到转弯族的表现）；
3. 用真实权重产物在这个队列上做 FP32↔INT8 一致性，并给"真实权重 × 数据集"矩阵补第 4 个点。

## 1. 新通行证格式：content-bound（非签名），但绑定可复算

该 release **没有** `B1_SIGNED_PASS.json`，改为 `B1_CONTENT_BOUND_PASS.json`：

```
signature_status = CONTENT_BOUND_UNSIGNED      # 不是加密签名
status           = PASS
binding.sha256   = 1f264294f76fbf31765ed336e8a6393525abde3a8c4e31f1f8143df4cd108800
```

B3 的校验器现在识别三种通行证（`B1_SIGNED_PASS` × 2 种字段集、`B1_CONTENT_BOUND_PASS`），
并显式输出 **assurance level**。对本次的绑定：

- **可以独立复算**：`sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")))` = 声明值，**match=True**；
- 但它是**内容绑定**而不是签名——只证明"payload 没被改动"，不证明"是谁绑的"，
  **保证等级低于前两版签名 release**。这条写进结论，避免把两者等同。

其余复核结果（`00_release_integrity.log`）：**PASS**，211 个锁定文件全部匹配
（10 个文本文件只有 CRLF→LF 归一后才匹配，即 F12 现象延续），**200 张图全部字节一致**，
train 171 + val 29 行配对齐全，声明值（60 run / 200 样本）与实际一致。

## 2. 真实权重回放：转弯族暴露了**行为词表缺口**

29 例 × 3 轮 = 87 例次，全部 ready/structural 通过，结论仍是 `DIAGNOSTIC_ONLY`
（`gate_verified=false`，唯一失败项 `gate_status_passed`）。

**行为匹配 0.5517、目标匹配 0.8621**——明显低于前三个数据集（1.0000 / 0.9518 / 0.9192）。
拆到场景与行为层面，原因非常明确：

| 场景 | 例次 | teacher 行为 | 学生输出 | 行为匹配 |
|---|---:|---|---|---:|
| TC_C01_true_3step_left | 45 | KEEP_LANE 15 / **TURN_LEFT 15** / SET_SPEED 15 | KEEP_LANE 15 / SET_SPEED 30 | **0.667** |
| TC_C02_yield_left_3step | 18 | **YIELD 6** / **TURN_LEFT 6** / SET_SPEED 6 | SET_SPEED 18 | **0.333** |
| TC_C03_true_4step_follow_left | 24 | FOLLOW 6 / SLOW_DOWN 6 / **TURN_LEFT 6** / KEEP_LANE 6 | FOLLOW 6 / SLOW_DOWN 6 / SET_SPEED 12 | **0.500** |

混淆矩阵（全部 87 例次）：

```
TURN_LEFT -> SET_SPEED   27x  WRONG     SET_SPEED -> SET_SPEED  21x  OK
KEEP_LANE -> SET_SPEED    6x  WRONG     KEEP_LANE -> KEEP_LANE  15x  OK
YIELD     -> SET_SPEED    6x  WRONG     FOLLOW    -> FOLLOW      6x  OK
                                        SLOW_DOWN -> SLOW_DOWN   6x  OK
```

**结论：这个候选从不产出 `TURN_LEFT` 与 `YIELD`**——33 次 TURN_LEFT 与 6 次 YIELD 全部被答成
`SET_SPEED`；其余四种行为则完全复现。这是**行为词表缺口，不是随机噪声**，而且正好对上团队清单里
早先记录的训练数据缺口（**GAP-03：YIELD = 0**、**GAP-06：TURN_LEFT 严重不足**、
GAP-01/02：3-step/4-step 计划为 0）。对 A1/A3 的直接含义：这批定向补采数据正是它没学过的部分，
需要进入下一轮训练分布，而不是指望现有权重泛化过去。

## 3. 真实权重 INT8：本队列上非常干净（与 D3 Wave2 形成对照）

| 产物（校准集） | 评估集 | 最差头 | min | 低于 0.99 |
|---|---|---|---:|---:|
| turn 128 train | turn val 29 | `target_speed_mps` | **0.999889** | 0 |
| 定向补采 128 train | turn val 29 | `target_speed_mps` | **0.999886** | 0 |

两个产物在本队列上都保持 **十头 min ≥ 0.999886、0 例低于 0.99**。对比前一轮：同一个定向补采校准产物
在 **D3 Wave2 val** 上速度头掉到 **0.989066（8/56 低于 0.99）**。所以"速度头敏感"是
**分布相关**的现象，而不是这个产物的固有缺陷——正式校准发布仍应覆盖多个部署分布并单独盯速度头。

## 文件

| 文件 | 内容 |
|---|---|
| `00_release_integrity.log` / `01_release_integrity_compact.json` | 新 release 独立复核（PASS + content-bound 绑定复算 + assurance level） |
| `02_real_weights_turn_replay.json` | 真实权重回放：逐场景行为匹配与 teacher→student 混淆矩阵 |
| `03_int8_real_weights_turn_val.json` | 两个真实权重产物的 INT8 逐头分布（本队列上 0 例低于 0.99） |
| `04_hb_compile_turn.log` | turn-train 128 例校准的 PTQ 编译摘要 |
| `05_frozen_snapshot.json` | 冻结的 29 例 val 快照摘要 |
