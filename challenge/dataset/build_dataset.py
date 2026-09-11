#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


VALID_CLASSES = {
    "NORMAL": "normal",
    "COMPLEX": "complex",
    "SAFETY_CRITICAL": "safety_critical",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: record must be object")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )


def normalize_class(sample: dict[str, Any]) -> str:
    sample_class = sample.get("sample_class")
    if not isinstance(sample_class, dict):
        raise ValueError("sample_class must be object")
    primary = str(sample_class.get("primary", "")).upper()
    if primary not in VALID_CLASSES:
        raise ValueError(f"unsupported sample class: {primary!r}")
    return VALID_CLASSES[primary]


def packaged_rgb_path(
    sample: dict[str, Any],
    *,
    package_root: Path | None,
    output_dir: Path,
) -> tuple[str, str | None]:
    visual = sample.get("visual_input")
    if not isinstance(visual, dict):
        raise ValueError("visual_input missing")

    digest = visual.get("rgb_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("visual_input.rgb_sha256 missing or invalid")

    if package_root is None:
        # Preserve original reference only when no portable package is supplied.
        rgb_ref = visual.get("rgb_ref")
        if not isinstance(rgb_ref, str) or not rgb_ref:
            raise ValueError("visual_input.rgb_ref missing")
        return rgb_ref, None

    candidates = list((package_root / "rgb").glob(digest + ".*"))
    if len(candidates) != 1:
        raise ValueError(
            f"expected exactly one packaged RGB for {digest}, found {len(candidates)}"
        )

    rgb_file = candidates[0].resolve()
    if sha256_file(rgb_file) != digest:
        raise ValueError(f"packaged RGB SHA mismatch: {rgb_file}")

    # Store a path portable relative to the training-view JSONL location.
    rel = Path(
        __import__("os").path.relpath(
            rgb_file,
            start=output_dir.resolve(),
        )
    ).as_posix()
    return rel, rgb_file.as_posix()


def build_training_record(
    sample: dict[str, Any],
    *,
    split: str,
    dataset_version: str,
    package_root: Path | None,
    output_dir: Path,
) -> dict[str, Any]:
    if split not in {"train", "val"}:
        raise ValueError(f"unsupported split: {split}")

    model_request = sample.get("model_request")
    teacher_plan = sample.get("teacher_plan")
    metadata = sample.get("metadata")
    quality = sample.get("quality")
    training_policy = sample.get("training_policy")

    if not isinstance(model_request, dict):
        raise ValueError("model_request missing")
    if not isinstance(teacher_plan, dict):
        raise ValueError("teacher_plan missing")
    if not isinstance(metadata, dict):
        raise ValueError("metadata missing")
    if not isinstance(quality, dict):
        raise ValueError("quality missing")
    if not isinstance(training_policy, dict):
        raise ValueError("training_policy missing")
    if training_policy.get("train_eligible") is not True:
        raise ValueError("non-train-eligible sample must not enter Train/Val view")

    if teacher_plan.get("request_id") != model_request.get("request_id"):
        raise ValueError("request_id mismatch")
    if teacher_plan.get("command_id") != model_request.get("command_id"):
        raise ValueError("command_id mismatch")

    normalized_metadata = copy.deepcopy(metadata)
    normalized_metadata["dataset_version"] = dataset_version
    normalized_metadata["split"] = split
    normalized_metadata["sample_class"] = normalize_class(sample)

    portable_ref, resolved_packaged_path = packaged_rgb_path(
        sample,
        package_root=package_root,
        output_dir=output_dir,
    )

    training_input = copy.deepcopy(model_request)
    training_input["rgb_ref"] = portable_ref

    normalized_quality = {
        "schema_valid": bool(
            quality.get("model_request_schema_version_valid")
            and quality.get("maneuver_plan_schema_version_valid")
            and quality.get("request_id_match")
            and quality.get("command_id_match")
            and quality.get("rgb_exists")
            and quality.get("target_grounding_valid")
        ),
        "closed_loop_success": bool(training_policy.get("closed_loop_success")),
        "safety_critical": normalize_class(sample) == "safety_critical",
    }

    record = copy.deepcopy(sample)
    record["dataset_version"] = dataset_version
    record["metadata"] = normalized_metadata
    record["input"] = training_input
    record["teacher"] = {"maneuver_plan": copy.deepcopy(teacher_plan)}
    record["quality"] = normalized_quality

    record["training_view_provenance"] = {
        "source_sample_id": sample.get("sample_id"),
        "source_dataset_version": sample.get("dataset_version"),
        "canonical_rgb_ref": (
            (sample.get("visual_input") or {}).get("rgb_ref")
            if isinstance(sample.get("visual_input"), dict)
            else None
        ),
        "packaged_rgb_ref": portable_ref,
        "packaged_rgb_resolved_at_build": resolved_packaged_path,
    }

    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--val", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument(
        "--package-root",
        help=(
            "Optional delivery package root containing rgb/<sha256>.*. "
            "When supplied, input.rgb_ref is rewritten to a portable path "
            "relative to the output JSONL directory."
        ),
    )
    args = parser.parse_args()

    train_source = Path(args.train)
    val_source = Path(args.val)
    output_dir = Path(args.output_dir)
    package_root = Path(args.package_root).resolve() if args.package_root else None

    train_rows = read_jsonl(train_source)
    val_rows = read_jsonl(val_source)

    converted_train: list[dict[str, Any]] = []
    converted_val: list[dict[str, Any]] = []
    class_counts = {"train": Counter(), "val": Counter()}

    for sample in train_rows:
        record = build_training_record(
            sample,
            split="train",
            dataset_version=args.dataset_version,
            package_root=package_root,
            output_dir=output_dir,
        )
        converted_train.append(record)
        class_counts["train"][record["metadata"]["sample_class"]] += 1

    for sample in val_rows:
        record = build_training_record(
            sample,
            split="val",
            dataset_version=args.dataset_version,
            package_root=package_root,
            output_dir=output_dir,
        )
        converted_val.append(record)
        class_counts["val"][record["metadata"]["sample_class"]] += 1

    train_ids = {x["sample_id"] for x in converted_train}
    val_ids = {x["sample_id"] for x in converted_val}
    overlap = train_ids & val_ids
    if overlap:
        raise RuntimeError("sample ID leakage detected")

    output_dir.mkdir(parents=True, exist_ok=True)
    train_out = output_dir / "train_a3.jsonl"
    val_out = output_dir / "val_a3.jsonl"
    write_jsonl(train_out, converted_train)
    write_jsonl(val_out, converted_val)

    manifest = {
        "source_dataset_version": args.dataset_version,
        "training_view_version": "a3_view_v1",
        "student_contract": "student_v0_r3",
        "view": "A3_DISTILLATION_COMPATIBLE",
        "source_train": str(train_source),
        "source_val": str(val_source),
        "counts": {"train": len(converted_train), "val": len(converted_val)},
        "classes": {
            "train": dict(sorted(class_counts["train"].items())),
            "val": dict(sorted(class_counts["val"].items())),
        },
        "sample_id_overlap": len(overlap),
        "field_mapping": {
            "model_request": "input",
            "teacher_plan": "teacher.maneuver_plan",
            "sample_class.primary": "metadata.sample_class",
            "dataset_version": "metadata.dataset_version",
            "split": "metadata.split",
        },
        "student_contract_limits": {
            "max_steps": 4,
            "max_targets": 8,
            "no_target_index": 8,
        },
        "rgb_policy": {
            "portable_package_root_used": package_root is not None,
            "input_rgb_ref_relative_to_training_view": package_root is not None,
            "canonical_rgb_ref_preserved_in_training_view_provenance": True,
        },
        "raw_fields_preserved": True,
        "files": {
            "train_a3": {
                "path": train_out.name,
                "sha256": sha256_file(train_out),
            },
            "val_a3": {
                "path": val_out.name,
                "sha256": sha256_file(val_out),
            },
        },
    }

    (output_dir / "a3_view_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print(f"TRAIN_RECORDS={len(converted_train)}")
    print(f"VAL_RECORDS={len(converted_val)}")
    print(
        "TRAIN_CLASSES="
        + json.dumps(dict(sorted(class_counts["train"].items())), ensure_ascii=False)
    )
    print(
        "VAL_CLASSES="
        + json.dumps(dict(sorted(class_counts["val"].items())), ensure_ascii=False)
    )
    print(f"SAMPLE_ID_OVERLAP={len(overlap)}")
    print(f"PORTABLE_RGB_REFS={'YES' if package_root is not None else 'NO'}")
    print("A3_VIEW_BUILD=PASS")


if __name__ == "__main__":
    main()
