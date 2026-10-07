# B3 测试结果与缺口汇总（材料 #10 初稿：2026-10-03 建，2026-10-07 更新）

> 本文是**给别人直接用的汇总**：所有数字都指向本目录下已提交的证据文件，口径按
> `X86_MEASURED` / `BPU_ESTIMATED` / `J6P_MEASURED` 三类分别标注。
> **本文不含任何板端数字**（无板卡、无探针）。
> 机读版本：`evidence/scoring_requirements_20261003/results_and_gaps.json`（10-03 基线）。
> **10-07 的新数字**（v3 官方镜像复跑、行为归因、多模态全队列消融、ONNX 身份、采样器修复）在
> `evidence/a3_v3_simulation_20261007/07`–`11`，本文对应章节为 §2.1、§2.2、§2.9、§2.11。

## 0. 一页结论

| 项 | 状态 | 一句话 |
|---|---|---|
| 官方 X86 环境可用 | ✅ | 官方镜像本机就有，**已在其中完成实测**（539×3 与 30 分钟长稳） |
| 端到端延迟 | ✅ 实测 | planner 链 **P50 13.2 / P95 16.3 / P99 18.3 ms**（阈值 150 ms；v3 复测） |
| 30 分钟稳定性 | ✅ 实测 | **128,545 次迭代、0 失败、恢复 10/10**（v3 复测，采样器修复后重跑） |
| 内存 | ✅ 实测 | 峰值 RSS **368.5 MiB**（官方镜像内，v3 复测） |
| 行为匹配口径 | ⚠️ **已更正** | 旧口径（解码后计划）把**解码器可行性掩码**算成了模型缺口；未受限 argmax 在 6 队列 931/931 步等于教师行为（见 §2.9） |
| INT8 量化损失 | ✅ 实测 | 结构不变（747 例 0 失配）；速度头最大偏差 0.52–1.41 m/s |
| INT8→BPU 编译保真 | ✅ 实测 | 6 队列 **850 例**，十头 min 余弦 **0.999125**，<0.99 为 0 |
| 异构算力利用率 | ❌ **缺口** | 无官方公式 + 无 A4 Runtime → 按细则**当前 0 分** |
| 核心指标衰减 | ❌ **缺口** | 需 B2 冻结 Benchmark + A3 同基准对比 → **当前 0 分** |
| FLOPs 压缩比 | ⚠️ 数据齐、口径待定 | 相对 Teacher 下界 = **0.1769**（15 分档）；分母定义需确认 |
| 功耗 / 板端 | ❌ 无硬件 | `NOT_MEASURED`，材料中写明依赖实板 |

## 1. 环境与身份（材料 #12 可直接引用）

| 项 | 值 |
|---|---|
| 镜像 | `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1` |
| 镜像 id | `sha256:cf06f721448e30f8f569cfeb6fc3356c1ad6e77ba180042d0c3babe891b6b5c4` |
| OS / Python | Ubuntu 22.04.3 LTS / Python 3.10.12 |
| 库版本 | torch 2.8.0+cpu、numpy 1.23.0、onnxruntime 1.19.0、psutil 7.2.1 |
| 工具链 | horizon_tc_ui 3.5.16、hb_compile、hb_verifier、X86 版 hrt_model_exec |
| 被测权重 | A3 closeout candidate **v3 `7f379c78…`（当前最新）**；历史：v1 `eaee4402…`、v2 `6b6ec1d8…`。三者门禁均为 `PENDING_A3_FP32_GATE` |
| 交付的 FP32 ONNX | 本目录记录的有两份字节：B3 导出 `b76b5a32…`（torch 2.6.0）、官方镜像重导 `b552b860…`（torch 2.8.0）；两者**权重/拓扑/数值等价**，见 §2.11 |
| 评测数据 | 自建留出队列 6 个、共 **850 例**（D2 v1.1 539 / gap300 123 / targeted-gap 99 / d3_wave2 56 / turn-gap 29 / ms34 4），脚本冻结于 `challenge/hil/harness/` |
| 环境指纹文件 | `evidence/scoring_requirements_20261003/official_env_fingerprint.txt` |

## 2. 测试结果

### 2.1 官方镜像内完整测量（539 例 × 3 轮，1,622 次全部 READY / 结构通过）

