"""Attribute behaviour misses to the model or to the decoder's feasibility mask.

The previous B3 rounds reported that the Student never emits ``TURN_LEFT``
(turn-gap 27/27, gap300 108/108 answered ``SLOW_DOWN``).  That statement is
about the *decoded* plan.  The repository adapter
(``challenge/planner/student_adapter.py``) removes behaviours that contradict
the request's ``scene_capabilities`` before it looks at the logits, so a decoded
miss can come from either of two very different places:

* the model never ranks ``TURN_LEFT`` first (a model/capacity problem), or
* the mask removed ``TURN_LEFT`` even though the model ranked it first
  (a contract/data problem, and retraining cannot fix it).

This script separates the two by recomputing, for every step of every case,
the unrestricted argmax and the masked choice, and comparing both with the
teacher plan and with the decoded plan.

It is a read-only diagnostic over the frozen dumps; it changes no repository
code and produces no accuracy claim.

Usage:
    python3 turn_left_attribution.py --onnx <model.onnx> --dumps <dump_dir> \
        --frozen <snapshot_dir> [--limit N] [--out <json>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from challenge.planner.student_adapter import (
    StudentPlanAdapter,
    _best_allowed,
    _feasible_behaviors,
)
from challenge.student.contract import BEHAVIORS, OUTPUT_NAMES
from challenge.student.preprocess import _expanded_allowed_behaviors


def _teacher_behaviours(case) -> list[str]:
    steps = (case.get("teacher_plan") or {}).get("steps") or []
    return [str(step.get("behavior")) for step in steps]


def _margin_and_rank(logits: np.ndarray, name: str) -> tuple[float, int]:
    """Return (logit[name] - logit[best other], 1-based rank of name)."""
    order = np.argsort(-logits)
    rank = int(np.where(order == BEHAVIORS.index(name))[0][0]) + 1
    top = float(logits[order[0]])
    value = float(logits[BEHAVIORS.index(name)])
    runner_up = float(logits[order[1]]) if order[0] == BEHAVIORS.index(name) else top
    return value - runner_up, rank


def _mask_reason(request, teacher_step: str, allowed) -> str:
    """Say which feasibility rule removed the teacher's behaviour."""
    capabilities = request.get("scene_capabilities") or {}
    constraints = request.get("constraints") or {}
    if teacher_step in {"TURN_LEFT", "TURN_RIGHT", "RETURN_TO_LANE"} and not capabilities.get(
        "route_available", False
    ):
        return "route_available=false"
    if teacher_step in {"TURN_LEFT", "TURN_RIGHT"} and not capabilities.get(
        "intersection_ahead", False
    ):
        return "intersection_ahead=false"
    if teacher_step == "CHANGE_LANE_LEFT" and not (
        capabilities.get("left_lane_exists", False) and capabilities.get("left_gap_safe", False)
    ):
        return "left_lane_exists/left_gap_safe not both true"
    if teacher_step == "CHANGE_LANE_RIGHT" and not (
        capabilities.get("right_lane_exists", False) and capabilities.get("right_gap_safe", False)
    ):
        return "right_lane_exists/right_gap_safe not both true"
    if teacher_step == "PULL_OVER":
        return "SHOULDER not in available_lanes"
    if teacher_step in {"FOLLOW", "AVOID_OBSTACLE"} and not request.get("targets"):
        return "no targets in the request"
    return "not in the request's allowed_behaviors %s" % (constraints.get("allowed_behaviors"),)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--dumps", required=True)
    parser.add_argument("--frozen", required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 means every case")
    parser.add_argument("--out")
    args = parser.parse_args()

    session = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
    names = [i.name for i in session.get_inputs()]
    outputs = [o.name for o in session.get_outputs()]
    adapter = StudentPlanAdapter()

    index = json.loads((Path(args.dumps) / "dump_index.json").read_text(encoding="utf-8"))
    frozen = {}
    for line in (Path(args.frozen) / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            case = json.loads(line)
            frozen[case["case_id"]] = case

    entries = index["dumps"]
    if args.limit:
        entries = entries[: args.limit]

    totals = {
        "cases": 0,
        "steps_compared": 0,
        "decoded_steps": 0,
        "teacher_steps": 0,
        "decoded_match_steps": 0,
        "unrestricted_match_steps": 0,
        "mask_removed_unrestricted_top": 0,
        "mask_removed_teacher_behaviour": 0,
        "teacher_turn_left_steps": 0,
        "teacher_turn_left_unrestricted_top": 0,
        "teacher_turn_left_masked_out": 0,
        "teacher_turn_left_decoded": 0,
    }
    per_behaviour: dict[str, dict[str, int]] = {}
    turn_left_detail: list[dict] = []
    blocked_detail: list[dict] = []

    for entry in entries:
        case = frozen.get(entry["case_id"])
        if case is None:
            continue
        directory = Path(entry["directory"])
        feed = {m: np.load(directory / f"{m}.npy").astype(np.float32) for m in names}
        raw = dict(zip(outputs, session.run(outputs, feed)))
        tensors = {name: torch.from_numpy(array) for name, array in raw.items()}
        missing = [n for n in OUTPUT_NAMES if n not in tensors]
        if missing:
            raise ValueError(f"model is missing outputs {missing}")

        request = case["request"]
        behaviour_logits = raw["behavior_logits"][0]
        step_count = int(behaviour_logits.shape[0])
        feasible = _feasible_behaviors(request, _expanded_allowed_behaviors(request))
        allowed = feasible or {"HOLD"}
        must_stop = bool(request["constraints"]["must_stop"])
        teacher = _teacher_behaviours(case)
        decoded = [step.get("behavior") for step in adapter.decode(request, tensors)["steps"]]

        totals["cases"] += 1
        totals["teacher_steps"] += len(teacher)
        totals["decoded_steps"] += len(decoded)
        for index_step in range(step_count):
            logits = np.asarray(behaviour_logits[index_step], dtype=np.float64)
            unrestricted = BEHAVIORS[int(np.argmax(logits))]
            masked = "STOP" if must_stop else _best_allowed(
                torch.from_numpy(logits.astype(np.float32)), BEHAVIORS, allowed,
            )
            teacher_step = teacher[index_step] if index_step < len(teacher) else None
            decoded_step = decoded[index_step] if index_step < len(decoded) else None
            totals["steps_compared"] += 1
            if teacher_step is not None:
                if decoded_step == teacher_step:
                    totals["decoded_match_steps"] += 1
                if unrestricted == teacher_step:
                    totals["unrestricted_match_steps"] += 1
            if masked != unrestricted:
                totals["mask_removed_unrestricted_top"] += 1
            if teacher_step is not None and teacher_step != masked and teacher_step == unrestricted:
                totals["mask_removed_teacher_behaviour"] += 1

            if teacher_step is not None:
                row = per_behaviour.setdefault(teacher_step, {"steps": 0, "decoded_match": 0,
                                                              "unrestricted_match": 0})
                row["steps"] += 1
                row["decoded_match"] += int(decoded_step == teacher_step)
                row["unrestricted_match"] += int(unrestricted == teacher_step)
                if teacher_step not in allowed:
                    blocked_detail.append({
                        "case_id": entry["case_id"],
                        "step": index_step,
                        "teacher": teacher_step,
                        "unrestricted_argmax": unrestricted,
                        "masked_choice": masked,
                        "decoded_choice": decoded_step,
                        "model_agrees_with_teacher": unrestricted == teacher_step,
                        "reason": _mask_reason(request, teacher_step, allowed),
                    })

            if teacher_step == "TURN_LEFT":
                margin, rank = _margin_and_rank(logits, "TURN_LEFT")
                totals["teacher_turn_left_steps"] += 1
                totals["teacher_turn_left_unrestricted_top"] += int(unrestricted == "TURN_LEFT")
                totals["teacher_turn_left_masked_out"] += int("TURN_LEFT" not in allowed)
                totals["teacher_turn_left_decoded"] += int(decoded_step == "TURN_LEFT")
                turn_left_detail.append({
                    "case_id": entry["case_id"],
                    "step": index_step,
                    "unrestricted_argmax": unrestricted,
                    "masked_choice": masked,
                    "decoded_choice": decoded_step,
                    "turn_left_allowed": "TURN_LEFT" in allowed,
                    "turn_left_logit_margin_vs_best_other": round(margin, 6),
                    "turn_left_logit_rank": rank,
                    "intersection_ahead": bool(
                        (request.get("scene_capabilities") or {}).get("intersection_ahead", False)
                    ),
                    "route_available": bool(
                        (request.get("scene_capabilities") or {}).get("route_available", False)
                    ),
                })

    report = {
        "model": args.onnx,
        "cohort": Path(args.frozen).name,
        "totals": totals,
        "teacher_behaviour_breakdown": per_behaviour,
        "teacher_turn_left_steps": turn_left_detail,
        "mask_blocked_teacher_steps": blocked_detail,
        "reading": (
            "decoded_match vs unrestricted_match separates model misses from mask-induced "
            "misses; mask_removed_unrestricted_top counts steps where the feasibility mask "
            "overrode the model's own first choice"
        ),
        "caveat": "X86 numerical diagnostic on frozen dumps; not an accuracy result",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
