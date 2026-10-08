# V3.1 契约下的 FP32 / INT8 全链路实测与同口径衰减（B3，2026-10-08）

> 口径：`X86_MEASURED`（官方机上的 X86 闭环与数值诊断）；**无板卡**；
> 权重门禁仍 `PENDING_A3_FP32_GATE`；场景为**自建 83 场验收矩阵**（非官方 1000 帧基准）。

## 0. 这一轮测的是什么

上游同日推进了两件事：**A2 落地 V3.1 语义契约**（adapter SHA `bb30726b…`，本机仓库已同步）、
**A2 交付 V3 的 FP32/INT8 产物**（FP32 `681a5d4b…`、Full INT8 `275dce5c…`、Mixed Top-3 `9a08a03c…`，
三者均由 B3 逐字节核验与 A2 公布值一致）。B3 因此可以做两件此前做不了的事：

1. **同一套 83 场景**分别用 FP32 与 Full INT8 在环各跑一轮，比较**判定**；
2. 在**同一评测口径**下给出 Teacher → Student(FP32) → Student(INT8) 的**核心指标衰减**。

## 1. 83 场全链路：FP32 与 INT8 结果完全相同

| 分组（官方 matrix 口径） | FP32 通过 | INT8 通过 | 完成率 |
|---|---:|---:|---:|
| basic_scoring | 12/18 | 12/18 | 66.7% |
| advanced_scoring | 23/30 | 23/30 | 76.7% |
| challenge_scoring | 18/24 | 18/24 | 75.0% |
| complex_regression | 5/6 | 5/6 | 83.3% |
| system_stability | **5/5** | **5/5** | **100%** |
| **合计** | **63/83** | **63/83** | **75.9%** |
| **加权（30/40/30）** | **0.7317** | **0.7317** | **10.97 / 15** |

**FP32 与 INT8 逐场判定完全一致（83/83，0 处差异）**（见 `03_fp32_vs_int8_verdicts.json`）。
即：**量化不改变闭环判定**——与数值层"行为 argmax 932/932 一致"互相印证。

闭环时延（逐帧池化，两轮同量级）：`sensor→control` 约 P50 31 ms / P95 47 ms；
决策服务延迟 FP32 **P50 3.34 ms**、INT8 **P50 2.18 ms**（CPU/ONNX Runtime）。

## 2. INT8 数值与计划对照（850 例 / 932 步）

| 口径 | Full INT8 | Mixed Top-3 |
|---|---|---|
| 行为（离散决策）一致率 | **100%（932/932）** | 100% |
| 计划完全相同（速度 3 位小数） | 56.6%（481/850） | 56.6% |
| 计划相同（速度容差 0.05 m/s） | **67.5%**（574/850） | 67.5% |
| 逐头最大绝对偏差 | `target_speed_mps` **1.63** ＞ replan 0.72 ＞ confirmation 0.65 ＞ pointer 0.52 … ＞ confidence 0.01 | 同左 |

→ 量化误差**几乎全部落在速度头**；离散行为一步未变。Mixed Top-3 与本批 Full INT8 结果相同
（A2 亦记录"Mixed 改善离散头、不改善速度头"）。

## 3. 同口径 Teacher / Student 衰减（三层）

**协议**：同一批冻结用例、同一比对器；教师侧为队列内固化的 Teacher 计划（场景级另按
release 记录的同场景闭环判定），学生侧用**同一个 V3.1 adapter** 解码对应 ONNX。

| 层级 | 分母（原始 Teacher） | 分子（轻量化 Student） | 相对衰减 |
|---|---|---|---|
| **场景级**（47 个共有场景，同一场景文件 + 同一验收脚本） | macro **92.12%**（micro 96.0%，324 次记录） | macro **78.72%**（37/47） | **14.54%** |
| **用例级**（850 例，FP32/V3.1） | 行为 100%（参照自身） | 行为 **99.57%**、车道 **99.79%**、完成条件 **99.79%**、目标 id（双方给值）100%、速度 MAE **0.226 m/s**（±0.5 m/s 命中 22.4%） | 见分项 |
| **用例级**（850 例，Full INT8） | 同上 | 行为 99.57%、车道 99.79%、完成 99.79%（与 FP32 **完全相同**）；速度 MAE 0.242、最差 6.62 | 量化增量 ≈ 0 |

**分解**：`D_total ≈ D_distill + D_quant`，实测 **`D_quant ≈ 0`**（判定与三个离散字段零差异，
仅速度略差 0.016 m/s）→ **衰减主要来自蒸馏段，且集中在速度回归**。