v3 候选（`7f379c78…`）与 v1 候选（`eaee4402…`）用**同一条命令、同一环境、同一队列**各跑一轮：

| 时段 | v1 P50 / P95 / P99 / max | **v3 P50 / P95 / P99 / max** |
|---|---:|---:|
| 预处理 | 7.359 / 8.091 / 8.521 / 10.108 | 7.731 / 9.616 / 11.077 / 15.980 |
| Token/Target packing | 0.287 / 0.407 / 0.517 / 1.535 | 0.346 / 0.491 / 0.854 / 1.622 |
| **模型纯推理** | **4.027 / 5.445** / 6.068 / 7.233 | **4.513 / 5.814** / 6.569 / 9.666 |
| 后处理 | 0.027 / 0.041 / 0.078 / 0.109 | 0.033 / 0.047 / 0.080 / 0.112 |
| Adapter | 0.163 / 0.236 / 0.459 / 1.602 | 0.197 / 0.277 / 0.409 / 0.845 |
| 计划校验 | 0.436 / 0.625 / 1.087 / 55.269 | 0.511 / 0.740 / 1.099 / 60.832 |
| **Planner E2E** | **11.917 / 14.244** / 15.460 / 68.983 | **13.223 / 16.339** / 18.275 / 70.131 |

证据：v1 → `evidence/scoring_requirements_20261003/official_full_and_soak.json`；
v3 → `evidence/a3_v3_simulation_20261007/07_official_env_v3_full_and_soak.json`。
口径：`X86_MEASURED`；范围是 **input_arrival → plan_ready**，**不含语音前端**。
v3 相对 v1 全链慢约 **+1.3 ms（P50）**，仍远离 150 ms 阈值。

### 2.2 30 分钟长稳

| 项 | 官方镜像 · v1 候选 | 官方镜像 · **v3 候选** | 宿主机（对照） |
|---|---|---|---|
| 时长 / 迭代 | 1,800.0 s / 141,118 次 | 1,800.0 s / **128,545 次** | 1,800.0 s / 77,653 次 |
| 失败 | **0**（成功率 1.0） | **0**（成功率 1.0） | 0 |
| 恢复探针 | **10/10 READY**，p95 14.2 ms | **10/10 READY**，p95 15.1 ms | 10/10 |
| 内存漂移 | 6,334.7 KiB（6.2 MiB） | **4,883.3 KiB（4.8 MiB）** | −94.2 KiB |
| 峰值 RSS | 370.0 MiB | **368.5 MiB** | 388.5 MiB |
| 进程 CPU 峰值 | 1,007%（约 10 核 / 20 核） | **1,008.1%**（约 10 核 / 20 核） | 332% |

说明：漂移**没有冻结阈值，只报数字不判定**；两个环境的差异建议在正式测量时固定环境后复现一次。

⚠️ **本轮修掉一个 B3 自己的遥测缺陷**：v3 第一次长稳报出 `cpu_percent_max = 27009.8`，在 20 核容器里
不可能（上限 2000%）。原因是 `stop()` 与监控线程背靠背采样，`psutil.Process.cpu_percent(None)` 的窗口
塌到微秒级而 CPU 时间差覆盖整秒，商被放大（`memory_during_soak.csv` 里 1,795 个间隔只有最后一个
缩短到 0.4976 s，其余 ≈1.0019 s）。`challenge/hil/samplers.py` 改为自持单调时钟窗口 + 锁，
窗口 < 50 ms 时沿用上一次读数且不消耗窗口；新增 `tests/test_samplers_cpu.py` 3 条。
上表 v3 列是**修复后重跑**的结果，缺陷前后对照见
`evidence/a3_v3_simulation_20261007/09_cpu_sampler_defect.json`。该缺陷只影响 CPU 最大值，
不影响延迟分位、内存漂移与成功率。

### 2.3 环境敏感性（重要：这是测量纪律，不是性能结论）

同样 100 例、同样权重、同样代码，只有环境不同：

| 环境 | 预处理 p50 | 模型推理 p50 | Planner E2E p50 / p95 |
|---|---:|---:|---:|
| Windows 宿主（py3.12） | 6.996 | 6.490 | 14.630 / 17.388 |
| 官方镜像 + 数据走 `D:` 挂载 | **75.716** | 10.618 | **89.197 / 99.507** |
| **官方镜像 + 数据在容器内** | 7.664 | 4.622 | **12.897 / 15.152** |

