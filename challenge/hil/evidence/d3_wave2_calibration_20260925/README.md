# 用签名 D3 Wave2 数据重跑 X86 仿真（2026-09-25）

> ⚠️ **仍然是替代条件下的可行性演练，不是最终测试结果。**
> 权重依旧是 A1 的随机初始化结构（`gate_status = NOT_PROVIDED`），X86 仿真运行时也不是板卡。
> **本轮相对上一轮的改进只在"数据"这一项**：从 B3 自建的 30 例冒烟输入，换成 B1 签名通过的
> D3 Wave2 发布数据，并采用 **train 校准 / val 评估** 的干净划分。
> 因此本文数字依然**不得作为性能或精度达标结论**引用。

## 为什么做这一轮

上一轮（`evidence/x86_simulation_20260924/`）暴露了一个真问题：没有校准数据时量化阈值退化为
默认 `1.0`，十头余弦掉到 0.79–1.00。当时只能用仓库里的 30 例冒烟输入自建校准集。
2026-09-25 B1 发布了 **D3 Wave2 safe-short**（`B1_SIGNED_PASS`），B3 立刻用它把这一环补成
方法上说得通的样子：**用 train 划分校准、用 val 划分评估**。

## 数据（来自 B1 的签名发布，不是我们自造）

| 项 | 值 |
|---|---|
| 发布 | `challenge/dataset/releases/d3_wave2_safe_short_v1/` |
| 版本 | `b1_d3_wave2_safe_short_v1`（增量发布，不替换 D2 v1.1 / D3 Wave1） |
| 门禁 | `B1_SIGNED_PASS` / `status PASS`，签名时间 2026-09-24T16:18:37Z |
| Teacher 身份 | `Qwen/Qwen3.5-2B` @ `15852e8c1636`，profile `b1-pinned-teacher-v4-wave2-scenario-sync-v1` |
| 样本 | 374 例严格正样本：A01 114 / A06 114 / CX01 146；CX02 全族按记录被排除 |
| 划分 | train 318 / val 56 / hard_negative 0 |
| 图像 | 374 张，每张都有 `rgb_sha256` 与打包引用 |

## 本轮四步与结果

### 1. 独立复核发布完整性（不盲信签名）

`challenge/hil/harness/release_check/verify_b1_release.py`：逐个文件比对 `b1_release_lock.sha256`、
`B1_SIGNED_PASS.json` 里的三个摘要、374 张图的哈希与大小、以及每行 request↔rgb 的配对。

| 结果 | 值 |
|---|---|
| 状态 | **PASS（0 失败）**，`--eol auto` |
| 锁定文件 | 11 个：10 个只有把 CRLF 归一成 LF 后才匹配，1 个（0 字节文件）原始匹配 |
| 图片 | 374/374 哈希与大小全部原始匹配 |
| 行配对 | train 318 / val 56：`model_request` 齐、`teacher_plan` 齐、rgb 全部可解析、哈希全对 |
| 样本类型 | train {NORMAL 131, SAFETY_CRITICAL 97, COMPLEX 90}；val {COMPLEX 24, SAFETY_CRITICAL 17, NORMAL 15} |

**发现一个新环境事实（已记入 `repo_environment_findings.md` F12）**：本机 `core.autocrlf=true`
且 `.gitattributes` 未给这批 release 固定行尾，所以在 Windows 上做**字节级**校验会看到 13 处假失败
（`--eol raw` 仍然复现）；CRLF→LF 归一后与 lock 完全一致。任何在 Windows 上校验 B1/B4 摘要的
消费方都会踩到，反过来也会。

### 2. 冻结 B3 快照（val 56 例）

```
cli freeze --delivery challenge/dataset/releases/d3_wave2_safe_short_v1 \
           --requests .../val_addition.jsonl --out challenge/hil/frozen \
           --name d3_wave2_safe_short_v1_val
```

56 例、rgb 复制 56/56、teacher plan 56/56，`case_set_digest_sha256 = 79513aa8…`。
它**不是 B2 的冻结 Benchmark**，只是 B3 的开发 val 划分。

