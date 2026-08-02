#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VLLM_VERSION="0.26.0"
EXPECTED_MODEL_REVISION="15852e8c16360a2fea060d615a32b45270f8a8fc"
MODEL_PATH="${QWEN_MODEL_PATH:-models/Qwen3.5-2B}"
SERVED_MODEL_NAME="${QWEN_SERVED_MODEL_NAME:-Qwen/Qwen3.5-2B}"
HOST="${QWEN_HOST:-127.0.0.1}"
PORT="${QWEN_PORT:-8000}"
REQUIRE_A800="${QWEN_REQUIRE_A800:-1}"

if [[ ! -d "${MODEL_PATH}" ]]; then
  echo "Qwen model directory not found: ${MODEL_PATH}" >&2
  exit 2
fi

revision_file="${MODEL_PATH}/.model_revision"
if [[ ! -f "${revision_file}" ]]; then
  echo "Missing ${revision_file}; download the pinned model revision first." >&2
  exit 2
fi
actual_revision="$(tr -d '[:space:]' < "${revision_file}")"
if [[ "${actual_revision}" != "${EXPECTED_MODEL_REVISION}" ]]; then
  echo "Model revision mismatch: expected ${EXPECTED_MODEL_REVISION}, got ${actual_revision}" >&2
  exit 2
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi is required" >&2
  exit 2
fi
gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 | tr -d '\r')"
if [[ "${REQUIRE_A800}" == "1" && "${gpu_name}" != *A800* ]]; then
  echo "Official evidence requires A800; detected: ${gpu_name}" >&2
  exit 3
fi

EXPECTED_VLLM_VERSION="${EXPECTED_VLLM_VERSION}" python - <<'PY'
import os
import torch
import vllm

expected = os.environ["EXPECTED_VLLM_VERSION"]
if vllm.__version__ != expected:
    raise SystemExit(f"vLLM version mismatch: expected {expected}, got {vllm.__version__}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available to torch")
if not torch.cuda.is_bf16_supported():
    raise SystemExit("GPU does not report BF16 support")
major, minor = torch.cuda.get_device_capability()
print(
    "A800 preflight ready: "
    f"gpu={torch.cuda.get_device_name()} cc={major}.{minor} "
    f"torch={torch.__version__} cuda_runtime={torch.version.cuda} "
    f"vllm={vllm.__version__}",
    flush=True,
)
PY

echo "Starting ${SERVED_MODEL_NAME} revision=${EXPECTED_MODEL_REVISION} on ${gpu_name}" >&2
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