**I/O 探针**：同一张 JPEG 走 Windows 盘挂载读取 **4.32 ms**、容器本地 **0.022 ms**（**200×**）；
解码+缩放 5.84 ms → 0.43 ms（**14×**）。
→ **在 Windows 上用 Docker 测延迟，必须先把数据复制进容器**，否则延迟虚高约 6×。

### 2.4 FP32 → INT8 量化损失（6 队列）

| 队列 | 例次 | 速度头 max\|Δ\| | 该队列最差头 | 头余弦 min |
|---|---:|---:|---|---:|
| targeted_gap | 99 | **1.4071 m/s** | target_speed_mps | 0.9996 |
| gap300 | 123 | 1.3799 m/s | target_speed_mps | 0.9996 |
| d2_v1_1 | 539 | 1.3128 m/s | target_speed_mps | 0.9994 |
| turn_gap | 29 | 0.9445 m/s | target_speed_mps | 0.9998 |
| d3_wave2 | 56 | 0.9255 m/s | target_speed_mps | 0.9998 |
| ms34 | 4 | 0.5150 m/s | target_speed_mps | 0.9999 |

**`target_speed_mps` 在全部队列都是最大绝对偏差的头**——建议 A2 的敏感层排序纳入物理量纲。

**解码级结果**：FP32 与 INT8 在 **747 例**上**计划结构失配 0 例**
（d2 0/539、gap300 0/123、d3_wave2 0/56、turn-gap 0/29）——行为序列/目标 id/完成类型从不因 INT8 改变。

### 2.5 INT8 → BPU 编译保真度（6 队列 850 例）

| 队列 | 例次 | 最差头 min | 骨干最差 |
|---|---:|---|---:|
| d2_v1_1 | 539 | 0.9991 | 0.9945 |
| gap300 | 123 | 0.9996 | 0.9961 |
| targeted_gap | 99 | 0.9995 | 0.9955 |
| d3_wave2 | 56 | 0.9996 | 0.9923 |
| turn_gap | 29 | 0.9997 | 0.9968 |
| ms34 | 4 | 0.9996 | 0.9922 |
| **合计** | **850** | **全局最低 0.999125** | 0.9922 |

**低于 0.99 的观测为 0** → 编译到 nash-p 没有引入超出量化本身的失真。

### 2.6 OpenExplorer 编译预检（`BPU_ESTIMATED`）

用 A2 的 YAML + 1200 个校准张量、在官方镜像内编译：**59/59 节点落在 BPU、零 CPU fallback**，
`.hbm` 23,579,816 B、`.bc` 23,179,259 B，最小内存需求 24,185,512 B，耗时 128.5 s。
**这不等于板端性能**，只是工具链预检；A4 的正式预估包仍需 `bpu-verify` 核验。

### 2.7 行为复测（真实权重，留出队列）

| 队列 | 例次 | 候选 v1 | 候选 v2 |
|---|---:|---:|---:|
| D3 Wave2 val | 168 | 1.0000 | — |
| D2 v1.1 val | 1617 | 0.9518 | — |
| targeted-gap val | 297 | 0.9192 | — |
| gap300 val | 369 | — | 0.7073 |
| turn-gap val | 87 | 0.6897 | 0.6897 |
| ms34 val | 12 | 0.3333 | **0.7083** |

**能力缺口（不是噪声）**：

- ~~**`TURN_LEFT` 连续两版都从不产出**~~ → **2026-10-07 已更正根因**：不是模型不会，而是
  **解码器可行性掩码**把 `TURN_LEFT`/`TURN_RIGHT` 裁掉了（`scene_capabilities.intersection_ahead=false`
  时 `_feasible_behaviors` 会剔除转弯族）。v3 的未受限 argmax 在这些步上**全部就是 `TURN_LEFT`**，
  详见 §2.9；
