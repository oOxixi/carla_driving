"""Assemble the D3 Wave2 X86-simulation evidence bundle (container side)."""
import glob
import json
import os
import re
import subprocess

LOGS = "/work/x86_sim/logs"
DST = "/work/x86_sim/evidence_d3w2"
CAL = "/work/student/.hb_compile_d3w2"
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

KEEP = ("Updated yaml config info", "calibration", "threshold", "memory", "march",
        "completes running", "ERROR", "WARNING", "BPU")


def write(name, text):
    os.makedirs(DST, exist_ok=True)
    with open(os.path.join(DST, name), "w", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")
    print("wrote", name, len(text.splitlines()), "lines")


def clean(path, keep=None):
    with open(path, encoding="utf-8", errors="ignore") as handle:
        lines = [ANSI.sub("", line).rstrip() for line in handle]
    if keep:
        lines = [line for line in lines if any(key in line for key in keep)]
    return "\n".join(lines)


def main() -> int:
    os.makedirs(DST, exist_ok=True)

    write("03_hb_compile_d3w2.log", clean(f"{LOGS}/20_hb_compile_d3w2.log", KEEP))

    with open(f"{LOGS}/22_verify_d3w2_summary.json", encoding="utf-8") as handle:
        summary = json.load(handle)
    with open(os.path.join(DST, "04_verify_d3w2_summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    print("wrote 04_verify_d3w2_summary.json cases:", summary["cases"])

    thresholds = subprocess.run(
        ["python3", "/work/x86_sim/thresholds_report.py",
         "skip-calibration=/work/student/.hb_compile/student_v0_fp32_quant_info.json",
         "smoke30-train=/work/student/.hb_compile_cal/student_v0_fp32_cal_quant_info.json",
         "d3w2-64train=/work/student/.hb_compile_d3w2/student_v0_fp32_d3w2_quant_info.json"],
        capture_output=True, text=True)
    write("05_thresholds_compare.log", thresholds.stdout + thresholds.stderr)

    cases = sorted(glob.glob("/work/dumps_d3w2/*/"))
    case = cases[0].rstrip("/") if cases else ""
    infer = clean(f"{LOGS}/25_infer_d3w2.log",
                  ("Infer time", "read file", "will padding", "Dump path"))
    compare = subprocess.run(
        ["python3", "/work/x86_sim/compare_dumps.py", case, "/work/x86_sim_d3w2",
         f"{LOGS}/24_model_info_d3w2.log", f"{LOGS}/26_dump_vs_onnx_d3w2.json"],
        capture_output=True, text=True)
    header = (
        f"case: {case}\n"
        f"artefact: {CAL}/student_v0_fp32_d3w2.hbm (calibrated on 64 D3 Wave2 train cases)\n"
        f"cli: hrt_model_exec infer --enable_dump=true, HB_UCP_SIM_PLATFORM_TYPE=nash-p\n\n"
    )
    write("06_cli_d3w2_single_case.log", header + infer + "\n" + compare.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
