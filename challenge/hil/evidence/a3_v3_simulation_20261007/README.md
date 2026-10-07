# 新候选 v3（robust closeout）仿真复测（2026-10-07）

> ⚠️ 门禁仍是 `PENDING_A3_FP32_GATE` / `PENDING_B2_INDEPENDENT_VALIDATION`，
> 跑在 X86（官方镜像）上，无板卡。所有结论 `DIAGNOSTIC_ONLY`，**不是精度或达标结论**。

## 0. 这一轮测的是"新模型"

`challenge` 新增 6 个提交，其中 A3 发布 **`a3_b1_closeout_robust_fp32_candidate_v3`**：

| 项 | v1（10-02） | v2（10-02 晚） | **v3（本次）** |
|---|---|---|---|
| 权重 sha256 | `eaee4402…` | `6b6ec1d8…` | **`7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`** |
| 训练视图 | 累计视图 | governed closeout | governed closeout（robust） |
| train / dev | 5826 / 1104 | 5856 / 1108 | 5856 / 1108 |
| 门禁 | PENDING | PENDING | PENDING |

包校验 **PASS**（9 文件、权重摘要与 `candidate_identity` 一致）。

同时 A2 在 10-06 更新了交接说明（`challenge/quantization/A2_HANDOFF_UPDATE_20261006.md`）：
由于没有 `A3_FP32_GATE_PASSED`，他们的三份包（A3/B2/A4）仍是 **PRE_GATE_ONLY**；
并记录了 B1 的"历史模板身份不可恢复"证明，B2 的 contract 对此是
`FAIL_CLOSED_IF_TEMPLATE_IDENTITY_MISSING`——也就是说**核心指标衰减这一项的阻塞原因已变成可校验证据**，
但 Gate 仍未通过。

## 1. 行为复测：v1 / v2 / v3 对照（真实权重，留出队列，各 3 轮）

| 队列 | 例次 | v1 | v2 | **v3** |
|---|---:|---:|---:|---:|
| D3 Wave2 val | 168 | 1.0000 | — | **1.0000** |
| D2 v1.1 val | 1617 | 0.9518 | — | **0.9518** |
| **targeted-gap val** | 297 | 0.9192 | — | **1.0000** ⬆ |
| gap300 val | 369 | — | 0.7073 | **0.7073** |
| turn-gap val | 87 | 0.6897 | 0.6897 | **0.6897** |
| ms34 val | 12 | 0.3333 | 0.7083 | **0.7083** |

**结论**：v3 的"robust"训练在 **targeted-gap 上从 0.9192 提升到 1.0000**（该队列此前是缺口），
其余队列与 v2 持平。**`TURN_LEFT` 依旧从不产出**——v3 在 turn-gap 27/27、gap300 108/108 上
仍把 TURN_LEFT 答成 `SLOW_DOWN`（v1 是 `SET_SPEED`，v2/v3 是 `SLOW_DOWN`）。
这已经是**连续三个候选**同一个缺口，建议把"转弯族补数与训练目标"列为最高优先级。

（`ms34` 的多步：v3 与 v2 相同——能出全长 3/4 步序列，但**最后一步错**：
teacher 的 `KEEP_LANE` 被答成 `RETURN_TO_LANE` 或 `YIELD`。）

## 2. v3 的数值仿真：FP32 ↔ 编译后的 BPU 产物（6 队列 850 例）

流程：用仓库导出器（**已合并且支持 `--weights`**）导出 v3 的 FP32 ONNX
（sha256 `b76b5a32dfde16d52b34ad553bce9e899eaf4220142a8ddd6e9b4aea4fc808e5`）→
在官方镜像里用 **A2 的 1200 个校准张量**编译（`cal_config_v3.yaml`）→
对全部 6 个留出队列逐例 `hb_verifier`（FP32 ONNX ↔ 编译产物 `.bc`）。

| 队列 | 例次 | 离散头 min | 速度头 min | 骨干最差 |
|---|---:|---:|---:|---:|
| d2_v1_1_val | 539 | 0.9999 | **0.9991** | 0.9958 |
| gap300_val | 123 | 0.9999 | 0.9996 | 0.9965 |
| targeted_gap_val | 99 | 0.9999 | 0.9995 | 0.9958 |
| d3_wave2_val | 56 | 1.0000 | 0.9996 | 0.9947 |
| turn_gap_val | 29 | 1.0000 | 0.9998 | 0.9967 |
| ms34_val | 4 | 1.0000 | 0.9997 | 0.9960 |
| **合计** | **850** | — | — | 0.9947 |