- `YIELD` 在 v1 起已修好（6/6、36/36）；
- 多步计划 v1 截断在 2 步 → **v2 能出全长 3/4 步**，但**最后一步错**（teacher 的 `KEEP_LANE` 被答成 `RETURN_TO_LANE`/`STOP`）。
  该"最后一步"同样是掩码造成的：`b1_ms34` 的请求 `allowed_behaviors` 里**没有** `KEEP_LANE`。

### 2.9 新候选 v3（robust closeout）复测（2026-10-07）

`challenge` 新增 6 个提交，A3 发布 `a3_b1_closeout_robust_fp32_candidate_v3`（权重 `7f379c78…`，包校验 PASS，门禁仍 PENDING）。B3 用新权重做了同口径复测：

| 队列 | 例次 | v1 | v2 | **v3** |
|---|---:|---:|---:|---:|
| D3 Wave2 val | 168 | 1.0000 | — | **1.0000** |
| D2 v1.1 val | 1617 | 0.9518 | — | **0.9518** |
| **targeted-gap val** | 297 | 0.9192 | — | **1.0000** ⬆ |
| gap300 val | 369 | — | 0.7073 | **0.7073** |
| turn-gap val | 87 | 0.6897 | 0.6897 | **0.6897** |
| ms34 val | 12 | 0.3333 | 0.7083 | **0.7083** |

**v3 的 robust 训练把 targeted-gap 从 0.9192 提升到 1.0000**；其余队列与 v2 持平。

**根因更正（2026-10-07，重要）**：上表是**解码后计划**的匹配率，它同时包含模型误差**和**
解码器的可行性掩码。B3 新增归因脚本 `harness/x86_sim/turn_left_attribution.py`，对 6 个队列
逐例逐步同时算"未受限 argmax"与"解码结果"：

| 队列 | 教师行为步 | 解码后匹配 | **未受限 argmax 匹配** | 被掩码裁掉的教师行为步 |
|---|---:|---:|---:|---:|
| d2_v1_1_val | 593 | 564 (95.1%) | **593 (100%)** | 29（7 `TURN_LEFT` + 22 `TURN_RIGHT`） |
| d3_wave2_safe_short | 73 | 73 (100%) | **73 (100%)** | 0 |
| d3_targeted_gap_strict | 99 | 99 (100%) | **99 (100%)** | 0 |
| d3_turn_gap_60_strict | 29 | 20 (69.0%) | **29 (100%)** | 9（全 `TURN_LEFT`） |
| d3_gap300_strict | 123 | 87 (70.7%) | **123 (100%)** | 36（全 `TURN_LEFT`） |
| b1_ms34_supplement | 14 | 10 (71.4%) | **14 (100%)** | 4（全 `KEEP_LANE`） |
| **合计** | **931** | **853 (91.6%)** | **931 (100%)** | **78** |

两类掩码规则造成全部 78 处差异：

1. `intersection_ahead=false` → 剔 `TURN_LEFT`/`TURN_RIGHT`（73 步）；
2. 请求的 `allowed_behaviors` 未含 `KEEP_LANE`（ms34 的"恢复"步，4 步）。

**含义**：所谓"连续三个候选都学不会转弯"并不成立——**模型侧一步没错，是契约/掩码把这些行为判成了不可行**。
对 A1/B1/B2 的建议因此改变：**先对齐 `scene_capabilities` / `allowed_behaviors` 与教师标签（或明确掩码策略），
再谈补数据**；否则再训练也不可能在这批用例上拿到分。
口径限制：这里比的是**行为 token（逐步）**，不含目标/车道/速度/完成条件等字段；整份计划的逐字段等价性
仍由 `02_behaviour_replay_v3.json` 与 `consistency` 覆盖。

数值侧：用仓库导出器导出 v3 FP32 ONNX（`b76b5a32…`）→ 官方镜像里用 A2 的 1200 个校准张量编译 → 对 6 队列 **850 例**逐例比对：**离散头 min ≥0.9999、速度头 ≥0.9991、低于 0.99 的观测为 0**（本轮参考是 FP32 ONNX，即把量化与编译损失合并测量，仍达到该水平）。
编译预检：**59/59 节点全在 BPU、零 fallback**，`.hbm` 23,579,544 B，最小内存 24,185,240 B。

