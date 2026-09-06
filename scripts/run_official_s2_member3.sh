#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

python_executable="${PYTHON_EXECUTABLE:-python3}"
qwen_service_url="${QWEN_SERVICE_URL:-http://127.0.0.1:18000}"
qwen_timeout_ms="${QWEN_TIMEOUT_MS:-5000}"
carla_host="${CARLA_HOST:-127.0.0.1}"
carla_port="${CARLA_PORT:-2000}"
log_dir="${S2_LOG_DIR:-artifacts/logs/official_competition}"
mode="${1:---run}"

scene_path="scenarios/official_competition/S2_complex_avoidance_8km.json"

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

"$python_executable" - "$qwen_service_url" <<'PY'
import json
import sys
from urllib.request import urlopen

base_url = sys.argv[1].rstrip("/")
with urlopen(base_url + "/health", timeout=10) as response:
    health = json.load(response)
if health.get("status") != "READY" or health.get("production_ready") is not True:
    raise SystemExit("Qwen service is not production-ready: " + json.dumps(health, ensure_ascii=False))
print("Qwen health PASS:", json.dumps(health, ensure_ascii=False))
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
  --qwen-mode planner_v2
  --qwen-timeout-ms "$qwen_timeout_ms"
  --qwen-queue-size 1
  --qwen-image-root "$project_root"
  --qwen-image-prefix artifacts/runtime/qwen_official
  --scenario-file "$scene_path"
)
if [[ "$mode" == "--smoke" ]]; then
  arguments+=(--max-frames 600)
fi

"$python_executable" "${arguments[@]}"

latest_jsonl="$(
  "$python_executable" - "$log_dir" <<'PY'
from pathlib import Path
import sys

paths = sorted(
    Path(sys.argv[1]).glob("OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM_*.jsonl"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)
if not paths:
    raise SystemExit("S2 evidence JSONL was not created")
print(paths[0])
PY
)"
"$python_executable" tools/validate_s2_member3_evidence.py "$latest_jsonl" \
  --output "${latest_jsonl%.jsonl}.member3.json"
