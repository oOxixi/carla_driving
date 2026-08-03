#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv="${QWEN_VLLM_VENV:-${repo_root}/.venv-qwen3b-cu130}"
model_path="${QWEN_MODEL_PATH:-${repo_root}/models/Qwen2.5-VL-3B-Instruct}"
served_model="${QWEN_SERVED_MODEL_NAME:-Qwen/Qwen2.5-VL-3B-Instruct}"
expected_revision="66285546d2b821cf421d4f5eb2576359d3770cd3"
host="${QWEN_HOST:-127.0.0.1}"
port="${QWEN_PORT:-8002}"
gpu="${QWEN_GPU:-0}"

if [[ ! -x "${venv}/bin/python" || ! -x "${venv}/bin/vllm" ]]; then
  echo "independent 3B vLLM environment not found: ${venv}" >&2
  exit 2
fi
if [[ ! -f "${model_path}/config.json" ]]; then
  echo "Qwen2.5-VL-3B model not found: ${model_path}" >&2
  exit 2
fi

export CUDA_VISIBLE_DEVICES="${gpu}"
export VLLM_USE_FLASHINFER_SAMPLER=0

MODEL_PATH="${model_path}" EXPECTED_REVISION="${expected_revision}" \
"${venv}/bin/python" - <<'PY'
import json
import os
from pathlib import Path

import torch
import vllm

if torch.version.cuda != "13.0":
    raise SystemExit(f"torch CUDA runtime must be 13.0; got {torch.version.cuda}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available to torch")

model_path = Path(os.environ["MODEL_PATH"])
config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
if config.get("model_type") != "qwen2_5_vl":
    raise SystemExit(f"unexpected model_type: {config.get('model_type')!r}")
if config.get("quantization_config"):
    raise SystemExit("the formal 3090 3B profile must use unquantized BF16 weights")

metadata = model_path / ".cache/huggingface/download/config.json.metadata"
revision = metadata.read_text(encoding="utf-8").splitlines()[0].strip()
expected_revision = os.environ["EXPECTED_REVISION"]
if revision != expected_revision:
    raise SystemExit(
        f"model revision mismatch: expected {expected_revision}, got {revision}"
    )

print(
    "Qwen2.5-VL-3B preflight ready: "
    f"gpu={torch.cuda.get_device_name()} torch={torch.__version__} "
    f"cuda_runtime={torch.version.cuda} vllm={vllm.__version__} "
    f"revision={revision}",
    flush=True,
)
PY

if [[ "${QWEN_DRY_RUN:-0}" == "1" ]]; then
  echo "dry-run: model=${served_model} gpu=${gpu} host=${host} port=${port}"
  exit 0
fi

exec "${venv}/bin/vllm" serve "${model_path}" \
  --served-model-name "${served_model}" \
  --host "${host}" \
  --port "${port}" \
  --dtype bfloat16 \
  --max-model-len 2048 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.65 \
  --enable-prefix-caching \
  --enforce-eager
