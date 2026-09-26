#!/usr/bin/env bash
# Calibrate on D3 Wave2 train, then check every D3 Wave2 val case for
# float-ONNX vs int8-bc consistency and summarise the distribution.
set -u

OUT=/work/student/.hb_compile_d3w2
BC="$OUT/student_v0_fp32_d3w2_quantized_model.bc"
LOGS=/work/x86_sim/logs

bash /work/x86_sim/batch_verify.sh /work/dumps_d3w2 "$BC" "$LOGS/verify_d3w2"
python3 /work/x86_sim/summarise_verify.py "$LOGS/verify_d3w2" "$LOGS/22_verify_d3w2_summary.json"
