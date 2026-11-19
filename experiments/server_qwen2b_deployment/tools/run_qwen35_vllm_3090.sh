#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VLLM_VERSION="0.26.0"
EXPECTED_CUDA_RUNTIME="13.0"
EXPECTED_MODEL_REVISION="15852e8c16360a2fea060d615a32b45270f8a8fc"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="${QWEN_ENV_PATH:-${ROOT}/.venv-qwen2b-cu130}"
MODEL_PATH="${QWEN_MODEL_PATH:-${ROOT}/models/Qwen3.5-2B}"
SERVED_MODEL_NAME="${QWEN_SERVED_MODEL_NAME:-Qwen/Qwen3.5-2B}"
HOST="${QWEN_HOST:-127.0.0.1}"
PORT="${QWEN_PORT:-8000}"
GPU_INDEX="${QWEN_GPU_INDEX:-0}"

if [[ ! -x "${ENV_PATH}/bin/python" || ! -x "${ENV_PATH}/bin/vllm" ]]; then
  echo "Independent Qwen 2B environment is incomplete: ${ENV_PATH}" >&2
  exit 2
fi
if [[ ! -d "${MODEL_PATH}" ]]; then
  echo "Qwen model directory not found: ${MODEL_PATH}" >&2
  exit 2
fi
revision_file="${MODEL_PATH}/.model_revision"
if [[ ! -f "${revision_file}" ]]; then
  echo "Missing model revision file: ${revision_file}" >&2
  exit 2
fi
actual_revision="$(tr -d '[:space:]' < "${revision_file}")"
if [[ "${actual_revision}" != "${EXPECTED_MODEL_REVISION}" ]]; then
  echo "Model revision mismatch: expected ${EXPECTED_MODEL_REVISION}, got ${actual_revision}" >&2
  exit 2
fi

export PATH="${ENV_PATH}/bin:${PATH}"
export CUDA_VISIBLE_DEVICES="${GPU_INDEX}"
# The host CUDA 12.3 nvcc/GCC combination cannot build FlashInfer JIT kernels.
# vLLM's native sampler avoids that optional JIT path without changing system libs.
export VLLM_USE_FLASHINFER_SAMPLER=0

EXPECTED_VLLM_VERSION="${EXPECTED_VLLM_VERSION}" \
EXPECTED_CUDA_RUNTIME="${EXPECTED_CUDA_RUNTIME}" \
python - <<'PY'
import os
import torch
import vllm

expected_vllm = os.environ["EXPECTED_VLLM_VERSION"]
expected_cuda = os.environ["EXPECTED_CUDA_RUNTIME"]
if vllm.__version__ != expected_vllm:
    raise SystemExit(f"vLLM mismatch: expected {expected_vllm}, got {vllm.__version__}")
if torch.version.cuda != expected_cuda:
    raise SystemExit(f"CUDA runtime mismatch: expected {expected_cuda}, got {torch.version.cuda}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available to torch")
if not torch.cuda.is_bf16_supported():
    raise SystemExit("GPU does not report BF16 support")
name = torch.cuda.get_device_name(0)
if "RTX 3090" not in name:
    raise SystemExit(f"This local profile requires RTX 3090; detected: {name}")
major, minor = torch.cuda.get_device_capability(0)
print(
    f"3090 preflight ready: gpu={name} cc={major}.{minor} "
    f"torch={torch.__version__} cuda_runtime={torch.version.cuda} "
    f"vllm={vllm.__version__}",
    flush=True,
)
PY

exec vllm serve "${MODEL_PATH}" \
  --served-model-name "${SERVED_MODEL_NAME}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --dtype bfloat16 \
  --max-model-len 2048 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.70 \
  --enable-prefix-caching \
  --limit-mm-per-prompt '{"image":1,"video":0}'
