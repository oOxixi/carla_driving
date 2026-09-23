# B3 硬件指标与原始数据列定义（D1 交付）

> 板端环境冻结、三轮实测、Gate 与证据交接见
> [`docs/architecture/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](../../docs/architecture/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md)。

> 本文件定义 `hardware_env.json`、四类 `*_raw.csv` 与稳定性日志的格式。
> 原则：**取不到就写 NOT_APPLICABLE 并说明原因，绝不用估计值或代理指标填充。**

## 1. `hardware_env.json`

每次运行一份，记录测量环境。J6P 相关字段在无板时填 `null` 且
`device_class` 为 `X86_WORKSTATION`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `device_class` | string | `X86_WORKSTATION` / `J6P_BOARD`，决定报告可信范围 |
| `run_started_at_utc` | string | ISO8601 |
| `host` | object | `hostname`, `os`, `kernel`, `cpu_model`, `cpu_cores`, `cpu_max_mhz` |
| `memory_total_mib` | number | 主机/板端物理内存 |
| `python` | object | `version`, `executable` |
| `accelerator` | object | `kind`(cpu/bpu/gpu), `name`, `driver`, `runtime_version` |
| `bpu` | object\|null | 板端：`arch`, `core_count`, `frequency_mhz`, `toolchain_version` |
| `openexplorer` | object\|null | 板端：`version`, `converter_version`, `runtime_version` |
| `model_artifact` | object | `path`, `sha256`, `size_bytes`, `format`(onnx/bin) |
| `identity` | object | 五个标识，见第 5 节 |
| `power_measurement` | object | `method`(`ONBOARD_INA`/`EXTERNAL_METER`/`NOT_MEASURED`), `probe_point`, `sampling_hz`, `notes` |
| `thermal` | object\|null | `ambient_c`, `cooling`(passive/fan/heatsink) |
| `cpu_governor` | string\|null | Linux 板端：`performance`/`ondemand` 等，影响结果可比性 |

### 1.1 运行环境指纹（每次运行自动写入）

延迟对机器状态极度敏感，因此以下字段与数字同等重要，缺一不可比较：

| 字段 | 说明 |
|---|---|
| `power_source` | `AC` / `BATTERY` / `UNKNOWN`。电池供电时 CPU 降频，延迟可差数倍 |
| `background_load_cpu_percent` | 测量开始时的系统 CPU 负载。过高说明机器被占用 |
| `cpu_calibration_ms` | 固定多线程矩阵乘耗时（重复取最小值）。**跨运行比较的第一依据** |
| `cpu_frequency` | 平台报告的当前/最大频率；Windows 上即使降频也可能报标称值，仅作参考 |
| `runtime_libraries` | torch / onnxruntime / onnx / numpy / Pillow / jsonschema / psutil 版本 |
| `clock` | 计时时钟源与分辨率（`perf_counter_ns`，以及平台 `monotonic` 的分辨率） |
| `teacher_baselines` | Teacher v1/v4 两个 pin 的 manifest SHA、tag→commit 与模型身份一致性 |
| `model_artifact` | 被测产物的路径、SHA256、大小与格式 |

测量开始时若发现电池供电或系统负载过高，工具会打印告警，提示该批数字不可作为基线。

## 2. 四类原始 CSV

统一约定：只写 UTF-8、逗号分隔、首行表头、数值使用 `.` 小数点，
时间戳同时给单调纳秒与墙钟，布尔用 `true`/`false`。
列定义在 `challenge/hil/columns.py` 中维护，并导出到 `schemas/`。

### 2.1 `latency_raw.csv`（每请求一行）

```text
run_id, round, phase, case_id, request_id, outcome, reason_code,
t0_input_arrival_ns, t1_preprocess_end_ns, t2_packing_end_ns,
t3_inference_start_ns, t4_inference_end_ns, t5_postprocess_end_ns,
t6_adapter_end_ns, t7_plan_ready_ns,
preprocess_ms, packing_ms, inference_setup_ms, model_inference_ms,
postprocess_ms, adapter_ms, plan_validation_ms, pre_model_ms, post_model_ms,
planner_e2e_ms, model_only_ms, planner_overhead_ms,
missing_stages, outcome_detail, model_id, model_sha256, config_id,
dataset_version, git_sha, wall_time_utc
```

- `phase` ∈ `warmup` / `measured`。
- 缺失的计时点留空（不放 0），并在 `missing_stages` 用 `|` 分隔列出。
- `model_sha256` 等五个标识逐行写入，保证任意一行都能独立追溯。

### 2.2 `memory_raw.csv`（周期采样）

```text
run_id, round, sample_index, wall_time_utc, monotonic_ns,
scope, rss_kib, peak_rss_kib, source
```

- `scope` ∈ `planner_process`（被测进程自身）。板端如需额外记录整机
  DDR 占用，另起 `scope=board_total` 的行，并在报告里分开说明。
- `source` ∈ `psutil` / `proc_status` / `win32_psapi` / `board_tool`。
- **不得**用模型文件大小或权重张量大小充当运行内存。

### 2.3 `power_raw.csv`（周期采样）

```text
run_id, round, sample_index, wall_time_utc, monotonic_ns,
scope, source, probe_point, voltage_v, current_a, power_w, notes
```

- `scope` ∈ `board_total` / `soc` / `bpu_rail`。**取电点必须在
  `hardware_env.json.power_measurement.probe_point` 中一致声明。**
- `source` ∈ `onboard_ina` / `external_meter` / `NOT_APPLICABLE`。
- 无板或未接测点时，写一行 `source=NOT_APPLICABLE`，其余数值列留空，
  `notes` 写原因（例如 `no_power_probe_attached`）。
- 平均功耗 = 测量窗口内 `power_w` 的时间加权均值；峰值 = `max(power_w)`。

### 2.4 `utilization_raw.csv`（周期采样）

```text
run_id, round, sample_index, wall_time_utc, monotonic_ns,
scope, source, cpu_percent, bpu_percent, ddr_bandwidth_gbps, notes
```

- `cpu_percent` 为进程级（非整机），板端 BPU 由厂商工具读取。
- `cpu_percent` 是多核累计值，单核满载即 100，因此超过 100 属正常；报告需说明。
- 无板时 `bpu_percent` 留空，写 `source=NOT_APPLICABLE`，报告中标
  `BPU_NOT_MEASURED`。

## 3. "异构算力利用率"口径（**待 A4/B2 确认，未确认前不得报数**）

官方指标 `≥80%` 没有唯一定义，本文件先固定候选公式与必须记录的分母/分子，
避免各人各算一版：

```text
BPU 忙时占比 = BPU 实际执行周期数 / 测量窗口内 BPU 可用周期数
```

必须一起记录：

1. 测量窗口起止（与 `latency_raw.csv` 的 `phase=measured` 对齐）；
2. BPU 是否被其他进程共享（`exclusive_use` true/false）；
3. 若采用 BPU+CPU 加权口径，权重来源与公式必须写在报告里。

在 A4/B2 给出正式公式前，报告只允许输出原始采样值，
不允许出现"异构利用率 = xx%"这样的结论行。

## 4. 稳定性与异常

- `stability_logs/soak.jsonl`：长稳期间每次探针一行
  （`wall_time_utc`, `monotonic_ns`, `iteration`, `outcome`, `latency_ms`,
  `rss_kib`, `power_w`, `bpu_percent`, `temperature_c`, `notes`）。
- `stability_logs/soak_summary.json`：起止时间、请求数、成功率、
  内存漂移（首尾窗口均值差）、结束时 recovery probe 结果、`success` 布尔。
- `stability_logs/memory_during_soak.csv`：与 `memory_raw.csv` 同列，采样线程
  在长稳期间独立记录，用于把内存漂移与请求延迟分开看。
- 注意：长稳里的 `latency_ms` 包含每轮遥测采样开销，只用于看趋势，
  不能当作绝对百分位；绝对延迟以 `latency_raw.csv` 为准（`soak_summary.json`
  的 `latency_note` 记录了这一点）。
- `failure_cases/<case_id>.json`：异常输入、期望行为、实际结果、
  是否 fail-closed、延迟是否有界。

## 5. 五标识（每个可评测版本必须有）

```text
git_sha, model_id, model_sha256, dataset_version, config_id
```

- 全部为非空字符串；`git_sha` 为完整 40 位十六进制。
- `model_sha256` 必须等于实际加载产物的 SHA256（由 `identity.py` 现场计算，
  不信任清单里的自述值）。
- 报告的每个数字都能回溯到这五项：`latency_raw.csv` 逐行携带，
  `hardware_env.json.identity` 汇总一次。

## 6. 运行清单

每次运行结束时生成 `measurement_manifest.json`，登记该 run 目录下
**除自身以外**所有文件的相对路径、大小与 SHA256，
并记录 `run_id`、`created_at_utc`、`identity`、`claim_scope`。
任何人可据此验证证据未被静默替换。

## 7. 可信范围（claim scope）

| `device_class` | 允许的结论 | 禁止的写法 |
|---|---|---|
| `X86_WORKSTATION` | `X86 PRE-VALIDATED`，工具链与相对趋势 | 任何形式的"J6P 达标" |
| `J6P_BOARD` 且功耗/利用率有真实来源 | `J6P` 实测 | 用桌面 GPU 数据补空缺 |
| `J6P_BOARD` 但功耗未测 | 只报延时/内存，功耗写 `NOT_MEASURED` | 用 TDP 或估算值代替实测 |

`report.py` 会依据 `hardware_env.json` 自动生成该章节，且当
`device_class=X86_WORKSTATION` 时强制插入 `J6P PENDING` 声明。
