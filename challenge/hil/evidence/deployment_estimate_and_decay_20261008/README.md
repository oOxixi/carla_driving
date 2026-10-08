# 部署性能预估与同口径 Teacher/Student 衰减（B3，2026-10-08）

本目录交付两件 B3 负责的产物：

1. **BPU 性能预估输出及其依据**（工具链估算，非板端实测）；
2. **同一评测口径下的 Teacher/Student 核心指标衰减比较**（850 例冻结留出队列）。

> 口径提醒：两件都是 `X86/工具链` 证据，无板卡、无 A4 Runtime、无 B2 冻结基准。
> 权重门禁仍为 `PENDING_A3_FP32_GATE`。

## 1. BPU 性能预估（`01_bpu_performance_estimate_v3.json`）

用 OpenExplorer 3.9.1（`horizon_tc_ui 3.5.16`、`HBDK 4.11.11`、`march nash-p`、单 BPU 核）
对 v3 候选的 FP32 ONNX 做 PTQ 编译，读出工具链的性能模型：

| 项 | 值 |
|---|---|
| **预估延迟** | **615.1 µs（0.615 ms）** |
| **预估吞吐** | **1625.78 FPS** |
| DDR 访问量 / 带宽需求 | 22.887 MB / 次；**37.209 GB/s** |
| 最小内存需求 | 24,185,240 B（static 23,579,544 + input 603,136 + output 2,560 + dynamic 605,696） |
| 算子落点 | **59/59 节点全部在 BPU，0 CPU fallback** |
| 数据类型分布 | si8 37 / f32 15 / si16 4 / fused 3 |
| 逐节点量化质量 | 校准后最差余弦 **0.971495**，量化后最差 **0.971386** |

**依据（可核验）**：

1. **身份绑定**：工具链读出的 int8 MACs **249,320,448** 与 Conv ops **498,640,896** 和
   `challenge/flops_report.json` 完全一致（B3 也独立复算过同一组数值）→ 预估值绑定的是"我们实测的那个模型"，
   不是过期产物；产物 SHA256 逐项记在 JSON 里（ONNX/PTQ ONNX/`.bc`/`.hbm`）。
2. **瓶颈判定**：47 个层的载入时间合计 **616 µs**，计算时间合计 **121 µs** →
   该模型在 nash-p 上**是 DDR 载入受限，不是 MAC 受限**。
3. **区间利用率**：工具链给出的 7 个区间（每段 0.1 ms）计算单元利用率
   `[0.243, 0.154, 0.126, 0.084, 0.084, 0.182, 0.091]`，**均值 13.8%、峰值 24.3%**。

**必须一起声明的限制**：这是 `BPU_ESTIMATED`，**不是板端延迟**；没有读 BPU/DDR 硬件计数器；
单核配置；DDR 带宽是工具的内存模型而非实测总线；算子统计不含注意力/归一化/激活/搬运；
上面那个 13.8% 是**单次推理内部**的计算单元利用率，**官方"异构算力利用率"公式（端到端 CPU/GPU/NPU/DSP）
仍归 B2/A4**。

**对材料的用法**：把它写成"轻量化模型在 nash-p 单核上的工具链预估值 0.615 ms、1625 FPS，且为内存受限"，
并明确"板端实测待 A4 Runtime / 实板"。它同时解释了为什么"算子已 100% 落在 BPU"不等于"利用率高"。

## 2. 同一评测口径的 Teacher/Student 衰减（`02_teacher_student_core_metric_decay.json`）

**协议（两侧完全同口径）**：6 个冻结留出队列共 **850 例**；每个用例自带 **Teacher 计划**（固定 Qwen 教师，
release 内固化），学生侧用**同一个 `StudentPlanAdapter`** 解码同一份 ONNX；逐步对齐后逐字段比对。
Teacher 以自身计划为参照，因此其一致率**构造性地为 100%**，衰减 = 1 − 学生一致率。

