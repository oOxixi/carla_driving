#!/usr/bin/env bash
# X86 simulation matrix: the compiled BPU artefact vs the ONNX model it should
# still be equivalent to, over every frozen validation cohort.
#
# Usage: run_x86_matrix.sh [<bc>] [<onnx_reference>] [<jobs>]
set -u

BC=${1:-/work/a2_oe_pkg/openexplorer_oe391/model_output/student_v0_j6p_quantized_model.bc}
ONNX_REF=${2:-/work/a2_oe_pkg/models/student_int8.onnx}
JOBS=${3:-8}
LOGS=/work/x86_sim/logs
TAG=${4:-bpuc}

declare -A COHORTS=(
  [d2_v1_1_val]=/work/dumps_d2
  [d3_wave2_val]=/work/dumps_d3w2
  [targeted_gap_val]=/work/dumps_gap
  [turn_gap_val]=/work/dumps_turn
  [gap300_val]=/work/dumps_gap300
  [ms34_val]=/work/dumps_ms34
)

for name in "${!COHORTS[@]}"; do
  dir=${COHORTS[$name]}
  if [ ! -d "$dir" ]; then
    echo "skip $name (no dumps at $dir)"
    continue
  fi
  echo "=== $name ($dir) ==="
  ONNX="$ONNX_REF" bash /work/x86_sim/batch_verify.sh "$dir" "$BC" "$LOGS/verify_${name}_${TAG}" "$JOBS"
  python3 /work/x86_sim/summarise_verify.py "$LOGS/verify_${name}_${TAG}" "$LOGS/90_matrix_${TAG}_${name}.json" \
    | tail -4
done
