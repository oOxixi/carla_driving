# X86 仿真实测（2026-09-24，无板端）

> ⚠️ **本目录是替代条件下的可行性演练证据，不是最终测试结果。**
> 被测对象是 A1 随机初始化结构（`gate_status = NOT_PROVIDED`）、自建校准集与 X86 仿真运行时；
> 不是 A3 真实权重、A2 官方 INT8 产物、A4 契约 Runtime 或 J6P 板卡。
> 数字只能用于验证测量链与判据可用，**不得作为性能/精度达标结论引用**。

**目的**：在"不做 J6P 板端开发、只做 X86 仿真"的口径下，把 PC 端能做的检查跑齐并留下可核验证据。
范围与口径见 [`../../x86_simulation_scope.md`](../../x86_simulation_scope.md)，复现脚本在
[`../../harness/x86_sim/`](../../harness/x86_sim/)。

**这不是达标结论**：被测模型是 A1 的随机初始化结构（`gate_status = NOT_PROVIDED`），
没有 A3 训练权重、没有 B2 冻结用例、没有板端遥测。它证明的是**工具链与流程可用、数字可解释**。

## 环境

| 项 | 值 |
|---|---|
| 宿主 | WSL2 Ubuntu 22.04.3（x86_64） |
| 镜像 | `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1` |
| 工具链 | `hb_compile 3.5.16` / `HBDK 4.11.11` / `HMCT 2.8.4` / `UCP 3.15.8` |
| 仿真平台 | `HB_UCP_SIM_PLATFORM_TYPE=nash-p`（不设会因 `platform march: nash-e` 拒绝加载） |
| 被测模型 | `challenge/student_v0_fp32.onnx`（4 输入 / 10 输出 / opset 17） |

产物摘要（`00_environment.log`）：

```
000a7e02fab45f6ab9bac86433ee7c32  student_v0_fp32.hbm          (未校准, O0)
a9dc1f1a7fe52c44a92be3516e6882b4  student_v0_fp32_quantized_model.bc
```

## 文件

| 文件 | 内容 |
|---|---|
| `00_environment.log` | 宿主/镜像/工具版本、产物 md5、仿真平台变量 |
| `01_model_info.log` | `hrt_model_exec model_info`：4 输入 + 10 输出的 valid shape / stride / 对齐字节 |
| `03_infer_hbm.log` | `hrt_model_exec infer --enable_dump`（未校准产物）：读文件、padding、dump 路径、Infer time |
| `04_sim_consistency.log` | `HBRuntime` 分别跑 `.hbm` 与 `.bc`，与浮点 ONNX 参考的逐头余弦 + 仿真耗时 |
| `05_dump_vs_onnx.json` | CLI dump（按 stride 去填充）对浮点 ONNX 的逐头余弦与最大绝对差 |
| `06_hb_verifier.log` | `hb_verifier`（onnx↔bc，未校准）16 行余弦 |
| `07_hb_compile_cal.log` | 带校准的 PTQ 编译摘要（yaml 配置、校准类型、内存、BPU march） |
| `08_hb_verifier_cal.log` | `hb_verifier`（onnx↔bc，已校准）16 行余弦 |
| `09_thresholds.log` | 两次编译的量化阈值分布对比（未校准 38/40 为默认 1.0） |
| `10_model_info_cal.log` | 校准产物的 `model_info` 摘要 |
| `11_infer_cal.log` | 校准产物的 infer 日志（padding + Infer time） |
| `12_dump_vs_onnx_cal.json` | 校准产物 CLI dump 对浮点 ONNX 的逐头余弦 |
| `13_node_placement_skip_cal.csv` | 未校准编译的节点落点（59/59 全在 BPU，输出 `si8`） |
| `14_node_placement_calibrated.csv` | 校准编译的节点落点（59/59 全在 BPU） |
| `sim_consistency.json` | `04` 的机器可读版本 |

## 结果

### 1. 编译与算子预检

- `hb_compile --march nash-p`：25.5 s，**0 warning / 0 error**，opset 17→19，
  节点落点 `13_node_placement_skip_cal.csv` 显示 **59/59 全在 BPU（无 CPU fallback）**、输出类型 `si8`；
- 内存：input 603,136 / output 2,560 / static 23,644,904 / dynamic 654,848 / temp 49,152，
  **min requirement 24,299,752 B**；
- 带校准（O2）编译：50 s，static 23,580,160，**min requirement 24,185,856 B**。

### 2. 逐头余弦（CLI / API / verifier 三路一致）

参考值为 onnxruntime 浮点 ONNX 输出，输入为 `ACC_A01_lead_brake#0000`。

| 输出头 | 未校准 | 已校准 |
|---|---:|---:|
| `plan_length_logits` | 0.793460 | 0.999214 |
| `behavior_logits` | 0.876491 | 0.999411 |
| `target_pointer_logits` | 0.840000 | 0.999117 |
| `target_lane_logits` | 0.851552 | 0.999193 |
| `target_speed_mps` | 0.997520 | 0.999950 |
| `completion_type_logits` | 0.921171 | 0.999689 |
| `on_failure_logits` | 0.850498 | 0.999693 |
| `confidence` | 1.000000 | 1.000000 |
| `requires_confirmation_logits` | 1.000000 | 1.000000 |
| `replan_condition_logits` | 0.859126 | 0.999154 |

视觉骨干：未校准 0.809–0.892，已校准 0.9996–1.0000。

### 3. 校准数据是低余弦的根因（证据）

`09_thresholds.log`：

```
未校准 : layers=59 values=40 distinct=2  min=0.731059 max=1   values==1.0: 38/40
已校准 : layers=60 values=40 distinct=21 min=0.34664  max=50  values==1.0: 4/40
```

校准集由 B3 自建：仓库冻结请求集 `challenge/hil/frozen/smoke_v0_snapshot` 的前 30 例，
经 `dump-tensors` 导出 4 个输入张量，再按 `cal_data_dir`（每个模型输入一个目录）组织。

### 4. X86 仿真耗时（**不可外推**）

| 路径 | 现象 |
|---|---|
| 浮点 ONNX（onnxruntime，原生） | mean 3.088 ms（n=30） |
| int8 `.bc`（X86 指令级仿真） | mean 228–318 ms（n=20–30） |
| `.hbm`（QEMU 周期级仿真） | 单次 19.4–33.6 s |

仿真比原生慢 74× 到数千倍，**任何来自 X86 的时延数字都不得写进 J6P 结论**。

## 限制（必须随数字一起引用）

- 权重为 A1 随机初始化结构，`gate_status = NOT_PROVIDED`；余弦值反映的是**工具链一致性**，
  不是模型精度；
- 校准集是自建的 30 例（真实 CARLA 帧 + B1 请求张量），不是 A3 的训练分布，量级可解释但不代表部署分布；
- 无 BPU 占用、DDR/ION、绑核调度、功耗、结温、板端延迟与 FPS；
- 板端专有约束（NV12 stride 64 对齐等）未验证；
- 容器重建后 `cmake` 与 X86 版 `hrt_model_exec` 需重装/重编。
