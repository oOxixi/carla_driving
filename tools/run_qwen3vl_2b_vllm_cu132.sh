#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
variant="${QWEN_MODEL_VARIANT:-int4}"
venv="${QWEN_VLLM_VENV:-/home/restar/.venvs/carla_qwen3_vllm_cu132}"
quant_args=()
graph_args=(-cc.cudagraph_mode=NONE)

case "${variant}" in
  int4)
    default_model_path="${repo_root}/models/Qwen3-VL-2B-Instruct-GPTQ-Int4"
    served_model="h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4"
    expected_revision="f91db2369bd00e7ec20bf09b6a0080cdb26aefa5"
    expected_quant="gptq"
    ;;
  fp8)
    default_model_path="${repo_root}/models/Qwen3-VL-2B-Instruct-FP8"
    served_model="Qwen/Qwen3-VL-2B-Instruct-FP8"
    expected_revision="46485250d8854c0a9be4f1adbc67ca47e5bb6fa5"
    expected_quant="fp8"
    ;;
  qwen25vl-7b-awq)
    default_model_path="${repo_root}/release_assets/weights/optional/qwen25vl-7b-awq"
    served_model="Qwen/Qwen2.5-VL-7B-Instruct-AWQ"
    expected_revision="536a35794df8831aa814970ee8f89eff577e7718"
    expected_quant="awq"
    quant_args=(--quantization awq_marlin)
    graph_args=()
    ;;
  *)
    echo "QWEN_MODEL_VARIANT must be int4, fp8, or qwen25vl-7b-awq; got: ${variant}" >&2
    exit 2
    ;;
esac

model_path="${QWEN_MODEL_PATH:-${default_model_path}}"
served_model="${QWEN_SERVED_MODEL_NAME:-${served_model}}"
host="${QWEN_HOST:-0.0.0.0}"
port="${QWEN_PORT:-8001}"

if [[ ! -x "${venv}/bin/python" || ! -x "${venv}/bin/vllm" ]]; then
  echo "CUDA 13.2 vLLM environment not found: ${venv}" >&2
  exit 2
fi
if [[ ! -f "${model_path}/config.json" ]]; then
  echo "Qwen model not found: ${model_path}" >&2
  exit 2
fi

export CUDA_HOME="${QWEN_CUDA_HOME:-${venv}/lib/python3.10/site-packages/nvidia/cu13}"
export PATH="${CUDA_HOME}/bin:${venv}/bin:${PATH}"
export VLLM_USE_V2_MODEL_RUNNER=0
export CUDNN_FRONTEND_CUDART_LIB_NAME=libcudart.so.13

MODEL_PATH="${model_path}" EXPECTED_QUANT="${expected_quant}" \
EXPECTED_REVISION="${expected_revision}" "${venv}/bin/python" - <<'PY'
import json
import os
from pathlib import Path

import torch
import vllm

if torch.version.cuda != "13.2":
    raise SystemExit(f"torch CUDA runtime must be 13.2; got {torch.version.cuda}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available to torch")

model_path = Path(os.environ["MODEL_PATH"])
config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
quant = config.get("quantization_config") or {}
actual_quant = str(quant.get("quant_method", "")).lower()
expected_quant = os.environ["EXPECTED_QUANT"]
if actual_quant != expected_quant:
    raise SystemExit(
        f"quantization mismatch: expected {expected_quant}, got {actual_quant or 'none'}"
    )

revision = os.environ.get("QWEN_MODEL_REVISION", "").strip()
revision_file = model_path / "REVISION"
if not revision and revision_file.is_file():
    revision = revision_file.read_text(encoding="utf-8").strip()
metadata = model_path / ".cache/huggingface/download/config.json.metadata"
if not revision and metadata.is_file():
    revision = metadata.read_text(encoding="utf-8").splitlines()[0].strip()
expected_revision = os.environ["EXPECTED_REVISION"]
if revision != expected_revision:
    raise SystemExit(
        f"model revision mismatch: expected {expected_revision}, got {revision or 'unknown'}"
    )

print(
    "Qwen VL preflight ready: "
    f"gpu={torch.cuda.get_device_name()} torch={torch.__version__} "
    f"cuda_runtime={torch.version.cuda} vllm={vllm.__version__} "
    f"quant={actual_quant} revision={revision}",
    flush=True,
)
PY

if [[ "${QWEN_DRY_RUN:-0}" == "1" ]]; then
  echo "dry-run: variant=${variant} model=${served_model} host=${host} port=${port}"
  exit 0
fi

exec "${venv}/bin/vllm" serve "${model_path}" \
  --served-model-name "${served_model}" \
  "${quant_args[@]}" \
  --host "${host}" \
  --port "${port}" \
  --dtype auto \
  --max-model-len 2048 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.70 \
  --enable-prefix-caching \
  --attention-backend TRITON_ATTN \
  --mm-encoder-attn-backend TORCH_SDPA \
  "${graph_args[@]}"
