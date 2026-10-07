"""Same-protocol Teacher/Student comparison on the frozen held-out cohorts.

The "core metric decay" scoring item asks for the lightweight model's application
performance *relative to the original model on one benchmark*.  The only place
where both sides can be evaluated under one protocol on this workstation is the
frozen release data: each case carries the Teacher's own plan (``teacher_plan``,
produced by the pinned Qwen teacher) and the Student's plan is decoded from the
Student ONNX through the same adapter, case by case, step by step.

The Teacher side is the reference, so by construction its agreement is 100%;
the decay is therefore ``1 - student_agreement`` on each field.  That is a
*plan-agreement proxy*, not an independent accuracy: it measures how far the
lightweight model drifted from the original model's plan on the same cases.

Usage::

    py -3.12 -m challenge.hil.harness.x86_sim.teacher_student_decay \
        --onnx <student_v0_fp32_v3.onnx> --work <dump root> --out <json>
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
from challenge.student.contract import OUTPUT_NAMES

COHORTS = {
    "d2_v1_1_val": "dumps_d2",
    "d3_wave2_safe_short_v1_val": "dumps_d3w2",
    "d3_targeted_gap_strict_v1_val": "dumps_gap",
    "d3_turn_gap_60_strict_v1_val": "dumps_turn",
    "d3_gap300_strict_v1_val": "dumps_gap300",
    "b1_ms34_supplement_v1_val": "dumps_ms34",
}

SPEED_TOLERANCE_MPS = 0.5


def _teacher_steps(case: dict[str, Any]) -> list[dict[str, Any]]:
    return list((case.get("teacher_plan") or {}).get("steps") or [])


def _target(step: dict[str, Any]) -> dict[str, Any]:
    value = step.get("target")
    return value if isinstance(value, dict) else {}


def _compare_case(
    teacher: list[dict[str, Any]], student: list[dict[str, Any]], counters: dict[str, Any],
) -> None:
    counters["teacher_steps"] += len(teacher)
    counters["student_steps"] += len(student)
    counters["cases"] += 1
    counters["step_count_match"] += int(len(teacher) == len(student))
    overlapping = min(len(teacher), len(student))
    def field_stats(name: str, t_value: Any, s_value: Any) -> None:
        """Track null-convention gaps separately from real disagreements."""
        if t_value is None and s_value is None:
            counters[f"{name}_both_null"] += 1
        elif t_value is None:
            counters[f"{name}_student_only"] += 1
        elif s_value is None:
            counters[f"{name}_teacher_only"] += 1
        else:
            counters[f"{name}_both_present"] += 1
            counters[f"{name}_both_present_agree"] += int(t_value == s_value)

    for index in range(overlapping):
        t, s = teacher[index], student[index]
        counters["steps_compared"] += 1
        counters["behaviour_match"] += int(t.get("behavior") == s.get("behavior"))
        t_target, s_target = _target(t), _target(s)
        field_stats("lane", t_target.get("target_lane"), s_target.get("target_lane"))
        field_stats("target_id", t_target.get("target_id"), s_target.get("target_id"))
        field_stats(
            "completion",
            (t.get("completion") or {}).get("type"),
            (s.get("completion") or {}).get("type"),
        )
        counters["lane_match"] += int(
            t_target.get("target_lane") == s_target.get("target_lane")
        )
        counters["completion_match"] += int(
            (t.get("completion") or {}).get("type") == (s.get("completion") or {}).get("type")
        )
        t_id, s_id = t_target.get("target_id"), s_target.get("target_id")
        if t_id is not None:
            counters["target_id_compared"] += 1
            counters["target_id_match"] += int(t_id == s_id)
        t_speed, s_speed = t_target.get("target_speed_mps"), s_target.get("target_speed_mps")
        if isinstance(t_speed, (int, float)):
            counters["speed_compared"] += 1
            if isinstance(s_speed, (int, float)):
                delta = abs(float(t_speed) - float(s_speed))
                counters["speed_abs_error_sum"] += delta
                counters["speed_within_tolerance"] += int(delta <= SPEED_TOLERANCE_MPS)
                counters["speed_max_abs_error"] = max(counters["speed_max_abs_error"], delta)
            else:
                counters["speed_missing"] += 1
    if len(student) > len(teacher):
        counters["extra_student_steps"] += len(student) - len(teacher)
    elif len(student) < len(teacher):
        counters["missing_student_steps"] += len(teacher) - len(student)


def _rate(numerator: int, denominator: int) -> float | None:
    return (numerator / denominator) if denominator else None


def run(onnx_path: str, work: Path, repo: Path, limit: int = 0) -> dict[str, Any]:
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inputs = [item.name for item in session.get_inputs()]
    outputs = [item.name for item in session.get_outputs()]
    missing = [name for name in OUTPUT_NAMES if name not in outputs]
    if missing:
        raise ValueError(f"ONNX is missing Student outputs: {missing}")
    adapter = StudentPlanAdapter()
    totals: dict[str, Any] = {
        "cases": 0, "teacher_steps": 0, "student_steps": 0, "steps_compared": 0,
        "step_count_match": 0, "behaviour_match": 0, "lane_match": 0,
        "completion_match": 0, "target_id_compared": 0, "target_id_match": 0,
        "speed_compared": 0, "speed_within_tolerance": 0, "speed_abs_error_sum": 0.0,
        "speed_max_abs_error": 0.0, "speed_missing": 0,
        "extra_student_steps": 0, "missing_student_steps": 0,
    }
    for name in ("lane", "target_id", "completion"):
        for suffix in ("both_null", "student_only", "teacher_only", "both_present", "both_present_agree"):
            totals[f"{name}_{suffix}"] = 0
    per_cohort: dict[str, Any] = {}
    for cohort, dumps_name in COHORTS.items():
        frozen_path = repo / "challenge" / "hil" / "frozen" / cohort / "cases.jsonl"
        dump_dir = work / dumps_name
        if not frozen_path.is_file() or not dump_dir.is_dir():
            per_cohort[cohort] = {"skipped": "missing frozen cases or dumps"}
            continue
        cases = {}
        for line in frozen_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                case = json.loads(line)
                cases[case["case_id"]] = case
        index = json.loads((dump_dir / "dump_index.json").read_text(encoding="utf-8"))["dumps"]
        if limit:
            index = index[:limit]
        counters: dict[str, Any] = {key: 0 for key in totals}
        counters["speed_max_abs_error"] = 0.0
        for entry in index:
            case = cases.get(entry["case_id"])
            if case is None:
                continue
            directory = Path(entry["directory"])
            feed = {name: np.load(directory / f"{name}.npy").astype(np.float32) for name in inputs}
            raw = dict(zip(outputs, session.run(outputs, feed)))
            tensors = {name: torch.from_numpy(array) for name, array in raw.items()}
            student = adapter.decode(case["request"], tensors)["steps"]
            _compare_case(_teacher_steps(case), student, counters)
        for key, value in counters.items():
            if key in totals and isinstance(value, (int, float)):
                totals[key] += value
        per_cohort[cohort] = {
            "cases": counters["cases"],
            "teacher_steps": counters["teacher_steps"],
            "behaviour_agreement": _rate(counters["behaviour_match"], counters["steps_compared"]),
            "lane_agreement": _rate(counters["lane_match"], counters["steps_compared"]),
            "lane_agreement_when_both_present": _rate(
                counters["lane_both_present_agree"], counters["lane_both_present"]
            ),
            "lane_teacher_only": counters["lane_teacher_only"],
            "completion_agreement": _rate(
                counters["completion_match"], counters["steps_compared"]
            ),
            "target_id_agreement": _rate(
                counters["target_id_match"], counters["target_id_compared"]
            ),
            "speed_mae_mps": (
                counters["speed_abs_error_sum"] / counters["speed_compared"]
            ) if counters["speed_compared"] else None,
            "speed_within_0p5_mps_rate": _rate(
                counters["speed_within_tolerance"], counters["speed_compared"]
            ),
        }
    summary = {
        "cases": totals["cases"],
        "teacher_steps": totals["teacher_steps"],
        "student_steps": totals["student_steps"],
        "steps_compared": totals["steps_compared"],
        "step_count_agreement": _rate(totals["step_count_match"], totals["cases"]),
        "behaviour_agreement": _rate(totals["behaviour_match"], totals["steps_compared"]),
        "lane_agreement": _rate(totals["lane_match"], totals["steps_compared"]),
        "lane_agreement_when_both_present": _rate(
            totals["lane_both_present_agree"], totals["lane_both_present"]
        ),
        "lane_both_null": totals["lane_both_null"],
        "lane_teacher_only": totals["lane_teacher_only"],
        "completion_agreement": _rate(totals["completion_match"], totals["steps_compared"]),
        "completion_agreement_when_both_present": _rate(
            totals["completion_both_present_agree"], totals["completion_both_present"]
        ),
        "target_id_agreement": _rate(totals["target_id_match"], totals["target_id_compared"]),
        "target_id_agreement_when_both_present": _rate(
            totals["target_id_both_present_agree"], totals["target_id_both_present"]
        ),
        "target_id_teacher_only": totals["target_id_teacher_only"],
        "speed_mae_mps": (
            totals["speed_abs_error_sum"] / totals["speed_compared"]
        ) if totals["speed_compared"] else None,
        "speed_max_abs_error_mps": totals["speed_max_abs_error"] or None,
        "speed_within_0p5_mps_rate": _rate(
            totals["speed_within_tolerance"], totals["speed_compared"]
        ),
        "speed_missing": totals["speed_missing"],
        "extra_student_steps": totals["extra_student_steps"],
        "missing_student_steps": totals["missing_student_steps"],
    }
    decay = {
        key: (1.0 - value) if isinstance(value, float) else None
        for key, value in summary.items()
        if key.endswith("agreement") and isinstance(value, float)
    }
    return {
        "protocol": {
            "benchmark": "6 frozen held-out cohorts (850 cases) shipped with the releases",
            "teacher_side": "teacher_plan recorded in each frozen case (pinned Qwen teacher)",
            "student_side": "Student ONNX decoded with the same StudentPlanAdapter",
            "comparison": "step-aligned field-by-field comparison; Teacher is the reference",
            "speed_tolerance_mps": SPEED_TOLERANCE_MPS,
        },
        "model": {"onnx": str(onnx_path)},
        "summary": summary,
        "decay": decay,
        "reading": (
            "Teacher agreement is 100% by construction (its own plan is the reference), so the "
            "decay column is the Student-side gap on the same cases: 1 - agreement. This is a "
            "plan-agreement proxy, not an independent accuracy measurement, and it does not "
            "replace B2's frozen benchmark."
        ),
        "field_convention": {
            "lane": (
                "the Teacher fills target_lane='CURRENT' on plain KEEP_LANE steps while the "
                "Student adapter deliberately leaves it null; quote lane_agreement_when_both_present"
            ),
            "speed": (
                "the Student adapter only emits target_speed_mps for SET_SPEED/SLOW_DOWN/FOLLOW, "
                "so the speed comparison only covers the overlapping steps"
            ),
            "target_id": (
                "the Student adapter only emits target_id for FOLLOW/AVOID_OBSTACLE; "
                "'teacher_only' counts steps where the Teacher grounded a target and the Student did not"
            ),
        },
        "per_cohort": per_cohort,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--work", required=True, help="root holding the dumps_* directories")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--limit", type=int, default=0, help="0 means every case")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = run(args.onnx, Path(args.work), Path(args.repo).resolve(), args.limit)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(json.dumps(report["decay"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
