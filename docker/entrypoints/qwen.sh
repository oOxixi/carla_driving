#!/usr/bin/env bash
set -euo pipefail

readonly REQUIRED_PROFILE="qwen3vl-2b-int4"
readonly REQUIRED_MODEL="h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4"
readonly QWEN_PROFILE="${QWEN_PROFILE:-$REQUIRED_PROFILE}"
readonly QWEN_SERVED_MODEL="${QWEN_SERVED_MODEL:-$REQUIRED_PROFILE}"

if [[ "$QWEN_PROFILE" != "$REQUIRED_PROFILE" ]]; then
  echo "unsupported QWEN_PROFILE: $QWEN_PROFILE" >&2
  exit 2
fi
if [[ "$QWEN_SERVED_MODEL" != "$REQUIRED_PROFILE" ]]; then
  echo "QWEN_SERVED_MODEL must remain $REQUIRED_PROFILE" >&2
  exit 2
fi

python3 /app/tools/verify_model_manifest.py \
  --manifest /models/model_manifest.json \
  --profile "$REQUIRED_PROFILE" \
  --root /models/qwen

readonly output_root="${QWEN_OUTPUT_ROOT:-/output/runs}"
readonly launch_id="$(python3 /app/tools/create_qwen_launch_logs.py --output-root "$output_root")"
readonly evidence_log="$output_root/qwen-evidence-$launch_id.log"
readonly vllm_log="$output_root/qwen-vllm-$launch_id.log"
readonly runtime_record="$output_root/qwen-runtime-$launch_id.json"

emit() {
  printf '%s\n' "$1" | tee -a "$evidence_log"
}

# This declares an in-progress observation window.  It is not a readiness
# claim; the END marker is emitted only after vLLM's own output is observed.
emit "QWEN_LAUNCH_BEGIN launch_id=$launch_id profile=$REQUIRED_PROFILE model=$REQUIRED_MODEL"

read -r -a extra_args <<< "${QWEN_EXTRA_ARGS:-}"
monitor_startup() {
  local deadline=$((SECONDS + ${QWEN_STARTUP_TIMEOUT_SECONDS:-300}))
  while kill -0 "$vllm_pid" 2>/dev/null && (( SECONDS < deadline )); do
    model_response="$(curl --fail --silent http://127.0.0.1:8001/v1/models 2>/dev/null || true)"
    if [[ -n "$model_response" ]]; then
      printf 'vllm_models=%s\n' "$model_response" >> "$vllm_log"
    fi

    if kill -0 "$vllm_pid" 2>/dev/null \
      && [[ -n "$model_response" ]] \
      && grep -Fq "$REQUIRED_MODEL" "$vllm_log" 2>/dev/null \
      && grep -Eq 'auto[_ -]?gptq' "$vllm_log" 2>/dev/null \
      && grep -Fq 'MarlinLinearKernel' "$vllm_log" 2>/dev/null \
      && grep -Fq "\"$REQUIRED_PROFILE\"" "$vllm_log" 2>/dev/null; then
      # Normalize only facts already present in vLLM output into the evidence
      # contract consumed by tools.verify_qwen_kernel.
      emit "quantization=auto_gptq"
      emit "Using MarlinLinearKernel for AutoGPTQLinearMethod"
      actual_attention="$(grep -Ei 'attention.*backend|backend.*attention' "$vllm_log" | tail -n 1 || true)"
      actual_cudagraph="$(grep -Ei 'cuda.?graph|cudagraph' "$vllm_log" | tail -n 1 || true)"
      python3 - "$runtime_record" "${QWEN_EXTRA_ARGS:-}" "$actual_attention" "$actual_cudagraph" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(json.dumps({
    "requested_qwen_extra_args": sys.argv[2],
    "actual_attention_backend_log": sys.argv[3] or None,
    "actual_cuda_graph_log": sys.argv[4] or None,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
      emit "QWEN_LAUNCH_END launch_id=$launch_id"
      return
    fi
    sleep 1
  done
  echo "Qwen startup did not produce ready evidence before vLLM exit or timeout" >&2
  kill "$vllm_pid" 2>/dev/null || true
}

vllm serve /models/qwen \
  --served-model-name "$QWEN_SERVED_MODEL" \
  --host 0.0.0.0 --port 8001 \
  --max-model-len "${QWEN_MAX_MODEL_LEN:-1024}" \
  --gpu-memory-utilization "${QWEN_GPU_MEMORY_UTILIZATION:-0.72}" \
  --limit-mm-per-prompt image=1 \
  "${extra_args[@]}" > >(tee -a "$vllm_log") 2>&1 &
vllm_pid=$!
monitor_startup &
monitor_pid=$!
if wait "$vllm_pid"; then
  vllm_status=0
else
  vllm_status=$?
fi
wait "$monitor_pid" 2>/dev/null || true
exit "$vllm_status"
