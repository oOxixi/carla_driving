#!/usr/bin/env bash
# One hb_verifier run: float ONNX vs the quantized .bc, with the B3 dump tensors
# passed in input_names order (a directory or the wrong count is rejected).
set -u

CASE=${1:-/work/dumps/ACC_A01_lead_brake_0000}
L=/work/x86_sim/logs
OUT=/work/student/.hb_compile

mkdir -p "$L"
hb_verifier \
  -m "/work/student/student_v0_fp32.onnx,$OUT/student_v0_fp32_quantized_model.bc" \
  -i "$CASE/rgb.npy,$CASE/text_tokens.npy,$CASE/targets.npy,$CASE/state.npy" \
  > "$L/06_hb_verifier.log" 2>&1
echo "exit=$?"
grep -iE "cosine|similar" "$L/06_hb_verifier.log" | head -20
