# A4 板端 Runtime 接口需求书（B3 提出）

> A4 从 INT8 输入、OpenExplorer 转换到 J6P 交付的完整门禁见
> [`docs/modules/A4_OPENEXPLORER_J6P_RUNTIME.md`](../../docs/modules/A4_OPENEXPLORER_J6P_RUNTIME.md)。

> 目的：让 A4 的 Runtime **一次做对**。本文件只列 B3 测量所必需的最小接口，
> 不干涉 A4 的实现方式。文末的自检命令能在交付前把契约跑一遍。
>
> 状态：待 A4 确认。任何一条无法满足时，请在确认时说明，B3 会调整测量口径，
> 而不是事后在报告里标注为"无法测量"。

## 1. 边界

B3 只测量、不修改。因此需要 A4 提供的是**入口**和**可观测性**，
而不是让 B3 复制一份推理逻辑。

不得为了配合测量而下述改动：

- 不改变 A/B/C/D 或 SafetySupervisor 的行为；
- 不为测量新增一套预处理或后处理实现；
- 不把 batch 改成大于 1（固定 shape 契约是 batch=1）。

## 2. 交付物一：Runtime 入口（CLI 契约）

```text
<runtime-command>  # 例如 python -m challenge.horizon.runtime.student_j6p --model x.bin
```

| 项 | 要求 |
|---|---|
| 输入 | 从 **stdin** 读取一个 `ModelRequest V1` JSON 对象（单行或整体均可） |
| 输出 | 向 **stdout** 写一个 `ManeuverPlan V2` JSON 对象；最后一行必须是完整 JSON |
| 退出码 | 成功 `0`；被拒绝/超时/异常用非 0，并在 stderr 说明原因 |
| 无交互 | 不得依赖 TTY、不得读环境外的交互输入 |
| 启动开销 | 允许进程级启动；但必须提供"常驻模式"或"批量模式"，否则 `model_load_ms` 会混进 E2E（见 §5） |

批量模式（推荐）：一次进程启动，从 stdin 逐行读多个请求，逐行输出多个计划。
B3 用它来避免把进程冷启动算进延迟。

## 3. 交付物二：打点（可选开启的 trace）

输出计划时，可在同一个 JSON 对象里附带打点字段：

```json
{
  "schema_version": "2.0",
  "request_id": "...",
  "command_id": "...",
  "steps": [ ... ],
  "trace": {
    "input_arrival":    1234567890123,
    "preprocess_end":   1234567891456,
    "packing_end":      1234567891580,
    "inference_start":  1234567891590,
    "inference_end":    1234567899921,
    "postprocess_end":  1234567900004,
    "adapter_end":      1234567900180,
    "plan_ready":       1234567900290
  }
}
```

要求：

1. 阶段名与上表完全一致，不得增删改名（B3 侧会校验）。
2. 值为**单调时钟纳秒整数**，严格递增。
3. 打点默认关闭；开启时不得改变控制流，开启与关闭的计划输出必须逐字节一致。
4. 打点开关用命令行参数或环境变量控制，B3 需要能通过配置文件开启。
5. **时钟必须用 `perf_counter_ns` 或等价的平台高分辨率单调时钟。**
   Windows 上 `time.monotonic_ns` 由 `GetTickCount64` 实现，约 15.6 ms 跳一次，
   会把 20 ms 以内的推理量化成 0；Linux 上 `monotonic_ns` 可用。
   若板端只能用另一种时钟，请在交付时注明 `clock_domain`。
6. 若某段无法打点（例如推理后端不暴露边界），**不要用外层时间代替**，
   直接不写该阶段；B3 会记录 `missing_stages` 并把该段标记为不可用。

合并规则（B3 侧行为，2026-09-21 修复后）：

- Runtime 自己给出的打点**优先**。上表 8 个阶段（含 `input_arrival` 与 `plan_ready`）
  全部由 Runtime 提供时，B3 全部采用 Runtime 的值，不会覆盖，也不会重复打点。
- Runtime 未提供的阶段由宿主补齐：`input_arrival` 用子进程启动前的宿主时刻，
  `plan_ready` 用收到输出的宿主时刻。补齐意味着该段含进程通信开销，属宿主包络，
  不能当作板端推理延时。
- 未识别的阶段名会被忽略并记录在运行信息的 `ignored_stages`；时间戳非单调或阶段顺序
  颠倒会让 B3 以 `AdapterError` 终止该次运行，而不是产生一份数字可疑的报告。

## 4. 交付物三：身份与描述查询

需要一个**不跑推理**就能拿到身份的子命令，例如：

```text
<runtime-command> --describe
```

输出 JSON，至少包含：

