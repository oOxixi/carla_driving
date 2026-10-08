"""Same-protocol Teacher/Student comparison on the acceptance scenarios.

Every dataset release row records ``metadata.scenario_id`` plus the Teacher's own
closed-loop verdict for that run (``closed_loop_quality.scenario_acceptance_passed``),
and the scenario files live in ``scenarios/acceptance_suite/`` -- the same files
B3 runs with the Student in the decision seat.  That makes a genuinely
same-protocol comparison possible:

* same scenario file, same repository acceptance script, same criteria;
* Teacher side: the recorded runs (several seeds/samples per scenario);
* Student side: one run per scenario from the B3 full-suite run.

It is not the same *moment*: the Teacher rows come from the data-collection runs
on the A800/B1 side, the Student rows from this workstation (seed 0, FP32).  The
report states that explicitly.

Usage::

    py -3.12 -m challenge.hil.harness.x86_sim.teacher_student_protocol_decay \
        --releases <val jsonl files> --suite <suite_full83.json> --out <json>
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

DEFAULT_RELEASES = (
    "challenge/dataset/releases/d2_v1_1/val.jsonl",
    "challenge/dataset/releases/d3_wave2_safe_short_v1/val_addition.jsonl",
    "challenge/dataset/releases/d3_targeted_gap_strict_v1/val_addition.jsonl",
    "challenge/dataset/releases/d3_turn_gap_60_strict_v1/val_addition.jsonl",
    "challenge/dataset/releases/d3_gap300_strict_v1/val_addition.jsonl",
    "challenge/dataset/releases/b1_ms34_supplement_v1/val_addition.jsonl",
)


def teacher_records(paths: list[Path]) -> tuple[dict[str, dict[str, Any]], int]:
    records: dict[str, dict[str, Any]] = {}
    rows = 0
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            metadata = row.get("metadata") or {}
            quality = row.get("closed_loop_quality") or {}
            scenario = metadata.get("scenario_id")
            if not scenario or not quality.get("available"):
                continue
            rows += 1
            entry = records.setdefault(scenario, {
                "runs": 0, "passed": 0,
                "scenario_config_path": metadata.get("scenario_config_path"),
                "seeds": set(),
            })
            entry["runs"] += 1
            if quality.get("scenario_acceptance_passed") is True:
                entry["passed"] += 1
            if metadata.get("seed") is not None:
                entry["seeds"].add(metadata["seed"])
    for entry in records.values():
        entry["seeds"] = sorted(entry["seeds"])[:8]
        entry["pass_rate"] = entry["passed"] / entry["runs"]
    return records, rows


def compare(releases: list[Path], suite_path: Path) -> dict[str, Any]:
    teacher, teacher_rows = teacher_records(releases)
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    student = {row["scenario"]: row for row in suite["scenarios"]}
    shared = sorted(set(teacher) & set(student))
    per_scenario = []
    for scenario in shared:
        t = teacher[scenario]
        s = student[scenario]
        per_scenario.append({
            "scenario": scenario,
            "teacher_runs": t["runs"],
            "teacher_passed": t["passed"],
            "teacher_pass_rate": t["pass_rate"],
            "student_status": s["status"],
            "student_passed": s["status"] == "SUCCEEDED",
            "student_failed_keys": s.get("failed_keys") or [],
            "student_extension_failed_keys": (s.get("extension") or {}).get("failed_keys") or [],
        })
    teacher_macro = statistics.mean(item["teacher_pass_rate"] for item in per_scenario)
    student_macro = statistics.mean(1.0 if item["student_passed"] else 0.0 for item in per_scenario)
    teacher_micro = (
        sum(item["teacher_passed"] for item in per_scenario)
        / sum(item["teacher_runs"] for item in per_scenario)
    )
    return {
        "protocol": {
            "benchmark": "acceptance-suite scenarios that appear in both the release rows and the B3 full run",
            "judging": "the repository's own scenario acceptance (same script, same criteria)",
            "teacher_side": "closed_loop_quality.scenario_acceptance_passed recorded during data collection",
            "student_side": "B3 full-suite run, one run per scenario, seed 0, FP32 in the loop",
            "difference_to_declare": (
                "same scenario files and criteria, but different machines/times/seeds: the Teacher rows come "
                "from the collection runs, the Student rows from this workstation"
            ),
        },
        "coverage": {
            "teacher_scenarios": len(teacher),
            "teacher_rows": teacher_rows,
            "student_scenarios": len(student),
            "shared_scenarios": len(shared),
        },
        "result": {
            "teacher_micro_pass_rate": teacher_micro,
            "teacher_macro_pass_rate": teacher_macro,
            "student_macro_pass_rate": student_macro,
            "relative_decay": 1.0 - student_macro / teacher_macro if teacher_macro else None,
            "student_passed": sum(1 for item in per_scenario if item["student_passed"]),
        },
        "teacher_passed_student_failed": [
            item["scenario"] for item in per_scenario
            if item["teacher_pass_rate"] == 1.0 and not item["student_passed"]
        ],
        "student_passed_teacher_had_failures": [
            item["scenario"] for item in per_scenario
            if item["student_passed"] and item["teacher_pass_rate"] < 1.0
        ],
        "per_scenario": per_scenario,
        "reading": (
            "macro rates treat every scenario equally; the micro rate weights the Teacher by how many runs "
            "it contributed. relative_decay = 1 - student_macro / teacher_macro is the same-protocol decay "
            "estimate for this scenario set, not the official B2 benchmark result"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--releases", nargs="*", default=list(DEFAULT_RELEASES))
    parser.add_argument("--suite", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = compare([Path(item) for item in args.releases], Path(args.suite))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["coverage"], indent=2, ensure_ascii=False))
    print(json.dumps(report["result"], indent=2, ensure_ascii=False))
    print("teacher passed / student failed:", report["teacher_passed_student_failed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