### 3. 用 train 校准、编译（PTQ）

校准集 = D3 Wave2 **train 前 64 例**（`cal_config_d3w2.yaml`，`march: nash-p`，`O2`）。
阈值分布对比（`05_thresholds_compare.log`）：

```
build                        layers values distinct       min     max   ==1.0
skip-calibration                 59     40        2    0.7311       1   38/40
smoke30-train                    60     40       21    0.3466      50    4/40
d3w2-64train                     60     40       21    0.3296      50    4/40
```

内存：static 23,580,176 / dynamic 605,696 / **min requirement 24,185,872 B**。

### 4. 用 val 56 例逐例评估一致性

`hb_verifier`（浮点 ONNX ↔ int8 `.bc`）逐例跑，56/56 成功，十头统计（`04_verify_d3w2_summary.json`）：

| 输出头 | min | p05 | p50 | mean | <0.99 |
|---|---:|---:|---:|---:|---:|
| `plan_length_logits` | 0.9974 | 0.9979 | 0.9994 | 0.9993 | 0 |
| `behavior_logits` | 0.9992 | 0.9992 | 0.9994 | 0.9994 | 0 |
| `target_pointer_logits` | 0.9985 | 0.9987 | 0.9992 | 0.9991 | 0 |
| `target_lane_logits` | 0.9987 | 0.9989 | 0.9992 | 0.9992 | 0 |
| `target_speed_mps` | 0.9999 | 0.9999 | 1.0000 | 1.0000 | 0 |
| `completion_type_logits` | 0.9991 | 0.9993 | 0.9996 | 0.9995 | 0 |
| `on_failure_logits` | 0.9989 | 0.9990 | 0.9993 | 0.9994 | 0 |
| `confidence` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 |
| `requires_confirmation_logits` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 |
| `replan_condition_logits` | 0.9983 | 0.9984 | 0.9994 | 0.9992 | 0 |

视觉骨干 6 个中间张量：最差 min 0.9995。**没有任何一例（任何一个头）低于 0.99。**

CLI 路径互证（`06_cli_d3w2_single_case.log`）：`hrt_model_exec infer --enable_dump` 在
`ACC_A01_lead_brake__GEN_000_0009` 上十头 min 0.9992 / mean 0.9995，与逐例 `hb_verifier` 同量级
——三路（verifier / HBRuntime / CLI dump）的一致性在新产物上依然成立。

### 5. 完整回放链（真实数据 + 替代权重）

用冻结的 56 例 val 跑 B3 的回放链（3 轮 + 5 例 warmup，`--adapter both`，见 `08_wave2_replay_console.log`）：

| 项 | 结果 |
|---|---|
| 例次 | 168（56 例 × 3 轮），`ready_rate = 1.0`，`structural_pass_rate = 1.0`，rgb 解析 168/168 |
| 回放结论 | **`DIAGNOSTIC_ONLY`**，原因写明 "Student weights are not A3-gated"（失败检查：`gate_status_passed` / `weights_manifest_verified` / `digest_matches_identity`）——门禁按设计 fail-closed |
| torch ↔ ONNX | `passed=True`，最大绝对差 5.722e-06 |
| 后端一致性 | `PASS` |
| 异常输入套件 | 7 例产出计划 / 3 例 fail-closed |
| A3 回流 | `trainable=0, robustness=10`（权重未过闸，本就不该产出可训练样本） |
| 可信范围 | `X86_PRE_VALIDATED` |

X86 进程内 Planner 链的 P50/P95（ms，**不是板端性能**）：模型纯推理 33.34 / 61.57、
Planner E2E 74.83 / 111.53、Planner 开销 38.22 / 55.61。

### 6. 顺带发现：这批增量发布的指令文本几乎没有新意（给 B2 的独立观察）

B3 在复核时统计了请求文本分布，结果是：**train 318 例 + val 56 例只用了 3 个不同的
`source_text`、6 个 `scenario_id`**（train 里每句重复 90–131 次，val 里 15–24 次）。
回放的分组信号也独立复现了这一点（`instruction_text_reuse_signal = true`，
`distinct_source_texts = 3`）。

