# X86 30 分钟长稳（2026-09-21）

**目的**：把 B3 长稳从"15 秒冒烟"推进到文档要求的 **≥30 分钟**，验证漂移与恢复判据在
真实时间尺度上成立。

**这不是达标结论**：被测链是 X86 上的进程内 A1/A3 对象（随机初始化权重，
`gate_status = NOT_PROVIDED`），没有 Student/Teacher 接入、没有板端、没有功耗与 BPU 探针。
它只证明"长稳机制在 30 分钟尺度上可用、且数字可解释"。

## 运行

```powershell
py -3.12 -m challenge.hil.cli soak `
  --repo . --adapter inprocess `
  --frozen challenge/hil/frozen/d2_v1_1_val `
  --duration-minutes 30 --limit 8 --recovery-probe-cases 10 `
  --out artifacts/b3/soak_30min_streamed
```

run_id：`b3-soak-20260921T124212Z-03f43125`。同目录的 `contract_report.json` 是本次运行的
契约预检结果（先过契约再谈性能）。

## 结果

| 指标 | 值 |
|---|---|
| 请求时长 / 实测时长 | 1800 s / **1800 s**（`duration_met = true`） |
| 迭代次数 | **123,611** |
| 结局 | **READY 123,611 / 123,611**，`error_count = 0`，`success_rate = 1.0` |
| 首窗 P95 → 末窗 P95 | 17.14 ms → **16.63 ms**（无退化） |
| 整体 P95 / 最大 | 16.53 ms / 38.14 ms |
| 运行内存（峰值 RSS） | 322.4 MiB（psutil） |
| **内存漂移** | **+3,576 KiB（+3.49 MiB，比例 1.1%）** |
| 恢复探针 | 10/10 READY，0 失败，P95 15.45 ms |
| 判定 | `success = true`（四条判据：时长、无失败请求、恢复探针无失败、无遥测采样错误） |

## 漂移曲线的形状（重要）

1 Hz 采样（`memory_during_soak.csv`，1789 个样本）：

| 时刻 | RSS |
|---|---|
| 0 s | 315.2 MiB |
| 450 s | 318.6 MiB |
| 900 s | 318.6 MiB |
| 1350 s | 318.8 MiB |
| 1800 s | 319.4 MiB |

四分位均值：316.8 → 318.5 → 318.5 → 319.0 MiB。**约 7 分钟后走平**，之后 15 分钟只涨
0.8 MiB，属预热/分配器碎片形状，不是单调泄漏形状。min 311.9 / max 319.4 MiB。

注意：**B2/A4 尚未冻结"漂移受控"的阈值**，所以本目录只报告数字，不宣布"漂移受控"。

## 一次被作废的尝试（方法学缺陷，已修）

同一天第一轮 30 分钟长稳报告 `rss_drift_kib = 60,595`（59.2 MiB，18.6%），曲线单调上升且
后半段更快。追查发现是 **B3 自己的 harness**：`stability.run_soak` 把 10 万条逐次记录、
延迟与 RSS 全留在内存里，到结束才写盘，于是"漂移"量到的是自己的账本（详见
`repo_environment_findings.md` F10）。

修复后：逐次记录边跑边写 `soak.jsonl`；延迟只用有界聚合（首/末窗口 + 20k 蓄水池 + 精确最大值）；
**漂移改用 1 Hz 遥测序列**。修复当日 60 秒对照运行漂移为 266 KiB，本轮 30 分钟为 3.49 MiB。
第一轮的数字**不得**用于任何结论。

## 本目录文件

| 文件 | 内容 |
|---|---|
| `soak_summary.json` | 长稳汇总（含漂移、延迟窗口、恢复探针、四条判据） |
| `memory_during_soak.csv` | 1 Hz 内存采样（1789 行），漂移数字的原始依据 |
| `contract_report.json` | 同一运行的契约预检结果 |

逐次 `soak.jsonl`（约 30 MB）留在 `artifacts/b3/soak_30min_streamed/`（gitignore 覆盖），未入库。

## 限制

- 随机初始化权重、X86、无 Student/Teacher、无功耗/BPU → 只属 E1（结构预验证）级别；
- 本机为电池供电，延迟数字不可与 AC 运行对比（长稳的漂移结论对电源状态不敏感，但延迟是）；
- `overall_p95` 在样本数超过蓄水池时是蓄水池估计（`overall_percentiles_bounded = true`）。
