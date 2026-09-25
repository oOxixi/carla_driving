"""Assemble the d3_targeted_gap_strict_v1 X86-simulation evidence bundle."""
import json
import os
import re
import subprocess

LOGS = "/work/x86_sim/logs"
DST = "/work/x86_sim/evidence_gap"
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
KEEP = ("Updated yaml config info", "calibration", "memory", "march",
        "completes running", "ERROR", "WARNING", "BPU")


def write(name, text):
    os.makedirs(DST, exist_ok=True)
    with open(os.path.join(DST, name), "w", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")
    print("wrote", name)


def clean(path, keep=None):
    with open(path, encoding="utf-8", errors="ignore") as handle:
        lines = [ANSI.sub("", line).rstrip() for line in handle]
    if keep:
        lines = [line for line in lines if any(key in line for key in keep)]
    return "\n".join(lines)


def copy_json(src, dst):
    os.makedirs(DST, exist_ok=True)
    with open(src, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(os.path.join(DST, dst), "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    print("wrote", dst, "cases:", data.get("cases"))


def main() -> int:
    os.makedirs(DST, exist_ok=True)
    write("04_hb_compile_gap.log", clean(f"{LOGS}/40_hb_compile_gap.log", KEEP))
    copy_json(f"{LOGS}/41_verify_gap_summary.json", "06_verify_gap_val_99.json")
    copy_json(f"{LOGS}/42_verify_d3w2_with_gap_summary.json", "07_gap_artifact_on_d3w2_val.json")
    copy_json(f"{LOGS}/43_verify_gap_with_d3w2_summary.json", "08_d3w2_artifact_on_gap_val.json")
    report = subprocess.run(
        ["python3", "/work/x86_sim/thresholds_report.py",
         "skip-calibration=/work/student/.hb_compile/student_v0_fp32_quant_info.json",
         "smoke30-train=/work/student/.hb_compile_cal/student_v0_fp32_cal_quant_info.json",
         "d3w2-64train=/work/student/.hb_compile_d3w2/student_v0_fp32_d3w2_quant_info.json",
         "gap-128train=/work/student/.hb_compile_gap/student_v0_fp32_gap_quant_info.json"],
        capture_output=True, text=True)
    write("05_thresholds_compare.log", report.stdout + report.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
