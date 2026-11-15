#!/usr/bin/env bash
set -eu
scope=$1
repo=/home/tiaozhansai/carla-driving-challenge
q=/home/tiaozhansai/carla-driving-2B
py=$q/.venv-qwen2b-cu130/bin/python
out=$(mktemp -d "$repo/artifacts/numeric_speed_conditioned_20261112/turn_phase_run.XXXXXXXX")
echo "Run directory: $out"
test -z "$(ss -H -ltn 'sport = :22220 or sport = :18300 or sport = :18306 or sport = :18307')"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HF_HUB_OFFLINE=1 PYTHONPATH="$scope:$repo"
backend=
teacher=
student=
carla=
trap 'for p in "$teacher" "$student" "$carla" "$backend"; do if test -n "$p"; then kill "$p" 2>/dev/null || true; fi; done' EXIT
cd "$scope"
QWEN_PORT=18300 QWEN_GPU_INDEX=0 bash "$q/tools/run_qwen35_vllm_3090.sh" >"$out/vllm.log" 2>&1 &
backend=$!
ready() {
    for _ in $(seq 1 "$3"); do
        if "$py" -c 'import sys; from urllib.request import urlopen; urlopen(sys.argv[1], timeout=2)' "http://127.0.0.1:$1/health" 2>/dev/null; then return 0; fi
        kill -0 "$2" 2>/dev/null || return 1
        sleep 3
    done
    return 1
}
ready 18300 "$backend" 80
"$py" -m qwen_service.server --host 127.0.0.1 --port 18306 --vllm-base-url http://127.0.0.1:18300/v1 --vllm-model Qwen/Qwen3.5-2B --qwen-mode planner_v2 --image-root "$out" --timeout-ms 15000 >"$out/teacher.log" 2>&1 &
teacher=$!
"$repo/.venv/bin/python" "$scope/turn_phase_student.py" --model "$scope/student_post_turn_explicit_dev.onnx" --root "$out" --port 18307 >"$out/student.log" 2>&1 &
student=$!
ready 18306 "$teacher" 15
ready 18307 "$student" 15
(
    cd /home/tiaozhansai/CARLA_0.9.16/runtime
    exec timeout --kill-after=5s 420s ./CarlaUE4.sh -RenderOffScreen -nosound -quality-level=Low -carla-rpc-port=22220
) >"$out/carla.log" 2>&1 &
carla=$!
for _ in $(seq 1 18); do
    if "$repo/.venv/bin/python" -c 'import carla; c=carla.Client("127.0.0.1",22220); c.set_timeout(3); print(c.get_server_version(),c.get_world().get_map().name)' 2>/dev/null; then
        break
    fi
    kill -0 "$carla"
    sleep 2
done
"$repo/.venv/bin/python" - "$scope/original.json" "$out/scenario.json" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text())
d["map"] = "Town03_Opt"
Path(sys.argv[2]).write_text(json.dumps(d, ensure_ascii=False))
PY
roles=(teacher student)
if test -n "${TURN_PHASE_FIXED_SRC:-}"; then roles+=(student_fixed); fi
for role in "${roles[@]}"; do
    port=18306
    role_source=$scope
    if test "$role" != teacher; then port=18307; fi
    if test "$role" = student_fixed; then role_source=$TURN_PHASE_FIXED_SRC; fi
    mkdir "$out/$role"
    code=0
    args=(--port 22220 --scenario-file "$out/scenario.json" --seed 4201 --realtime --sensor-profile low
        --default-speed-mps 3 --qwen-service-url "http://127.0.0.1:$port" --qwen-mode planner_v2
        --sensor-timeout-s 1.5 --watchdog-timeout-s 4
        --qwen-timeout-ms 12000 --qwen-image-root "$out" --qwen-image-prefix "$role/rgb"
        --log-dir "$out/$role/evidence")
    (cd "$role_source" && PYTHONPATH="$role_source:$repo" "$repo/.venv/bin/python" -m integration.carla_runner "${args[@]}") >"$out/$role/runner.log" 2>&1 || code=$?
    echo "$role exit=$code"
    printf '%s\n' "$code" >"$out/$role/exit_code.txt"
done
