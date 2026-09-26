# A3 FP32 候选（handoff v3）独立复核与真实权重回放（2026-09-26）

> ⚠️ **这不是达标证据，也不是泛化证据。**
> 该候选包自报 `gate_status = PENDING_A3_FP32_GATE`、
> `package_status = PENDING_B2_INDEPENDENT_VALIDATION`，其 `limitations` 字段明确写着
> *"This package is not A3_FP32_GATE_PASSED"*、*"Development Validation is not independent
> generalization evidence"*。B3 的结论等级因此**没有变化**：回放仍为 `DIAGNOSTIC_ONLY`、
> 可信范围仍是 `X86_PRE_VALIDATED`。板端数值一律 `NOT_MEASURED`。

## 背景

A3 交付了 `a3_d2_d3_fp32_candidate_handoff_v3`（本地 `D:\nana\`），这是 B3 等了一个多星期的
**真实 FP32 权重**。B3 做了两件事：先按"不盲信交付"的原则**独立校验整包**，再用真实权重
把回放链跑起来，第一次得到有意义的"Student 行为 vs Teacher 计划"读数。

## 1. 独立包校验（PASS）

`harness/release_check/verify_a3_handoff.py`：

| 项 | 结果 |
|---|---|
| 清单文件 | `handoff_manifest.json`（schema 1.0） |
| 文件校验 | **9 个文件逐个 SHA256 + 尺寸全部匹配，0 失败**（本包从 zip 解出，未触发 CRLF 归一） |
| 权重 | `student_v0_fp32_candidate.pt`，92,045,422 B，sha256 `1afb8ebd11e401d4…` —— **与 `candidate_identity.weights_sha256` 一致** |
| 身份 | `model_id = student-v0-r3-fp32`、`config_id = student-v0-r3-structure-20260911`、数据集 `b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1`、训练 git sha `151efbbf…` |
| 门禁 | `gate_status = PENDING_A3_FP32_GATE`（**未通过**）、`package_status = PENDING_B2_INDEPENDENT_VALIDATION` |
| 训练证据（自报） | train 4079 / val 797 / hard cases 310 |

权重 SHA256 与 A2 在 `A2_CANDIDATE_V3_RESULT.md` 里记录的候选权重一致（`1afb8ebd…`），
说明 A2/B3 看到的是**同一份权重**。

## 2. 真实权重回放（两个数据集）

用 inprocess（torch）适配器、`--weights` + `--weights-manifest` 跑 B3 的回放链：

| 数据集 | 例次 | ready / structural | 行为匹配 | 目标匹配 | 学生输出分布 | 结论 |
|---|---:|---|---:|---:|---|---|
| D3 Wave2 开发 val（56 例 × 3 轮） | 168 | **168/168** | **1.0000** | **1.0000** | 3 种（= teacher 3 种），dominant `FOLLOW\|\|C-0001` 42.9% | `DIAGNOSTIC_ONLY` |
| 定向补采 val（99 例 × 3 轮） | 297 | **297/297** | **0.9192** | **0.9192** | 6 种（teacher 9 种），dominant `SET_SPEED\|\|NONE` 45.5% | `DIAGNOSTIC_ONLY` |

对照：**同一份 D3 Wave2 切片**上，A1 随机初始化结构只有 46.4% 行为匹配 / 47.3% 目标匹配，
dominant 输出是 `STOP||NONE`（55%）。So 权重确实带来了学到的行为，而不是模板化的常量输出。

**两个 run 的门禁都按设计 fail-closed**：`gate_verified=false`，**唯一失败项是 `gate_status_passed`**
——也就是说身份校验（`weights_manifest_vs_artifact_sha256 = verified`、嵌套
`candidate_identity` 布局识别正确、摘要一致）全部通过，只是**闸没开**。这正是 B3 期望的行为：
身份对得上不等于可以给出结论。

## 3. 这些数字为什么仍然不能当"泛化"证据

B3 自己在前面两轮已经测过这两个 val 划分的**模板泄漏**：

| 划分 | 指令文本数 | 查表可复现 teacher 计划 | 判定 |
|---|---:|---:|---|
| D3 Wave2 val（56） | 3 | **56/56 = 100%** | `LOOKUP_SHORTCUT_PRESENT` |
| 定向补采 val（99） | 8 | **88/99 = 88.9%** | `LOOKUP_SHORTCUT_PRESENT` |

所以：

- D3 Wave2 上的 **100% 匹配**出现在一个"不看图像、查表就能答"的划分上，**没有泛化含义**——
  这也是为什么 B3 必须自己先做泄漏复核，而不是直接把 100% 报成成绩；
- 定向补采上的 **91.9%** 略高于该划分的查表命中率（88.9%），说明权重确实在起作用，
  但差距太小，**不能据此声称泛化能力**；
- 学生输出种类 6 < teacher 9，是一个值得跟踪的诊断信号（存在输出塌缩），B3 只报事实。

**正式判定只能由 B2 在其冻结的独立 Validation 上给出**（`benchmark_config.yaml` 目前
`case_manifest_path` / `policy_version` 仍为 `null`）。

## 4. 附带发现（供其他组参考）

- `challenge/export/export_onnx.py`（已合入 challenge 的版本）**CLI 只支持 `--output` 与
  `--source-git-sha`，不能传 `--weights`**；A2 那版增强导出器仍在未合并的 `a2-quantization`
  分支上。因此 B3 这次**没有**跑 torch↔ONNX 一致性（没有真实权重的 ONNX 可用）。
  若要跑通"真实权重 → FP32 ONNX → INT8 → OE 编译"这条链，需要先合并 A2 的导出器
  或由 A3 在交接包里直接提供 ONNX。
- 异常输入套件在两批真实权重下都更倾向 fail-closed（D3 Wave2：7 例产出计划 / 3 例 fail-closed；
  定向补采：10 例全部 fail-closed），与随机权重时的分布不同；**仅记录观察，不作结论**。

## 5. 第三个数据集：D2 v1.1 val 全量 539 例（真实权重）

| 数据集 | 例次 | ready / structural | 行为匹配 | 目标匹配 | 学生/教师输出种类 |
|---|---:|---|---:|---:|---|
| D3 Wave2 开发 val | 168 | 168/168 | 1.0000 | 1.0000 | 3 / 3 |
| **D2 v1.1 val（全量）** | **1617** | **1617/1617** | **0.9518** | **0.9712** | **16 / 14** |
| 定向补采 val | 297 | 297/297 | 0.9192 | 0.9192 | 6 / 9 |

X86 进程内延迟（**不是板端性能**）：Planner E2E P50/P95 = 22.65/30.60 ms，
模型纯推理 P50/P95 = 9.69/12.58 ms。

三个数据集一起看才有信息量：训练分布上的 D3 Wave2 是 100%，更早的 D2 是 95.2%，
最新的定向补采是 91.9%——**呈下降趋势**，说明候选在"更晚、更杂"的数据上并不完美，
这与它训练数据的构成（D2 v1.1 + D3 Wave1）一致。**仍然不是泛化证据**（见第 3 节）。

## 6. 真实权重的 FP32→ONNX→INT8 链路（本轮技术含量最高的一段）

### 6.1 导出真实权重 ONNX：先撞到一个跨组接口缺陷

`challenge` 上的 `challenge/export/export_onnx.py` **只接受 `--output` / `--source-git-sha`**，
不能传权重；A2 那版增强导出器（支持 `--weights` / `--weights-manifest` /
`--allow-pending-candidate`）还在**未合并**的 `a2-quantization` 分支上。

B3 只读地取出该文件试跑，**立刻失败**：

```
ValueError: weights manifest model_id does not match Student
```

原因：A2 的导出器读**扁平字段**（顶层 `model_id` / `config_id` / `weights_sha256`），
而 A3 的 handoff v3 用**嵌套 `candidate_identity`** 布局。**这正是 B3 在 2026-09-24
踩过并修掉的同一个坑**（commit `3b09f1f`：`identity_from_weight_manifest()` 同时接受两种布局）。

**建议**：A2 复用 B3 的 `challenge/hil/identity.py` 加载器（或至少同样支持嵌套），
否则"真实权重 → ONNX → INT8 → OE 编译"这条正式链路在合并后会当场报错。

### 6.2 B3 的绕行与结果

B3 在 scratch 目录里从嵌套 manifest **机械派生**了一份扁平视图（摘要值逐字复制，未新增任何值，
sha256 `604e7568…`），据此导出真实权重 ONNX：

| 项 | 值 |
|---|---|
| ONNX | `student_v0_fp32_real.onnx`，92,040,848 B，sha256 `c6d4f3ec…`（**B3 演练产物，非 A2 交付物**） |
| torch ↔ ONNX 一致性 | **PASS**，10/10 请求，全局最大绝对差 **7.629e-06**（rtol 1e-4 / atol 1e-5） |

### 6.3 真实权重的 INT8（PTQ）与 FP32↔INT8 一致性

用定向补采 train 128 例做校准、真实权重 ONNX 编译（`cal_config_real.yaml`），
再对定向补采 val 99 例逐例 `hb_verifier`（**真实 FP32 ONNX ↔ 真实 INT8 `.bc`**）：

| 输出头 | min | p05 | p50 | 低于 0.999 |
|---|---:|---:|---:|---:|
| `plan_length_logits` | 0.999989 | 0.999994 | 0.999998 | 0 |
| `behavior_logits` | 0.999984 | 0.999988 | 0.999992 | 0 |
| `target_pointer_logits` | 0.999988 | 0.999990 | 0.999995 | 0 |
| `target_lane_logits` | 0.999987 | 0.999989 | 0.999993 | 0 |
| `target_speed_mps` | **0.999835** | 0.999873 | 0.999962 | 0 |
| `completion_type_logits` | 0.999968 | 0.999983 | 0.999990 | 0 |
| `on_failure_logits` | 0.999987 | 0.999992 | 0.999995 | 0 |
| `confidence` / `requires_confirmation_logits` | **1.000000** | 1.000000 | 1.000000 | 0 |
| `replan_condition_logits` | 0.999997 | 0.999998 | 0.999999 | 0 |

骨干 6 个中间张量最差 min **0.998213**。99/99 跑通。

**换到第二个数据集后出现一个有意义的差异**（同一 INT8 产物，校准集仍是定向补采 train 128 例）：

| 输出头 | 定向补采 val（99）min | D3 Wave2 val（56）min | 低于 0.99 的例数（D3W2） |
|---|---:|---:|---:|
| 行为/长度/目标/完成/失败/重规划 等 | ≥ 0.999968 | ≥ 0.9987 | 0 |
| **`target_speed_mps`（速度回归头）** | **0.999835** | **0.9891** | **8 / 56** |
| 骨干最差 | 0.998213 | 0.998213 | — |

也就是说：**唯一带连续值的速度头是敏感头**，它的 INT8 保真度**依赖校准数据是否覆盖评估分布**——
校准集来自定向补采，在同类 val 上速度头 min 0.9998，换到 D3 Wave2 val 就掉到 0.9891
（8/56 例低于 0.99，p50 仍有 0.9987）。这条正好对上 A2 的"敏感输出排序"工作，
也是给 A2/A3 的具体建议：**校准集必须覆盖部署分布，速度头需要单独盯**。

**与随机权重对比（同一个 val 集）**：随机权重下十头 min 只有 0.9933–0.9986；
**真实权重下 min 提升到 0.999835 以上**——说明此前的低余弦主要来自"权重是随机的 + 校准分布不匹配"，
而不是量化链路本身有问题。这也让 B3 第一次可以说：**这条 FP32→INT8 链路在真实权重上工作正常**。
（仍然只是工具链结论：门禁未开、无板卡、无精度判定。）

阈值分布（`07_thresholds_compare.log`）：

```
build                        layers values distinct       min     max   ==1.0
real-weights                     60     40       21      0.48      50    4/40
gap-128train                     60     40       21    0.4618      50    4/40
skip-calibration                 59     40        2    0.7311       1   38/40
```

## 7. 真实权重的 30 分钟长稳

| 项 | 值 |
|---|---|
| 运行 | `b3-soak-20260926T075419Z-7e867ba3`，1800 s（`duration_met=true`） |
| 迭代 | **77,653 次**，全部 `READY`，`error_count=0`，`success_rate=1.0` |
| 恢复探针 | 10/10 `READY`，0 错误，p95 33.1 ms |
| 内存漂移 | **−94.2 KiB**（1 Hz 遥测，无增长；上一次随机权重轮是 +1.82 MiB） |
| RSS | 峰值 **388.5 MiB**（真实权重比随机初始化的 316.8 MiB 高，符合"权重确实被加载并使用"） |
| CPU | 峰值 332.2%（多核） |
| 功耗 / BPU | `NOT_APPLICABLE` / 未测（无探针、无板卡） |

**吞吐口径提醒（第三次记录）**：同形状命令三次 30 分钟长稳分别得到 **123,611（09-21）/ 22,462（09-25）
/ 77,653（09-26）** 次迭代。同一台机器、同一条命令相差 5.5×，结论不变：
**X86 长稳的绝对吞吐不可跨会话比较**，只能比较同一次会话内的成功率、漂移与恢复行为
（跨会话要比必须做同刻 A/B 对照）。

## 文件

| 文件 | 内容 |
|---|---|
| `00_handoff_integrity.log` / `01_handoff_integrity_compact.json` | 候选包 9 文件 + 权重摘要的独立校验（PASS） |
| `02_real_weights_replay.json` | 两个数据集回放的机读摘要（含身份与门禁明细） |
| `03_real_weights_replay_console.log` | 两次回放的控制台输出与"真实 vs 随机权重"对照 |
| `04_real_weights_d2_539.json` | D2 v1.1 val 全量 539 例 × 3 轮的真实权重回放（行为 0.9518 / 目标 0.9712） |
| `05_export_and_consistency.json` | 真实权重 ONNX 导出记录：跨组接口缺陷、B3 绕行方式、ONNX 摘要、torch↔ONNX 结果 |
| `06_int8_real_weights_gap99.json` | 真实权重 FP32↔INT8 逐头分布（99 例，十头 min ≥ 0.999835） |
| `07_thresholds_compare.log` | 真实权重编译与既有编译的阈值对照 |
| `08_soak_real_weights.json` | 真实权重 30 分钟长稳摘要（77,653 次、0 失败、漂移 −94 KiB、峰值 RSS 388.5 MiB） |
| `09_int8_real_weights_d3w2_56.json` | 同一 INT8 产物换到 D3 Wave2 val（56 例）的逐头分布：速度头 min 0.9891、8 例低于 0.99 |