| 指标 | 学生一致率 | 衰减 | 说明 |
|---|---:|---:|---|
| 计划步数 | **99.88%** | 0.12% | 931 步 vs 932 步（多 1 步） |
| **行为 token（解码后）** | **91.62%** | **8.38%** | 差额 78 步**全部**由解码器可行性掩码造成；未受限 argmax 为 **100%** |
| 完成条件（completion type） | 89.04% | 10.96% | 双方都给值 |
| 目标车道（双方都给值时） | **100%** | 0% | 严格口径只有 19.3%，差额 751 步是**字段约定**：教师对 KEEP_LANE 填 `CURRENT`，学生按设计留空 |
| 目标 id（双方都给值时） | **100%** | 0% | 但有 **50 步**教师绑定了目标、学生没有（适配器只在 FOLLOW/AVOID_OBSTACLE 填 id） |
| **速度值**（重叠步） | ±0.5 m/s 命中 **30.4%**；MAE **0.236 m/s** | — | 最大偏差 6.13 m/s；**487 步**教师给了速度而学生不给（适配器只在 SET_SPEED/SLOW_DOWN/FOLLOW 填） |

**读法（重要）**：

- **结构层面几乎无损**：步数、行为语义（掩码前）、车道、目标绑定在"双方都给值"时全部 100% 一致；
- **真正的衰减集中在"显式速度值"**：与 CARLA 闭环里 B02/B03 因 `target_speed_kph` 失败、
  SUP_A14 弯道超速互相印证——速度回归是这版候选最大的单点差距；
- 逐字段比较里出现的"低一致率"必须区分**字段约定差异**（null 约定）与**真实分歧**，本目录的 JSON 把
  两者分开统计（`*_when_both_present` / `*_teacher_only`）。

**场景级对照（不同口径，仅作参考）**：团队技术报告里原始模型（Qwen2.5-VL-7B AWQ）在 83 个自建验收场景为
**83/83**；B3 用同一套 83 场景、把决策位换成轻量化学生模型得到 **60/83（72.3%）**。
两者**条件不同**（不是同一批运行），只能作为"应用性能差距的代理"，**不能直接当作细则定义的衰减幅度**。

## 3. 与挑战赛道三项指标的关系

| 指标 | 本轮补上的证据 | 仍缺 |
|---|---|---|
| FLOPs 压缩比（15 分） | A1 于 10-08 交付分母数据：按固定 Teacher（Qwen3.5-2B，24 层实配、267 prefill token）复算，**比值 0.000558（0.0558%）**，仍处 ≤0.5 的 15 分档；另一口径（同结构 FP32 学生）为 1.0 | 团队选定被认可的原始模型与计数范围（`formal_ratio_pass` 仍为 null） |
| 异构算力利用率（10 分） | **CPU 侧**：闭环实测 planner 进程 16.7%（p95 26.1、max 70.8）、系统 38.2%；**BPU 侧**：工具链单次推理内部计算单元利用率均值 13.8%、峰值 24.3% | 官方公式 + A4 Runtime + 板端计数器 |
| 核心指标衰减（15 分） | 同口径 850 例：行为（未受限）100%、解码后 91.62%、完成条件 89.04%、速度 ±0.5 m/s 命中 30.4%；场景级代理 72.3% vs 83/83 | B2 冻结基准与正式分子分母 |

## 4. 文件

| 文件 | 内容 |
|---|---|
| `01_bpu_performance_estimate_v3.json` | BPU 预估数值、身份绑定、瓶颈判定、区间利用率与全部限制 |
| `02_teacher_student_core_metric_decay.json` | 850 例同口径逐字段一致率/衰减、字段约定差异分类、逐队列明细 |
| `03_flops_ratio_chosen_option.json` | **已选定口径** `fixed_teacher_conv_linear` 的正式测算：分子/分母/比值/档位/交叉核对/限制 |
| `04_same_protocol_scenario_decay.json` | **同口径场景级衰减**：47 个共有场景上教师闭环记录 vs 学生全量运行 |
| `../carla_student_loop_20261007/07_suite_full83_summary.json` | 83 场景闭环全量结果（判定/失败键/行为/时延/安全/舒适性） |

