# B3：HIL 与 J6P 独立实测

> B3 的前置输入、证据等级、正式测试矩阵、门禁和完成定义见
> [`docs/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](../../docs/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md)。

本目录是 B3 在挑战赛道的交付物：测量工具链、测量口径、跨组接口契约，以及一次
X86 预验证的策展证据。

B3 只**测量** A4 交付的板端 Runtime，不修改它，也不维护第二套部署实现。
挑战赛道只替换 Planner 链（`ModelRequest V1 → Student Planner → ManeuverPlan V2`），
既有 A/B/C/D 与 SafetySupervisor 保持原样。

## 1. 边界

允许：定义口径、调用 A1/A3/A4 的**同一个**入口来测量、采集进程与板端遥测、产出原始日志。

不做：

- 不修改 A/B/C/D、SafetySupervisor 或任何 A 组代码，本目录只 `import`；
- 不复制一份前处理/推理逻辑来"测量"——那测的就不是被测对象；
- 不把 X86 或桌面 GPU 数据写成 J6P 结果；
- 不把模型文件大小当运行内存，不用估算值填充功耗与 BPU 利用率。

## 2. 目录结构

```text
challenge/hil/
├── README.md                     本文件（含阻塞项与未完成任务）
├── latency_schema.md             计时点与统计口径（D1 交付）
├── hardware_metrics_schema.md    硬件指标与 CSV 列定义（D1 交付）
├── a4_runtime_contract.md        A4 Runtime 接口需求书（打点 + CLI + 模型级测量）
├── a4_runtime_gap_report.md      A4 当前交付与该契约的差距清单（含复现证据）
├── repo_environment_findings.md  验证过程中发现的仓库环境问题（F1–F6，含绕行方式）
├── hard_cases_handoff.md         B3 → A3 失败样本交接格式
├── MERGE_INTO_REPO.md            入库过程记录（历史文件）
├── requirements.txt              依赖清单
├── stages.py                     挑战链阶段定义、单调性校验、百分位统计
├── columns.py                    全部 CSV/JSONL 的列定义（schema 单一真源）
├── identity.py                   五标识与 SHA256 工具
├── provenance.py                 Teacher 基线 pin（v1/v4 双 pin + tag 交叉校验）
├── run_io.py                     run 目录、原子写、逐文件 SHA256 清单
├── samplers.py                   内存/利用率/功耗采样（缺失时显式 NOT_APPLICABLE）
├── runtime_adapter.py            被测入口抽象 + 进程内/ONNX/板端 CLI 三种实现
├── replay.py                     冻结请求集回放与输入输出一致性检查
├── rounds.py                     同配置多轮调度与合并统计
├── consistency.py                torch↔ONNX（未来 INT8）逐输出等价性比对
├── contract.py                   A4 Runtime 契约的可执行检查
├── artifact.py                   模型产物独立校验（opset/算子/契约/SHA）
├── freeze.py                     冻结回放快照（自包含、内容寻址）
├── stability.py                  长稳 soak + 内存漂移 + recovery probe
├── failure_cases.py              异常输入用例与归档
├── handoff.py                    B3 → A3 失败样本导出
├── report.py                     报告生成与可信范围守卫
├── cli.py                        命令行入口（9 个子命令）
├── frozen/
│   ├── smoke_v0_snapshot/        早期冻结输入基线（B1 smoke，30 例）
│   └── d2_v1_1_val/              当前输入基线（B1 D2 v1.1 的 val 划分，539 例）
├── evidence/
│   ├── x86_prevalidation_20260918/  Planner 链的 X86 预验证证据
│   ├── carla_smoke_20260918/        CARLA 闭环可行性冒烟（无 Student/Teacher）
│   ├── carla_qwen_deterministic_20260918/  CARLA 闭环经 Qwen 契约层（确定性后端）
│   └── carla_chain_coverage_20260918/      CARLA 链路覆盖 / 多轮 / 稳定性（37 次运行）
├── schemas/                      导出的列定义
└── tests/                        71 项自测
```

### 2.1 文档地图

| 文档 | 作用 | 什么场景看 |
|---|---|---|
| `README.md` | 入口：边界、逐条完成情况、阻塞项、证据索引 | 先看这份 |
| `latency_schema.md` | 8 个计时点、统计口径、A4 打点契约（D1 交付） | 想知道某个数字怎么量出来的 |
| `hardware_metrics_schema.md` | 硬件指标、四类 CSV 列定义、运行环境指纹字段 | 要写采集代码或核对字段 |
| `a4_runtime_contract.md` | A4 Runtime 接口需求书：CLI、打点、身份查询、模型级模式 | A4 实现板端 Runtime 前 |
| `a4_runtime_gap_report.md` | A4 当前交付与该契约的差距，含 13.8 ms 不可复现的复现证据 | 与 A4 对账时 |
| `hard_cases_handoff.md` | B3 → A3 失败样本交接格式与使用规则 | A3 接入补训数据前 |
| `repo_environment_findings.md` | 验证中发现的仓库环境问题 F1–F6 与绕行方式 | 在新机器上复现环境时 |
| `MERGE_INTO_REPO.md` | 入库过程记录（历史文件，不代表当前状态） | 追溯产物来源时 |
| `evidence/*/README.md` | 四份策展证据各自的说明与限制 | 引用具体数字前 |

## 3. 快速开始

```powershell
# 自测（不需要模型产物）
py -3.12 -m challenge.hil.cli selftest
py -3.12 -m pytest -q challenge/hil/tests

# 用当前冻结输入跑一次 X86 预验证（3 轮 + 两项一致性 + A3 交接）
py -3.12 -m challenge.hil.cli run `
  --repo . --adapter both --rounds 3 --limit 100 `
  --frozen challenge/hil/frozen/d2_v1_1_val `
  --out  artifacts/b3_runs `
  --verify-consistency --verify-backend-consistency
```

## 4. 当前需要的文件（阻塞项）

以下输入仍须由对应负责人提供。在此之前，本目录只能产出 `X86 PRE-VALIDATED`
级别的工具链验证结果，不能产出任何达标结论。

| 需要的文件 | 提供方 | 拿到后立刻能做什么 |
|---|---|---|
| 真实 FP32 权重 + `weights_manifest.json`（五标识 + `A3_FP32_GATE_PASSED`） | A3 | 第一次有意义的回放：行为/目标对比、`handoff` 开始产出 `usable_for_training=true` 的样本 |
| 符合契约的 Runtime 入口（stdin `ModelRequest` → stdout `ManeuverPlan V2` + 打点） | A4 | 用 A4 的真实入口替换 B3 的自建适配器；缺口见 `a4_runtime_gap_report.md`，完整门禁见 [`A4_OPENEXPLORER_J6P_RUNTIME.md`](../../docs/modules/A4_OPENEXPLORER_J6P_RUNTIME.md) |
| 板端 `.bin` 产物 + 启动脚本 + `contract_report.json` | A4 | 板端全部测量。契约检查已就绪，A4 可先自检 |
| INT8 量化产物 + 校准配置与校准集说明 | A2 | 按 [`A2_INT8_QUANTIZATION_AND_QAT.md`](../../docs/modules/A2_INT8_QUANTIZATION_AND_QAT.md) 核对身份后，用 `consistency --baseline-onnx` 跑 INT8 vs FP32 逐输出偏差，再做量化后性能对照 |
| 冻结 Benchmark case 清单 + 判定策略（**含"异构算力利用率"公式**） | B2 | Seen/Variant/Unseen 正式结论；公式到位后 `hardware_metrics_schema.md` 第 3 节可定稿 |
| J6P 板卡 + 功耗探针（板端 INA 或外部功率计）取数方式 | 硬件/团队 | `power_raw.csv` 与 `utilization_raw.csv` 才能有真实数字 |

### 4.1 已解除的阻塞

| 曾经需要 | 现状 |
|---|---|
| 可重复的开发回放请求集 | **已交付**：`challenge/dataset/releases/d2_v1_1/`（train 2513 / val 539 / reserved candidates 540）。B3 已把开发 Val 冻结为 `frozen/d2_v1_1_val`（539 例，digest `003f0ed8e279…`）；这不是 B2 Frozen Test |
| A4 X86 运行时 | **部分交付**：`challenge/runtime/student_x86.py` 可运行，但不满足测量契约（无请求入口、无打点、无身份查询）；差距清单见 `a4_runtime_gap_report.md` |
| Teacher 基线 pin | **已就绪**：v1 与 v4 双 pin 自动记录，模型身份一致（`Qwen/Qwen3.5-2B` @ `15852e8c1636`） |
| A1 结构产物 | **已在仓库**：`challenge/student_v0_fp32.onnx`（`ffb1ed5e…`），B3 独立校验通过 |

仍待团队决策：**`main_optimization` 上那批基础链 S2 修复是否会同步到本分支**。
若会，闭环部分需重新 baseline，并在 provenance 中记录新的链版本。

## 5. 对照 B3 要求的完成情况

本节逐条对照团队文档中 B3 的要求，显式标注**已完成 / 部分完成 / 未完成**。
状态口径：`已完成` = 机制已实现并有可核验产出；`部分完成` = 机制就绪但缺少板端或
真实模型等前置条件；`未完成` = 尚未开始或前置条件完全缺失。

### 5.1 职责（文档「负责内容」10 条）

| # | 文档要求 | 状态 | 依据 |
|---:|---|---|---|
| 1 | 建 HIL/回放输入输出链 | **已完成** | `replay.py` + 三种适配器（进程内 / ONNX / 板端 CLI）+ `freeze.py` 快照；已在 539 例 D2 val 快照上跑通 300 次回放。另用仓库自研 runner 跑通一个 CARLA 闭环冒烟（`SUCCEEDED`，600 帧，A/B/C/D 全链被调用，见 `evidence/carla_smoke_20260918/`） |
| 2 | 记录时间戳 | **已完成** | `stages.py` 8 个计时点，强制单调与顺序；`perf_counter_ns` + UTC 双时钟 |
| 3 | 记录板端硬件/软件环境 | **部分完成** | 每次运行已记录电源、系统负载、CPU 标定、库版本、时钟源；**BPU 架构 / OpenExplorer 版本 / governor / 散热待 J6P** |
| 4 | 测 P50/P95/P99/max | **已完成** | 线性插值百分位（与 `metrics/reference_5070` 口径一致），报告输出全部四个分位 |
| 5 | 测运行内存 | **已完成** | RSS / 峰值 RSS；psutil 与 Win32 两条路径均实现并有测试 |
| 6 | 测平均/峰值功耗 | **未完成** | 列定义、采样器与取电点字段已就绪，但本机无探针，当前行内容为 `NOT_APPLICABLE`（未用估算值填充） |
| 7 | 测 CPU/BPU 利用率与异构调度 | **部分完成** | CPU 已实测；**BPU 待 J6P**；"异构算力利用率"公式待 A4/B2 确认 |
| 8 | 运行 Seen/Variant/Unseen | **未完成** | 依赖 B2 冻结的 case 清单与 A3 权重。链路侧已跑 13 个场景（smoke + `safety_D`），但**不是 B2 冻结的三类分组，也没有 Student 在环** |
| 9 | 做异常和长时间稳定性测试 | **部分完成** | 异常：软件用例 10 例 + **CARLA 8 个安全场景全部通过**（红灯、行人、前车急刹、偏离、NaN 控制、油门刹车冲突、低 TTC、红灯冲突）。长稳：X86 15 秒冒烟 + **CARLA 连续 7.1 分钟 15 轮无失败**；**正式 30 分钟板端长稳待 J6P** |
| 10 | 同配置至少重复 3 轮 | **部分完成** | X86：3 轮 × 100 例。CARLA：**5 个 smoke 场景各 3 轮 + 3 个代表场景各 3 轮，结果一致**；**交付配置（J6P）上的 ≥3 轮待硬件** |

### 5.2 计时拆分（文档「计时必须拆分」）

| 文档要求的时段 | 状态 | 实现 |
|---|---|---|
| 输入到达 | **已完成** | `input_arrival`（T0） |
| 预处理 | **已完成** | `preprocess_end`（T1） |
| Token/Target packing | **已完成** | `packing_end`（T2） |
| BPU inference | **部分完成** | 计时点已实现（`inference_start`/`inference_end`，T3/T4）；**当前在 X86 上测的是 ONNX Runtime CPU 前向，BPU 实测待 J6P** |
| 后处理 | **已完成** | `postprocess_end`（T5） |
| Student Adapter | **已完成** | `adapter_end`（T6） |
| ManeuverPlan 输出 | **已完成** | `plan_ready`（T7，含 `PlanValidator`，单列校验开销） |
| 同时报告模型纯推理与完整 Planner 端到端 | **已完成** | `model_only_ms` 与 `planner_e2e_ms` 同时输出，并给出差值 `planner_overhead_ms` |

### 5.3 必须交付物（文档「必须交付」9 项）

| 交付物 | 状态 | 位置 / 说明 |
|---|---|---|
| `hil_replay.*` | **已完成** | `hil_replay.jsonl`、`hil_replay_summary.json`、`hil_replay_plans.jsonl` |
| `hardware_env.json` | **已完成** | 每次运行生成，含环境指纹、五标识与 v1/v4 双 Teacher pin |
| `latency_raw.csv` | **已完成** | 每请求一行，8 个纳秒戳与全部推导时段，逐行带五标识 |
| `memory_raw.csv` | **已完成** | RSS 与峰值 RSS（进程级） |
| `power_raw.csv` | **部分完成** | 列定义与写入已实现；**当前行内容为 `NOT_APPLICABLE`**（无探针） |
| `utilization_raw.csv` | **部分完成** | CPU 已实测；**BPU 字段待 J6P** |
| `stability_logs/` | **部分完成** | `soak.jsonl`、`soak_summary.json`、`memory_during_soak.csv` 均已产出；但仅 15 秒冒烟 |
| `j6p_test_report.md` | **未完成** | X86 运行生成的是 `x86_test_report.md`；`j6p_test_report.md` 仅在 `--device-class J6P_BOARD` 运行时生成，尚未产生 |
| `failure_cases/` | **已完成** | 10 个用例逐个落盘 + `failure_summary.json` |

### 5.4 完成标准（文档「完成标准」5 条）

文档给出的五条"完成标准"是对 **B3 最终交付物**（A4 板端 Runtime 在 CARLA/HIL/J6P
上的实测）的验收条件，其被测对象尚未交付，**因此五条现在一条都未达成**。

必须区分"完成标准是否达成"与"工具链是否就绪"这两件事——后者是前者的必要条件，
不是达成本身：

| 完成标准 | 是否达成 | 工具链就绪情况 |
|---|---|---|
| 三类场景完成板端/HIL 验证 | 未达成 | 回放链与场景标签框架已就绪；缺被测对象与 B2 冻结的 case |
| 同配置重复 ≥3 轮 | 未达成 | 多轮调度与合并统计已实现，但**未在交付配置上执行过**；X86 上的 3 轮只是机制演练 |
| 原始日志完整 | 未达成 | 原始 CSV/JSONL 与逐文件 SHA256 清单已实现；正式运行的日志尚不存在 |
| 明确测量起止 | 未达成 | 双时钟打点与 phase 划分已实现；正式运行的记录尚不存在 |
| 无 J6P 时只能标 `X86 PRE-VALIDATED` | 未达成 | 由报告生成器的 claim scope 守卫强制，人工无法绕过；但该声明只能在交付时作出 |

**当前可以声明的只有一句**：与上述五条对应的**机制**已实现，并在一次 X86 预验证中
演练过（见第 6 节）。这不等于完成标准达成，也不构成任何达标结论。

### 5.5 仍需外部输入

对应第 4 节表格里的六项（A3 权重、A4 契约入口、A4 板端产物、A2 INT8、
B2 Benchmark、J6P 硬件）。其中 A3 权重与 A4 契约入口是两条主线的起点。

## 6. 已验证结论（X86 预验证）

全部数字限定在"工具链正确性"范围内，**不构成性能或精度达标结论**。
以下数字取自 `evidence/x86_prevalidation_20260918`，输入为 B1 D2 v1.1 val 的前 100 例，
产物为 `ffb1ed5e…`。

| 结论 | 证据 |
|---|---|
| torch 结构与 ONNX 产物逐输出等价 | `consistency_report.json`：10 个输出张量最大绝对差 7.6e-06 |
| 打点路径与生产入口 `StudentBackend.infer` 输出一致 | `backend_consistency.json` = `PASS` |
| 模型产物结构合法 | `artifact_report.json`：opset 17、无动态 shape/控制流算子、输入输出契约一致 |
| 输入快照可复现且防篡改 | `frozen/d2_v1_1_val/manifest.json`：539 例、set digest `003f0ed8e279…` |
| 长稳链路可用 | `soak_summary.json`：15 s / 899 次请求、成功率 100%、内存漂移 626 KiB |
| 异常输入不崩溃且可归档 | `failure_cases/`：10 例，**10 例全部符合预期** |

基线数字（100 例 × 3 轮，in-process torch 链，AC 供电、系统负载 5.8%、
`cpu_calibration_ms = 11.84`，单位 ms）：

| 时段 | P50 | P95 |
|---|---:|---:|
| 预处理 | 7.88 | 18.99 |
| Token/Target packing | 0.52 | 1.80 |
| 模型纯推理 | 8.10 | 12.89 |
| 后处理 + Adapter | 0.56 | 1.10 |
| 计划校验 | 0.84 | 1.94 |
| **完整 Planner E2E** | **18.25** | **35.43** |

独立 ONNX 模型压测（CPU EP，batch=1，warmup=5）：P50 2.96 ms。

### 限制（必读）

1. 权重是**随机初始化**的（`torch.manual_seed=20260911`），所有行为对比只验证工具链。
2. 功耗与 BPU 利用率是 `NOT_APPLICABLE`（本机无探针）。
3. 长稳只跑了 15 秒冒烟，正式要求 30 分钟。
4. 全部结果标记 `X86 PRE-VALIDATED` / `J6P PENDING`。
5. 延迟对机器状态高度敏感。同一台机器、同一份代码，B3 观察到过 ONNX 推理 P50
   为 2.7 / 27 / 92 ms 三种状态。每次运行都会记录 `power_source`、
   `background_load_cpu_percent`、`cpu_calibration_ms` 与
   `runtime_libraries`；**跨运行比较前先比标定值**，并注意本批是 300 次请求的
   持续负载（09-16 那批仅 30 次，E2E P50 为 13.26 ms）。

## 7. 环境

B3 的所有测量由 **`py -3.12`** 执行（对应 `challenge/requirements.txt`）。

| 包 | 本机 py3.12 | 仓库声明 |
|---|---|---|
| torch | 2.6.0+cpu | `>=2.6,<2.7` ✓ 已对齐 |
| onnx | 1.22.0 | `>=1.17,<2` |
| onnxruntime | 1.27.0 | `>=1.20,<2` |
| numpy | 2.4.6 | `>=2,<3` |
| jsonschema | 4.26.0 | `>=4.20` |

torch 已从 2.13.0 换到声明要求的 2.6.0。切换前先在独立 venv 中验证过：两个版本
与 A1 导出产物的逐输出最大绝对差完全相同（`7.62939453125e-06`），即权重初始化的
随机流跨版本稳定，切换不会破坏既有对齐。切换后全量测试与一致性检查均通过。

## 8. 命令一览

| 命令 | 用途 |
|---|---|
| `selftest` | 无依赖的内部一致性检查 |
| `schema` | 导出列定义到 `schemas/` |
| `run` | 执行一次测量（多轮 + 回放 + 异常用例 + 一致性 + 交接） |
| `soak` | 长稳 + 内存漂移 + recovery probe |
| `contract` | 检查 Runtime 是否符合 A4 接口契约 |
| `artifact` | 独立校验 ONNX 产物（FP32/INT8 通用） |
| `freeze` | 冻结请求集为自包含快照 |
| `consistency` | 两个图之间的逐输出等价性比对 |
| `handoff` | 导出失败样本给 A3 |

## 9. 证据位置

两份策展证据在 `challenge/hil/evidence/` 下：

| 目录 | 内容 |
|---|---|
| `x86_prevalidation_20260918/` | Planner 链的 X86 预验证：原始 CSV、汇总 JSON、报告与逐文件 SHA256 清单 |
| `carla_smoke_20260918/` | CARLA 闭环可行性冒烟：`S01_set_speed_20` 的 summary 与说明（无 Student/Teacher） |
| `carla_qwen_deterministic_20260918/` | CARLA 闭环经 Qwen 契约层：走通 `planner_v2`、计划执行与 fail-closed（后端为确定性规则，非模型） |
| `carla_chain_coverage_20260918/` | CARLA 链路覆盖：13 场景逐次 + 同配置各 3 轮 + 连续 7.1 分钟稳定性窗口，共 37 次运行全部成功（无 Student、无 Qwen） |

完整运行历史（含被取代与作废的运行）保留在仓库外的 B3 工作区，未入库。
逐帧原始日志体积大，留在 `artifacts/logs/`（被 gitignore 覆盖）。

B3 的全部产物都在 `challenge/hil/` 一个目录内，不向 `metrics/` 等目录分散写入。

### 报告文件命名

`x86_test_report.md` 与 `j6p_test_report.md` 由运行环境自动决定：当
`--device-class X86_WORKSTATION`（默认）时生成前者，`J6P_BOARD` 时生成后者
（即文档要求的最终交付名）。这样 X86 预验证报告不会与 J6P 实机报告同名混淆。
