"""Run the v3 per-cohort diagnostics (modality ablation + TURN_LEFT attribution).

Drives the two standalone scripts over the six frozen held-out cohorts and
merges their JSON reports into one file, so the result can be quoted without
hand-copying numbers.

Usage:
    py -3.12 challenge/hil/harness/x86_sim/cohort_diagnostics.py \
        --onnx <model.onnx> --work <dump_root> --out <json>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# cohort name -> dumps directory name under --work
COHORTS = {
    "d2_v1_1_val": "dumps_d2",
    "d3_wave2_safe_short_v1_val": "dumps_d3w2",
    "d3_targeted_gap_strict_v1_val": "dumps_gap",
    "d3_turn_gap_60_strict_v1_val": "dumps_turn",
    "d3_gap300_strict_v1_val": "dumps_gap300",
    "b1_ms34_supplement_v1_val": "dumps_ms34",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--work", required=True, help="root holding the dumps_* directories")
    parser.add_argument("--repo", default=".", help="repository root (holds challenge/hil)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 means every case")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    harness = repo / "challenge" / "hil" / "harness" / "x86_sim"
    frozen_root = repo / "challenge" / "hil" / "frozen"
    work = Path(args.work)

    report = {
        "model": args.onnx,
        "limit": args.limit or "all",
        "ablation": {},
        "turn_left_attribution": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for cohort, dumps_name in COHORTS.items():
            frozen = frozen_root / cohort
            dumps = work / dumps_name
            if not dumps.is_dir():
                report["ablation"][cohort] = {"skipped": f"missing dumps {dumps}"}
                report["turn_left_attribution"][cohort] = {"skipped": f"missing dumps {dumps}"}
                continue
            # modality_ablation defaults to 150 and treats 0 as "nothing", so an
            # explicit "all" limit has to be passed for a full-cohort run.
            extra = ["--limit", str(args.limit or 10**9)]
            ablation_out = tmpdir / f"{cohort}.ablation.json"
            attribution_out = tmpdir / f"{cohort}.attribution.json"
            ablation = run_script(
                harness / "modality_ablation.py", args.onnx, dumps, frozen, ablation_out, extra
            )
            attribution = run_script(
                harness / "turn_left_attribution.py", args.onnx, dumps, frozen, attribution_out, extra
            )
            report["ablation"][cohort] = ablation["modalities"]
            report["turn_left_attribution"][cohort] = {
                "totals": attribution["totals"],
                "teacher_behaviour_breakdown": attribution["teacher_behaviour_breakdown"],
                "teacher_turn_left_steps": attribution["teacher_turn_left_steps"],
            }
            print(f"done {cohort}: cases={ablation['cases']}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


def run_script(script: Path, onnx: str, dumps: Path, frozen: Path, out: Path,
               extra: list[str]) -> dict:
    command = [
        sys.executable, str(script),
        "--onnx", onnx, "--dumps", str(dumps), "--frozen", str(frozen), "--out", str(out),
    ] + extra
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{script.name} failed for {frozen.name}: {completed.stderr[-2000:]}")
    return json.loads(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