**十头全局最低余弦 0.999134，低于 0.99 的观测为 0。**
注意口径：v1 那一轮的矩阵参考是 **INT8 ONNX**（只测"编译保真度"），
本轮的参考是 **FP32 ONNX**（把量化损失与编译损失合并测量），
即便如此 v3 的离散头仍全部 ≥0.9999——说明 v3 的预测轨迹对量化**更稳**。

## 3. v3 的 OpenExplorer 编译预检

| 项 | 值 |
|---|---|
| 结果 | 成功，`nash-p`，0 error |
| 算子落点 | **59/59 节点全在 BPU，零 CPU fallback** |
| 产物 | `.hbm` 23,579,544 B；`.bc` 23,179,197 B |
| 内存 | input 603,136 / output 2,560 / static 23,579,544 / dynamic 605,696，**min requirement 24,185,240 B** |

口径：`BPU_ESTIMATED`（工作站工具链预检），不是板端性能。

## 文件

| 文件 | 内容 |
|---|---|
| `00_handoff_integrity.log` / `01_handoff_integrity_compact.json` | v3 包独立校验（PASS） |
| `02_behaviour_replay_v3.json` | v1/v2/v3 行为复测与 teacher→student 混淆矩阵 |
| `03_matrix_summary_v3.json` | 6 队列 × 850 例的逐头余弦矩阵 |
| `04_oe_compile_v3.log` | v3 编译预检日志（节选） |
| `05_node_placement_v3.csv` | 59 个节点落点（全部 BPU） |
| `06_flops_crosscheck_and_modality_ablation.json` | FLOPs 独立复算 + 多模态消融（见下） |
| `07_official_env_v3_full_and_soak.json` | v3 在官方镜像内的 539×3 分位与 30 分钟长稳摘要（§5） |
| `08_cohort_diagnostics_v3.json` | 6 队列 850 例的多模态消融 + 行为缺口归因（§6） |
| `09_cpu_sampler_defect.json` | 进程 CPU 峰值异常的定位与修复记录（§7） |
| `10_onnx_export_identity.json` | 两份字节不同的 FP32 ONNX 的权重/拓扑/数值等价性实测（§8） |
| `11_onnx_source_sha_probe.json` | 用 `--source-git-sha` 反推 A2 字节的穷举结果（全部不匹配，§8.3） |

## 4. 追加：评分口径相关的两项可测数据（2026-10-07）

### 4.1 FLOPs：B3 独立复算与仓库报告**完全一致**

用仓库的 `challenge/export/compute_flops.py` 在干净检出上重跑，7 个关键字段
（参数 23,006,581、MACs 249,320,448、FLOPs 498,640,896、教师下界参数/FLOPs、
比值 0.1769125802176339、`ratio_pass=true`）与 `challenge/flops_report.json` **逐项相同**。
说明：同一工具重跑只能证明**可复现**，不构成方法独立；**分母定义仍需团队确认**。

### 4.2 多模态融合有效性：消融实验（v3，D2 val 150 例）

做法：把四个输入之一**置零**，走同一解码器（`StudentPlanAdapter`），与全输入基线比较。

| 置零的输入 | 最差头余弦（min） | 行为 logits 平均最大偏差 | 相对变化（均值） | 行为 argmax 翻转 |
|---|---:|---:|---:|---:|
| **`state`** | **0.4654** | **8.0242** | **71.6%** | **122/150** |
| `targets` | 0.9544 | 0.8701 | 9.8% | 0/150 |
| `rgb` | 0.9637 | 0.5026 | 4.1% | 0/150 |
| `text_tokens` | 0.9930 | 0.3467 | 3.3% | 0/150 |

**读法（重要，含口径限制）**：去掉 `state` 会让模型剧烈变化；而去掉 **rgb / text / targets**
只让 logits 轻微变化，且**从不改变解码后的行为**。也就是说：**这一版候选的计划几乎完全由
state 主导**，视觉、语言、目标三路在决策层面的贡献很小。

⚠️ 口径限制：置零 ≠ 移除证据（全黑图仍是图，零 token 仍是 token 序列），
该数字衡量的是"把某模态替换为其零值后的敏感性"，不是严格的意义上的模态贡献度；
且这是 X86 数值诊断，不是精度结论。这项数据对应评分细则里"多模态信息融合有效性"，
建议 A1/A3 复核（若正式评测也呈现同样形态，"VLA 多模态联合压缩"的创新性叙事会被质疑）。

### 4.3 模糊指令安全策略（代理数据）