另记 A2 的 10-06 交接说明：三份包仍是 **PRE_GATE_ONLY**；B1 的`HISTORICAL_TEMPLATE_LINEAGE_UNRECOVERABLE` 证明使 B2 contract 走`FAIL_CLOSED_IF_TEMPLATE_IDENTITY_MISSING` —— **核心指标衰减的阻塞原因已变成可校验证据，但 Gate 仍未通过**。

证据见 [`evidence/a3_v3_simulation_20261007/`](evidence/a3_v3_simulation_20261007/README.md)。

### 2.10 评分口径相关的可测项：本轮补测（2026-10-07）

| 评分项 | 分值 | 状态 | 数据 |
|---|---:|---|---|
| 端到端响应时延 | 2 | ✅ 已测 | 官方镜像 planner 链 v3 **P50 13.223 / P95 16.339 / P99 18.275 ms**（不含语音前端；v1 为 11.917 / 14.244） |
| 连续 30 分钟稳定性 | 2 | ✅ 已测 | 官方镜像 v3 **128,545 次、0 失败、恢复 10/10、漂移 4.8 MiB**（v1：141,118 次） |
| **多模态信息融合有效性** | 5 | ⚠️ 已补测（代理，**6 队列 850 例**） | 置零 `state` → 逐例最差头余弦均值 **0.626–0.883**、行为 argmax 翻转 **36%–100%**（各队列 20/56、82/99、111/123、458/539、29/29、2/4）；置零 `rgb`/`text_tokens` → 余弦 **≥0.993**、**行为在 6 个队列全部 0 改变**；置零 `targets` 仅 ms34 有 2/4 改变 |
| 模糊指令安全策略 | 2 | ⚠️ 代理数据 | 异常输入 10 例，9/10 符合预期；`empty_source_text` 未 fail-closed |
| 语义-动作对齐度 | 5 | ⚠️ 代理数据（口径已更正） | 解码后匹配 v3：D2 0.9518 / d3w2 1.0000 / targeted-gap 1.0000 / gap300 0.7073 / turn-gap 0.6897 / ms34 0.7083；**未受限 argmax 行为匹配 931/931 = 1.0000**（差额 78 步全部来自解码器可行性掩码，见 §2.9） |
| FLOPs 压缩比 | 15 | ✅ 数据齐且 B3 独立复算一致 | 0.1769125802176339（相对 Teacher 下界）；**分母定义待团队确认** |
| 场景任务完成率（三级难度） | 15 | ❌ **未测** | 缺官方 1000 帧基准与闭环场景；此前只跑过 13 个 CARLA 场景冒烟 + 8 个安全场景 |
| ASR 准确率 / 解析延时 | 3 | ❌ **未测** | 语音前端不在 B3 链路 |
| 自然语言意图解析正确率 | 8 | ❌ **未测** | A3/B2 职责 |
| 方言与噪声鲁棒性 | 2 | ❌ **未测** | 需要音频输入，当前链路无 |
| 行驶动作合理性 | 5 | ❌ **未测** | 需要闭环舒适性指标（CARLA 实测） |
| 异构算力利用率 | 10 | ❌ **未测** | 缺官方公式 + A4 Runtime |
| 核心指标衰减 | 15 | ❌ **未测** | 缺 B2 冻结 Benchmark + A3 同基准对比 |

结论：**挑战赛道四项里只有 FLOPs 一项的数据齐**（且 B3 已独立复算），异构利用率与核心衰减仍未测；基础赛道 11 个数据相关项里，B3 能覆盖的 3 项已测/已补测，其余 8 项依赖语音前端、闭环场景或 B2 的基准。

### 2.11 ONNX 字节身份项（submission ledger 的阻塞项之一，2026-10-07）

`submission/challenge/PRE_SUBMISSION_LEDGER_20261007.md` 要求 A4/B3 先解决 A2 的
`681a5d4b…` 与 B3 的 `b76b5a32…` 两份 FP32 ONNX 的**字节差异**。B3 的结论：

* **同一个 `state_dict` 用仓库导出器导出本来就不保证字节可复现**——导出器把
  `source_git_sha`（默认 = 导出检出的 HEAD）等溯源字段写进 `metadata_props`，
  `producer_version` 记录 torch 版本；换掉这些字段，文件大小可以完全不变而 SHA 不同；
