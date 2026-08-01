"""Correct detector-miss cases so every explicit semantic match is removed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.build_qwen_four_modal_stress_set import _mutate_detector


def _read(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = _read(args.dataset_dir / "cases.jsonl")
    baseline = {
        row["case_id"].removesuffix("__baseline"): row
        for row in rows
        if row["category"] == "baseline"
    }
    original_miss = [
        row for row in rows if row["category"] == "detector_miss"
    ]
    corrected: list[dict[str, Any]] = []
    for old in original_miss:
        root_id = old["case_id"].removesuffix("__detector_miss")
        source = baseline[root_id]
        perception, expected = _mutate_detector(source, "detector_miss")
        row = json.loads(json.dumps(old))
        row["case_id"] = f"{root_id}__detector_miss_v2"
        row["category"] = "detector_miss_v2"
        row["perception"] = perception
        row["expected"] = expected
        row["provenance"]["supersedes_case_id"] = old["case_id"]
        row["provenance"]["detector_miss_policy"] = (
            "all high-confidence semantic matches removed"
        )
        corrected.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in corrected
        ),
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output.resolve()),
        "case_count": len(corrected),
        "all_have_detector_fault": all(
            row["perception"].get("detector_fault") for row in corrected
        ),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
