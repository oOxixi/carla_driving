# Qwen 模型与 GPU 部署测试结果汇总

日期：2026-08-03
角色：7 月 30 日四人方案中的 B（Qwen 模型与 GPU 部署）

## 1. 最终结论

本地部署路线已从 `Qwen2.5-VL-3B-AWQ` 转向 Qwen3-VL-2B + vLLM，并按顺序完成：

1. 官方 `Qwen/Qwen3-VL-2B-Instruct-FP8`；
2. `h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4`，由 vLLM 实际启用 Marlin INT4 内核。

在 RTX 5070 8GB / CUDA 13.2 上，两条 2B 路线的预热后热请求都通过 P95≤300 ms 门禁。最终本机默认采用 INT4/Marlin：FP8 热请求略快，但 INT4 在当前 10 条冻结目标关联代理集上达到 10/10，且模型权重显存更低。

这些数据是本地代理结果，不是主办方隐藏集成绩，也不能代替 A800 80GB 上的完整闭环验收。

## 2. 固定测试环境

| 项目 | 配置 |
|---|---|
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU，8GB，compute capability 12.0 |
| 驱动 | 581.57 |
| 系统 | Windows + WSL2 Ubuntu-22.04 |
| CUDA runtime | 13.2 |
| nvcc | 13.2.78 |
| PyTorch | 2.12.1+cu132 |
| vLLM | 0.26.1.dev0+g568afb3a1.d20260802，针对 CUDA 13.2 源码构建 |
| 文本注意力 | `TRITON_ATTN` |
| 视觉注意力 | `TORCH_SDPA` |
| CUDA Graph | 关闭；本机驱动/WSL 组合下兼容性优先 |
| 视觉输入 | 固定 256×256 场景/目标拼图，预算 64 |
| 输出 | `A/B/C/D/E` 单 Token；严格 Schema 由代码组装 |
| 安全阈值 | 置信度 0.60，未为提高准确率而降低 |

正式复现设备是 A800 80GB / CUDA 13.2。A800 与 RTX 5070 的架构、显存和内核支持不同，必须在正式设备重新测量。

## 3. 延迟与正确率总表

### 3.1 旧 3B AWQ 路线

| 测试 | 样本 | READY / 完整契约 | mean | P95 | max | 结论 |
|---|---:|---:|---:|---:|---:|---|
| 单次基线烟测 | 1 | 1/1 | 2616.59 ms | — | 2616.59 ms | 延迟直接失败 |
| 目标关联子集，原环境 | 10 | 10/10，100% | 1367.22 ms | 1873.20 ms | 2301.53 ms | 正确但远超门槛 |
| 目标关联子集，CUDA 13.2/Triton | 10 | 10/10，100% | 1411.52 ms | 2389.49 ms | 3205.64 ms | CUDA 13.2 未降低延迟 |
| 冻结代理全集 | 320 | 271/320，84.69% | 1379.73 ms | 1501.26 ms | 2350.25 ms | 49 条目标缺失边界错误 |

结论：3B 路线满足部分小集合正确性，但 P95 约 1.5–2.4 秒，按早停规则淘汰。

### 3.2 官方 Qwen3-VL-2B FP8

模型 revision：`46485250d8854c0a9be4f1adbc67ca47e5bb6fa5`。模型权重占用约 2.93 GiB GPU 显存。

| 测试 | strict parse | action / 完整契约 | target association | mean | P95 | max |
|---|---:|---:|---:|---:|---:|---:|
| 热请求门禁，5 次预热 + 10 次测量 | — | — | — | 70.29 ms | 76.97 ms | 80.98 ms |
| 初始提示词，10 条不同请求 | 100% | 60% | 100% | 162.13 ms | 535.96 ms | 887.55 ms |
| 提示词 v2 | 100% | 60% | 100% | 96.15 ms | 236.53 ms | 365.47 ms |
| 提示词 v3 | 100% | 80% | 100% | 111.51 ms | 282.76 ms | 332.20 ms |

提示词 v3 修复了普通车辆被误认为停车风险的主要问题，但 seed03 的两条请求仍输出 STOP，因此最终为 8/10。没有降低安全置信度阈值来掩盖该错误。

### 3.3 Qwen3-VL-2B GPTQ INT4 + Marlin

模型 revision：`f91db2369bd00e7ec20bf09b6a0080cdb26aefa5`。量化配置为 GPTQ 4-bit、group size 128；模型权重占用约 2.29 GiB GPU 显存。启动日志确认：

```text
quantization=auto_gptq
Using MarlinLinearKernel for AutoGPTQLinearMethod
```

