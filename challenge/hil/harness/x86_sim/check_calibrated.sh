#!/usr/bin/env bash
# Compare the skip-calibration build with the calibrated build, then re-run the
# float-ONNX vs int8-bc consistency check on the calibrated artifact.
set -u

CASE=${1:-/work/dumps/ACC_A01_lead_brake_0000}
L=/work/x86_sim/logs
CAL=/work/student/.hb_compile_cal
SKIP=/work/student/.hb_compile
mkdir -p "$L"

python3 - "$SKIP/student_v0_fp32_quant_info.json" "$CAL/student_v0_fp32_cal_quant_info.json" \
  > "$L/09_thresholds.log" 2>&1 <<'PY'
import json
import sys

for path in sys.argv[1:3]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    flat = []
    for entry in data.values():
        for group in entry.get("thresholds") or []:
            flat.extend(float(x) for x in group)
    uniq = sorted({round(v, 6) for v in flat})
    print(f"{path}")
    print(f"  layers={len(data)} values={len(flat)} "
          f"distinct={len(uniq)} min={min(flat):.6g} max={max(flat):.6g}")
    print(f"  first 8 distinct: {uniq[:8]}")
    default_ones = sum(1 for v in flat if v == 1.0)
    print(f"  values exactly 1.0: {default_ones}/{len(flat)}")
PY
cat "$L/09_thresholds.log"

hb_verifier \
  -m "/work/student/student_v0_fp32.onnx,$CAL/student_v0_fp32_cal_quantized_model.bc" \
  -i "$CASE/rgb.npy,$CASE/text_tokens.npy,$CASE/targets.npy,$CASE/state.npy" \
  > "$L/08_hb_verifier_cal.log" 2>&1
echo "hb_verifier exit=$?"
tail -n 22 "$L/08_hb_verifier_cal.log"