这与团队清单里 GAP-09（Language Novelty 不足）与 GAP-12（缺少真正独立的新场景族）一致：
该发布是"安全短场景增量"，用于补样本量有效，但**不宜当作 Seen/Variant/Unseen 中
Variant/Unseen 的代表**。B3 只报事实，不替 B2 判定；正式划分与判据仍属 B2。

### 7. 查表捷径复核：该 val 划分可被查表完全命中（`LOOKUP_SHORTCUT_PRESENT`）

顺着上一条，B3 用 `cli leakage-probe` 做了独立复核（`09_leakage_probe_wave2.json`）：

| 指标 | 值 |
|---|---|
| train / val 例数 | 318 / 56 |
| val 指令文本出现在 train | **56 / 56（share = 1.0）** |
| val 场景 id 出现在 train | **56 / 56（share = 1.0）** |
| 查表键命中 | 56 / 56 |
| **查表即可复现 teacher 计划** | **56 / 56（share = 1.0）**，歧义键 0 |
| 结论 | **`LOOKUP_SHORTCUT_PRESENT`** |

含义（B3 只报事实，策略归 B2）：在这个 val 划分上，"行为匹配"**不看图像也能做出来**，
所以它不能支撑任何泛化结论，也不能当 Variant/Unseen 的替身。相对地，上一节的量化一致性
读数（十头 min ≥ 0.9974）**不受影响**——那里比的是同一输入下浮点与定点的一致性，
与"输入是否有新意"是两件事。

### 8. 跨数据集复核：把同一产物放到 D2 v1.1 val 的 539 例上

上一节的 56 例只是 D3 Wave2 的 val。为了确认定点一致性不是"只在这批数据上成立"，
B3 用**同一个**产物（`student_v0_fp32_d3w2`，校准集仍是 D3 Wave2 train 64 例）
在 **D2 v1.1 val 全量 539 例**上又跑了一遍逐例 `hb_verifier`（`10_verify_d2_539.json`）：

| 输出头 | min | p05 | p50 | mean | 低于 0.99 | 低于 0.999 |
|---|---:|---:|---:|---:|---:|---:|
| `plan_length_logits` | 0.9949 | 0.9985 | 0.9995 | 0.9994 | 0 | 92/539 |
| `behavior_logits` | 0.9987 | 0.9992 | 0.9995 | 0.9994 | 0 | 3/539 |
| `target_pointer_logits` | 0.9981 | 0.9987 | 0.9992 | 0.9992 | 0 | 113/539 |
| `target_lane_logits` | 0.9981 | 0.9989 | 0.9993 | 0.9993 | 0 | 74/539 |
| `target_speed_mps` | 0.9999 | 0.9999 | 1.0000 | 1.0000 | 0 | 0/539 |
| `completion_type_logits` | 0.9989 | 0.9992 | 0.9995 | 0.9995 | 0 | 5/539 |
| `on_failure_logits` | 0.9975 | 0.9989 | 0.9994 | 0.9993 | 0 | 75/539 |
| `confidence` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0/539 |
| `requires_confirmation_logits` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0/539 |
| `replan_condition_logits` | 0.9971 | 0.9982 | 0.9992 | 0.9991 | 0 | 174/539 |

539 例逐例全部跑通（`ok=539 fail=0`）；**没有任何一例、任何一个头低于 0.99**，
视觉骨干 6 个中间张量最差 min 0.9994。也就是说：**"用 D3 Wave2 train 校准出来的定点产物，
在原 D2 分布上同样与浮点保持一致"**——这是上一轮拿不到的证据（当时只有单例）。

### 9. 30 分钟长稳（换用签名快照）+ 吞吐口径的提醒

在签名快照上重跑了 30 分钟长稳（`11_soak_d3w2_30min_summary.json`）：

