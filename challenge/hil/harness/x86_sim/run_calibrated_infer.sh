#!/usr/bin/env bash
# hrt_model_exec (X86 simulation) against the calibrated artifact, with dumps.
set -u

W=/work/x86_sim_cal
L=/work/x86_sim/logs
CAL=/work/student/.hb_compile_cal
TOOL=/open_explorer/samples/ucp_tutorial/tools/hrt_model_exec/output_shared_J6_x86
BINS=/work/x86_sim/bins

mkdir -p "$W"
export LD_LIBRARY_PATH="$TOOL/x86/lib:${LD_LIBRARY_PATH:-}"
export HB_UCP_SIM_PLATFORM_TYPE=${HB_UCP_SIM_PLATFORM_TYPE:-nash-p}

"$TOOL/x86/bin/hrt_model_exec" model_info \
  --model_file="$CAL/student_v0_fp32_cal.hbm" > "$L/10_model_info_cal.log" 2>&1
echo "model_info exit=$?"

cd "$W" || exit 1
"$TOOL/x86/bin/hrt_model_exec" infer \
  --model_file="$CAL/student_v0_fp32_cal.hbm" \
  --input_file="$BINS/rgb.bin,$BINS/text_tokens.bin,$BINS/targets.bin,$BINS/state.bin" \
  --enable_dump=true > "$L/11_infer_cal.log" 2>&1
echo "infer exit=$?"
grep -E "Infer time" "$L/11_infer_cal.log"

python3 /work/x86_sim/compare_dumps.py \
  /work/dumps/ACC_A01_lead_brake_0000 "$W" "$L/10_model_info_cal.log" \
  "$L/12_dump_vs_onnx_cal.json"