异常输入套件 10 例：**9/10 与预期一致**，唯一不符是
`empty_source_text`（预期 `MUST_FAIL_CLOSED`，实际产出了计划）。是否算 Gate 失败由 B2 判定
（套件自带的 `policy_note` 已写明）。

## 5. v3 在官方镜像内的同口径复测（2026-10-07）

命令与 v1 那一轮完全相同（官方镜像 + 539 例 × 3 轮 + 30 分钟长稳），只把候选目录换成 v3。
`run_official_full_and_soak.sh` 现在接受第 3 个参数（候选目录），输出目录按候选名区分，
避免覆盖上一轮：

```bash
bash challenge/hil/harness/x86_sim/run_in_official_env.sh -- \
  "bash challenge/hil/harness/x86_sim/run_official_full_and_soak.sh 30 539 \
   challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3"
```

### 5.1 539 例 × 3 轮（1,622 次调用，全部 `READY`）

| 时段 | v1 P50 / P95 / P99 / max | **v3 P50 / P95 / P99 / max** |
|---|---:|---:|
| 预处理 | 7.359 / 8.091 / 8.521 / 10.108 | 7.731 / 9.616 / 11.077 / 15.980 |
| Token/Target packing | 0.287 / 0.407 / 0.517 / 1.535 | 0.346 / 0.491 / 0.854 / 1.622 |
| **模型纯推理** | **4.027 / 5.445** / 6.068 / 7.233 | **4.513 / 5.814** / 6.569 / 9.666 |
| 后处理 | 0.027 / 0.041 / 0.078 / 0.109 | 0.033 / 0.047 / 0.080 / 0.112 |
| Adapter | 0.163 / 0.236 / 0.459 / 1.602 | 0.197 / 0.277 / 0.409 / 0.845 |
| 计划校验 | 0.436 / 0.625 / 1.087 / 55.269 | 0.511 / 0.740 / 1.099 / 60.832 |
| **Planner E2E** | **11.917 / 14.244** / 15.460 / 68.983 | **13.223 / 16.339** / 18.275 / 70.131 |

v3 全链比 v1 慢约 **+1.3 ms（P50）/+2.1 ms（P95）**；两者都远离 150 ms 阈值。
口径 `X86_MEASURED`：官方镜像、候选权重 `7f379c78…`（`PENDING_A3_FP32_GATE`）、无板卡、无 A4 Runtime。

### 5.2 30 分钟长稳

| 项 | v1（2026-10-03） | **v3（2026-10-07，采样器修复后重跑）** |
|---|---:|---:|
| 时长 | 1,800.0 s | 1,800.0 s |
| 迭代 | 141,118 | **128,545** |
| 失败 / 成功率 | 0 / 1.0 | **0 / 1.0** |
| 恢复探针 | 10/10 READY，p95 14.2 ms | **10/10 READY，p95 15.1 ms** |
| 内存漂移 | 6,334.7 KiB | **4,883.3 KiB（4.8 MiB）** |
| 峰值 RSS | 370.0 MiB | **368.5 MiB** |
| 进程 CPU 峰值 | 1,007%（20 核机器上约 10 核） | **1,008.1%**（< 100 × 20 核） |

漂移**没有冻结阈值，只报数字不判定**（阈值归 B2/A4）。

⚠️ v3 的**第一次**长稳（`b3-soak-20261007T121914Z-9a226211`）报了 `cpu_percent_max = 27009.8`，
在 20 核容器里不可能。B3 定位为**自己的遥测采样器竞态缺陷**并修复（详见 §7 与
`09_cpu_sampler_defect.json`），上表是修复后重跑的结果；两轮的成功率、漂移、RSS 结论一致，
差异只出现在"是否把竞态样本计入 MAX"。

## 6. 行为缺口的根因归因：模型还是解码器掩码（2026-10-07）

前三轮一直记着一条"能力缺口"：学生**从不产出 `TURN_LEFT`**（turn-gap 27/27、gap300 108/108 全答
`SLOW_DOWN`），并据此建议 A1/A3 去补转弯族数据。本轮把这件事查到了根上。

**方法**：新增 `harness/x86_sim/turn_left_attribution.py`。仓库适配器
`challenge/planner/student_adapter.py` 在取 argmax 之前会按请求的 `scene_capabilities`
剔除不可行行为（`_feasible_behaviors`）；因此我们**同时**记录每一步的
①未受限 argmax、②掩码后的选择、③解码结果、④教师行为，四者互相对照。

