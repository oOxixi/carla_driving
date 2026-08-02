# Qwen 常驻推理服务

> 定位：这是旧 Transformers/AWQ 兼容服务，用于复查既有 3B/7B 证据。A800 正式主线已经切换到 `Qwen3.5-2B BF16 + vLLM`，启动和早停步骤见 `docs/QWEN_REMOTE_OPENAI_COMPATIBLE.md`。不要把本服务的 RTX 5070 延迟写成正式复现成绩。

该服务复用仓库现有严格高层动作边界，提供 `/health`、`/infer`、`/metrics`。GPU 推理槽有界；请求超时、并发已满、模型错误和非法输出均返回明确错误码，不会进入车辆控制。

## 旧服务启动（兼容性复查）

先安装与 CUDA 匹配的 `torch`/`torchvision`，再安装普通依赖。不要从普通 PyPI 单独升级 `torchvision`，否则可能把 CUDA 版 torch 替换成 CPU 版。

```powershell
conda run -n carla python -m pip install -r requirements-qwen.txt
conda run -n carla python -m qwen_service `
  --model-path models/Qwen2.5-VL-3B-Instruct-AWQ `
  --image-root artifacts/runtime/qwen_live `
  --host 127.0.0.1 --port 18000 `
  --max-concurrency 1 --timeout-s 5 `
  --max-new-tokens 48 --awq-backend gemm_triton
```

AWQ 额外使用 `requirements-qwen-awq.txt`，当前在 Linux/WSL2 GPU 环境部署。RTX 50 系若系统 NVCC 不能编译 `compute_120`，优先使用无需该 Marlin JIT 的 `gemm_triton`；Triton 不可用时再退回较慢的 `torch_awq`。服务启动前完成模型加载，因此 `/health` 返回 `READY` 时模型已常驻。

## CARLA 接入

服务与 runner 在同机运行，并共享相同的 `artifacts/runtime/qwen_live` 图像目录：

```powershell
conda run -n carla python -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --scenario-file scenarios/smoke/S01_set_speed_20.json `
  --perception-mode sensors --scenario-facts-mode perception `
  --qwen-service-url http://127.0.0.1:18000 `
  --realtime
```

三个接口均返回 JSON：

- `GET /health`：模型名、状态、最大并发和在途请求数。
- `POST /infer`：接收 `QwenInputContext`，返回严格校验后的高层 `decision`。
- `GET /metrics`：请求计数、mean/P95/P99/max、吞吐、在途请求和 GPU 显存。

错误码为 `INVALID_REQUEST`、`BUSY`、`TIMEOUT`、`MODEL_ERROR`。超时后的后台 GPU 任务真正结束前不会释放并发槽，防止请求继续堆积。
