"""Combine completed, hash-verified event experiments into matrix coverage."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.generalization_gate import load_generalization_matrix
from tools.run_s2_optimization_matrix import reevaluate_manifest


def summarize_manifests(paths: list[Path], matrix_path: Path) -> dict:
    matrix = load_generalization_matrix(matrix_path)
    windows = json.loads(matrix_path.read_text(encoding="utf-8"))["event_windows"]
    source_hash = hashlib.sha256((ROOT / "scenarios/official_competition/S2_complex_avoidance_8km.json").read_bytes()).hexdigest()
    attempts: dict[str, list[dict]] = {}
    for path in paths:
        original = json.loads(path.read_text(encoding="utf-8"))
        if original["source_scenario_sha256"] != source_hash:
            raise ValueError("base scenario changed; this matrix requires a separate coverage report")
        checked = reevaluate_manifest(path, matrix_path)
        for task, result in zip(original["results"], checked["results"], strict=True):
            index, event = task["case_index"], task["event"]
            if index < 0 or index >= matrix.samples_per_scenario or event not in windows:
                raise ValueError("task is outside the current matrix")
            # Compare actual perturbation fields, so a reused index cannot silently
            # substitute a different seed, sensor condition, weather or speed.
            expected = asdict(tuple(matrix.cases("OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM"))[index])
            if original["cases"][index]["perturbation"] != expected:
                raise ValueError("perturbations changed; case indices are not interchangeable")
            summary_path = next((path.parent / "runs" / f"case_{index:03d}_{event}").glob("*.summary.json"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            report = result["report"]
            runner_ok = task.get("runner_exit_code") in {0, 1}
            source = (summary.get("provenance") or {}).get("source", {})
            attempts.setdefault(f"{index:03d}:{event}", []).append({
                "manifest": str(path), "finished_at": task.get("finished_at", ""),
                "passed": report["functional_passed"] and runner_ok,
                "runner_exit_code": task.get("runner_exit_code"),
                "failed_checks": [key for key, check in report["checks"].items() if not check["passed"]],
                "git_sha": source.get("git_sha"), "dirty": source.get("dirty"),
                "changes_sha256": source.get("changes_sha256"),
                "summary_sha256": result["summary_sha256"],
                "original_matrix_sha256": original.get("matrix_sha256"),
                "requirements_revised": original["event_windows"][event] != windows[event],
            })
    latest = {key: max(rows, key=lambda row: row["finished_at"]) for key, rows in attempts.items()}
    total = matrix.samples_per_scenario * len(windows)
    passed = sum(row["passed"] for row in latest.values())
    baselines = {(row["git_sha"], row["dirty"], row["changes_sha256"]) for row in latest.values()}
    return {
        "schema_version": "1.0", "scope": "EVENT_MATRIX_COVERAGE", "full_8km": "NOT_EVALUATED",
        "evaluation_matrix_sha256": hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
        "total_tasks": total, "executed_unique_tasks": len(latest),
        "passed_tasks": passed, "failed_tasks": len(latest) - passed,
        "not_run_tasks": total - len(latest),
        "coverage_status": "COMPLETE" if len(latest) == total else "PARTIAL",
        "same_source_tree": len(baselines) == 1,
        "frozen_baseline_gate_passed": passed == total and len(baselines) == 1 and all(
            row["dirty"] is False and isinstance(row["git_sha"], str) and len(row["git_sha"]) == 40
            for row in latest.values()
        ),
        "note": "Latest completed attempt wins. Mixed code versions contribute coverage only, not a frozen-baseline Gate.",
        "latest_tasks": latest, "attempts": attempts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="+", type=Path)
    parser.add_argument("--matrix", type=Path, default=ROOT / "config/s2_optimization_matrix.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new coverage report path")
    report = summarize_manifests([path.resolve() for path in args.manifest], args.matrix.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("passed_tasks", "failed_tasks", "not_run_tasks", "frozen_baseline_gate_passed")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
