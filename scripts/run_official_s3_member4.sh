#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

python_executable="${PYTHON_EXECUTABLE:-python3}"
qwen_service_url="${QWEN_SERVICE_URL:-http://127.0.0.1:18000}"
# Keep the established 7B route. This value is evidence metadata for the
# canonical service path; model selection remains owned by the running service.
qwen_model="${QWEN_MODEL:-Qwen/Qwen2.5-VL-7B-Instruct-AWQ}"
carla_host="${CARLA_HOST:-127.0.0.1}"
carla_port="${CARLA_PORT:-2000}"
log_dir="${S3_LOG_DIR:-artifacts/logs/official_competition}"
mode="${1:---run}"
scene_path="scenarios/official_competition/S3_extreme_emergency_6km.json"

if [[ "${qwen_model^^}" != *"7B"* ]]; then
  echo "S3 member-4 acceptance requires the established 7B model; got: $qwen_model" >&2
  exit 2
fi

"$python_executable" tools/validate_official_scenes.py
"$python_executable" -m integration.carla_runner \
  --scenario-file "$scene_path" \
  --validate-scenario-only

if [[ "$mode" == "--validate" ]]; then
  exit 0
fi
if [[ "$mode" != "--smoke" && "$mode" != "--run" ]]; then
  echo "usage: $0 [--validate|--smoke|--run]" >&2
  exit 2
fi

"$python_executable" - "$qwen_service_url" "$qwen_model" <<'PY'
import json
import sys
from urllib.request import urlopen

base_url, expected_model = sys.argv[1].rstrip("/"), sys.argv[2]
with urlopen(base_url + "/health", timeout=10) as response:
    health = json.load(response)
if health.get("status") != "READY" or health.get("production_ready") is not True:
    raise SystemExit("Qwen service is not production-ready: " + json.dumps(health, ensure_ascii=False))
reported = str(health.get("model") or health.get("model_id") or health.get("served_model") or "")
if reported and "7B" not in reported.upper():
    raise SystemExit(f"Qwen service model is not 7B: {reported}")
print("Qwen 7B health PASS:", json.dumps(health, ensure_ascii=False), "evidence_model=", expected_model)
PY

arguments=(
  -m integration.carla_runner
  --host "$carla_host"
  --port "$carla_port"
  --timeout-s 60
  --warmup-frames 40
  --sensor-warmup-frames 30
  --sensor-timeout-s 1.0
  --perception-mode sensors
  --scenario-facts-mode perception
  --follow-spectator
  --realtime
  --print-every 20
  --log-dir "$log_dir"
  --qwen-service-url "$qwen_service_url"
  --qwen-model "$qwen_model"
  --qwen-mode planner_v2
  --qwen-timeout-ms 100
  --qwen-queue-size 1
  --qwen-image-root "$project_root"
  --qwen-image-prefix artifacts/runtime/qwen_official
  --scenario-file "$scene_path"
)
if [[ "$mode" == "--smoke" ]]; then
  arguments+=(--max-frames 900)
fi

"$python_executable" "${arguments[@]}"

latest_jsonl="$(
  "$python_executable" - "$log_dir" <<'PY'
from pathlib import Path
import sys

paths = sorted(
    Path(sys.argv[1]).glob("OFFICIAL_S3_EXTREME_EMERGENCY_6KM_*.jsonl"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)
if not paths:
    raise SystemExit("S3 evidence JSONL was not created")
print(paths[0])
PY
)"

validator_args=(
  tools/validate_s3_member4_evidence.py "$latest_jsonl"
  --output "${latest_jsonl%.jsonl}.member4.json"
)
if [[ "$mode" == "--smoke" ]]; then
  validator_args+=(--functional-only)
fi
"$python_executable" "${validator_args[@]}"
