# A4 X86 运行时：与 B3 测量契约的差距

> 当前部署目标、证据分级和关闭这些缺口的验收条件见
> [`docs/architecture/modules/A4_OPENEXPLORER_J6P_RUNTIME.md`](../../docs/architecture/modules/A4_OPENEXPLORER_J6P_RUNTIME.md)。

> 提出方：B3（独立实测）　核对版本：`challenge` @ `64577ea0`
> 对照契约：`challenge/hil/a4_runtime_contract.md`
> 本报告只列缺口与证据，不涉及对 A4 代码的修改。

## 1. A4 当前已交付的内容

```
challenge/horizon/README.md                  部署范围、模型与输入输出、J6P 待办
challenge/horizon/operator_mapping.md        算子映射
challenge/runtime/student_x86.py             X86 ONNX 计时脚本
challenge/runtime/x86_run.sh                 启动脚本
challenge/runtime/runtime_profile_x86.json   性能档案
```

这是一个合格的**阶段性交付**：A4 自己的 README 也写明 "X86 ONNX Runtime validation:
in progress"、"J6P deployment is pending"。下面的缺口是按最终契约衡量的，不是否定
当前进度。

## 2. 契约逐项对照

| 契约要求 | A4 现状 | 结论 |
|---|---|---|
| 从 stdin 读 `ModelRequest V1`，向 stdout 写 `ManeuverPlan V2` | 脚本自行构造全零张量，不读请求、不产出计划 | **缺** |
| 打点：8 个阶段（T0–T7）可选开启 | 无任何打点 | **缺** |
| `--describe` 输出身份（model_sha256 / git_sha / config_id / dataset_version / opset） | `runtime_profile_x86.json` 只含后端名、provider、模型路径、输入输出 shape | **缺**（且无产物 SHA） |
| 模型级测量模式（只跑前向，可与端到端区分） | 脚本本身即模型级，但没有模式开关，也没有端到端模式 | **部分** |
| 批量/常驻模式，避免进程冷启动计入延迟 | 无（`x86_run.sh` 每次新起进程） | **缺** |
| 记录测量环境 | 无电源状态、无系统负载、无 CPU 标定、无 onnxruntime 版本 | **缺** |
| 板端遥测探针 | 不适用（X86 阶段） | 待 J6P |

## 3. 已有档案中的延迟数字不可复现

`runtime_profile_x86.json` 记录：

```
backend: onnxruntime / CPUExecutionProvider
warmup_runs: 5, benchmark_runs: 20
latency_ms: { avg: 13.816, min: 11.705, max: 23.158 }
```

B3 把该脚本**原样复现**（源码逐行相同，仅补打印分位数）在同一台机器上重跑：

```
runs 20 / warmup 5
avg 2.568 ms   min 2.215 ms   max 2.828 ms   p50 2.612 ms   p95 2.817 ms
复现时的环境：AC 供电、系统负载 8.8%、CPU 标定 7.75 ms
```

差异 **5.4 倍**。B3 自己的独立 harness（`challenge/hil`）在同一产物上量到
P50 2.90–2.96 ms，与复现值相差 2% 以内，两条独立代码路径互相印证。

**结论**：13.816 ms 反映的是 A4 测量当时机器的状态（降频/被占用），不是模型性能。
由于该档案没有记录任何环境信息，这个数字事后既无法验证，也无法与别人比较。

同类现象 B3 自己也踩过并已量化：同一台机器、同一份代码，ONNX 推理 P50 曾出现
2.7 / 27 / 92 ms 三种状态。B3 因此把 CPU 标定、电源状态与系统负载写进了每次运行的
`hardware_env.json`。

## 4. 对 A4 的三条最小建议

**建议 1：给 `student_x86.py` 加 `--describe`。**

不跑推理，输出：

```json
{
  "git_sha": "<40 位十六进制>",
  "model_id": "student-v0-r3-fp32",
  "model_sha256": "<ONNX 文件 SHA256>",
  "config_id": "<与 A1 的 student_config.json 一致>",
  "dataset_version": "<A3 训练集版本或 NOT_APPLICABLE_RANDOM_INIT>",
  "opset": 17,
  "precision": "fp32",
  "input_shapes": {"rgb": [1,3,224,224], "text_tokens": [1,32], "targets": [1,8,14], "state": [1,64]}
}
```

**建议 2：在性能档案里记录测量环境。**

最少四项：电源状态、测量开始时的系统负载、CPU 标定值、onnxruntime 版本。
可以直接复用 B3 的采样器，避免各写一套：

```python
from challenge.hil.samplers import power_source, machine_load_percent, cpu_calibration_ms
import importlib.metadata as metadata
environment = {
    "power_source": power_source(),
    "background_load_cpu_percent": machine_load_percent(),
    "cpu_calibration_ms": cpu_calibration_ms(),          # 内部已做"多次取最小"
    "onnxruntime_version": metadata.version("onnxruntime"),
}
```

**建议 3：把脚本扩展成契约入口。**

```text
<runtime-command>              # stdin: ModelRequest JSON → stdout: ManeuverPlan V2 JSON
<runtime-command> --trace ...  # 附带 8 个阶段的单调纳秒时间戳
<runtime-command> --describe   # 身份
<runtime-command> --model-only # 只跑前向
```

阶段名与格式见 `a4_runtime_contract.md` §3。打点默认关闭、开启时不得改变输出。

## 5. A4 交付前可自行运行的检查

B3 已把契约做成可执行检查，**不需要 B3 参与**：

```powershell
py -3.12 -m challenge.hil.cli contract `
  --repo . --frozen challenge/hil/frozen/d2_v1_1_val `
  --adapter board `
  --board-command "py -3.12 challenge/runtime/student_x86.py" `
  --out artifacts/a4_contract_check
```

它会检查：进程能否被驱动、输出是否为合法计划 JSON、`request_id/command_id` 是否回显、
是否出现 `steer/throttle/brake/waypoints`、步数是否在 1–4、打点阶段名是否合法、
打点是否单调、`model_only_ms` 与 `planner_e2e_ms` 是否可得、是否超出延迟预算。
结果写在 `contract_report.json`，`passed=false` 时列出具体失败项。

同样可复用的两项：

```powershell
# 产物结构独立校验（opset / 算子 / 输入输出契约 / SHA）
py -3.12 -m challenge.hil.cli artifact --repo .

# 量化后与 FP32 的逐输出偏差（A2 交付 INT8 后）
py -3.12 -m challenge.hil.cli consistency --repo . --baseline-onnx <fp32.onnx> --onnx <int8.onnx>
```

## 6. 边界

- B3 不修改 A4 的部署代码；本报告只提供缺口清单与可复用的检查工具。
- A4 的 X86 与 J6P 交付节奏由 A4 决定；B3 只在收到入口后开始独立实测。
- 本报告中的复现实验脚本保存在仓库外，未进入版本库。
