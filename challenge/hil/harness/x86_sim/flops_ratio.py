"""Compute the FLOPs compression ratio for a declared denominator option.

The scoring rules define ``FLOPs compression ratio = optimised model FLOPs /
original model FLOPs`` with tiers <=0.5 -> 15 points, <=0.7 -> 10, <=0.9 -> 5.
Which model counts as "original" and which operators are counted changes the
denominator by orders of magnitude, so the ratio is only meaningful together
with the option it was computed from.

A1's handoff package publishes the candidate options (``flops_options.json``)
and this tool selects one, recomputes the ratio from numerator/denominator,
cross-checks the numerator against the repository's own Student FLOPs report
and records the rule tier, the scope and the caveats.

Usage::

    py -3.12 -m challenge.hil.harness.x86_sim.flops_ratio \
        --options <A1 package>/challenge/flops_options.json \
        --choice fixed_teacher_conv_linear \
        --student-report challenge/flops_report.json --out <json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def tier_points(ratio: float) -> int:
    if ratio <= 0.5:
        return 15
    if ratio <= 0.7:
        return 10
    if ratio <= 0.9:
        return 5
    return 0


def compute(options_path: Path, choice: str, student_report: Path | None) -> dict[str, Any]:
    options = json.loads(options_path.read_text(encoding="utf-8"))
    candidates = {item["id"]: item for item in options.get("candidates", [])}
    if choice not in candidates:
        raise SystemExit(f"option {choice!r} not in {sorted(candidates)}")
    item = candidates[choice]
    numerator = int(item["numerator"])
    denominator = int(item["denominator"])
    ratio = numerator / denominator
    points = tier_points(ratio)
    record: dict[str, Any] = {
        "chosen_option": choice,
        "baseline": item.get("baseline"),
        "scope": item.get("scope"),
        "numerator_flops": numerator,
        "denominator_flops": denominator,
        "ratio": ratio,
        "ratio_percent": ratio * 100.0,
        "rule_tier": {
            "thresholds": {"<=0.5": 15, "<=0.7": 10, "<=0.9": 5, ">0.9": 0},
            "points_if_accepted": points,
        },
        "package_declared": {
            "ratio": item.get("ratio"),
            "ratio_kind": item.get("ratio_kind"),
            "numeric_le_0p5_under_declared_scope": item.get("numeric_le_0p5_under_declared_scope"),
            "conditional_tier_points": item.get("conditional_tier_points_if_baseline_and_scope_accepted"),
        },
        "options_source": str(options_path),
    }
    if student_report is not None and student_report.is_file():
        report = json.loads(student_report.read_text(encoding="utf-8"))
        repo_flops = report.get("flops_per_fixed_batch") or report.get("flops")
        record["numerator_cross_check"] = {
            "repository_report": str(student_report),
            "flops_per_fixed_batch": repo_flops,
            "matches": repo_flops == numerator,
        }
    record["caveats"] = [
        "the tier is conditional: A1's package keeps formal_ratio_pass = null until the team fixes the denominator",
        "numerator and denominator must come from the same counting scope; do not mix rows",
        "1 MAC = 2 FLOPs; Conv/Linear only unless the option says otherwise",
        "no ASR/NLU, preprocessing, adapter, safety layer or controller is included",
        "the teacher number depends on the declared input fixture (267 prefill tokens, 64 visual, 224x224, batch=1)",
    ]
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--options", required=True)
    parser.add_argument("--choice", default="fixed_teacher_conv_linear")
    parser.add_argument("--student-report", default="challenge/flops_report.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    record = compute(
        Path(args.options),
        args.choice,
        Path(args.student_report) if args.student_report else None,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
