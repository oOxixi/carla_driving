#!/usr/bin/env bash
# Single-case cross-check of the D3 Wave2 artefact through the hrt_model_exec
# (X86 simulation) CLI path, dumped outputs compared against the float ONNX.
set -u

CASE=${1:-$(ls -d /work/dumps_d3w2/*/ | head -1)}
CASE=${CASE%/}
W=/work/x86_sim_d3w2
L=/work/x86_sim/logs
OUT=/work/student/.hb_compile_d3w2
TOOL=/open_explorer/samples/ucp_tutorial/tools/hrt_model_exec/output_shared_J6_x86

mkdir -p "$W" "$L"
export LD_LIBRARY_PATH="$TOOL/x86/lib:${LD_LIBRARY_PATH:-}"
export HB_UCP_SIM_PLATFORM_TYPE=${HB_UCP_SIM_PLATFORM_TYPE:-nash-p}

python3 /work/x86_sim/make_bins.py "$CASE" /work/x86_sim/bins_d3w2 > "$L/23_make_bins_d3w2.log" 2>&1
echo "case: $CASE"

"$TOOL/x86/bin/hrt_model_exec" model_info \
  --model_file="$OUT/student_v0_fp32_d3w2.hbm" > "$L/24_model_info_d3w2.log" 2>&1
echo "model_info exit=$?"

cd "$W" || exit 1
"$TOOL/x86/bin/hrt_model_exec" infer \
  --model_file="$OUT/student_v0_fp32_d3w2.hbm" \
  --input_file="/work/x86_sim/bins_d3w2/rgb.bin,/work/x86_sim/bins_d3w2/text_tokens.bin,/work/x86_sim/bins_d3w2/targets.bin,/work/x86_sim/bins_d3w2/state.bin" \
  --enable_dump=true > "$L/25_infer_d3w2.log" 2>&1
echo "infer exit=$?"
grep -E "Infer time" "$L/25_infer_d3w2.log"

python3 /work/x86_sim/compare_dumps.py "$CASE" "$W" "$L/24_model_info_d3w2.log" \
  "$L/26_dump_vs_onnx_d3w2.json"
