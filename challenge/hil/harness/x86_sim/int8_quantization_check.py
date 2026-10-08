"""B3 independent FP32/INT8 comparison for the v3 candidate.

Runs the A2 INT8 artifacts (Full INT8 / Mixed Top-3) against the FP32 reference
on all frozen held-out cohorts and reports two levels:

* numeric: per-output max absolute difference and argmax agreement;
* plan: decode both sides with the *same* StudentPlanAdapter and compare the
  decoded plan fields, so any difference is attributable to quantization only.

Usage::

    py -3.12 -m challenge.hil.harness.x86_sim.int8_quantization_check \
        --fp32 <student_v0_fp32_candidate.onnx> \
        --int8 full=<student_int8.onnx> --int8 mixed=<student_int8_mixed_top3.onnx> \
        --work <dumps root> --repo . --out <json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
import torch

from challenge.planner.student_adapter import StudentPlanAdapter
from challenge.hil.harness.x86_sim.onnx_export_equivalence import numeric_equivalence

COHORTS = {
    "d2_v1_1_val": "dumps_d2",
    "d3_wave2_safe_short_v1_val": "dumps_d3w2",
    "d3_targeted_gap_strict_v1_val": "dumps_gap",
    "d3_turn_gap_60_strict_v1_val": "dumps_turn",
    "d3_gap300_strict_v1_val": "dumps_gap300",
    "b1_ms34_supplement_v1_val": "dumps_ms34",
}


SPEED_TOLERANCE_MPS = 0.05


def _plan_signature(plan: dict[str, Any], *, speed_tolerance: float | None = None) -> tuple:
    steps = []
    for step in plan.get("steps") or []:
        target = step.get("target") or {}
        speed = target.get("target_speed_mps")
        value = None if speed is None else float(speed)
        if value is not None and speed_tolerance is None:
            value = round(value, 3)
        steps.append((
            step.get("behavior"),
            target.get("target_id"),
            target.get("target_lane"),
            (step.get("completion") or {}).get("type"),
            value,
        ))
    return tuple(steps)


def _plans_match(a: tuple, b: tuple, *, speed_tolerance: float | None) -> bool:
    if len(a) != len(b):
        return False
    for left, right in zip(a, b):
        if left[:4] != right[:4]:
            return False
        if speed_tolerance is None:
            if left[4] != right[4]:
                return False
        elif (left[4] is None) != (right[4] is None):
            return False
        elif left[4] is not None and abs(left[4] - right[4]) > speed_tolerance:
            return False
    return True


def _plan_level(
    fp32_path: Path, int8_path: Path, cases: dict, index: list, limit: int,
) -> dict[str, Any]:
    fp32 = ort.InferenceSession(str(fp32_path), providers=["CPUExecutionProvider"])
    int8 = ort.InferenceSession(str(int8_path), providers=["CPUExecutionProvider"])
    inputs = [i.name for i in fp32.get_inputs()]
    outputs = [o.name for o in fp32.get_outputs()]
    adapter = StudentPlanAdapter()
    same = compared = tolerant_same = 0
    behaviour_same = 0
    steps_compared = 0
    for entry in (index[:limit] if limit else index):
        case = cases.get(entry["case_id"])
        if case is None:
            continue
        directory = Path(entry["directory"])
        feed = {name: np.load(directory / f"{name}.npy").astype(np.float32) for name in inputs}
        left = {n: torch.from_numpy(a) for n, a in zip(outputs, fp32.run(outputs, feed))}
        right = {n: torch.from_numpy(a) for n, a in zip(outputs, int8.run(outputs, feed))}
        plan_a = adapter.decode(case["request"], left)
        plan_b = adapter.decode(case["request"], right)
        sig_a, sig_b = _plan_signature(plan_a), _plan_signature(plan_b)
        sig_a_t = _plan_signature(plan_a, speed_tolerance=SPEED_TOLERANCE_MPS)
        sig_b_t = _plan_signature(plan_b, speed_tolerance=SPEED_TOLERANCE_MPS)
        compared += 1
        if sig_a == sig_b:
            same += 1
        if _plans_match(sig_a_t, sig_b_t, speed_tolerance=SPEED_TOLERANCE_MPS):
            tolerant_same += 1
        for a, b in zip(sig_a, sig_b):
            steps_compared += 1
            behaviour_same += int(a[0] == b[0])
    return {
        "cases_compared": compared,
        "plans_identical": same,
        "plan_identical_rate": (same / compared) if compared else None,
        "plans_identical_within_0p05_mps": tolerant_same,
        "plan_identical_rate_within_0p05_mps": (tolerant_same / compared) if compared else None,
        "steps_compared": steps_compared,
        "behaviour_identical_rate": (behaviour_same / steps_compared) if steps_compared else None,
    }


def run(
    fp32_path: Path, int8_variants: dict[str, Path], work: Path, repo: Path, limit: int = 0,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "fp32": str(fp32_path),
        "variants": {},
        "protocol": (
            "FP32 vs each INT8 artifact on every frozen held-out cohort; numeric level compares "
            "raw outputs, plan level decodes both sides with the same StudentPlanAdapter (V3.1)"
        ),
    }
    for label, int8_path in int8_variants.items():
        entry: dict[str, Any] = {"path": str(int8_path), "cohorts": {}, "totals": {}}
        worst_numeric = 0.0
        total_cases = total_same = total_steps = total_behaviour = 0
        for cohort, dumps_name in COHORTS.items():
            frozen = repo / "challenge" / "hil" / "frozen" / cohort / "cases.jsonl"
            dumps = work / dumps_name
            if not frozen.is_file() or not dumps.is_dir():
                entry["cohorts"][cohort] = {"skipped": True}
                continue
            cases = {}
            for line in frozen.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    case = json.loads(line)
                    cases[case["case_id"]] = case
            index = json.loads((dumps / "dump_index.json").read_text(encoding="utf-8"))["dumps"]
            numeric = numeric_equivalence(
                fp32_path, int8_path, dumps, frozen, limit,
            )
            plan = _plan_level(fp32_path, int8_path, cases, index, limit)
            entry["cohorts"][cohort] = {"numeric": numeric, "plan": plan}
            worst_numeric = max(worst_numeric, numeric["worst_max_abs_diff"])
            total_cases += plan["cases_compared"]
            total_same += plan["plans_identical"]
            total_tolerant = entry["totals"].get("plans_identical_within_0p05_mps", 0)
            entry["totals"]["plans_identical_within_0p05_mps"] = (
                total_tolerant + plan["plans_identical_within_0p05_mps"]
            )
            total_steps += plan["steps_compared"]
            total_behaviour += int(round(
                (plan["behaviour_identical_rate"] or 0.0) * plan["steps_compared"]
            ))
        entry["totals"] = {
            "worst_max_abs_diff": worst_numeric,
            "cases_compared": total_cases,
            "plans_identical": total_same,
            "plan_identical_rate": (total_same / total_cases) if total_cases else None,
            "plans_identical_within_0p05_mps": entry["totals"].get(
                "plans_identical_within_0p05_mps", 0
            ),
            "plan_identical_rate_within_0p05_mps": (
                entry["totals"].get("plans_identical_within_0p05_mps", 0) / total_cases
            ) if total_cases else None,
            "steps_compared": total_steps,
            "behaviour_identical_rate": (total_behaviour / total_steps) if total_steps else None,
        }
        report["variants"][label] = entry
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fp32", required=True)
    parser.add_argument("--int8", action="append", required=True,
                        help="label=path (repeatable)")
    parser.add_argument("--work", required=True)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    variants = {}
    for item in args.int8:
        label, _, path = item.partition("=")
        variants[label] = Path(path)
    report = run(Path(args.fp32), variants, Path(args.work), Path(args.repo).resolve(), args.limit)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({label: entry["totals"] for label, entry in report["variants"].items()},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
