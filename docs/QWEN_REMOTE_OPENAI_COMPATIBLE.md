# Qwen3.5-2B / vLLM A800 主线

正式复现使用 `Qwen/Qwen3.5-2B` BF16，不使用 A800 上非原生 W8A8 的 FP8 作为默认路线。模型只生成一个 `A/B/C/D/E` 代码；速度、目标 ID、确认状态、安全覆盖和最终严格 Schema 均由仓库代码组装。

## 固定环境和模型

Linux/A800 环境安装：

```bash
uv pip install -r requirements-qwen-vllm.txt --torch-backend=auto
hf download Qwen/Qwen3.5-2B \
  --revision 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --local-dir models/Qwen3.5-2B
printf '%s\n' 15852e8c16360a2fea060d615a32b45270f8a8fc \
  > models/Qwen3.5-2B/.model_revision
```

启动脚本默认拒绝非 A800、错误模型 revision、非 vLLM 0.26.0 或不支持 BF16 的环境：

```bash
QWEN_MODEL_PATH=models/Qwen3.5-2B \
  bash tools/run_qwen35_vllm_a800.sh
```

服务地址为 `http://127.0.0.1:8000/v1`，served model 为 `Qwen/Qwen3.5-2B`。配置固定 BF16、单卡、`max_model_len=2048`、`max_num_seqs=1` 和 prefix cache。

## 延迟早停

模型常驻后，只运行 5 次预热和 10 次测量：

```bash
python -m tools.run_qwen_latency_gate \
  --image artifacts/runtime/qwen_test.jpg \
  --output artifacts/B_role_validation/qwen35_a800_latency_gate.json
```

- `p95 <= 300 ms`：退出码 0，才允许继续跑冻结正确率集合。
- `p95 > 300 ms`：退出码 2，报告状态 `EARLY_STOP`，停止正确率测试。
- 报告明确标记为 `latency_gate_only_no_correctness`，不会自动触发其他测试。

## CARLA 接入

```bash
python -m integration.carla_runner \
  --scenario-file scenarios/smoke/S01_set_speed_20.json \
  --perception-mode sensors --scenario-facts-mode perception \
  --qwen-remote --realtime
```

远端请求固定为：

- 256×256 场景/目标关注拼图，对应 Qwen3.5 的 64 个合并视觉 Token；
- `structured_outputs.choice=[A,B,C,D,E]`；
- `max_tokens=1`、`temperature=0`、`logprobs=true`；
- `enable_thinking=false`。

等待、超时、低置信度、视觉无效、目标歧义或非法响应均 fail-closed。旧的 `qwen_service` Transformers/3B-AWQ 服务只保留用于复查历史证据，不是 A800 正式主线。
