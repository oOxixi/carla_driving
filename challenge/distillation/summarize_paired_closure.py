"""Summarize the complete project matrix without dropping missing or failed runs."""

import json
import sys
from collections import Counter
from pathlib import Path

from summarise_student_loop import _suite_groups


def summarize(root: Path) -> dict:
    matrix = root / "matrix.json"
    entries = json.loads(matrix.read_text(encoding="utf-8"))["scenarios"]
    expected = {r["scenario_id"]: r["suite_group"] for r in entries}
    if len(expected) != len(entries) or dict(Counter(expected.values())) != {
        "basic_scoring": 18, "advanced_scoring": 30, "challenge_scoring": 24,
        "complex_regression": 6, "system_stability": 5,
    } or {p.stem for p in (root / "cases").glob("*.json")} != set(expected):
        raise ValueError("Not the complete original 83-scenario matrix")
    rows = []
    missing = []
    for name in expected:
        pair = {"scenario": name, "group": expected[name]}
        for role in ("teacher", "student"):
            run = root / name / role
            verdict = run / "acceptance.json"
            summaries = list((run / "evidence").glob("*.summary.json"))
            if not verdict.is_file() or not (run / "exit_code.txt").is_file():
                missing.append((name, role))
                continue
            records = [json.loads(line) for line in verdict.read_text(encoding="utf-8").splitlines()]
            if len(records) != 1 or len(summaries) != 1 or (run / "exit_code.txt").read_text().strip() != "0":
                missing.append((name, role))
                continue
            record = records[0]
            summary = json.loads(summaries[0].read_text(encoding="utf-8"))
            if record.get("scenario") != name or record.get("status") not in {"SUCCEEDED", "FAILED"} or record["status"] != summary.get("status"):
                raise ValueError(f"Unbound verdict: {name} / {role}")
            extension = ((summary.get("acceptance") or {}).get("metrics") or {}).get("extension_acceptance") or {}
            pair[role] = {
                "scenario": name,
                "status": record["status"],
                "failed_keys": record.get("failed_keys"),
                "extension_failed_keys": extension.get("failed_keys"),
                "safety": {key: summary.get(key) for key in (
                    "collision_count", "red_light_violation_count", "serious_route_deviation",
                )},
            }
        rows.append(pair)
    report = {"scope": "FULL_PROJECT_CARLA83_NOT_OFFICIAL_HOLDOUT_OR_J6P",
              "verdicts_collected": 166 - len(missing), "missing_verdicts": missing,
              "relative_decay": None, "weighted_project_3pct_line_met": None, "pairs": rows}
    if not missing:
        report["roles"] = {
            role: _suite_groups({"scenarios": [row[role] for row in rows]}, matrix)
            for role in ("teacher", "student")
        }
        teacher, student = (report["roles"][role]["weighted_completion_rate"] for role in ("teacher", "student"))
        if teacher > 0:
            decay = (teacher - student) / teacher
            report.update(relative_decay=decay, weighted_project_3pct_line_met=decay <= 0.03 + 1e-12)
    return report


if __name__ == "__main__":
    root = Path(sys.argv[1])
    report = summarize(root)
    temporary = root / "paired_report.json.tmp"
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(root / "paired_report.json")
    print({k: report[k] for k in ("verdicts_collected", "relative_decay", "weighted_project_3pct_line_met")})
