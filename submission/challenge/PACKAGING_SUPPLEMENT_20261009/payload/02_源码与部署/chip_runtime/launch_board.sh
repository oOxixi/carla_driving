#!/usr/bin/env bash
set -euo pipefail
TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export LD_LIBRARY_PATH="$TASK_DIR/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
exec python3 "$TASK_DIR/student_board.py" \
  --worker "$TASK_DIR/build_arm/student_hbdnn" \
  --model "${MODEL_HBM:-$TASK_DIR/../../05_B3性能与评测/03_BPU工具原报告/student_v0_v3.hbm}" \
  --serve --metrics "$@"