| 测试 | strict parse | action / 完整契约 | target association | mean | P95 | max |
|---|---:|---:|---:|---:|---:|---:|
| 初始热请求门禁 | — | — | — | 71.80 ms | 82.82 ms | 85.06 ms |
| 初始提示词，10 条不同请求 | 100% | 50% | 100% | 104.66 ms | 202.10 ms | 277.41 ms |
| 提示词 v3，10 条不同请求 | 100% | 100% | 100% | 150.33 ms | 481.41 ms | 780.64 ms |
| 提示词 v3 最终热请求门禁 | — | — | — | 74.28 ms | 83.85 ms | 84.19 ms |

初始 INT4 原始分类多数正确，但部分置信度低于 0.60，安全闭锁后记为 STOP。提示词 v3 明确了“安全规则 > 明确语音动作 > 普通视觉线索”以及“普通车辆本身不是停车风险”，在不降低阈值的情况下达到 10/10。

不同图片集合首条请求为 780.64 ms，说明图像变化带来的编译/缓存成本仍需处理。最终热门禁只证明模型常驻、固定输入形态下的服务延迟，不等于传感器到车辆动作的完整闭环延迟。

## 4. 最终选择依据

| 项目 | FP8 | INT4/Marlin |
|---|---:|---:|
| 热请求 P95 | **76.97 ms** | 83.85 ms |
| 10 条代理集完整契约 | 80% | **100%** |
| 目标关联准确率 | 100% | 100% |
| 模型权重显存 | 约 2.93 GiB | **约 2.29 GiB** |
| 发布方 | Qwen 官方 | h2oai 第三方量化 |

本机默认选 INT4/Marlin，原因是当前代理集完整契约更高、显存更低，而热请求 P95 仍明显低于 300 ms。FP8 保留为官方权重基线和正式设备对照路线。

## 5. 已实施优化

- 模型只生成 A-E 单 Token，不生成完整 JSON。
- vLLM 请求固定 `structured_outputs.choice`、`max_tokens=1`、`temperature=0`、`logprobs=true`、non-thinking。
- 视觉输入固定为 256×256 场景/目标拼图，预算固定为 64。
- 速度、目标 ID、严格 Schema 与安全覆盖继续由确定性代码处理。
- 保留红灯、TTC≤2 秒、碰撞风险和低置信度 fail-closed。
- 提示词只针对已复现误判压缩和调整优先级，没有增加冗余推理步骤。
- 严格 CUDA 13.2 环境中，本机采用 Triton/SDPA 兼容内核；INT4 线性层采用 Marlin。

## 6. 最短复现

在 WSL 仓库目录启动默认 INT4：

```bash
bash tools/run_qwen3vl_2b_vllm_cu132.sh
```

切换官方 FP8：

```bash
QWEN_MODEL_VARIANT=fp8 bash tools/run_qwen3vl_2b_vllm_cu132.sh
```

仅做环境、revision 和量化格式预检：

```bash
QWEN_DRY_RUN=1 bash tools/run_qwen3vl_2b_vllm_cu132.sh
```

服务 READY 后先执行延迟门禁：

```bash
python -m tools.run_qwen_latency_gate \
  --base-url http://127.0.0.1:8001/v1 \
  --image artifacts/qwen_target_assoc_0728/collection/images/town03opt_target_seed_00.png \
  --output artifacts/B_role_validation/qwen3vl_2b_latency_gate.json
```

只有 P95≤300 ms 才运行正确率集合。

## 7. 证据索引

3B：

- `artifacts/B_role_validation/local_3b_awq_0803_baseline_smoke.json`
- `artifacts/B_role_validation/qwen25_3b_awq_0803_target10_baseline.json`
- `artifacts/B_role_validation/qwen25_3b_awq_0803_target10_cuda132_triton.json`
- `artifacts/B_role_validation/qwen25_3b_awq_0803_frozen320_baseline.json`

FP8：

- `artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_latency_gate.json`
- `artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_target10.json`
- `artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_target10_prompt_v2.json`
- `artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_target10_prompt_v3.json`

INT4/Marlin：

- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate.json`
- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate_prompt_v3.json`
- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_target10.json`
- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_target10_prompt_v3.json`
- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_cu132_kernel_evidence.txt`

## 8. 尚未完成的正式验收

- A800 80GB / CUDA 13.2 实机门禁。
- 主办方隐藏集 ≥98% 指标。
- 传感器接收完成到车辆动作的完整闭环 ≤150 ms 指标。
- 达到前述门槛后的 30 分钟稳定性测试。

在正式 A800 上应先跑 5+10 门禁；若 P95>300 ms 立即停止，不运行正确率和稳定性大测试。

提交前仓库全量验证：`438 passed, 1 skipped`；双模型启动脚本的 CUDA 13.2 dry-run 预检均通过。
