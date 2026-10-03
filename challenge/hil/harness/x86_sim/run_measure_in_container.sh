#!/usr/bin/env bash
# Run one B3 measurement run INSIDE the official X86 image (repo mounted at /repo).
# Usage (inside the image): bash challenge/hil/harness/x86_sim/run_measure_in_container.sh \
#        [<out_dir>] [<limit>] [<rounds>]
set -eu

cd /repo
CAND=challenge/distillation/releases/a3_final_fp32_candidate_v1
OUT=${1:-/work/b3_official_env/d2_100x3}
LIMIT=${2:-100}
ROUNDS=${3:-3}

echo "environment : $(grep PRETTY_NAME /etc/os-release | cut -d= -f2), python $(python3 -V 2>&1 | cut -d' ' -f2)"
echo "weights     : $CAND/student_v0_fp32_candidate.pt"
echo "snapshot    : challenge/hil/frozen/d2_v1_1_val"
echo "out         : $OUT"

python3 -m challenge.hil.cli run \
  --repo . \
  --adapter inprocess \
  --weights "$CAND/student_v0_fp32_candidate.pt" \
  --weights-manifest "$CAND/handoff_manifest.json" \
  --frozen challenge/hil/frozen/d2_v1_1_val \
  --rounds "$ROUNDS" --warmup 5 --limit "$LIMIT" \
  --out "$OUT"
