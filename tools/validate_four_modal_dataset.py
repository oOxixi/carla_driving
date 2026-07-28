"""Validate every four-modal manifest reference and split invariant."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--cases-file", default="cases_v2.jsonl")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.dataset_dir.resolve()
    rows = [
        json.loads(line)
        for line in (root / args.cases_file).read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    cache: dict[Path, str] = {}
    errors: list[str] = []
    scene_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        case_id = row["case_id"]
        modalities = set(row["scene_state"].get("modalities", {}))
        if modalities != {"voice", "rgb", "lidar", "ego_state"}:
            errors.append(f"{case_id}: invalid modality declaration")
        references = [
            (
                root / row["audio_ref"],
                row["audio_sha256"],
                "audio",
            ),
            (
                root / row["rgb_ref"],
                row["provenance"]["augmentation"]["output_rgb_sha256"],
                "rgb",
            ),
            (
                root / row["perception"]["lidar_summary"]["raw_ref"],
                row["perception"]["lidar_summary"]["raw_sha256"],
                "lidar",
            ),
        ]
        for path, expected, modality in references:
            if not path.is_file():
                errors.append(f"{case_id}: missing {modality}: {path}")
                continue
            actual = cache.get(path)
            if actual is None:
                actual = _sha256(path)
                cache[path] = actual
            if actual != expected:
                errors.append(f"{case_id}: {modality} hash mismatch")
        source_scene_id = row["source_scene_id"]
        scene_splits[source_scene_id].add(row["split"])
        if "较远" in row["expected_transcript"]:
            errors.append(f"{case_id}: ambiguous far-target wording remains")
        if row["category"] == "detector_miss":
            fault = row["perception"].get("detector_fault", {})
            if not fault.get("removed_track_ids"):
                errors.append(f"{case_id}: detector miss has no removed IDs")

    leaking = {
        scene: sorted(splits)
        for scene, splits in scene_splits.items()
        if len(splits) > 1
    }
    if leaking:
        errors.append(f"scene split leakage: {leaking}")
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": args.cases_file,
        "case_count": len(rows),
        "category_counts": dict(Counter(row["category"] for row in rows)),
        "split_counts": dict(Counter(row["split"] for row in rows)),
        "unique_audio_files": len({row["audio_ref"] for row in rows}),
        "unique_rgb_files": len({row["rgb_ref"] for row in rows}),
        "unique_lidar_files": len({
            row["perception"]["lidar_summary"]["raw_ref"] for row in rows
        }),
        "hashed_unique_file_count": len(cache),
        "scene_split_leakage": leaking,
        "error_count": len(errors),
        "errors": errors,
        "valid": not errors and len(rows) > 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