```json
{
  "git_sha": "<40 位十六进制，Runtime 代码所在提交>",
  "model_id": "student-v0-r3-...",
  "model_sha256": "<板端模型产物 .bin 的 SHA256>",
  "dataset_version": "<A3 训练集版本>",
  "config_id": "<A1 的 student_config.json config_id>",
  "precision": "int8",
  "batch": 1,
  "input_shapes": {"rgb": [1,3,224,224], "text_tokens": [1,32], "targets": [1,8,14], "state": [1,64]},
  "openexplorer_version": "..."
}
```

理由：报告的每个数字都要能回溯到这五项；如果只能靠人工填，就无法防错。
`model_sha256` 必须是**板端实际加载**的产物，不是导出前的 ONNX。

## 5. 交付物四：模型级测量模式

需要一个"只跑前向"的路径，用于报告 `model_only_ms`，与 `hrt_model_exec perf`
的结果对齐：

```text
<runtime-command> --model-only --input <tensor-dump-dir>
```

- 该模式只做 `inference_start → inference_end`，**不含**预处理、packing、后处理、Adapter；
- 输入用 B3 提供的固定张量。B3 已实现生成命令，A4 直接取用即可：

  ```powershell
  py -3.12 -m challenge.hil.cli dump-tensors `
    --repo <carla_driving 路径> --frozen <冻结请求集> --limit 1 --out <输出目录>
  ```

  每个用例一个子目录，内含 `rgb.npy`、`text_tokens.npy`、`targets.npy`、`state.npy`
  与 `manifest.json`（逐文件 shape/dtype/SHA256 及该请求的规范摘要）。这些张量由 A1 的
  `StudentPreprocessor` 原样生成，A4 不要自己重算；
- 输出可以只是原始张量或校验和，用于确认输入被正确加载。

  为便于跨机对比，请输出为 `{"outputs": {"<输出名>": "<原始字节的 SHA256>", ...}}`；
B3 会把板端校验和与 X86/ONNX 在**同一份张量**上的校验和对照，不一致即视为实现分歧，
而不是"测量误差"。

若没有这个模式，B3 只能报端到端，无法回答"板端推理本身是否达标"。

## 6. 交付物五：遥测取数命令（建议）

B3 已经支持"执行一条命令、解析其 stdout 的 JSON"这种探针。若板端有功耗/BPU
读数，请提供类似：

```text
python tools/board_power_probe.py    → {"power_w": 12.3, "voltage_v": 12.0, "current_a": 1.02}
python tools/board_util_probe.py     → {"bpu_percent": 78.5, "cpu_percent": 41.0}
```

并请一并确认：

- 功耗**取电点**（整板 / SoC / BPU 单路）；
- 采样频率与被测进程的关系（同一时间窗口）；
- BPU 是否被其他进程共享（`exclusive_use` true/false）。

没有探针时 B3 会写 `NOT_APPLICABLE` 并说明原因，不会用 TDP 或估算值顶替。

## 7. 交付前自检

B3 提供可执行的契约检查，A4 在交付前自行运行：

```powershell
py -3.12 -m challenge.hil.cli contract `
  --repo <carla_driving 路径> `
  --frozen <冻结请求集> `
  --adapter board `
  --board-command "python -m challenge.horizon.runtime.student_j6p --model student_int8.bin --trace" `
  --out <输出目录>
```

它会检查：进程能否被驱动、计划是否为合法 JSON、`request_id/command_id` 是否回显、
是否出现 `steer/throttle/brake/waypoints`、步数是否在 1–4、打点阶段名是否合法、
打点是否单调、`model_only_ms` 与 `planner_e2e_ms` 是否可得、是否超出延迟预算；
以及三条**独立驱动**的接口路径（对应本文 §4 / §2 / §5）：

| 检查项 | 怎么判 | 失败意味着 |
|---|---|---|
| `describe_endpoint` | 跑 `<命令> --describe`，要求 8 个必备字段齐全 | 无法把报告数字绑定到具体模型产物 |
| `describe_matches_artifact` | `--describe` 的 `model_sha256` 与 `--board-artifact` 的实测 SHA256 一致 | 报告会指向另一个模型 |
| `batch_mode` | 一个进程喂 2 个请求（每行一个），要求回来 2 个计划且回显 `request_id` | 每次请求的冷启动被算进 E2E |
| `model_only_mode` | 带 `--model-only --input <张量目录>`，要求返回输出校验和 | 无法回答"板端推理本身是否达标"；未提供张量目录时记 `NOT_RUN`（不算通过，也不算失败） |

结果写在 `contract_report.json`，`passed=false` 时会列出具体失败的检查项。
**这份报告就是 B3 的验收前置条件**，先过契约检查，再谈性能数字。

## 8. A4 需要回给 B3 的信息

1. Runtime 的启动命令（含打点开关与批量模式）；
2. 板端 OpenExplorer / 工具链版本，以及转化用的配置路径；
3. 是否具备 §5 的模型级测量模式；
4. 功耗与 BPU 读数的取数方式与取电点；
5. 契约检查报告 `contract_report.json`。
