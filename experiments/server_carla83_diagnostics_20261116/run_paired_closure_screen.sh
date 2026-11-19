#!/usr/bin/env bash
# Paired CARLA runs; a staged matrix enables the complete 83-scenario report.
set -euo pipefail
out=$1
repo=/home/tiaozhansai/carla-driving-challenge
art=$repo/artifacts/numeric_speed_conditioned_20261112
scope=${CLOSURE_RUNTIME_SCOPE:-$art/turn_phase_fixed.IqtQifLR}
student=${CLOSURE_STUDENT_SCOPE:-$art/turn_phase_src.p2pXTsla}
teacher=$repo/artifacts/teacher_v4_isolated_source
q=/home/tiaozhansai/carla-driving-2B
py=$repo/.venv/bin/python
qpy=$q/.venv-qwen2b-cu130/bin/python
roles=(teacher student)
if [[ ${CLOSURE_STUDENT_ONLY:-0} == 1 ]]; then
    test ! -f "$out/matrix.json"
    roles=(student)
fi
test "$(git -C "$teacher" rev-parse HEAD)" = 95e97b00def8ec36f12937da34ce8bb9082c4a04
test -z "$(git -C "$teacher" status --porcelain --untracked-files=no)"
test -z "$(ss -H -ltn 'sport = :22230 or sport = :18331 or sport = :18336 or sport = :18337')"
printf '%s  %s\n' e8e4cb0f500a848b0462015d7f80f7716316aa5364cd3494526c72724d04a63c \
    "$student/student_post_turn_explicit_dev.onnx" | sha256sum -c
sha256sum "$out"/cases/*.json "$student/turn_phase_student.py" >"$out/inputs.sha256"
(cd "$scope"; find . -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum) >"$out/runtime.sha256"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HF_HUB_OFFLINE=1
pids=()
cleanup() { if ((${#pids[@]})); then kill "${pids[@]}" 2>/dev/null || true; fi; }
trap cleanup EXIT
ready() {
    for _ in $(seq 1 "$3"); do
        if "$qpy" -c 'import sys; from urllib.request import urlopen; urlopen(sys.argv[1], timeout=2)' "http://127.0.0.1:$1/health" 2>/dev/null; then return 0; fi
        kill -0 "$2" || return 1
        sleep 3
    done
    return 1
}
if [[ ${CLOSURE_STUDENT_ONLY:-0} != 1 ]]; then
    test "$(tr -d '[:space:]' < "$q/models/Qwen3.5-2B/.model_revision")" = 15852e8c16360a2fea060d615a32b45270f8a8fc
    # Leave GPU memory for CARLA and the already running services.
    VLLM_USE_FLASHINFER_SAMPLER=0 "$q/.venv-qwen2b-cu130/bin/vllm" serve "$q/models/Qwen3.5-2B" \
        --served-model-name Qwen/Qwen3.5-2B --host 127.0.0.1 --port 18331 --dtype bfloat16 \
        --max-model-len 2048 --max-num-seqs 1 --gpu-memory-utilization 0.45 --enable-prefix-caching \
        --limit-mm-per-prompt '{"image":1,"video":0}' >"$out/vllm.log" 2>&1 &
    pids+=("$!")
    ready 18331 "${pids[-1]}" 90
    (cd "$teacher"; exec "$qpy" -m qwen_service.server --host 127.0.0.1 --port 18336 --vllm-base-url http://127.0.0.1:18331/v1 --vllm-model Qwen/Qwen3.5-2B --qwen-mode planner_v2 --image-root "$out" --timeout-ms 15000) >"$out/teacher.log" 2>&1 &
    pids+=("$!")
    ready 18336 "${pids[-1]}" 20
fi
(cd "$scope"; export PYTHONPATH="$scope:$student:$repo"; exec "$py" "$student/turn_phase_student.py" --model "$student/student_post_turn_explicit_dev.onnx" --root "$out" --port 18337) >"$out/student.log" 2>&1 &
pids+=("$!")
ready 18337 "${pids[-1]}" 20
(cd /home/tiaozhansai/CARLA_0.9.16/runtime; exec ./CarlaUE4.sh -RenderOffScreen -nosound -quality-level=Low -carla-rpc-port=22230) >"$out/carla.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 24); do
    if "$py" -c 'import carla; c=carla.Client("127.0.0.1",22230); c.set_timeout(3); print(c.get_server_version(),c.get_world().get_map().name)' >"$out/rpc.txt" 2>&1; then break; fi
    sleep 2
done
grep -q '^0.9.16 ' "$out/rpc.txt"
cd "$scope"
export PYTHONPATH="$scope:$student:$repo"
for case in "$out"/cases/*.json; do
    name=$(basename "$case" .json)
    for role in "${roles[@]}"; do
        port=18336
        if [[ "$role" = student ]]; then port=18337; fi
        run=$out/$name/$role
        mkdir -p "$run"
        rc=0
        timeout --kill-after=5s 600s "$py" -m integration.carla_runner --port 22230 --scenario-file "$case" \
            --realtime --sensor-profile low --perception-mode sensors --scenario-facts-mode perception \
            --qwen-service-url "http://127.0.0.1:$port" --qwen-mode planner_v2 --qwen-timeout-ms 12000 \
            --sensor-timeout-s 1.5 --watchdog-timeout-s 4 --qwen-image-root "$out" \
            --qwen-image-prefix "$name/$role/rgb" --log-dir "$run/evidence" --print-every 1000000 \
            >"$run/runner.log" 2>&1 || rc=$?
        printf '%s\n' "$rc" >"$run/exit_code.txt"
        grep '"record_type": "scenario_acceptance"' "$run/runner.log" >"$run/acceptance.json" || true
        "$py" -c 'import json, pathlib, sys; p=pathlib.Path(sys.argv[1]); print(p.parent.name,p.name,sys.argv[2],[(r.get("status"),r.get("failed_keys")) for r in map(json.loads,(p/"acceptance.json").read_text().splitlines())],flush=True)' "$run" "$rc"
    done
done
if [[ -f "$out/matrix.json" ]]; then
    "$py" "$out/summarize_paired_closure.py" "$out"
fi