| 项 | 值 |
|---|---|
| 运行 | `b3-soak-20260925T055126Z-3e8873cb`，1800.1 s（`duration_met=true`） |
| 迭代 | 22,462 次，**全部 `READY`**，`error_count=0`，`success_rate=1.0` |
| 恢复探针 | 10/10 `READY`，0 错误，p95 118.0 ms |
| 内存漂移 | **1,816 KiB（≈1.77 MiB，0.57%）**，来自 1 Hz 遥测的 1772 个样本（非 harness 自身记账） |
| RSS | 最大 323,196 KiB；峰值 324,376 KiB（≈316.8 MiB） |
| CPU | 峰值 392.2%（多核） |
| 功耗 / BPU | `NOT_APPLICABLE` / 未测（无探针、无板卡） |
| 长稳延迟 | p95 117.5 ms、max 362.0 ms（含遥测采样，只作趋势看，不作绝对分位引用） |

**吞吐口径提醒（本轮新记录）**：2026-09-21 那次同形状命令跑了 **123,611** 次（≈68.7/s），
今天这次只有 **22,462** 次（≈12.5/s）。为区分"数据不同"还是"机器状态不同"，B3 在同一时刻
对两个快照各做了 1 分钟对照（`14_soak_throughput_probe.json`）：D3 Wave2 **656 次/分钟**、
D2 **642 次/分钟**——两者几乎相同，说明差异来自**主机状态随时间变化**（WSL/Docker/整机占用），
**不是新数据造成的**。结论：X86 长稳的**绝对吞吐不可跨会话比较**，只能比较同一次会话内的
成功率、漂移与恢复行为；跨会话要比，必须在同一时刻做对照（如这里的 1 分钟 A/B）。

## 文件

| 文件 | 内容 |
|---|---|
| `00_release_integrity.log` / `01_release_integrity_compact.json` | 发布完整性独立复核（PASS + EOL 说明） |
| `02_frozen_snapshot.json` | 冻结的 val 快照摘要 |
| `03_hb_compile_d3w2.log` | 带校准编译摘要（yaml、校准、内存、march） |
| `04_verify_d3w2_summary.json` | 56 例逐例余弦 + 十头分布统计（含每例明细） |
| `05_thresholds_compare.log` | 三次编译的阈值分布对照 |
| `06_cli_d3w2_single_case.log` | CLI 路径单例互证（padding、Infer time、逐头余弦） |
| `07_wave2_replay_summary.json` | 56 例 × 3 轮回放的机读摘要（结论、门禁、延迟分位、文本复现信号） |
| `08_wave2_replay_console.log` | 回放控制台输出与 P50/P95 明细 |
| `09_leakage_probe_wave2.json` | train↔val 查表捷径复核（`LOOKUP_SHORTCUT_PRESENT`，56/56 可查表命中） |
| `10_verify_d2_539.json` | 跨数据集复核：同一产物在 D2 v1.1 val 全量 539 例上的逐头分布（含逐例明细） |
| `11_soak_d3w2_30min_summary.json` | 签名快照上的 30 分钟长稳摘要（22,462 次、0 失败、漂移 1.77 MiB） |
| `12_soak_contract_report.json` | 长稳运行前的契约预检结果 |
| `13_soak_memory_trace.csv` | 长稳期间的 1 Hz 内存遥测（1772 个样本） |
| `14_soak_throughput_probe.json` | 两个快照的 1 分钟 A/B 吞吐对照，用于判定吞吐差异来自主机状态 |

## 仍然不能说的话

- 不能把这里的余弦当作**模型精度**：被测权重仍是随机初始化结构，没有经过训练；
- 不能把这里的任何耗时当作**性能**：X86 仿真是指令/周期级模拟（单次 20 s 量级），板端数值一律 `NOT_MEASURED`；
- 不能声称完成了 Seen/Variant/Unseen：本轮的 val 是 B1 增量发布的开发划分，正式划分与判据仍属 B2；
- 不能因为"数据是签名的"就升级结论等级：门禁按证据逐项核验，缺板端证据就只能是 `X86 PRE-VALIDATED`。