* 在官方镜像内把 `--source-git-sha` 依次换成 6 个候选提交重导出，**没有一个**等于 A2 的
  `681a5d4b…`（明细见 `11_onnx_source_sha_probe.json`）→ 靠猜参数对齐字节不可行；
* 新增 `harness/x86_sim/onnx_export_equivalence.py`：对两份 ONNX 比对
  文件 SHA / 元数据差异 / 图拓扑摘要 / 50 个 initializer 的逐张量 SHA / 冻结输入上的十头数值。
  实测（torch 2.6.0 导出 × torch 2.8.0 导出）：**元数据差异只有 `source_git_sha`，
  拓扑一致、initializer 逐张量一致、100 例数值 max abs diff = 0.0、argmax 100/100**，
  判定 `METADATA_ONLY_DIFFERENCE_NUMERICALLY_IDENTICAL`。

**给 RC 的判据**：不要求两边字节相同，要求「**唯一交付字节 + 等价证明**」这一对证据——
要么 A2 交出 `681a5d4b…` 的文件（或其 `initializer_digest`/`topology_digest`），B3 跑一遍
该工具；要么 RC 直接采用官方镜像内固定 `--source-git-sha` 重导的那一份（`b552b860…`），
A2 量化 / A4 编译 / B3 核验全部指向它。
证据：`evidence/a3_v3_simulation_20261007/10_onnx_export_identity.json`。

### 2.8 数据与交付物复核

| 对象 | 结果 |
|---|---|
| A2→A4 OpenExplorer 包（154 MB） | **PASS**：1217/1217 文件匹配；两份 INT8 与其 manifest 逐字节一致；**告警**：绑定候选 **v1**，而最新是 v2 |
| 冻结校准 `calibration_v1` | **PASS**：300 例、7/7 哈希；与 6 个 val 划分（850 例）**零重叠** |
| B1 release（5 个，三种通行证形态） | 全部 **PASS**（含"content-bound 非签名"的等级差异说明） |
| A3 候选包（v1/v2/v3） | 包校验 **PASS**（9 文件 + 权重摘要一致） |
| A2 的 robust v3 量化结果（上游 2026-10-07 文档） | 已读取：FP32 ONNX `681a5d4b…`、Full INT8 `275dce5c…`（23,273,686 B）、Mixed Top-3 `9a08a03c…`（23,622,853 B）；**但本机的 A2 包仍是 v1 期的**（`student_int8.onnx` = `560a6166…`、mixed = `02c600d4…`），所以 **v3 的 INT8 逐头漂移尚不是 B3 独立复算的结果**——需要 A2/A4 把 v3 的两个 INT8 文件放到本机或仓库 |
| B3 对 A2 v3 FP32/INT8 的身份关系 | 两份 FP32 ONNX 的**字节不同但权重/拓扑/数值等价**（§2.11，100 例 max abs diff = 0.0）；INT8 与 FP32 的等价性待 v3 INT8 文件到位后按同一工具补测 |

## 3. 缺口清单（按分数影响排序）