| 队列 | 教师行为步 | 解码后匹配 | **未受限 argmax 匹配** | 被掩码裁掉的教师行为步 |
|---|---:|---:|---:|---:|
| d2_v1_1_val | 593 | 564 (95.1%) | **593 (100%)** | 29（7 `TURN_LEFT` + 22 `TURN_RIGHT`） |
| d3_wave2_safe_short | 73 | 73 (100%) | **73 (100%)** | 0 |
| d3_targeted_gap_strict | 99 | 99 (100%) | **99 (100%)** | 0 |
| d3_turn_gap_60_strict | 29 | 20 (69.0%) | **29 (100%)** | 9（全 `TURN_LEFT`） |
| d3_gap300_strict | 123 | 87 (70.7%) | **123 (100%)** | 36（全 `TURN_LEFT`） |
| b1_ms34_supplement | 14 | 10 (71.4%) | **14 (100%)** | 4（全 `KEEP_LANE`） |
| **合计** | **931** | **853 (91.6%)** | **931 (100%)** | **78** |

全部 78 处差异来自两条掩码规则：

1. **`scene_capabilities.intersection_ahead = false`** → 剔除 `TURN_LEFT`/`TURN_RIGHT`
   （73 步）。被删的每一步，模型的未受限 argmax **就是** `TURN_LEFT`，且 logit 领先次优
   **+6.7 ~ +7.4**、排名第 1（逐例明细见 `08_cohort_diagnostics_v3.json` 的
   `teacher_turn_left_steps`）。
2. **请求的 `allowed_behaviors` 不含 `KEEP_LANE`** → ms34 的"恢复"步被判不可行（4 步），
   于是被答成 `RETURN_TO_LANE`/`YIELD`。

**读法**：所谓"连续三个候选都学不会转弯"**不成立**——模型侧一步没漏，是**契约/掩码**把这些
行为判成了不可行。对团队的直接含义：

* 对 **A1/B1/B2**：先判定这是"场景能力字段标错"还是"掩码规则过严"。数据里
  `intersection_ahead=false` 却标注 `TURN_LEFT/RIGHT`，两者必须有一个改；
* 对 **A3**：**不要**为这批用例去补转弯训练数据（解不了），先等字段口径对齐；
* 保留口径：这里比的是**行为 token（逐步）**，不含目标/车道/速度/完成条件等字段；
  整份计划的逐字段等价性仍由 `02_behaviour_replay_v3.json` 与 `consistency` 覆盖。

逐案清单（78 步，含 `case_id`/`step`/教师行为/模型 argmax/掩码后选择/被挡原因）在
`08_cohort_diagnostics_v3.json` 的 `turn_left_attribution.<队列>.mask_blocked_teacher_steps`；
面向 B1/B2/A1/A3 的决策请求见 [`../../mask_contract_conflict_handoff.md`](../../mask_contract_conflict_handoff.md)。

### 6.1 多模态消融扩到 6 队列（850 例）

把第 4.2 节的消融从"d2 150 例"扩到**全部 6 个队列 850 例**（同一 ONNX、同一解码器）：

| 置零的输入 | 逐例最差头余弦（均值，范围） | 行为 argmax 翻转 | 行为序列改变 |
|---|---|---|---|
| **`state`** | **0.626 – 0.883** | **36% – 100%**（6 个队列全部非零：20/56、82/99、111/123、458/539、29/29、2/4） | 124/539（d2）…16/29（turn-gap） |
| `targets` | 0.876 – 0.997 | 0 | 仅 ms34 2/4 |
| `rgb` | 0.994 – 0.999 | 0 | **0（六个队列全部）** |
| `text_tokens` | 0.996 – 1.000 | 0 | **0（六个队列全部）** |

结论与第 4.2 节一致且更稳：**这一版候选的计划几乎完全由 `state` 决定**，`rgb`/`text_tokens`
在决策层面**从不改变行为**。这项数据对应评分细则的"多模态信息融合有效性"，建议 A1/A3 复核；
若正式评测也呈同样形态，"VLA 多模态联合压缩"的创新性叙事会被质疑。

## 7. B3 自修缺陷：进程 CPU 峰值被采样竞态放大（2026-10-07）

