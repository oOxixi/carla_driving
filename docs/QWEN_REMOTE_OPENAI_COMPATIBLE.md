# Qwen3-VL-2B / vLLM / CUDA 13.2 路线

当前默认模型为 `h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4`；`Qwen/Qwen3-VL-2B-Instruct-FP8` 作为官方权重基线。模型只输出受约束的 `A/B/C/D/E` 单代码，速度、目标 ID、确认状态、安全覆盖和最终严格 Schema 均由仓库代码确定性组装。

## 本机固定环境

```text
GPU: NVIDIA GeForce RTX 5070 Laptop GPU 8GB / compute capability 12.0
Driver: 581.57
WSL: Ubuntu-22.04
torch: 2.12.1+cu132
CUDA runtime / nvcc: 13.2 / 13.2.78
vLLM: 0.26.1.dev0+g568afb3a1.d20260802（CUDA 13.2 源码编译）
```

模型 revision 固定为：

- FP8：`46485250d8854c0a9be4f1adbc67ca47e5bb6fa5`
- GPTQ INT4：`f91db2369bd00e7ec20bf09b6a0080cdb26aefa5`

INT4 不是 Qwen 官方发布仓库；启动日志必须出现 `quantization=auto_gptq` 和 `Using MarlinLinearKernel`，否则不把结果记作 INT4/Marlin。

## 最短启动命令

以下命令在 WSL 仓库目录运行，默认启动 INT4：

```bash
bash tools/run_qwen3vl_2b_vllm_cu132.sh
```

切换官方 FP8：

```bash
QWEN_MODEL_VARIANT=fp8 bash tools/run_qwen3vl_2b_vllm_cu132.sh
```

脚本固定 CUDA 13.2、模型 revision、量化格式和当前可工作的内核组合；`QWEN_DRY_RUN=1` 只执行预检。新机器可通过 `QWEN_VLLM_VENV`、`QWEN_MODEL_PATH` 覆盖路径，不跳过校验。

本机 CUDA 13.2 下，FlashAttention2 的旧 PTX 无法由当前驱动 JIT，FlashInfer 文本内核也出现 `invalid resource handle`；因此使用已实测可工作的 Triton/SDPA 并关闭 CUDA Graph。该限制不能直接外推到 A800，正式设备应先尝试 vLLM 默认内核，失败时再使用上述兼容配置。

## 延迟早停

模型 READY 后严格先跑 5 次预热、10 次测量：

```bash
python -m tools.run_qwen_latency_gate \
  --base-url http://127.0.0.1:8001/v1 \
  --image artifacts/qwen_target_assoc_0728/collection/images/town03opt_target_seed_00.png \
  --output artifacts/B_role_validation/qwen3vl_2b_latency_gate.json
```

- `P95 <= 300 ms`：退出码 0，才运行正确率集合。
- `P95 > 300 ms`：退出码 2，立即停止该模型路线。
- 门禁测的是预热后的模型服务请求，不等同于 CARLA 完整闭环端到端延迟。

## 已测结果

| 模型 | 权重显存 | 热请求 mean / P95 / max | 10 条冻结代理集 | 结论 |
|---|---:|---:|---:|---|
| 官方 FP8 | 约 2.93 GiB | 70.29 / 76.97 / 80.98 ms | 8/10 | 官方基线 |
| GPTQ INT4 + Marlin | 约 2.29 GiB | 74.28 / 83.85 / 84.19 ms | 10/10 | 当前本机默认 |

代理集只覆盖 10 条 CARLA 跟随/避让目标关联样例，不代表官方隐藏集准确率。正确率集合切换图片时首次请求存在额外编译/缓存成本；INT4 该组 P95 为 481.41 ms，因此完整闭环仍需在正式 A800 上单独计时。

## 请求边界

- 256×256 场景/目标关注拼图，视觉预算固定为 64；
- `structured_outputs.choice=[A,B,C,D,E]`；
- `max_tokens=1`、`temperature=0`、`logprobs=true`、`enable_thinking=false`；
- 安全规则优先于明确语音动作，明确语音动作优先于普通视觉线索；
- 超时、低置信度、视觉无效、目标歧义或非法响应均 fail-closed；不降低 0.60 安全置信度阈值。

CARLA 使用 `--qwen-remote` 接入；默认 served model 已改为 INT4，使用 FP8 时显式设置 `QWEN_MODEL=Qwen/Qwen3-VL-2B-Instruct-FP8`。
