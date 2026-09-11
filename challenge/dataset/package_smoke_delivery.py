#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_VERSION = "teacher_distill_v0.1_smoke"
TEACHER_MODEL = "Qwen/Qwen3.5-2B"
TEACHER_GIT_SHA = "a05c8b76efcd4c176965223c661f40b153cb1836"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if not path.is_file():
        raise FileNotFoundError(path)

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
                    f"{path}:{line_no}: row is not object"
                )

            rows.append(row)

    return rows


def copy_verified(
    src: Path,
    dst: Path,
) -> dict[str, Any]:
    if not src.is_file():
        raise FileNotFoundError(src)

    dst.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(src, dst)

    return {
        "path": dst.as_posix(),
        "size_bytes": dst.stat().st_size,
        "sha256": sha256_file(dst),
    }


def relative_to_root(
    path: Path,
    root: Path,
) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    parser.add_argument(
        "--output-dir",
        default="challenge/dataset/smoke_v0",
    )

    args = parser.parse_args()

    repo_root = (
        Path(args.repo_root)
        .expanduser()
        .resolve()
    )

    output_dir_arg = Path(args.output_dir)

    if output_dir_arg.is_absolute():
        output_dir = output_dir_arg.resolve()
    else:
        output_dir = (
            repo_root / output_dir_arg
        ).resolve()

    source_dir = (
        repo_root
        / "artifacts"
        / "b1_teacher_smoke"
        / "dataset"
    )

    if not source_dir.is_dir():
        raise SystemExit(
            f"SOURCE_DATASET_DIR_NOT_FOUND={source_dir}"
        )

    data_dir = output_dir / "data"
    manifests_dir = output_dir / "manifests"
    reports_dir = output_dir / "reports"
    rgb_dir = output_dir / "rgb"

    for directory in (
        output_dir,
        data_dir,
        manifests_dir,
        reports_dir,
        rgb_dir,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    source_files: dict[str, tuple[Path, Path]] = {
        "smoke_valid": (
            source_dir / "smoke_valid.jsonl",
            data_dir / "smoke_valid.jsonl",
        ),
        "smoke_with_targets": (
            source_dir / "smoke_with_targets.jsonl",
            data_dir / "smoke_with_targets.jsonl",
        ),
        "smoke_with_policy": (
            source_dir / "smoke_with_policy.jsonl",
            data_dir / "smoke_with_policy.jsonl",
        ),
        "smoke_train_eligible": (
            source_dir / "smoke_train_eligible.jsonl",
            data_dir / "smoke_train_eligible.jsonl",
        ),
        "smoke_hard_cases": (
            source_dir / "smoke_hard_cases.jsonl",
            data_dir / "smoke_hard_cases.jsonl",
        ),
        "smoke_rejected": (
            source_dir / "smoke_rejected.jsonl",
            data_dir / "smoke_rejected.jsonl",
        ),
        "train": (
            source_dir / "splits" / "train.jsonl",
            data_dir / "train.jsonl",
        ),
        "val": (
            source_dir / "splits" / "val.jsonl",
            data_dir / "val.jsonl",
        ),
        "dataset_manifest": (
            source_dir / "dataset_manifest_v0.json",
            manifests_dir / "dataset_manifest_v0.json",
        ),
        "train_manifest": (
            source_dir / "splits" / "train_manifest.json",
            manifests_dir / "train_manifest.json",
        ),
        "val_manifest": (
            source_dir / "splits" / "val_manifest.json",
            manifests_dir / "val_manifest.json",
        ),
        "split_manifest": (
            source_dir / "splits" / "split_manifest.json",
            manifests_dir / "split_manifest.json",
        ),
        "quality_report": (
            source_dir / "dataset_quality_report.md",
            reports_dir / "dataset_quality_report.md",
        ),
        "dataset_schema": (
            repo_root
            / "challenge"
            / "dataset"
            / "dataset_schema.md",
            output_dir
            / "dataset_schema.md",
        ),
    }

    copied_files: dict[str, dict[str, Any]] = {}

    print("===== COPY DATA ARTIFACTS =====")

    for name, (src, dst) in source_files.items():
        info = copy_verified(src, dst)

        info["path"] = relative_to_root(
            dst,
            output_dir,
        )

        copied_files[name] = info

        print(
            f"COPIED {name}: "
            f"{info['path']}"
        )

    raw_samples = read_jsonl(
        source_dir
        / "smoke_with_policy.jsonl"
    )

    train_eligible = read_jsonl(
        source_dir
        / "smoke_train_eligible.jsonl"
    )

    hard_cases = read_jsonl(
        source_dir
        / "smoke_hard_cases.jsonl"
    )

    train_rows = read_jsonl(
        source_dir
        / "splits"
        / "train.jsonl"
    )

    val_rows = read_jsonl(
        source_dir
        / "splits"
        / "val.jsonl"
    )

    rejected_rows = read_jsonl(
        source_dir
        / "smoke_rejected.jsonl"
    )

    if len(raw_samples) != 30:
        raise RuntimeError(
            f"EXPECTED_30_RAW_SAMPLES_GOT={len(raw_samples)}"
        )

    if len(train_eligible) != 28:
        raise RuntimeError(
            "EXPECTED_28_TRAIN_ELIGIBLE_GOT="
            f"{len(train_eligible)}"
        )

    if len(hard_cases) != 2:
        raise RuntimeError(
            f"EXPECTED_2_HARD_CASES_GOT={len(hard_cases)}"
        )

    if len(train_rows) != 22:
        raise RuntimeError(
            f"EXPECTED_22_TRAIN_GOT={len(train_rows)}"
        )

    if len(val_rows) != 6:
        raise RuntimeError(
            f"EXPECTED_6_VAL_GOT={len(val_rows)}"
        )

    if (
        len(train_rows)
        + len(val_rows)
        != len(train_eligible)
    ):
        raise RuntimeError(
            "TRAIN_VAL_PARTITION_MISMATCH"
        )

    print()
    print("===== PACKAGE RGB =====")

    rgb_entries: list[dict[str, Any]] = []
    missing_rgb: list[dict[str, Any]] = []
    unique_rgb: dict[str, str] = {}

    for sample in raw_samples:
        sample_id = sample.get("sample_id")
        visual = sample.get("visual_input")

        if not isinstance(visual, dict):
            missing_rgb.append({
                "sample_id": sample_id,
                "reason": "VISUAL_INPUT_MISSING",
            })
            continue

        rgb_ref = visual.get("rgb_ref")
        expected_sha = visual.get("rgb_sha256")

        if not isinstance(rgb_ref, str) or not rgb_ref:
            missing_rgb.append({
                "sample_id": sample_id,
                "reason": "RGB_REF_MISSING",
            })
            continue

        src_rgb = Path(rgb_ref)

        if not src_rgb.is_absolute():
            src_rgb = repo_root / src_rgb

        src_rgb = src_rgb.resolve()

        if not src_rgb.is_file():
            missing_rgb.append({
                "sample_id": sample_id,
                "rgb_ref": rgb_ref,
                "reason": "RGB_FILE_MISSING",
            })
            continue

        actual_sha = sha256_file(src_rgb)

        if (
            isinstance(expected_sha, str)
            and expected_sha != actual_sha
        ):
            raise RuntimeError(
                "RGB_SHA256_MISMATCH "
                f"sample={sample_id} "
                f"expected={expected_sha} "
                f"actual={actual_sha}"
            )

        suffix = src_rgb.suffix.lower()

        if not suffix:
            suffix = ".jpg"

        packaged_name = (
            actual_sha + suffix
        )

        packaged_path = (
            rgb_dir / packaged_name
        )

        if actual_sha not in unique_rgb:
            shutil.copy2(
                src_rgb,
                packaged_path,
            )

            unique_rgb[actual_sha] = (
                packaged_path
                .relative_to(output_dir)
                .as_posix()
            )

        rgb_entries.append({
            "sample_id": sample_id,
            "original_rgb_ref": rgb_ref,
            "rgb_sha256": actual_sha,
            "packaged_rgb_path": unique_rgb[
                actual_sha
            ],
            "size_bytes": src_rgb.stat().st_size,
        })

    if missing_rgb:
        print(
            "MISSING_RGB_ENTRIES="
            f"{len(missing_rgb)}"
        )

        for row in missing_rgb:
            print(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
            )

        raise RuntimeError(
            "RGB_PACKAGING_INCOMPLETE"
        )

    rgb_manifest = {
        "manifest_schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "sample_count": len(raw_samples),
        "sample_rgb_entries": len(rgb_entries),
        "unique_rgb_files": len(unique_rgb),
        "missing_rgb_entries": 0,
        "entries": rgb_entries,
    }

    rgb_manifest_path = (
        manifests_dir
        / "rgb_manifest.json"
    )

    rgb_manifest_path.write_text(
        json.dumps(
            rgb_manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    readme_lines = [
        "# B1 Teacher Smoke Dataset v0",
        "",
        f"Dataset version: `{DATASET_VERSION}`",
        "",
        "## 1. Purpose",
        "",
        "This is the B1 Teacher-data Smoke Test delivery package.",
        "",
        "Validated pipeline:",
        "",
        "ModelRequest V1 → actual Teacher RGB → "
        "Qwen/Qwen3.5-2B → ManeuverPlan V2 → "
        "closed-loop quality → target pointer → "
        "training policy → group-aware Train/Val split",
        "",
        "## 2. Final Counts",
        "",
        "- Raw structurally valid Teacher samples: 30",
        "- Train-eligible samples: 28",
        "- Quarantined hard cases: 2",
        "- Train samples: 22",
        "- Val samples: 6",
        "- Safety override samples retained: 7",
        "- Run-status inconsistent but command successful: 2",
        "",
        "## 3. Teacher",
        "",
        f"- Model: `{TEACHER_MODEL}`",
        f"- Git SHA: `{TEACHER_GIT_SHA}`",
        "- Planner mode: `planner_v2`",
        "",
        "## 4. Target Pointer Smoke Configuration",
        "",
        "- TopK = 8",
        "- Valid pointers = 0..7",
        "- NO_TARGET = 8",
        "- Candidate order preserves ModelRequest.targets order",
        "- TARGET_OUTSIDE_TOPK must never silently become NO_TARGET",
        "",
        "TopK=8 is a Smoke validation setting, "
        "not the final frozen Student contract.",
        "",
        "## 5. Training Policy",
        "",
        "Raw Teacher supervision is retained separately from "
        "normal supervised training eligibility.",
        "",
        "Train eligible requires:",
        "",
        "- teacher_label_valid = true",
        "- closed_loop_success = true",
        "",
        "Two hard cases are quarantined:",
        "",
        "- ACC_A05_lane_change_left",
        "- SUP_A13_lane_change_right",
        "",
        "Both terminate with `LANE_GAP_UNSAFE`.",
        "",
        "SafetySupervisor intervention does not automatically "
        "invalidate an otherwise successful sample.",
        "",
        "## 6. Train / Val Split",
        "",
        "- Split seed = 1",
        "- Train = 22 samples",
        "- Val = 6 samples",
        "- Train groups = 10",
        "- Val groups = 2",
        "- Group overlap = 0",
        "- Sample ID overlap = 0",
        "",
        "Group definition:",
        "",
        "`scenario_family + map + route_hash + seed`",
        "",
        "Frame-level random splitting is forbidden.",
        "",
        "## 7. Directory Layout",
        "",
        "```text",
        "smoke_v0/",
        "├── README.md",
        "├── dataset_schema.md",
        "├── data/",
        "│   ├── smoke_valid.jsonl",
        "│   ├── smoke_with_targets.jsonl",
        "│   ├── smoke_with_policy.jsonl",
        "│   ├── smoke_train_eligible.jsonl",
        "│   ├── smoke_hard_cases.jsonl",
        "│   ├── smoke_rejected.jsonl",
        "│   ├── train.jsonl",
        "│   └── val.jsonl",
        "├── manifests/",
        "│   ├── dataset_manifest_v0.json",
        "│   ├── train_manifest.json",
        "│   ├── val_manifest.json",
        "│   ├── split_manifest.json",
        "│   ├── rgb_manifest.json",
        "│   └── delivery_manifest.json",
        "├── reports/",
        "│   └── dataset_quality_report.md",
        "└── rgb/",
        "    └── <SHA256>.jpg",
        "```",
        "",
        "## 8. Important",
        "",
        "This Smoke dataset validates the B1 data pipeline.",
        "",
        "It is not the final D3 Train/Val/Test dataset.",
        "",
    ]

    (
        output_dir / "README.md"
    ).write_text(
        "\n".join(readme_lines),
        encoding="utf-8",
    )

    delivery_manifest = {
        "delivery_schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "counts": {
            "raw_teacher_samples": len(
                raw_samples
            ),
            "train_eligible_samples": len(
                train_eligible
            ),
            "hard_cases": len(
                hard_cases
            ),
            "rejected_collection_records": len(
                rejected_rows
            ),
            "train_samples": len(
                train_rows
            ),
            "val_samples": len(
                val_rows
            ),
            "rgb_sample_entries": len(
                rgb_entries
            ),
            "unique_rgb_files": len(
                unique_rgb
            ),
        },
        "teacher": {
            "model_id": TEACHER_MODEL,
            "git_sha": TEACHER_GIT_SHA,
            "planner_mode": "planner_v2",
        },
        "target_pointer": {
            "smoke_top_k": 8,
            "no_target_index": 8,
            "candidate_order_policy": (
                "PRESERVE_MODEL_REQUEST_ORDER"
            ),
        },
        "training_policy": {
            "raw_teacher_samples": 30,
            "train_eligible": 28,
            "quarantined_hard_cases": 2,
            "hard_case_scenarios": [
                "ACC_A05_lane_change_left",
                "SUP_A13_lane_change_right",
            ],
        },
        "split": {
            "seed": 1,
            "train_samples": 22,
            "val_samples": 6,
            "train_groups": 10,
            "val_groups": 2,
            "group_definition": [
                "scenario_family",
                "map",
                "route_hash",
                "seed",
            ],
            "group_overlap": 0,
            "sample_id_overlap": 0,
        },
        "files": copied_files,
        "rgb_manifest": {
            "path": (
                "manifests/rgb_manifest.json"
            ),
            "sha256": sha256_file(
                rgb_manifest_path
            ),
        },
    }

    delivery_manifest_path = (
        manifests_dir
        / "delivery_manifest.json"
    )

    delivery_manifest_path.write_text(
        json.dumps(
            delivery_manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("===== DELIVERY SUMMARY =====")
    print(f"DELIVERY_DIR={output_dir}")
    print(
        f"RAW_TEACHER_SAMPLES={len(raw_samples)}"
    )
    print(
        "TRAIN_ELIGIBLE_SAMPLES="
        f"{len(train_eligible)}"
    )
    print(
        f"HARD_CASES={len(hard_cases)}"
    )
    print(
        f"TRAIN_SAMPLES={len(train_rows)}"
    )
    print(
        f"VAL_SAMPLES={len(val_rows)}"
    )
    print(
        "RGB_SAMPLE_ENTRIES="
        f"{len(rgb_entries)}"
    )
    print(
        "UNIQUE_RGB_FILES="
        f"{len(unique_rgb)}"
    )
    print("MISSING_RGB_ENTRIES=0")
    print("DELIVERY_PACKAGING=PASS")


if __name__ == "__main__":
    main()
