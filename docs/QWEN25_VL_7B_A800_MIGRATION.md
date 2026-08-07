# Qwen2.5-VL 7B A800 迁移方案

## 结论

7B 迁移模型固定为官方 `Qwen/Qwen2.5-VL-7B-Instruct-AWQ`，revision `536a35794df8831aa814970ee8f89eff577e7718`。A800 使用现有 CUDA 13.2 + vLLM 环境，强制 `awq_marlin`、单并发、64 个视觉 token 和现有严格动作 Schema。2B INT4 仍是默认路线；7B 只在 A800 上作为质量提升候选，不在 8 GB RTX 5070 上下载或测试。

## 一次性准备

```bash
bash weights/download_optional_models.sh qwen25vl-7b-awq
```

下载目录固定为 `release_assets/weights/optional/qwen25vl-7b-awq`，脚本同时写入固定 revision。不要使用 `main`、缓存软链接或运行时联网下载。

## A800 启动

```bash
export QWEN_VLLM_VENV=/path/to/carla_qwen_vllm_cu132
export QWEN_MODEL_PATH=$PWD/release_assets/weights/optional/qwen25vl-7b-awq
export QWEN_MODEL_REVISION=536a35794df8831aa814970ee8f89eff577e7718
bash tools/run_qwen25vl_7b_awq_vllm_cu132.sh
```

这是独立 A800 手工迁移入口，不会改变当前 `run.sh` 的默认 2B Docker 路线。启动前置检查会拒绝非 CUDA 13.2、错误 revision、非 AWQ 权重或缺失模型。vLLM 服务名固定为官方模型 ID，端口默认 `8001`；7B 优化入口保留 CUDA Graph。

服务健康后、计时前必须校验运行时内核：

```bash
python tools/verify_qwen7b_awq_kernel.py \
  --log output/qwen25vl-7b-awq-vllm.log
```

日志必须同时证明 `awq_marlin` 和 `MarlinLinearKernel`；未通过时停止，不接受普通 AWQ 内核替代结果。

## 最小验收顺序

1. 只做服务健康检查和 1 次 Schema smoke。
2. 固定 64 个视觉 token，做 5 次预热和 10 次计时。
3. 全链 P95 `>300 ms`：立即停止 7B，不跑准确率和 CARLA 场景。
4. 全链 P95 `<=300 ms`：再跑冻结正确率集合；目标仍是正式 P95 `<=150 ms`。
5. 接近正式延迟线后才跑 CARLA 场景和 30 分钟稳定性。

先执行独立延迟门禁；它固定 5 次预热和 10 次计时，退出码非零时到此停止：

```bash
python -m tools.run_qwen_latency_gate \
  --base-url http://127.0.0.1:8001/v1 \
  --profile qwen25vl-7b-awq \
  --dynamic-frames-dir release_assets/package/datasets/frozen_validation/multimodal/images \
  --threshold-ms 300 --timeout-s 5 \
  --output output/qwen25vl-7b-awq-a800-latency.json
```

延迟门禁通过后才调用完整评测入口：

```bash
python -m tools.run_four_modal_full_chain \
  --qwen-base-url http://127.0.0.1:8001/v1 \
  --profile qwen25vl-7b-awq \
  --asr-manifest release_assets/package/datasets/frozen_validation/asr/manifest.json \
  --multimodal-cases release_assets/package/datasets/frozen_validation/multimodal/cases.jsonl \
  --latency-manifest release_assets/package/datasets/frozen_validation/full_chain_latency_v1.json \
  --warmup 5 --measured 10 --hardware-label A800 \
  --output output/qwen25vl-7b-awq-a800.json
```

## 迁移记录要求

只记录真实 A800 结果：GPU 型号、CUDA 13.2、vLLM wheel revision、模型 revision、量化内核、视觉 token、预热/计时次数、P50/P95/max、准确率和原始日志。迁移前状态统一写 `NOT_RUN`，不得由 2B 或 RTX 5070 数据推算。

官方依据：[Qwen2.5-VL-7B-Instruct-AWQ 模型页](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct-AWQ)、[vLLM 量化硬件支持](https://docs.vllm.ai/en/latest/features/quantization/)。
