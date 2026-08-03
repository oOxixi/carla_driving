"""Validate frozen target labels against deterministic semantic grounding."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from integration.qwen_vl_adapter import _explicit_target_candidates
from tools.run_qwen_batch_benchmark import _context, _load_cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    cases_path = args.cases.expanduser().resolve()
    cases = _load_cases(cases_path)
    inconsistent: list[dict[str, Any]] = []
    checked = 0
    for index, case in enumerate(cases):
        expected = case.get("expected", {})
        expected_id = expected.get("target_track_id")
        if expected_id is None:
            continue
        checked += 1
        candidates = _explicit_target_candidates(_context(case, None, index))
        candidate_ids = sorted({
            str(item["track_id"])
            for item in candidates or []
            if item.get("track_id") is not None
        })
        if candidate_ids != [str(expected_id)]:
            inconsistent.append({
                "case_id": case["case_id"],
                "category": case.get("category"),
                "voice_command": case.get("voice_command"),
                "expected_target_track_id": expected_id,
                "semantic_candidate_track_ids": candidate_ids,
                "reason": "expected target is not the unique semantic candidate",
            })

    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(cases_path),
        "total_cases": len(cases),
        "target_label_cases": checked,
        "consistent_cases": checked - len(inconsistent),
        "inconsistent_cases": len(inconsistent),
        "valid_for_strict_grounding_rate": (
            (checked - len(inconsistent)) / checked if checked else None
        ),
        "inconsistencies": inconsistent,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "checked": checked,
        "consistent": checked - len(inconsistent),
        "inconsistent": len(inconsistent),
    }, ensure_ascii=False))
    return 0 if not inconsistent else 2


if __name__ == "__main__":
    raise SystemExit(main())
