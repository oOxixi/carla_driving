# 第二组成员 B 交接（Qwen 模型与 GPU 部署，2026-08-03）

## 结论

按 7 月 30 日四人方案，本成员负责 B：Qwen 模型与 GPU 部署。当前已从 3B/Qwen3.5 路线转到 Qwen3-VL-2B + vLLM，并按要求先测官方 FP8、再测 GPTQ INT4。

本机 RTX 5070 8GB 的默认路线选 `h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4` + Marlin：热请求 P95 83.85 ms，10 条冻结目标关联代理集 10/10。官方 `Qwen/Qwen3-VL-2B-Instruct-FP8` 保留为基线：热请求 P95 76.97 ms，代理集 8/10。

这不是正式 A800 成绩，也不是官方隐藏集准确率。正式复现设备为 A800 80GB / CUDA 13.2，仍需在该设备复跑门禁和闭环计时。

## 已完成

- 建成严格 CUDA 13.2 环境：torch `2.12.1+cu132`、nvcc `13.2.78`、vLLM `0.26.1.dev0+g568afb3a1.d20260802` 源码构建。
- 官方 FP8 revision 固定为 `46485250d8854c0a9be4f1adbc67ca47e5bb6fa5`。
- GPTQ INT4 revision 固定为 `f91db2369bd00e7ec20bf09b6a0080cdb26aefa5`；日志确认 `auto_gptq` 和 `MarlinLinearKernel`。
- 视觉输入保持 256×256 / 64 预算；输出保持 A-E 单 Token、严格 Schema 与代码侧安全闭锁。
- 提示词只修复已复现的问题：普通车辆不等同停车风险；安全规则 > 明确语音动作 > 普通视觉线索。0.60 低置信度阈值未降低。
- 新增 `tools/run_qwen3vl_2b_vllm_cu132.sh`，默认 INT4，`QWEN_MODEL_VARIANT=fp8` 切官方 FP8；运行时、烟测和门禁默认 served model 也已切到 INT4。

## 证据

| 路线 | 热门禁（5 次预热 + 10 次测量） | 冻结代理集 |
|---|---|---|
| FP8 | mean 70.29，P95 76.97，max 80.98 ms | strict/target 100%，完整契约 80% |
| INT4/Marlin | mean 74.28，P95 83.85，max 84.19 ms | strict/target/完整契约均 100% |

证据文件：

- `artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_latency_gate.json`
- `artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_target10_prompt_v3.json`
- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate_prompt_v3.json`
- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_target10_prompt_v3.json`
- `artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_cu132_kernel_evidence.txt`

正确率集合含不同图片，INT4 第一个请求为 780.64 ms、该组 P95 481.41 ms；因此不能用重复热图门禁替代端到端成绩。这里只做了用户指定的早停门禁和 10 条代理集，没有补跑无关大测试。

## 复现与接入

最短启动命令、CUDA 13.2 环境和兼容内核原因见 `docs/QWEN_REMOTE_OPENAI_COMPATIBLE.md`。当前 INT4 服务在 WSL `127.0.0.1:8001` 健康；Windows 侧直接访问 WSL IP 受本机网络/代理路径影响，测试命令放在 WSL 内执行。

正式 A800 顺序固定：

1. 使用相同 revision 启动；先尝试 vLLM 默认内核，失败才回退 Triton/SDPA 兼容配置。
2. 只跑 5 次预热 + 10 次门禁；P95 > 300 ms 立即停。
3. 门禁通过后跑冻结正确率集合，再跑真实 CARLA 闭环端到端延迟。
4. 只有正确率与闭环延迟接近评分门槛，才运行 30 分钟稳定性测试。

## 未完成且不能代替的验收

- A800 80GB / CUDA 13.2 实机结果。
- 官方隐藏集 ≥98% 指标。
- 传感器输入至车辆动作的完整闭环 ≤150 ms 指标。
- 30 分钟稳定运行。
