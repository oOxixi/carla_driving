#!/usr/bin/env bash
# Run B3's full measurement and a 30-minute soak INSIDE the official X86 image,
# with the dataset copied into the container filesystem first.
#
# Why the copy matters: reading JPEGs through the Windows-drive bind mount costs
# ~200x more than reading them inside the container, which inflates latency by
# roughly 6x (see evidence/scoring_requirements_20261003/env_comparison.json).
#
# Usage (inside the image):
#   bash challenge/hil/harness/x86_sim/run_official_full_and_soak.sh [<soak_minutes>] [<limit>]
set -eu

cd /repo
MINUTES=${1:-30}
LIMIT=${2:-539}
CAND=challenge/distillation/releases/a3_final_fp32_candidate_v1
DATA=/tmp/frozen_d2
OUT=/tmp/b3_official_full

if [ ! -d "$DATA" ]; then
  cp -r challenge/hil/frozen/d2_v1_1_val "$DATA"
fi
mkdir -p "$OUT"

echo "== environment =="
grep PRETTY_NAME /etc/os-release | cut -d= -f2
python3 -V
echo "data: $DATA ($(ls "$DATA/rgb" | wc -l) rgb files)"
echo

echo "== full measurement: $LIMIT cases x 3 rounds =="
python3 -m challenge.hil.cli run \
  --repo . --adapter inprocess \
  --weights "$CAND/student_v0_fp32_candidate.pt" \
  --weights-manifest "$CAND/handoff_manifest.json" \
  --frozen "$DATA" --rounds 3 --warmup 5 --limit "$LIMIT" \
  --out "$OUT/full_${LIMIT}x3"

echo
echo "== soak: $MINUTES minutes =="
python3 -m challenge.hil.cli soak \
  --repo . --adapter inprocess \
  --weights "$CAND/student_v0_fp32_candidate.pt" \
  --weights-manifest "$CAND/handoff_manifest.json" \
  --frozen "$DATA" --duration-minutes "$MINUTES" --limit 8 --recovery-probe-cases 10 \
  --out "$OUT/soak_${MINUTES}min"
