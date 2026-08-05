#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export QWEN_MODEL_VARIANT=qwen25vl-7b-awq
log_path="${QWEN_VLLM_LOG:-$repo_root/output/qwen25vl-7b-awq-vllm.log}"
mkdir -p "$(dirname "$log_path")"
"$repo_root/tools/run_qwen3vl_2b_vllm_cu132.sh" "$@" 2>&1 | tee "$log_path"
exit "${PIPESTATUS[0]}"