| # | 缺口 | 影响 | 责任方 | 现状 / B3 能配合什么 |
|---|---|---|---|---|
| 1 | **核心指标衰减** 无同基准对比 | 挑战赛道 **15 分**（当前 0） | **B2**（冻结 Benchmark）+ **A3**（同基准对比） | B3 可提供可复现的评测脚本与一致性复核（`consistency`/`groups`） |
| 2 | **异构算力利用率** 无官方公式、无 Runtime | 挑战赛道 **10 分**（当前 0） | **B2**（公式）+ **A4**（Runtime） | `utilization_policy.py` 已就绪，公式一到即插即用；B3 负责核验 |
| 3 | **FLOPs 分母口径**未定 | 挑战赛道 **15 分**（口径误解则 0） | **A1 + 团队** | 数据已交叉核对（A1 与 A2 报告 11 字段零差异）；B3 可复算两种口径 |
| 4 | 最终 **A4 Runtime** 未交付 | 影响 #2、以及"官方环境实测"的正式性 | **A4** | Runtime 一到，B3 用同一条命令重跑官方环境测量 |
| 5 | 无板卡 / 无探针 | 功耗、真实 BPU 利用率、J6P 延迟 → `NOT_MEASURED` | 硬件/团队 | 材料里明确写"依赖实板，按官方口径处理"，不用估算冒充 |
| 6 | 语音前端相关评分项（ASR、意图解析、多模态融合、语义-动作对齐…） | 基础赛道多项 | A3/语音组/B2 | 非 B3；B3 只提供测量框架与证据格式 |
| 7 | 官方 1000 帧统一评测基准未提供 | 影响所有"数据同源"项 | 组委会/发榜单位 | 我们已备自建队列与冻结脚本，材料中说明来源与口径 |
| 8 | **契约/掩码与教师标签冲突**：`intersection_ahead=false` 却标注 `TURN_LEFT/RIGHT`；ms34 的 `allowed_behaviors` 不含教师用到的 `KEEP_LANE` | 直接决定 6 队列上 78/931 步的行为匹配（d2 4.9%、turn-gap 31.0%、gap300 29.3%、ms34 28.6% 的差额全在这里） | **B1（数据/场景能力字段）+ B2（契约口径）+ A1/A3（确认）** | B3 已给出逐步归因证据（`evidence/a3_v3_simulation_20261007/08_*`）与交接文档 [`mask_contract_conflict_handoff.md`](mask_contract_conflict_handoff.md)（含 78 步逐案清单与三条可选决策）；**先对齐字段再谈补数据**，否则训练无解 |
| 9 | **FP32 ONNX 唯一字节**（submission ledger 明列） | Final RC 的前置：A2 量化、A4 编译、B3 核验必须指向同一份 ONNX | **A2（交出文件）+ A4/B3（等价证明）** | B3 已给出可执行判据与工具：`onnx_export_equivalence.py`（实测两份字节不同的导出**数值逐位相同**，差异只在溯源元数据）；见 §2.11 |

## 4. 如何复现（材料 #12）

```bash
# 1) 官方环境指纹
bash challenge/hil/harness/x86_sim/check_official_env.sh

# 2) 在官方镜像内跑测量（仓库挂 /repo；数据先复制进容器）
#    第 3 个参数是候选目录，脚本会把输出写到 /tmp/b3_official_full_<候选名>/
bash challenge/hil/harness/x86_sim/run_in_official_env.sh --recreate -- \
     "bash challenge/hil/harness/x86_sim/run_official_full_and_soak.sh 30 539 \
      challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3"

# 3) 挂载 I/O 探针（解释环境敏感性）
bash challenge/hil/harness/x86_sim/run_in_official_env.sh -- "python3 /work/x86_sim/probe_mount_io.py"

# 4) INT8 编译保真度 / 计划等价性
bash challenge/hil/harness/x86_sim/run_x86_matrix.sh
py -3.12 -m challenge.hil.cli consistency --repo . --onnx <int8.onnx> --baseline-onnx <fp32.onnx> \
        --adapter onnx --frozen challenge/hil/frozen/d2_v1_1_val --limit 539 --out <out.json>

# 5) 本地自测
py -3.12 -m pytest -q challenge/hil/tests   # 127 passed

# 6) 行为缺口归因 + 多模态消融（宿主；6 队列 850 例一次跑完）
py -3.12 challenge/hil/harness/x86_sim/cohort_diagnostics.py \
        --onnx <student_v0_fp32_v3.onnx> --work <dumps 根目录> --out <out.json>

# 7) 把运行目录压成证据 JSON（只留身份/分位/长稳摘要）
py -3.12 challenge/hil/harness/x86_sim/collect_official_run.py \
        --run <run_dir> --out <evidence.json> --label a3_v3
```

## 5. 声明

- 本文所有数字来自 **X86** 或**工具链分析**，**没有任何 J6P 板端实测**；
- 测试所用权重为 **PENDING_A3_FP32_GATE** 候选，**不构成精度或达标结论**；
- 评测数据为**自建留出队列**（非官方 1000 帧基准），来源、规模与口径见 §1；
- 正式提交前，延迟/内存/长稳三项需在**官方环境 + A4 最终 Runtime** 上按同一命令重跑。
- 引用 §2.9 的行为匹配时**必须写明分母**：`解码后匹配`是"解码器 + 模型"的合计表现，
  `未受限 argmax 匹配`才是模型侧表现；两者在 6 队列上相差 78 步，差额全部来自解码器的可行性掩码。
