#!/usr/bin/env bash
# Collect a text-only evidence bundle from the X86 simulation run.
set -u

W=/work/x86_sim
L=$W/logs
D=$W/evidence
OUT=/work/student/.hb_compile
TOOL=/open_explorer/samples/ucp_tutorial/tools/hrt_model_exec/output_shared_J6_x86

mkdir -p "$D"

{
  echo "== kernel =="; uname -srm
  echo; echo "== distro =="; grep PRETTY_NAME /etc/os-release
  echo; echo "== toolchain =="
  hb_verifier --version 2>&1 | head -2
  echo "hb_compile / hb_model_info: $(command -v hb_compile), $(command -v hb_model_info)"
  echo "hrt_model_exec: $(ls -l $TOOL/x86/bin/hrt_model_exec)"
  echo; echo "== artifacts =="
  md5sum "$OUT/student_v0_fp32.hbm" "$OUT/student_v0_fp32_quantized_model.bc" 2>/dev/null
  echo; echo "== simulation env =="
  echo "HB_UCP_SIM_PLATFORM_TYPE=${HB_UCP_SIM_PLATFORM_TYPE:-<unset>}"
} > "$D/00_environment.log" 2>&1

python3 - "$L" "$D" <<'PY'
import json
import os
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def clean(name, keep_prefixes=None, keep_keys=None):
    with open(os.path.join(src, name), encoding="utf-8", errors="ignore") as fh:
        lines = [ANSI.sub("", line).rstrip() for line in fh]
    if keep_prefixes:
        lines = [line for line in lines if line.startswith(keep_prefixes)]
    if keep_keys:
        lines = [line for line in lines if any(key in line for key in keep_keys)]
    with open(os.path.join(dst, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(lines)


print("01_model_info.log      lines:", clean("01_model_info.log"))
print("03_infer_hbm.log       lines:", clean("03_infer_hbm.log"))
print("04_sim_consistency.log lines:",
      clean("04_sim_consistency.log", keep_prefixes=("onnxruntime", "   ", "==", "wrote")))
print("06_hb_verifier.log     lines:",
      clean("06_hb_verifier.log",
            keep_keys=("|", "inference onnx", "inference bc", "verifier tool version")))
print("07_hb_compile_cal.log  lines:",
      clean("07_hb_compile_cal.log",
            keep_keys=("Updated yaml config info", "calibration", "threshold",
                       "memory", "march", "completes running", "ERROR", "WARNING")))
print("08_hb_verifier_cal.log lines:",
      clean("08_hb_verifier_cal.log",
            keep_keys=("|", "inference onnx", "inference bc", "verifier tool version")))
print("09_thresholds.log      lines:", clean("09_thresholds.log"))
print("10_model_info_cal.log  lines:",
      clean("10_model_info_cal.log",
            keep_keys=("name:", "valid shape:", "stride:", "aligned byte size",
                       "MARCH", "CALI_TYPE", "CAL_DATA_DIR", "model desc")))
print("11_infer_cal.log       lines:",
      clean("11_infer_cal.log",
            keep_keys=("Infer time", "read file", "will padding", "dump_path")))
for name in ("sim_consistency.json", "05_dump_vs_onnx.json", "12_dump_vs_onnx_cal.json"):
    path = os.path.join(src, name) if os.path.exists(os.path.join(src, name)) else \
        os.path.join("/work/x86_sim_cal", name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        with open(os.path.join(dst, name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        print("copied", name)
PY

ls -l "$D"
