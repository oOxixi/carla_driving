#!/usr/bin/env bash
# B3 on-PC (X86) simulation harness -- no J6P board involved.
#   * hrt_model_exec model_info / infer  against the compiled .hbm
#   * HBRuntime (X86 instruction-level simulation) vs onnxruntime reference
# Logs land in /work/x86_sim/logs.
set -u

W=/work/x86_sim
L=$W/logs
OUT=/work/student/.hb_compile
HBM=$OUT/student_v0_fp32.hbm
BC=$OUT/student_v0_fp32_quantized_model.bc
TOOL=/open_explorer/samples/ucp_tutorial/tools/hrt_model_exec/output_shared_J6_x86
CASE=${1:-$(ls -d /work/dumps/*/ | head -1)}
CASE=${CASE%/}

mkdir -p "$L" "$W/bins"
export LD_LIBRARY_PATH="$TOOL/x86/lib:${LD_LIBRARY_PATH:-}"
# The X86 DNN runtime defaults to the nash-e platform, so a nash-p artifact
# (J6P) fails with "Model march incompatible" unless the platform is pinned.
export HB_UCP_SIM_PLATFORM_TYPE=${HB_UCP_SIM_PLATFORM_TYPE:-nash-p}

echo "case dir : $CASE"
echo "hbm      : $HBM"
echo

echo "--- [1/4] hrt_model_exec model_info (X86 sim build)"
"$TOOL/x86/bin/hrt_model_exec" model_info --model_file="$HBM" > "$L/01_model_info.log" 2>&1
echo "exit=$?  -> $L/01_model_info.log"
tail -n 30 "$L/01_model_info.log"
echo

echo "--- [2/4] dump inputs as raw float32 .bin"
python3 "$W/make_bins.py" "$CASE" "$W/bins" > "$L/02_make_bins.log" 2>&1
echo "exit=$?  -> $L/02_make_bins.log"
cat "$L/02_make_bins.log"
echo

echo "--- [3/4] hrt_model_exec infer --enable_dump"
"$TOOL/x86/bin/hrt_model_exec" infer --model_file="$HBM" \
  --input_file="$W/bins/rgb.bin,$W/bins/text_tokens.bin,$W/bins/targets.bin,$W/bins/state.bin" \
  --enable_dump=true > "$L/03_infer_hbm.log" 2>&1
echo "exit=$?  -> $L/03_infer_hbm.log"
tail -n 20 "$L/03_infer_hbm.log"
echo

echo "--- [4/4] consistency + latency: float ONNX reference vs artifacts"
python3 "$W/sim_consistency.py" "$CASE" "$HBM" "$BC" > "$L/04_sim_consistency.log" 2>&1
echo "exit=$?  -> $L/04_sim_consistency.log"
tail -n 40 "$L/04_sim_consistency.log"
