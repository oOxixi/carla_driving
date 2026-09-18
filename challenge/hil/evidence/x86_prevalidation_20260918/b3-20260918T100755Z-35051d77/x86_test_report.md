# B3 HIL / J6P 实测报告 — `b3-20260918T100755Z-35051d77`

- 生成时间（UTC）：`2026-09-18T10:08:07.556164+00:00`
- 可信范围：`X86_PRE_VALIDATED`
- J6P 状态：`J6P_PENDING`

> 本报告的全部数字来源于同一次运行目录内的原始文件，
> 每个文件的 SHA256 记录在 `measurement_manifest.json` 中。

## 1. 被测身份（五标识）

| 字段 | 值 |
|---|---|
| git_sha | 64577ea046ced0fef3a177f39d88280a82f45253 |
| model_id | student-v0-r3-fp32 |
| model_sha256 | b4493f3fdb00f6673520bebd64f7915b37f5ecdc9d65737226046b12d74d434f |
| dataset_version | NOT_APPLICABLE_RANDOM_INIT |
| config_id | student-v0-r3-structure-20260911 |
| weights gate_status | NOT_PROVIDED |
| 身份完整 | 是 |

被测链能力：

| 能力 | 状态 |
|---|---|
| 完整 Planner 链 | True |
| 模型纯推理 | True |
| PlanValidator | True |
| 打点来源 | INSTRUMENTED |

- 说明：random-initialized weights (torch.manual_seed=20260911): structure/toolchain validation only

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
| CPU 标定 (ms) | 11.8413 |
| 时钟源 | perf_counter_ns |
| 时钟分辨率 (ns) | 100.0 |

> 注意：本机 `time.monotonic` 分辨率约 15.6 ms，低于该量级的推理会被量化成 0，因此本次测量统一使用 `perf_counter_ns`（分辨率 100.0 ns）。

## 3. 延迟

口径：单调时钟纳秒；预热样本单独记录且不计入统计；仅 `outcome=READY` 的 measured 样本进入百分位；百分位为线性插值。

有效样本 `300` / 总记录 `303`；结果分布 `{'READY': 303}`。

| 时段 | n | mean | P50 | P95 | P99 | max |
|---|---|---|---|---|---|---|
| 预处理 (T0→T1) | 300 | 10.138 | 7.876 | 18.986 | 21.181 | 23.342 |
| Token/Target packing (T1→T2) | 300 | 0.748 | 0.520 | 1.800 | 1.967 | 2.089 |
| 推理提交开销 (T2→T3) | 300 | 0.004 | 0.003 | 0.008 | 0.011 | 0.020 |
| 模型纯推理 (T3→T4) | 300 | 8.769 | 8.097 | 12.894 | 14.448 | 14.698 |
| 后处理 (T4→T5) | 300 | 0.082 | 0.081 | 0.120 | 0.154 | 0.255 |
| Student Adapter (T5→T6) | 300 | 0.553 | 0.480 | 0.982 | 1.213 | 1.524 |
| 计划校验 (T6→T7) | 300 | 0.958 | 0.835 | 1.940 | 2.550 | 3.049 |
| 进入推理前合计 (T0→T3) | 300 | 10.890 | 8.726 | 20.473 | 22.988 | 25.247 |
| 推理后合计 (T4→T7) | 300 | 1.593 | 1.450 | 3.014 | 3.860 | 4.544 |
| 模型纯推理 | 300 | 8.769 | 8.097 | 12.894 | 14.448 | 14.698 |
| Planner 额外开销 | 300 | 12.482 | 10.185 | 22.870 | 25.842 | 28.073 |
| 完整 Planner 端到端 (T0→T7) | 300 | 21.252 | 18.247 | 35.427 | 39.080 | 40.977 |

### 3.1 分轮 P95 / max（ms）

| round | n | E2E P95 | E2E max | 模型 P95 |
|---|---|---|---|---|
| 1 | 100 | 32.696 | 40.977 | 11.739 |
| 2 | 100 | 36.984 | 40.320 | 13.980 |
| 3 | 100 | 32.899 | 37.159 | 11.384 |

- 独立模型压测（ONNX Runtime，CPU EP，batch=1，warmup=5）：P50=2.95805 ms，P95=3.274175 ms，max=3.3552 ms，n=100；详见 latency_model_only_raw.csv。
- torch↔ONNX 逐输出等价性：通过，全输出最大绝对差 7.629e-06（rtol=0.0001, atol=1e-05）
- 打点路径 vs 生产入口（StudentBackend.infer）输出一致性：PASS

## 4. 内存

| 指标 | 值 |
|---|---|
| 采样数 | 4 |
| 进程峰值 RSS (KiB) | 324064.0 |
| 进程峰值 RSS (MiB) | 317.62 |
| 数据来源 | psutil |

> 运行内存为进程实测峰值 RSS，与模型文件大小无关。

## 5. 功耗

`NOT_MEASURED`：本机没有配置功耗探针（`NOT_APPLICABLE`）。按口径要求，此状态下不给出任何功耗结论。

## 6. 算力利用率

| 指标 | 值 |
|---|---|
| 采样数 | 4 |
| 进程 CPU 峰值 (%) | 164.1 |
| BPU 均值 (%) |  |
| BPU 是否实测 | 否 |

> “异构算力利用率 ≥80%”的正式公式由 A4/B2 确认前，本报告只提供原始采样值，不给结论行。

## 7. 回放与输入输出一致性

| 指标 | 值 |
|---|---|
| 回放样本数 | 300 |
| 计划产出率 | 1.0000 |
| 图像解析成功率 | 1.0000 |
| 结构检查通过率 | 1.0000 |
| Teacher 对比 | DIAGNOSTIC_ONLY |

> Student weights are not A3-gated in this run; behaviour match is recorded for toolchain validation and must not be read as accuracy.

## 8. 异常输入

| 用例 | 观察结论 | outcome |
|---|---|---|
| missing_rgb_ref | OBSERVED_FAIL_CLOSED | READY |
| missing_rgb_file | OBSERVED_FAIL_CLOSED | READY |
| source_text_over_32_chars | OBSERVED_FAIL_CLOSED | READY |
| targets_over_8 | OBSERVED_FAIL_CLOSED | READY |
| nan_target_distance | OBSERVED_FAIL_CLOSED | READY |
| infinite_relative_speed | OBSERVED_FAIL_CLOSED | READY |
| missing_targets_key | OBSERVED_FAIL_CLOSED | ERROR |
| empty_source_text | OBSERVED_FAIL_CLOSED | READY |
| degenerate_deadline | OBSERVED_FAIL_CLOSED | READY |
| must_stop_with_narrow_allowlist | OBSERVED_FAIL_CLOSED | READY |

> The harness records runtime behaviour on abnormal input; whether each verdict passes the gate is B2's decision.

## 9. 长稳与内存漂移

（本次运行未执行长稳）

## 10. 运行摘要

| 字段 | 值 |
|---|---|
| 轮数 | 3 |
| measured 记录 | 300 |
| warmup 记录 | 3 |
| 回放记录 | 300 |
| 总耗时 (s) | 6.39 |

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

