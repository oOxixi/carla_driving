#!/usr/bin/env bash
set -u

ROOT="$(pwd)"
PY="${PY:-python}"

BASE_OUT="artifacts/b1_ms34_supplement_v1"

SHARED_QWEN_ROOT="/home/dcase_task2/dongfeng_voice/carla_driving_challenge_b1"

SCENARIO_3="scenarios/targeted_collection/multistep34/TC_MS34_real_3step_avoid_resume.json"
SCENARIO_4="scenarios/targeted_collection/multistep34/TC_MS34_real_4step_yield_avoid_resume.json"

TARGET_PER_KIND=15
MAX_ATTEMPTS_PER_KIND=30

mkdir -p "$BASE_OUT/3step" "$BASE_OUT/4step"

validate_run() {
    local console="$1"
    local runner_rc="$2"

    "$PY" - "$console" "$runner_rc" <<'PY'
import json
import sys
from pathlib import Path

console = Path(sys.argv[1])
runner_rc = int(sys.argv[2])

if runner_rc != 0 or not console.exists():
    raise SystemExit(1)

qwen_rows = []
scenario_rows = []

for raw in console.read_text(encoding="utf-8", errors="replace").splitlines():
    line = raw.strip()
    if not line.startswith("{"):
        continue
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        continue

    record_type = row.get("record_type")
    if record_type == "qwen_scenario_acceptance":
        qwen_rows.append(row)
    elif record_type == "scenario_acceptance":
        scenario_rows.append(row)

if not qwen_rows or not scenario_rows:
    raise SystemExit(1)

qwen = qwen_rows[-1]
scenario = scenario_rows[-1]

observed = qwen.get("observed", {})

qwen_ok = (
    qwen.get("passed") is True
    and observed.get("qwen_calls") == 1
    and observed.get("replans") == 0
    and "SUCCEEDED" in observed.get("terminals", [])
)

# 兼容当前 scenario_acceptance 可能使用 passed/status/failed_keys 的不同表示。
scenario_ok = True

if "passed" in scenario:
    scenario_ok = scenario_ok and scenario.get("passed") is True

if "status" in scenario:
    scenario_ok = scenario_ok and str(
        scenario.get("status", "")
    ).upper() == "SUCCEEDED"

if "failed_keys" in scenario:
    scenario_ok = scenario_ok and not scenario.get("failed_keys")

if not qwen_ok or not scenario_ok:
    raise SystemExit(1)

raise SystemExit(0)
PY
}

run_kind() {
    local kind="$1"
    local scenario="$2"
    local seed="$3"

    local accepted=0
    local attempt=0

    while (( accepted < TARGET_PER_KIND )); do
        attempt=$((attempt + 1))

        if (( attempt > MAX_ATTEMPTS_PER_KIND )); then
            echo "ERROR: ${kind} exceeded ${MAX_ATTEMPTS_PER_KIND} attempts"
            return 1
        fi

        local candidate=$((accepted + 1))
        local run_name
        run_name="$(printf 'accepted_%03d_attempt_%03d' "$candidate" "$attempt")"

        local out="$BASE_OUT/$kind/$run_name"
        local image_prefix="$BASE_OUT/$kind/$run_name/qwen_images"

        echo
        echo "============================================================"
        echo "MS34 ${kind}"
        echo "attempt=${attempt}"
        echo "accepted_so_far=${accepted}/${TARGET_PER_KIND}"
        echo "scenario=${scenario}"
        echo "seed=${seed}"
        echo "out=${out}"
        echo "============================================================"

        rm -rf "$out"
        rm -rf "$SHARED_QWEN_ROOT/$image_prefix"

        mkdir -p "$out/logs"
        mkdir -p "$SHARED_QWEN_ROOT/$image_prefix"

        set +e
        "$PY" -m integration.carla_runner \
          --host 127.0.0.1 \
          --port 2000 \
          --scenario-file "$scenario" \
          --seed "$seed" \
          --perception-mode sensors \
          --scenario-facts-mode perception \
          --sensor-profile competition_multiview \
          --realtime \
          --qwen-service-url http://127.0.0.1:18009 \
          --qwen-mode planner_v2 \
          --qwen-timeout-ms 5000 \
          --qwen-queue-size 1 \
          --qwen-image-root "$SHARED_QWEN_ROOT" \
          --qwen-image-prefix "$image_prefix" \
          --sensor-warmup-frames 20 \
          --sensor-timeout-s 1.0 \
          --print-every 100 \
          --log-dir "$out/logs" \
          2>&1 | tee "$out/console.log"

        runner_rc=${PIPESTATUS[0]}
        set -e

        echo "$runner_rc" > "$out/runner_rc.txt"

        if validate_run "$out/console.log" "$runner_rc"; then
            accepted=$((accepted + 1))
            echo "ACCEPTED: ${kind} ${accepted}/${TARGET_PER_KIND}"
            echo "PASS" > "$out/collection_status.txt"
        else
            echo "REJECTED: ${kind} attempt ${attempt}"
            echo "FAIL" > "$out/collection_status.txt"

            mkdir -p "$BASE_OUT/rejected/$kind"
            mv "$out" "$BASE_OUT/rejected/$kind/"
        fi
    done

    echo
    echo "DONE: ${kind} accepted=${accepted}/${TARGET_PER_KIND}"
}

set -e

echo "===== MS34 SUPPLEMENT V1 ====="
echo "root=$ROOT"
echo "target=15 accepted 3-step + 15 accepted 4-step"

run_kind \
    "3step" \
    "$SCENARIO_3" \
    253000

run_kind \
    "4step" \
    "$SCENARIO_4" \
    253001

echo
echo "===== COLLECTION COMPLETE ====="
echo "3-step target = 15"
echo "4-step target = 15"
echo "total target  = 30"
