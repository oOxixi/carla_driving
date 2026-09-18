# B3 HIL / J6P 实测报告 — `b3-soak-20260918T100812Z-50ebf75e`

- 生成时间（UTC）：`2026-09-18T10:08:31.902951+00:00`
- 可信范围：`X86_PRE_VALIDATED`
- J6P 状态：`J6P_PENDING`

> 本报告的全部数字来源于同一次运行目录内的原始文件，
> 每个文件的 SHA256 记录在 `measurement_manifest.json` 中。

## 1. 被测身份（五标识）

| 字段 | 值 |
|---|---|
| git_sha | f8e567ef8cd3cce592b920947dee9c6a2f3a9cf0 |
| model_id | student-v0-r3-fp32 |
| model_sha256 | ffb1ed5e9b23aa7100343bb4f02c8cfef3da5049e9c5eba4c0e66247c96ee243 |
| dataset_version | NOT_APPLICABLE_RANDOM_INIT |
| config_id | student-v0-r3-structure-20260911 |
| weights gate_status | NOT_PROVIDED |
| 身份完整 | 是 |

被测链能力：

| 能力 | 状态 |
|---|---|
| 完整 Planner 链 | True |
| 模型纯推理 | True |
| PlanValidator | False |
| 打点来源 | INSTRUMENTED |

- 说明：model-only chain; adapter runs on host tensors converted from numpy
- 说明：no PlanValidator: A4/J6P runtime owns the deployed validation step

## 2. 测量环境

| 字段 | 值 |
|---|---|
| device_class | X86_WORKSTATION |
| host | LAPTOP-RG7O496D |
| cpu | Intel64 Family 6 Model 183 Stepping 1, GenuineIntel |
| accelerator | Intel64 Family 6 Model 183 Stepping 1, GenuineIntel |
| bpu |  |
| openexplorer |  |
| power_measurement | {'method': 'NOT_MEASURED', 'probe_point': 'NOT_MEASURED', 'sampling_hz': 1.0, 'notes': ''} |
| cpu_governor |  |
| torch | 2.6.0 |
| onnxruntime | 1.27.0 |
| numpy | 2.4.6 |
| 电源 | AC |
| CPU 标定 (ms) | 3.9279 |
| 时钟源 | perf_counter_ns |
| 时钟分辨率 (ns) | 100.0 |

> 注意：本机 `time.monotonic` 分辨率约 15.6 ms，低于该量级的推理会被量化成 0，因此本次测量统一使用 `perf_counter_ns`（分辨率 100.0 ns）。

## 3. 延迟

口径：单调时钟纳秒；预热样本单独记录且不计入统计；仅 `outcome=READY` 的 measured 样本进入百分位；百分位为线性插值。

有效样本 `899` / 总记录 `899`；结果分布 `{'READY': 899}`。

（无有效 measured 样本）


## 4. 内存

| 指标 | 值 |
|---|---|
| 采样数 | 16 |
| 进程峰值 RSS (KiB) | 320572.0 |
| 进程峰值 RSS (MiB) | 314.21 |
| 数据来源 | psutil |

> 运行内存为进程实测峰值 RSS，与模型文件大小无关。

## 5. 功耗

`NOT_MEASURED`：本机没有配置功耗探针（`NOT_APPLICABLE`）。按口径要求，此状态下不给出任何功耗结论。

## 6. 算力利用率

| 指标 | 值 |
|---|---|
| 采样数 | 16 |
| 进程 CPU 峰值 (%) | 1428.1 |
| BPU 均值 (%) |  |
| BPU 是否实测 | 否 |

> “异构算力利用率 ≥80%”的正式公式由 A4/B2 确认前，本报告只提供原始采样值，不给结论行。

## 7. 回放与输入输出一致性

（本次运行未执行回放）

## 8. 异常输入

（本次运行未执行异常用例）

## 9. 长稳与内存漂移

| 指标 | 值 |
|---|---|
| 请求时长 (s) | 15.0 |
| 实测时长 (s) | 15.0 |
| 时长达标 | True |
| 请求数 | 899 |
| 成功率 | 1.00000 |
| 首窗 P95 (ms) | 24.245 |
| 末窗 P95 (ms) | 24.273 |
| 整体 P95 (ms) | 24.153 |
| 内存漂移 (KiB) | 625.5 |
| 内存漂移比例 | 0.00196 |
| recovery probe 失败数 | 0 |
| 长稳结论 | 通过 |

判定条件：wall-clock duration met；no failed request during the soak；recovery probe produced no failed request；no telemetry sampling error

## 10. 运行摘要

| 字段 | 值 |
|---|---|
| 轮数 | 1 |
| measured 记录 | 899 |
| warmup 记录 | 0 |
| 回放记录 | 0 |
| 总耗时 (s) | 15.02 |

## 11. 可信范围与禁止表述

允许的结论：

- 工具链与测量流程的正确性
- 相对趋势（同一主机、同一配置下的版本间比较）

禁止的表述：

- 把 X86 或桌面 GPU 结果写成 J6P 实机达标
- 把模型文件大小当作运行内存
- 用 INT8 体积下降代替 FLOPs 下降
- 用估算值或 TDP 代替实测功耗
- 用未确认公式给出“异构算力利用率 = xx%”结论
- 在功耗未实测时给出功耗达标结论
- 在 BPU 未实测时给出 BPU 利用率结论

## 12. 未解除的外部依赖

- 无

