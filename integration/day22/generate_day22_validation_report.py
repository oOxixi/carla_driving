from __future__ import annotations

import json
from pathlib import Path


RESULTS_PATH = Path("integration/day22/day22_results.json")
REPORT_PATH = Path(
    "integration/day22/day22_validation_report.json"
)


def main() -> None:
    results = json.loads(
        RESULTS_PATH.read_text(encoding="utf-8")
    )

    failed_cases = []

    for item in results:
        decision = item["decision"]

        action_ok = (
            decision["action"]
            == item["expected"]
        )

        confirmation_ok = (
            decision["requires_confirmation"]
            == item["expected_confirmation"]
        )

        if not (action_ok and confirmation_ok):
            failed_cases.append({
                "case": item["case"],
                "expected": item["expected"],
                "actual": decision["action"],
                "expected_confirmation": item[
                    "expected_confirmation"
                ],
                "actual_confirmation": decision[
                    "requires_confirmation"
                ],
            })

    total = len(results)
    passed = total - len(failed_cases)

    report = {
        "schema_version": "1.0",
        "total_cases": total,
        "passed": passed,
        "failed": len(failed_cases),
        "accuracy": passed / total if total else 0.0,
        "failed_cases": failed_cases,
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
