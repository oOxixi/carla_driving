# B3 延迟计时点与统计口径（D1 交付）

> 本口径在完整 B3 独立实测流程中的使用方式见
> [`docs/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](../../docs/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md)。

> 状态：口径冻结候选。数值仅在 A4 Runtime 按本文件打点后才有意义。
> 本文件定义"怎么量"，不定义"量到多少算过"（那是 B2 的 Gate 判据）。

## 1. 适用范围

覆盖挑战赛道替换后的 Planner 链：

```text
ModelRequest V1
      ↓
Student Planner（预处理 / packing / 推理 / 后处理 / Adapter / Validator）
      ↓
ManeuverPlan V2
      ↓
既有 A/B/C/D（不在本计时范围内，由 B2 的闭环指标覆盖）
```

基础赛道语音链的 `runtime/latency_trace.py::STAGES` 保持不变，B3 不修改它。
本文件定义的是挑战链的独立阶段表。

## 2. 计时点（时间戳标记）

所有时间戳为**同一次请求内**的单调时钟纳秒值，严格递增。

| ID | 名称 | 含义 | 代码锚点（建议） |
|---|---|---|---|
| T0 | `input_arrival` | Runtime 收到完整 `ModelRequest` 的时刻 | 运行入口校验通过后立即 |
| T1 | `preprocess_end` | RGB 解码 / letterbox / 缩放 / 归一化完成 | `StudentPreprocessor._rgb` 返回后 |
| T2 | `packing_end` | 文本编码、目标组装、状态向量组装完成 | `_text/_targets/_state` 全部返回后 |
| T3 | `inference_start` | 张量交给推理后端的时刻 | 进入 `session.run` / `model(...)` 前 |
| T4 | `inference_end` | 推理后端返回原始输出的时刻 | `session.run` / `model(...)` 返回后 |
| T5 | `postprocess_end` | 输出张量落到主机侧、可供解码 | Adapter 解码开始前 |
| T6 | `adapter_end` | `ManeuverPlan V2` 由 Adapter 生成（**尚未过 Validator**） | `StudentPlanAdapter.decode` 返回后 |
| T7 | `plan_ready` | 计划通过 `PlanValidator`，交由 A/B/C/D | `PlanValidator.validate` 返回后 |

说明：

- T1 与 T2 分开是官方计分表要求（"预处理"与"Token/Target packing"分开列示）。
  若某实现无法分开，必须在报告里写 `COMBINED_WITH_T2`，不得用估计值拆分。
- T4 是**模型纯推理**的唯一来源；任何包含前后处理的时间都不能标成"模型推理"。
- T6/T7 之间是纯 CPU 的契约校验开销。它与模型无关，必须单列，
  否则会被误算进推理时间去和 A2/A4 对账。
- 若某次请求未走到 T7（拒绝、超时、异常），缺失的点不补零，按第 5 节处理。

## 3. 推导时段

```text
preprocess_ms      = T1 - T0
packing_ms         = T2 - T1
inference_setup_ms = T3 - T2     框架/内存拷贝/任务提交开销
model_inference_ms = T4 - T3     ← 模型纯推理
postprocess_ms     = T5 - T4
adapter_ms         = T6 - T5
plan_validation_ms = T7 - T6

pre_model_ms       = T3 - T0     进入推理前的全部主机侧开销
post_model_ms      = T7 - T4
planner_e2e_ms     = T7 - T0     ← 完整 Planner 端到端
model_only_ms      = model_inference_ms
```

报告里 `planner_e2e_ms` 与 `model_only_ms` **必须同时出现**，
并额外给出两者的差值 `planner_overhead_ms = planner_e2e_ms - model_only_ms`。

## 4. 统计口径

- 百分位算法：线性插值（`position = (n-1) * q`），与 `runtime/latency_trace.py`
  的 `_percentile` 一致，保证与既有 `metrics/reference_5070/metrics/latency.json`
  的 `P95` 可直接对比。
- 每个时段输出 `count / mean / p50 / p95 / p99 / max`。
- 预热与测量窗口分开：默认 `warmup = 5`（与 reference_5070 的既有约定一致），
  预热样本写入 CSV 并标 `phase=warmup`，但不进入正式统计。
- 同一配置至少 3 轮；报告必须同时给出**单轮**与**合并**统计。
- 模型加载时间不计入延迟，但单列为 `model_load_ms`。

## 5. 异常与拒绝样本

| 情况 | 处理 |
|---|---|
| 计划被拒绝（Validator 不通过） | 记录到 `plan_ready` 之前实际到达的最远计时点，`outcome=REJECTED`，进入统计但**单列** |
| 推理异常 | 写到 T3 或 T4 为止，`outcome=ERROR`，计入失败率，不计入 P95 |
| 超时放弃 | `outcome=TIMEOUT`，只统计到 T0，并记录 `timeout_budget_ms` |
| 打点缺失 | `outcome=INCOMPLETE` 且 `missing_stages` 列出缺失项，不计入任何时段统计 |

`P95` 只对 `outcome=READY` 的样本计算。失败率与超时率单独报告。

## 6. 时钟与时间基准

- 延迟一律使用高分辨率单调时钟：`time.perf_counter_ns`。
  **不要用 `time.monotonic_ns` 做延迟测量**：Windows 上它由 `GetTickCount64`
  实现，仅约 15.6 ms 跳一次，会把 20 ms 以内的推理直接量化成 0。
- 墙钟（UTC ISO8601）只用于跨机器/跨日志关联，不得参与延迟计算。
- 板端与主机时间戳不混算。`ModelRequest.created_at_ns` 若来自另一时钟域，
  只用于 `sensor_to_model` 的参考值，并标注 `clock_domain`。
- 计时器分辨率：`hardware_env.json.clock` 记录 `source`、`resolution_ns` 与
  平台 `monotonic` 的分辨率，报告第 2 节在两者差距过大时自动加提示。
- 若某段耗时为 0，先检查时钟分辨率，再怀疑实现；报告必须能区分这两种情况。

## 7. A4 打点契约

B3 不修改 A4 代码，因此打点由 A4 实现，需满足：

1. 提供可选 trace sink（默认关闭，关闭时不产生任何额外开销）。
2. 每次请求输出一份 `<request_id, {stage: monotonic_ns}>` 记录，
   阶段名与本文件第 2 节一致。
3. 打点不得改变控制流；开启打点与关闭打点的输出计划必须逐字节一致
   （由 B3 的同输入比对验证）。
4. 若无法暴露 T3/T4（例如推理后端不提供边界），必须在报告中标
   `stage_source=NOT_INSTRUMENTED`，不得用外层时间代替模型推理时间。

## 8. 原始数据

每次运行产出 `latency_raw.csv`，列定义见 `hardware_metrics_schema.md` 第 2 节。
每行一次请求，保留全部原始纳秒戳与推导时段，便于任何人独立重算百分位。
