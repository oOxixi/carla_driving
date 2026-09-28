#!/usr/bin/env bash
# Run hb_verifier (float ONNX vs one int8 .bc) over every case of a dump set.
# Usage: batch_verify.sh <dump_root> <bc_path> <log_dir> [parallelism]
set -u

DUMP_ROOT=${1:?dump root}
BC=${2:?quantized bc path}
LOGDIR=${3:?log dir}
JOBS=${4:-1}
: "${ONNX:=/work/student/student_v0_fp32.onnx}"

mkdir -p "$LOGDIR"
export ONNX BC LOGDIR

# hb_verifier is single-case by design, so fan the cases out across processes.
find "$DUMP_ROOT" -mindepth 1 -maxdepth 1 -type d -print0 \
  | xargs -0 -P "$JOBS" -I{} bash -c '
      case_dir="$1"
      name=$(basename "$case_dir")
      hb_verifier -m "$ONNX,$BC" \
        -i "$case_dir/rgb.npy,$case_dir/text_tokens.npy,$case_dir/targets.npy,$case_dir/state.npy" \
        > "$LOGDIR/$name.log" 2>&1
    ' _ {}

ok=0
fail=0
for log in "$LOGDIR"/*.log; do
  if grep -q "CosineSimilarity" "$log"; then ok=$((ok + 1)); else fail=$((fail + 1)); fi
done
echo "cases ok=$ok fail=$fail -> $LOGDIR"