## 5. FLOPs 压缩比：选定第一行并正式测算（2026-10-08）

团队选定 **`fixed_teacher_conv_linear`**（原始模型＝固定 Teacher `Qwen/Qwen3.5-2B`，revision
`15852e8c…`；计数范围＝Conv2D/Linear；固定输入样例＝267 prefill token（含 64 视觉 token）、224×224、batch=1）。

| 项 | 值 |
|---|---|
| 分子（轻量化 Student） | **498,640,896 FLOPs**（与 `challenge/flops_report.json` **逐项一致**，本次测算做了交叉核对） |
| 分母（原始 Teacher） | **892,929,605,632 FLOPs** |
| **压缩比** | **0.0005584324820847111（0.055843%）** |
| 规则档位 | ≤0.5 → **15 分**（条件档位；包内 `formal_ratio_pass` 仍为 `null`） |

口径要点：1 MAC = 2 FLOPs；不含 ASR/NLU、图像预处理、Adapter、安全层与控制器；**INT8 量化不减少 MAC 次数**，
因此不构成额外的 FLOPs 压缩。工具：`challenge/hil/harness/x86_sim/flops_ratio.py`。

## 6. 同口径场景级衰减：47 个共有场景（2026-10-08）

dataset release 的每一行都记录了 `metadata.scenario_config_path`（即验收套件里的场景文件）与
**教师自己的闭环判定**（`closed_loop_quality.scenario_acceptance_passed`）。因此可以构造**同场景文件、
同验收脚本、同判据**的两侧对比：教师侧用采集运行中记录的结果，学生侧用 B3 的 83 场全量运行。

| 项 | 值 |
|---|---|
| 教师侧覆盖场景 / 记录数 | 98 个场景 / 850 次记录 |
| 学生侧 | 83 个场景（每场景 1 次） |
| **共有场景** | **47** |
| 教师 逐记录（micro）通过率 | **311/324 = 96.0%** |
| **教师 macro（每场景通过率均值）** | **92.12%** |
| **学生 macro（每场景 1 次）** | **74.47%**（35/47） |
| **相对衰减 = 1 − 学生/教师** | **19.16%** |

**教师全过、学生未过的 9 个场景**（这是最可直接改进的清单）：
`ACC_A04_static_obstacle_stop`、`ACC_B02_set_speed_20`、`ACC_B06_offset_recovery`、`ACC_C01_heavy_rain_fog`、
`SUP_A06_yellow_to_red`、`SUP_A10_static_vehicle_center`、`SUP_B06_right_offset_recovery`、
`VAR_A01_lead_brake_late`、`VAR_B06_lane_keep_smooth_curve`。

**反向情况（学生过、教师也有失败记录）3 个**：`SUP_A07_pedestrian_right_to_left`（教师 1/2）、
`SUP_A08_fast_pedestrian`（3/5）、`VAR_A04_lane_change_right`（3/4）——说明学生并非在所有场景都更差。

**必须声明的差异**：这套对比是"**同场景文件、同判据、不同时间/机器/seed**"——教师行来自 A800/B1 侧的采集运行
（每场景多条记录），学生行来自本机单次运行（seed 0、FP32 在环）。因此这是**同口径衰减估计**，
仍不是 B2 冻结基准上的正式分子分母。工具：
`challenge/hil/harness/x86_sim/teacher_student_protocol_decay.py`。

复现命令：

```bash
# BPU 预估（官方镜像内，用 A2 校准集编译后读报告）
hb_compile -c <cal_config_v3.yaml> ...   # 产物：student_v0_v3.json / .html / _node_info.csv

# 同口径衰减
py -3.12 -m challenge.hil.harness.x86_sim.teacher_student_decay \
  --onnx <student_v0_fp32_v3.onnx> --work <dumps 根目录> --repo . --out <json>
```
