#!/usr/bin/env bash
# Run hb_verifier (float ONNX vs one int8 .bc) over every case of a dump set.
# Usage: batch_verify.sh <dump_root> <bc_path> <log_dir>
set -u

DUMP_ROOT=${1:?dump root}
BC=${2:?quantized bc path}
LOGDIR=${3:?log dir}
ONNX=/work/student/student_v0_fp32.onnx

mkdir -p "$LOGDIR"
ok=0
fail=0
for case_dir in "$DUMP_ROOT"/*/; do
  case_name=$(basename "$case_dir")
  hb_verifier \
    -m "$ONNX,$BC" \
    -i "$case_dir/rgb.npy,$case_dir/text_tokens.npy,$case_dir/targets.npy,$case_dir/state.npy" \
    > "$LOGDIR/$case_name.log" 2>&1
  if [ $? -eq 0 ]; then ok=$((ok + 1)); else fail=$((fail + 1)); fi
done
echo "cases ok=$ok fail=$fail -> $LOGDIR"
