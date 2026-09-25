# B1 D3 targeted-gap 数据上的 X86 仿真复跑（2026-09-26）

> ⚠️ **仍然是替代条件下的可行性演练，不是最终测试结果。**
> 权重依旧是 A1 随机初始化结构（`gate_status = NOT_PROVIDED`），跑的是 X86 仿真而不是板卡。
> 本轮新增的是**数据条件**：B1 新发 `d3_targeted_gap_strict_v1`，B2 的实现并入了 `challenge`。
> 所有数字只能用于"测量链是否可用、数字是否可解释"，**不得作为性能或精度结论**。

## 为什么做这一轮

1. `challenge` 一次前进 28 个提交：B2 的 `challenge/benchmark/` 实现合并进来，B1 新发
   `d3_targeted_gap_strict_v1`（660 严格正样本 / 280 闭环 run），A3 准备了 D3 Wave2 派生视图。
2. B3 手上有两件待办：发布校验器要能兼容**新签名格式**；以及把"跨数据集定点一致性"的证据
   从 2 个数据集扩到 3 个。

## 1. 发布完整性（PASS，且发现签名格式变了）

`harness/release_check/verify_b1_release.py` 改为**按签名实际声明的摘要逐项校验**：

| 项 | `d3_wave2_safe_short_v1`（上一版） | `d3_targeted_gap_strict_v1`（本版） |
|---|---|---|
| 签名声明 | `release_lock_sha256` + `release_manifest_sha256` + `integrity_report_sha256` + teacher 块 | **只有 `release_manifest_sha256`**（无 gate / teacher / 时间戳字段） |
| 校验结果 | PASS（10/11 个文本文件只有 CRLF→LF 归一后才匹配） | **PASS**（672 个锁定文件；11 个文本文件同样只有归一后才匹配） |
| 图片 | 374 张原始哈希全部匹配 | **660 张原始哈希全部匹配** |
| 行配对 | train 318 / val 56 全部 `model_request`+`teacher_plan`+rgb 可解析 | train **561** / val **99** 同样全部通过；声明值（280 run / 660 样本）与实际行数一致 |
| 样本类型 | — | train {COMPLEX 295, NORMAL 234, SAFETY_CRITICAL 32}；val {NORMAL 46, COMPLEX 45, SAFETY_CRITICAL 8} |

校验器现在会区分 **claimed / not_claimed / not_recomputable** 三类摘要：这次它正确报告
"只声明了 release_manifest_sha256，lock 与 integrity 未声明"，并对旧版正确报告
"`image_set_canonical_sha256` 已声明但本工具无法独立重算"。**声明了就必须匹配，没声明不算失败**——
这样才能在签名格式变化时既不放过真问题，也不制造假失败。

## 2. 查表捷径探针：新版划分改善了，但结论未变

| 项 | `d3_wave2_safe_short_v1` | `d3_targeted_gap_strict_v1` |
|---|---|---|
| train / val | 318 / 56 | 561 / 99 |
| 不同指令文本 | 3（train 与 val 都是 3） | 8（train 与 val 都是 8） |
| val 指令文本出现在 train | 56/56 = 100% | 99/99 = 100% |
| **查表可复现 teacher 计划** | **56/56 = 100%** | **88/99 = 88.9%**（11 例键有歧义） |
| 结论 | `LOOKUP_SHORTCUT_PRESENT` | **`LOOKUP_SHORTCUT_PRESENT`** |

新版改成**按闭环 run 分组划分**（同一次 run 的样本留在同一侧），所以查表命中率从 100% 降到 88.9%；
但**"按 run 分组"不等于"按模板/指令去重"**，8 句指令在两侧都出现，所以文本级捷径依然成立。
B3 只报事实：**这个划分不能支撑泛化结论**；策略判定权在 B2。

## 3. 冻结快照与校准

- 快照：`challenge/hil/frozen/d3_targeted_gap_strict_v1_val`，99 例、rgb 99/99、teacher plan 99/99，
  `case_set_digest_sha256 = 5e2cd6cb…`。
- 校准：用该 release 的 **train 前 128 例**（`cal_config_gap.yaml`，`march nash-p`，`O2`）。
- 阈值分布（四次编译对照，`05_thresholds_compare.log`）：

