#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(row, dict):
                raise ValueError(
                    f"{path}:{line_no}: row is not a JSON object"
                )

            rows.append(row)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--accepted",
        required=True,
        help="accepted JSONL dataset",
    )

    parser.add_argument(
        "--rejected",
        required=True,
        help="rejected JSONL dataset",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="manifest output path",
    )

    parser.add_argument(
        "--dataset-version",
        default="teacher_distill_v0.1_smoke",
    )

    args = parser.parse_args()

    accepted_path = Path(args.accepted)
    rejected_path = Path(args.rejected)
    output_path = Path(args.output)

    accepted = read_jsonl(accepted_path)
    rejected = read_jsonl(rejected_path)

    teacher_models = Counter()
    teacher_shas = Counter()
    scenarios = Counter()
    maps = Counter()
    difficulties = Counter()
    classes = Counter()
    groups = defaultdict(int)
    rejection_reasons = Counter()

    for sample in accepted:
        metadata = sample.get("metadata") or {}
        sample_class = sample.get("sample_class") or {}

        teacher_models[
            str(metadata.get("teacher_model_id"))
        ] += 1

        teacher_shas[
            str(metadata.get("teacher_git_sha"))
        ] += 1

        scenarios[
            str(metadata.get("scenario_id"))
        ] += 1

        maps[
            str(metadata.get("map"))
        ] += 1

        difficulties[
            str(metadata.get("difficulty"))
        ] += 1

        classes[
            str(sample_class.get("primary"))
        ] += 1

        group_key = metadata.get("group_key")

        if group_key is not None:
            groups[str(group_key)] += 1

    for row in rejected:
        reasons = row.get("rejection_reasons")

        if reasons is None:
            quality = row.get("quality") or {}
            reasons = quality.get("rejection_reasons")

        if not isinstance(reasons, list):
            continue

        for reason in reasons:
            rejection_reasons[str(reason)] += 1

    manifest = {
        "manifest_schema_version": "1.0",
        "dataset_version": args.dataset_version,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "source": {
            "accepted_jsonl": str(accepted_path),
            "rejected_jsonl": str(rejected_path),
            "accepted_sha256": (
                sha256_file(accepted_path)
                if accepted_path.is_file()
                else None
            ),
            "rejected_sha256": (
                sha256_file(rejected_path)
                if rejected_path.is_file()
                else None
            ),
        },

        "counts": {
            "accepted": len(accepted),
            "rejected": len(rejected),
            "effective_teacher_samples": len(accepted),
            "groups": len(groups),
            "scenarios": len(scenarios),
        },

        "teacher": {
            "model_ids": dict(teacher_models),
            "git_shas": dict(teacher_shas),
        },

        "distribution": {
            "scenarios": dict(scenarios),
            "maps": dict(maps),
            "difficulties": dict(difficulties),
            "sample_classes": dict(classes),
            "group_sizes": dict(groups),
        },

        "rejection_reasons": dict(
            rejection_reasons
        ),

        "split_policy": {
            "unit": "group_key",
            "group_definition": [
                "scenario_family",
                "map",
                "route_hash",
                "seed",
            ],
            "frame_level_random_split_forbidden": True,
        },

        "target_policy": {
            "preserve_model_request_order": True,
            "raw_dataset_topk_truncation": False,
            "null_target_is_valid_no_target": True,
        },

        "status": {
            "phase": "SMOKE",
            "test_frozen": False,
            "calibration_frozen": False,
        },
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"MANIFEST_WRITTEN={output_path}")
    print(f"ACCEPTED={len(accepted)}")
    print(f"REJECTED={len(rejected)}")
    print(f"GROUPS={len(groups)}")


if __name__ == "__main__":
    main()
