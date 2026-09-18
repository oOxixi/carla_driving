# B3 X86 预验证证据（2026-09-18）

本目录是 B3 的策展证据。**全部为 `X86 PRE-VALIDATED`，不是 J6P 实机结果，
也不构成任何性能或精度达标结论。**

权重是随机初始化的（`torch.manual_seed=20260911`），因此行为对比没有精度含义；
本批数据只用于证明测量工具链正确、并在真实产物上建立可比较的基线。

## 内容

| 目录/文件 | 是什么 | 关键结论 |
|---|---|---|
| `b3-20260918T100755Z-35051d77/` | 100 例 × 3 轮的主测量运行 | 见下表 |
| `b3-soak-20260918T100812Z-50ebf75e/` | 15 秒长稳 | 899 次请求、成功率 100%、内存漂移 626 KiB |
| `artifact_report.json` | 产物独立校验 | opset 17、11 个算子、无动态 shape/控制流算子、契约一致 |

## 被测对象与输入

| 项 | 值 |
|---|---|
| 产物 | `challenge/student_v0_fp32.onnx` |
| 产物 SHA256 | `ffb1ed5e9b23aa7100343bb4f02c8cfef3da5049e9c5eba4c0e66247c96ee243` |
| 模型身份（权重指纹） | `b4493f3fdb00f6673520bebd64f7915b37f5ecdc9d65737226046b12d74d434f` |
| `config_id` | `student-v0-r3-structure-20260911` |
| 代码版本 | `64577ea046ced0fef3a177f39d88280a82f45253` |
| 输入快照 | `challenge/hil/frozen/d2_v1_1_val`（B1 D2 v1.1 的 val 划分，539 例） |
| 快照 digest | `003f0ed8e279fef8ac10b77844a73e8e1a5ad5a70e85d80af82435468641eb4d` |
| 本批实际回放 | 快照前 100 例（确定性顺序）× 3 轮 = 300 次 |

### 关于两个 `git_sha`

本目录下两个 run 的 `git_sha` 不同，这是**正确的**，不是数据错误：

| run | 链 | `git_sha` | 来源 |
|---|---|---|---|
| `b3-20260918T100755Z-35051d77`（主测量） | in-process torch | `64577ea046c…` | 运行时的仓库 HEAD |
| `b3-soak-20260918T100812Z-50ebf75e`（长稳） | ONNX Runtime | `f8e567ef8c…` | **ONNX 产物元数据**里的 `source_git_sha`，即该产物**导出时**所在的提交 |

两条链各自记录自己权威的身份：torch 链测的是当前代码，ONNX 链测的是那个已固化的产物。
把 ONNX 链的 SHA 写成"当前代码版本"才是错的。

## 测量环境

| 字段 | 值 |
|---|---|
| 电源 | `AC` |
| 测量开始时的系统负载 | 5.8% |
| **CPU 标定值** | **11.84 ms**（进程内，多线程矩阵乘重复取最小） |
| Teacher 基线 | v1 与 v4 双 pin 均已记录，模型身份一致（`Qwen/Qwen3.5-2B` @ `15852e8c1636`） |
| torch | 2.6.0+cpu |
| onnxruntime | 1.27.0 |
| 时钟 | `perf_counter_ns`，分辨率 100 ns |

### 关于 CPU 标定值

标定是固定的多线程矩阵乘（512×512 ×5，重复 3 次取**最小值**），用来判断两次运行是否
可比。本机实测到的漂移幅度很大：

| 会话 | 标定方法 | 标定值 | 同批 ONNX 推理 P50 |
|---|---|---:|---:|
| 09-16 上午 | 单次采样 | 7.23 ms | 2.96 ms |
| 09-18 首次 | 单次采样 | 14.06 ms | 2.84 ms |
| 09-18 最终 | 重复取最小（进程内） | 11.84 ms | 2.96 ms |
| 09-18 最终 | 重复取最小（独立进程） | 3.9–7.8 ms | — |

两点必须一起看：

1. **单次采样不可靠**：同一台机器上曾在 7.2–18.7 ms 之间跳动，因此改为"重复取最小"。
   即使如此，进程内采样（已加载 torch）仍系统性高于独立进程，所以**只与同样被测方式
   的运行比较**。
2. **持续负载会导致上浮**：09-16 那批只跑了 30 次请求（E2E P50 13.26 ms），本批跑了
   300 次（E2E P50 18.25 ms），即便标定值同量级，长跑的散热效应也会抬高延迟。
   跨批次比较前请同时看标定值、标定方法与总请求数。

## 主测量运行的关键数字

in-process torch 链，100 例 × 3 轮（300 个有效样本），单位 ms：

| 时段 | P50 | P95 | max |
|---|---:|---:|---:|
| 预处理 | 7.88 | 18.99 | 23.34 |
| Token/Target packing | 0.52 | 1.80 | 2.09 |
| 模型纯推理 | 8.10 | 12.89 | 14.70 |
| 后处理 | 0.08 | 0.12 | 0.26 |
| Student Adapter | 0.48 | 0.98 | 1.52 |
| 计划校验 | 0.84 | 1.94 | 3.05 |
| **完整 Planner E2E** | **18.25** | **35.43** | **40.98** |

独立 ONNX 模型压测（CPU EP，batch=1，warmup=5）：P50 2.96 ms。

## 一致性验证

| 验证 | 结果 |
|---|---|
| torch ↔ ONNX 逐输出 | 10 个输出张量最大绝对差 `7.62939453125e-06`（rtol=1e-4） |
| 打点路径 ↔ `StudentBackend.infer` | `PASS`（逐字节相同） |
| 回放结构检查 | 300 例全部产出计划且结构合法 |
| 异常输入用例 | 10 例，**10 例全部符合预期** |

## 已知限制

1. 权重随机初始化 → 无精度含义；`handoff` 因此产出 0 条可训练样本；
2. 功耗与 BPU 利用率记为 `NOT_APPLICABLE`（本机无探针，未用估算值填充）；
3. 长稳仅 15 秒冒烟，正式要求 30 分钟；
4. 输入是 B1 D2 v1.1 的 **val** 划分；`reserved_test_candidates` 是 B2 的冻结基准，
   B3 不自动使用它；
5. A4 的 `challenge/runtime/student_x86.py` 目前不满足 B3 的运行时契约
   （见 `challenge/hil/a4_runtime_gap_report.md`），所以本批测量用的是 B3 自己的
   ONNX/in-process 适配器，不是 A4 的运行时入口。

## 与上一批证据的关系

`x86_prevalidation_20260916` 那一批是在**旧 ONNX 产物**（`36c4b6b3…`）上测的。
A4 的 `A4: add X86 ONNX runtime smoke validation` 提交重新导出了产物
（现为 `ffb1ed5e…`），因此那一批已移出仓库，仅作历史参考。

## 复算方式

```powershell
py -3.12 -m challenge.hil.cli run `
  --repo . --adapter both --rounds 3 --warmup 3 --limit 100 `
  --frozen challenge/hil/frozen/d2_v1_1_val `
  --out  challenge/hil/evidence/x86_prevalidation_20260918 `
  --verify-consistency --verify-backend-consistency
```

复算前确认：电源为 AC、系统空闲、`hardware_env.json.cpu_calibration_ms` 与本批同量级
（约 8 ms），并注意本批是 300 次请求的持续负载。