```
build                        layers values distinct       min     max   ==1.0
skip-calibration                 59     40        2    0.7311       1   38/40
smoke30-train                    60     40       21    0.3466      50    4/40
d3w2-64train                     60     40       21    0.3296      50    4/40
gap-128train                     60     40       21    0.4618      50    4/40
```

## 4. val 99 例逐例一致性

`hb_verifier`（浮点 ONNX ↔ int8 `.bc`）逐例跑，99/99 成功：

| 输出头 | min | p05 | p50 | 低于 0.99 |
|---|---:|---:|---:|---:|
| `plan_length_logits` | 0.9986 | 0.9988 | 0.9996 | 0 |
| `behavior_logits` | 0.9994 | 0.9994 | 0.9996 | 0 |
| `target_pointer_logits` | 0.9988 | 0.9990 | 0.9993 | 0 |
| `target_lane_logits` | 0.9990 | 0.9992 | 0.9995 | 0 |
| `target_speed_mps` | 0.9999 | 0.9999 | 1.0000 | 0 |
| `completion_type_logits` | 0.9992 | 0.9993 | 0.9996 | 0 |
| `on_failure_logits` | 0.9989 | 0.9990 | 0.9994 | 0 |
| `confidence` | 1.0000 | 1.0000 | 1.0000 | 0 |
| `requires_confirmation_logits` | 1.0000 | 1.0000 | 1.0000 | 0 |
| `replan_condition_logits` | 0.9987 | 0.9989 | 0.9995 | 0 |

骨干 6 个中间张量最差 min 0.9996。**没有任何一例、任何一个头低于 0.99。**

## 5. 交叉矩阵：产物 × 数据集（本轮最有价值的新证据）

两个校准产物 × 三个 val 数据集，共 **849 例次**逐例 `hb_verifier`：

| 校准产物 ↓ / 评估集 → | D3 Wave2 val（56） | Gap val（99） | D2 val（539） |
|---|---:|---:|---:|
| **D3 Wave2 train 64 例** | min 0.9974 | min 0.9966 | min 0.9949 |
| **Gap train 128 例** | **min 0.9933** | **min 0.9986** | 未跑（539 例≈21 min，边际价值低） |

**全局最低 0.993331，低于 0.99 的"头×例"观测数为 0。**

读法（重要）：**校准分布与评估分布匹配时更紧**——gap→gap 0.9986 比 gap→d3w2 0.9933 高，
d3w2→d3w2 0.9974 比 d3w2→gap 0.9966 高，代价约 **0.004–0.006**。也就是说，
定点一致性对"校准集选择"敏感但**幅度很小**，且所有组合都远高于 0.99。

## 6. 仍然不能说的话

- 权重是随机初始化结构，**没有任何精度含义**；
- X86 仿真耗时（单次 20 s 量级）不是性能，板端数值一律 `NOT_MEASURED`；
- 本轮的 val 是 B1 增量发布的开发划分，**不是 B2 的冻结 Benchmark**（`case_manifest_path` 仍为 `null`）；
- 查表捷径结论属于事实报告，判定权在 B2。

## 文件

| 文件 | 内容 |
|---|---|
| `00_release_integrity.log` / `01_release_integrity_compact.json` | 新 release 完整性独立复核（PASS + 签名格式差异 + CRLF 说明） |
| `02_leakage_probe.json` / `.log` | 查表捷径探针（88/99 可查表命中 → `LOOKUP_SHORTCUT_PRESENT`） |
| `03_frozen_snapshot.json` | 冻结的 val 快照摘要（99 例） |
| `04_hb_compile_gap.log` | 128 例校准的 PTQ 编译摘要 |
| `05_thresholds_compare.log` | 四次编译的阈值分布对照 |
| `06_verify_gap_val_99.json` | Gap 产物在 Gap val 上的逐头分布（含逐例明细） |
| `07_gap_artifact_on_d3w2_val.json` | 交叉：Gap 产物 × D3 Wave2 val（56） |
| `08_d3w2_artifact_on_gap_val.json` | 交叉：D3 Wave2 产物 × Gap val（99） |
| `09_cross_matrix.json` | 交叉矩阵汇总（849 例次、全局 min、低于 0.99 计数） |
