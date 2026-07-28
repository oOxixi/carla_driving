"""Build an unambiguous v2 manifest while reusing immutable RGB/LiDAR files."""
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


def _target_object(row: dict[str, Any]) -> dict[str, Any] | None:
    target = row.get("expected", {}).get("target_track_id")
    return next(
        (
            item
            for item in row.get("perception", {}).get(
                "detected_objects", []
            )
            if item.get("track_id") == target
        ),
        None,
    )


def _canonical_command(target: dict[str, Any]) -> str:
    target_class = str(target.get("class", "")).lower()
    relation = str(target.get("relation", "")).lower()
    distance = round(float(target.get("distance_m", 0.0)))
    if target_class == "pedestrian":
        verb = "减速并避让"
        noun = "行人"
    else:
        verb = "减速并跟随"
        noun = "车辆"
    if "left_adjacent" in relation:
        return f"{verb}左侧相邻车道的{noun}"
    if "right_adjacent" in relation:
        return f"{verb}右侧相邻车道的{noun}"
    if relation == "center_ahead":
        return f"{verb}正前方的{noun}"
    if "occluded" in relation:
        return f"{verb}距离约{distance}米且被部分遮挡的{noun}"
    return f"{verb}距离约{distance}米的{noun}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("cases_v2.jsonl"),
    )
    args = parser.parse_args()
    dataset_dir = args.dataset_dir.resolve()
    rows = _read(dataset_dir / "cases.jsonl")
    baseline = {
        row["case_id"].removesuffix("__baseline"): row
        for row in rows
        if row["category"] == "baseline"
    }
    output_rows: list[dict[str, Any]] = []
    disambiguated = 0
    corrected_misses = 0
    for original in rows:
        row = json.loads(json.dumps(original))
        root_id = row["case_id"].rsplit("__", 1)[0]
        source = baseline[root_id]
        source_target = _target_object(source)
        if row["category"] == "detector_miss":
            row["perception"], row["expected"] = _mutate_detector(
                source, "detector_miss"
            )
            corrected_misses += 1
        if source_target is not None:
            command = _canonical_command(source_target)
            if command != row["expected_transcript"]:
                disambiguated += 1
            row["expected_transcript"] = command
        row.pop("audio_ref", None)
        row.pop("audio_sha256", None)
        row.setdefault("provenance", {})["manifest_v2"] = {
            "source_case_id": original["case_id"],
            "policy": (
                "unambiguous_distance_target_and_semantic_detector_miss"
            ),
        }
        output_rows.append(row)

    output = args.output
    if not output.is_absolute():
        output = dataset_dir / output
    output.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in output_rows
        ),
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "case_count": len(output_rows),
        "distance_disambiguated_count": disambiguated,
        "detector_miss_corrected_count": corrected_misses,
        "media_reused_without_modification": True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
