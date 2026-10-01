# B3 与《挑战赛道后续统一执行方案》（2026-09-30）的对接

> 方案把 B3 收窄为：**只对 Final FP32 / Final INT8 / Final A4 Runtime 做正式复测，不维护第二套推理链**。
> 本文件逐条说明 B3 的交付物如何对应新要求，哪些能力已经就绪，哪些仍在等输入。

## 1. 产物对照（方案 §12「B3 输出」）

| 方案要求 | B3 现状 | 位置 |
|---|---|---|
| `hardware_env.json` | 已有 | 每次 `run` / `soak` 产出 |
| `latency_raw.csv` | 已有 | `run` |
| `memory_raw.csv` | 已有 | `run` / `soak` |
| **`cpu_utilization_raw.csv`** | **已对齐**：新增列定义别名，与旧名 `utilization_raw.csv` 共用同一 schema | `columns.py` |
| `stability_logs/` | 已有（流式 `soak.jsonl` + 摘要 + 1 Hz 内存遥测） | `stability.py` |
| `contract_report.json` | 已有（契约子命令 + `run` 预检） | `contract.py` |
| **`bpu_estimate_verification.json`** | **已实现**（新子命令 `bpu-verify`） | `bpu_estimate.py` |
| `measurement_manifest.json` | 已有（逐文件 SHA256） | `run_io.py` |
| **`performance_report.md`** | **已改名**（原 `x86_test_report.md`；旧名保留为常量别名） | `report.py` |
| 有板端时追加 `bpu_utilization_raw.csv` / `power_raw.csv` / `j6p_latency_raw.csv` | `power_raw.csv` 已有（无探针时 `NOT_APPLICABLE`）；另两项等板卡 | `samplers.py` |

## 2. 三类口径必须分开（方案 §12 统一要求、§17 禁止项）

新增 `claim_scope.py`，把每个对外数字归入且只归入三类之一，并 fail-closed：

| 口径 | 含义 | 发布前提（缺一即失败） |
|---|---|---|
| `X86_MEASURED` | 工作站实测 | 必须带原始产物引用（`latency_raw.csv` 等） |
| `BPU_ESTIMATED` | 地平线工具链**预估** | 必须带工具、工具版本、估算方法、模型摘要 |
| `J6P_MEASURED` | J6P 板卡实测 | 必须带设备身份 + 板端原始日志 |

显式拒绝：`estimated=true` 却声明成 `J6P_MEASURED`（预估冒充实测）、未知来源标签、
缺少依据的预估、缺板端证据的板卡结论。`performance_report.md` 头部固定输出三分类表，
写明"本报告不含 J6P 实测；预估需另附 `bpu_estimate_verification.json`，未核验前不得引用"。

## 3. BPU 预估核验（方案 §12 B、§9 任务 2/3）

```bash
py -3.12 -m challenge.hil.cli bpu-verify \
  --a4-dir artifacts/a4/<runtime_id>/ \
  --out   artifacts/b3/<run>/bpu_estimate_verification.json
```

核验项（B3 定义的接收契约，对应 A4 方案 §9 的目录）：

1. **文件齐备**：`runtime_manifest.json`、`source_int8_manifest.json`、`conversion_config.yaml`、
   `compile_command.txt`、`compile.log`、`operator_mapping.json`、`fallback_report.json`、
   `bpu_performance_estimate.json`、`estimation_method.md`、`runtime_command.txt`、
   `contract_report.json`、`SHA256SUMS`（可选：`openexplorer_env.json`、`consistency_report.json`、
   `runtime_profile_x86.json`）。
2. **SHA256SUMS 逐项校验**，并列出未被清单覆盖的文件。
3. **算子映射 ↔ fallback 一致性**：计算 BPU 占比与落在 BPU 之外的节点；fallback 报告里
   出现"映射其实放在 BPU"的节点即判失败（phantom）。
4. **预估元数据完整**：工具、工具版本、OpenExplorer 版本、模型摘要、输入 shape、batch、量化方式、
   估算方法、假设列表。
5. **身份绑定**：`estimate.model_sha256` 必须能在 INT8 manifest 的摘要里找到，防止"预估的是别的模型"。
6. **`estimation_method.md`** 必须说明工具与版本（与预估里声明的字符串一致）且有实质内容。
7. **口径**：所有发布数字必须标 `BPU_ESTIMATED`（复用 §2 的校验器）。

PASS 的含义是"**可归因、自洽、口径正确**"，**不是**"BPU 性能达标"；它仍只是预估，永远不等于 J6P 实测。

## 4. 旧 candidate 诊断的冻结（方案 §12「停止继续对旧 candidate 做大量替代条件实验」）

自 2026-10-02 起：

- `evidence/x86_simulation_20260924/`、`evidence/d3_targeted_gap_20260926/`、`evidence/d3_turn_gap_20260927/`、
  `evidence/a3_fp32_candidate_v3_20260926/` 里**关于旧 candidate 的结论只作历史诊断**，不再扩展或复跑；
- `evidence/a3_final_fp32_v1_20261002/` 针对**当前** final FP32 候选，可随新候选更新；
- ⚠️ 只读约束：A3 的 `challenge/distillation/audit_b3_v3_diagnostic.py` 仍以
  `evidence/a3_fp32_candidate_v3_20260926/` 为默认输入，**该目录按只读保留**，要改必须先通知 A3
  （B3 已加回归测试守住格式）。

## 5. 48 小时清单（方案 §18 的 B3 六项）

| 方案要求 | 状态 |
|---|---|
| 暂停旧 candidate 重复诊断 | ✅ 见 §4 的冻结声明 |
| 准备接 Final FP32 / INT8 / A4 Runtime | ⏳ **Final FP32 已接**（包校验 + 三个队列复测）；INT8 与 A4 Runtime 等交付 |
| 核对 CPU/X86 正式 measurement schema | ✅ `performance_report.md` 改名、`cpu_utilization_raw.csv` 别名、报告三分类表 |
| 确认 X86 实测入口 | ✅ `cli run --adapter inprocess|onnx`（A4 的 `--adapter board` 等 `runtime_command`） |
| 增加 BPU 预估结果核验项 | ✅ `bpu-verify` 已实现并有 14 项测试（等 A4 的包） |
| 明确"实测/预估/实板"三种 claim scope | ✅ `claim_scope.py` + 报告表 + fail-closed 测试 |

## 6. 仍只能等外部输入的

| 输入 | 谁 | 到位后立刻能做 |
|---|---|---|
| B2 冻结 Independent Validation / Frozen Benchmark / policy manifest | B2 | Seen/Variant/Unseen 正式分组与精度 Gate |
| `A3_FP32_GATE_PASSED` | A3←B2 | 回放从 `DIAGNOSTIC_ONLY` 晋级、`handoff` 产出可训练样本 |
| 正式 INT8（`A2_INT8_GATE_PASSED` + manifest + 量化配置） | A2 | INT8 侧正式复测与敏感性结论 |
| `artifacts/a4/<runtime_id>/`（Runtime + 映射 + fallback + 预估） | A4 | 契约真检、`bpu-verify`、X86 全链实测 |
| J6P 板卡 + 功耗探针 | 硬件 | 三类口径里的 `J6P_MEASURED` 那一列 |