| 项 | 值 |
|---|---|
| 现象 | v3 第一次 30 分钟长稳报 `cpu_percent_max = 27009.8`，而容器只有 20 核（物理上限 2000%） |
| 机制 | `BackgroundMonitor.sample_once` 由监控线程、`start()`、`stop()` 三处调用；`psutil.Process.cpu_percent(None)` 用"该对象上次调用"当窗口，`stop()` 紧随监控线程时窗口塌到微秒级，而 CPU 时间差仍覆盖整秒 → 商被放大 |
| 佐证 | `memory_during_soak.csv` 的 1,795 个采样间隔里只有最后一个异常缩短（0.4976 s，其余 ≈1.0019 s） |
| 修复 | `challenge/hil/samplers.py`：自持 `monotonic` 窗口 + 锁；窗口小于下限（`min(50 ms, 间隔/2)`，本轮间隔 1 s → 50 ms）时沿用上一次有效读数且**不消耗窗口** |
| 测试 | 新增 `challenge/hil/tests/test_samplers_cpu.py`，3 条全绿 |
| 修复前 | `cpu_percent_max = 27009.8`（不可引用） |
| 修复后 | `cpu_percent_max = 1008.08`（约 10 核，可引用） |

影响范围：**只影响 utilization 遥测的最大值**；延迟分位（独立的 `perf_counter_ns` 打点）、
内存漂移、成功率均不受影响。逐项记录见 `09_cpu_sampler_defect.json`。

## 8. 解决 submission ledger 的 ONNX 身份项（2026-10-07）

`submission/challenge/PRE_SUBMISSION_LEDGER_20261007.md` 第 121 行要求 **A4/B3 先解决
`681a5d4b…`（A2 导出的 FP32 ONNX）与 `b76b5a32…`（B3 导出的同一权重 ONNX）的字节差异**
才能做 Final RC。B3 把这件"要求"变成了可执行的判据。

### 8.1 结论先写

**同一个 `state_dict` 用仓库导出器导出，本来就不保证字节可复现**——导出器会把
`source_git_sha` 等溯源字段写进 ONNX 的 `metadata_props`，而 `source_git_sha` 默认取
**导出时那个检出点的 HEAD**；`producer_version` 则记录导出环境的 torch 版本。
把这两个字段换掉，文件大小可以完全不变而 SHA 不同（本次两份文件都是 92,041,414 B）。

因此 RC 的正确判据不是"字节相同"，而是：**挑一份 ONNX 作为唯一交付字节，另一份用
权重/拓扑/数值三项等价性证明**。证明工具已落地：
`harness/x86_sim/onnx_export_equivalence.py`。

### 8.2 实测：torch 2.6（宿主）× torch 2.8（官方镜像）两次导出

| 项 | 结果 |
|---|---|
| 文件 SHA | `b76b5a32…`（torch 2.6.0）vs `b552b860…`（torch 2.8.0）——**不同** |
| 文件大小 | 92,041,414 B —— **相同** |
| `metadata_props` 差异 | 只有 `source_git_sha`（`6b6a2102…` vs `11823750…`） |
| `producer_version` | `2.6.0` vs `2.8.0` |
| 图拓扑（节点/输入/输出/属性摘要） | **完全一致** |
| 50 个 initializer 的逐张量 SHA | **逐张量一致**（`initializer_digest` 相同） |
| 100 例冻结输入的十头数值 | **max abs diff = 0.0**，argmax 一致 100/100 |
| 判定 | `METADATA_ONLY_DIFFERENCE_NUMERICALLY_IDENTICAL` |

### 8.3 把 A2 的字节反推出来的尝试：失败，但很有信息量

把 `--source-git-sha` 依次替换成 5 个可能的提交（`c2576e59`、`3ebd0682`、`242e79ee`、
`197bc045`、`6b6a2102`）在官方镜像内重导出，得到的 SHA 分别是
`42893c22…`、`798848e9…`、`af6acfea…`、`5a9e902d…`、`5245b5e8…`——**没有一个等于 A2 的
`681a5d4b…`**。也就是说，A2 的字节差异**不只是 git sha**（可能还含导出脚本路径、torch 小版本
或保存方式）。这正说明：**靠"猜参数"不可能对齐字节，必须由一方交出文件、另一方跑等价证明**。

### 8.4 给 RC 的两条可执行路径（任选其一）

1. **单一字节路线**：A2 把 `681a5d4b…` 的 ONNX 文件（或其 `initializer_digest` +
   `topology_digest`，本工具会打印）交给 B3/A4；B3 用同一工具跑一遍，若判定
   `…_NUMERICALLY_IDENTICAL`，则 RC 固定用该字节，A4 的编译与 B3 的核验都指向它；
2. **统一导出路线**：RC 直接采用**在官方镜像内、固定 `--source-git-sha` 重导出的那一份**
   （本次是 `b552b860…`），A2 的量化、A4 的编译、B3 的核验全部指向这唯一字节。

无论走哪条，都**不需要**两边字节相同；需要的是"**唯一字节 + 等价证明**"这一对证据。