## 4. 与上一版（旧 adapter）的对照：V3.1 契约的实际收益

| 指标 | 旧 adapter | **V3.1** |
|---|---:|---:|
| 83 场通过 | 60/83 | **63/83** |
| 加权完成率 → 15 分制 | 0.7058 → 10.59 | **0.7317 → 10.97** |
| 用例级行为一致率 | 91.62% | **99.57%** |
| 用例级车道一致率 | 19.33%（字段约定差异 751 步） | **99.79%**（`lane_teacher_only` **0**） |
| 用例级完成条件一致率 | 89.04% | **99.79%** |
| 目标 id（教师有学生无） | 50 步 | **24 步** |
| 场景级相对衰减 | 19.16% | **14.54%** |
| 教师全过而学生未过 | 9 场 | **7 场**（A04、B02、B06、SUP_A06、SUP_A10、SUP_B06、VAR_B06） |

**修复的 3 场**：`ACC_C01_heavy_rain_fog`、`CX05_sensor_dropout_route_recovery`、
`VAR_A01_lead_brake_late`；**无回归**。

## 5. 测量纪律记录（必须随材料一并声明）

1. **合盖冻结**：FP32 轮中 `CX_MAIN_01` 的运行含 **745.1 s 的相邻帧墙钟空档**（笔记本合盖被冻结），
   该次运行的**时延数据作废**；B3 已扫描全部逐帧日志确认**仅此一场受影响**，并**单独干净重跑**，
   结果与失败键**完全一致**（说明该失败是真实的调度问题：7 条命令只有 1 条派发到决策服务）。
   该机的"合盖动作"现已设为 **不采取任何操作**（AC/DC）。
2. **资源采样器缺陷（已修）**：早前版本在 `py -3.12 -m tool` 的父子进程同命中时误剔了真实工作进程，
   导致**服务侧 CPU 被低估**；现已改为按 RSS 保留工作进程。**83 场轮次中的服务侧 CPU 不得引用**，
   规划进程 CPU 有效（均值 16.7%、P95 26.1%、max 70.8%，另一轮 38.6%/59.4%/100.1%）。

## 6. 文件

| 文件 | 内容 |
|---|---|
| `01_suite_full83_fp32_v31.json` | FP32 轮 83 场：分组、加权、安全计数、时延、舒适性、失败清单 |
| `02_suite_full83_int8.json` | INT8 轮同结构结果 |
| `03_fp32_vs_int8_verdicts.json` | 两轮逐场判定对照（83/83 一致，0 差异） |
| `04_int8_numeric_and_plan_check.json` | 850 例 FP32↔Full INT8 / Mixed 数值与计划对照、逐头偏差 |
| `05_teacher_student_decay_v31.json` | 同口径衰减：用例级（FP32/INT8）+ 场景级（47 场景） |
| `06_measurement_notes.json` | 合盖冻结与重跑、采样器缺陷、逐帧冻结扫描结果 |

## 7. 复现

```bash
# 1) 身份核验（三份 ONNX 的 SHA256 应与 A2 公布值一致）
sha256sum student_v0_fp32_candidate.onnx student_int8.onnx student_int8_mixed_top3.onnx

# 2) FP32 / INT8 数值与计划对照（6 队列 850 例）
py -3.12 -m challenge.hil.harness.x86_sim.int8_quantization_check \
  --fp32 <fp32.onnx> --int8 full=<int8.onnx> --int8 mixed=<mixed.onnx> --work <dumps> --out <json>

# 3) 83 场闭环（把服务 --onnx 换成目标产物后）
py -3.12 -m challenge.hil.carla.run_student_loop_suite --repo . --service-url http://127.0.0.1:8100 \
  --out <suite.json> --run-root <dir> --groups "basic,advanced,challenge,complex,variants,supplemental/basic,supplemental/advanced,supplemental/challenge,supplemental/system"

# 4) 同口径衰减
py -3.12 -m challenge.hil.harness.x86_sim.teacher_student_decay --onnx <model.onnx> --work <dumps> --out <json>
py -3.12 -m challenge.hil.harness.x86_sim.teacher_student_protocol_decay --suite <suite.json> --out <json>
```

## 8. 限制

自建 83 场景（非官方 1000 帧基准）；单 seed；35 s/场景实时仿真；完成率包含确定性安全层；
FP32/INT8 均为 X86/CPU 在环（INT8 在 BPU 上的真实收益见 `deployment_estimate_and_decay_20261008/01_*`，
属 `BPU_ESTIMATED`）；教师侧数据来自采集运行（跨机器注脚保留）；无板卡、无 A4 正式 Runtime。
