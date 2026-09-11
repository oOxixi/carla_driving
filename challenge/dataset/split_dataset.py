#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPLIT_SCHEMA_VERSION = "1.0"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

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


def write_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def get_metadata(
    sample: dict[str, Any],
) -> dict[str, Any]:
    metadata = sample.get("metadata")

    if not isinstance(metadata, dict):
        raise ValueError(
            f"sample {sample.get('sample_id')} missing metadata"
        )

    return metadata


def get_group_key(
    sample: dict[str, Any],
) -> str:
    metadata = get_metadata(sample)

    group_key = metadata.get("group_key")

    if not isinstance(group_key, str) or not group_key:
        raise ValueError(
            f"sample {sample.get('sample_id')} missing group_key"
        )

    return group_key


def get_group_signature(
    sample: dict[str, Any],
) -> tuple[Any, Any, Any, Any]:
    metadata = get_metadata(sample)

    return (
        metadata.get("scenario_family"),
        metadata.get("map"),
        metadata.get("route_hash"),
        metadata.get("seed"),
    )


def validate_groups(
    rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    signatures: dict[str, tuple[Any, Any, Any, Any]] = {}

    seen_sample_ids: set[str] = set()

    for sample in rows:
        sample_id = sample.get("sample_id")

        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(
                "sample without valid sample_id"
            )

        if sample_id in seen_sample_ids:
            raise ValueError(
                f"duplicate sample_id: {sample_id}"
            )

        seen_sample_ids.add(sample_id)

        group_key = get_group_key(sample)
        signature = get_group_signature(sample)

        if group_key in signatures:
            if signatures[group_key] != signature:
                raise ValueError(
                    "group_key collision/inconsistency: "
                    f"{group_key}: "
                    f"{signatures[group_key]} != {signature}"
                )
        else:
            signatures[group_key] = signature

        groups[group_key].append(sample)

    return dict(groups)


def group_class_counts(
    samples: list[dict[str, Any]],
) -> Counter:
    counter = Counter()

    for sample in samples:
        sample_class = sample.get("sample_class") or {}

        if isinstance(sample_class, dict):
            value = sample_class.get("primary")
        else:
            value = None

        counter[str(value)] += 1

    return counter


def choose_val_groups(
    groups: dict[str, list[dict[str, Any]]],
    val_ratio: float,
    seed: int,
) -> set[str]:
    total_samples = sum(
        len(samples)
        for samples in groups.values()
    )

    if len(groups) < 2:
        raise ValueError(
            "need at least 2 groups for Train/Val split"
        )

    target_val_samples = max(
        1,
        round(total_samples * val_ratio),
    )

    group_keys = sorted(groups.keys())

    rng = random.Random(seed)
    rng.shuffle(group_keys)

    # Larger groups first helps the greedy search converge quickly.
    group_keys.sort(
        key=lambda key: len(groups[key]),
        reverse=True,
    )

    selected: set[str] = set()
    current = 0

    while group_keys:
        best_key = None
        best_distance = None

        for key in group_keys:
            candidate = current + len(groups[key])
            distance = abs(
                candidate - target_val_samples
            )

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_distance = distance
                best_key = key

        if best_key is None:
            break

        before_distance = abs(
            current - target_val_samples
        )

        after_distance = abs(
            current
            + len(groups[best_key])
            - target_val_samples
        )

        # Always choose at least one validation group.
        if selected and after_distance > before_distance:
            break

        selected.add(best_key)
        current += len(groups[best_key])
        group_keys.remove(best_key)

        if current >= target_val_samples:
            break

    if not selected:
        selected.add(
            min(
                groups.keys(),
                key=lambda key: len(groups[key]),
            )
        )

    # Never assign every group to validation.
    if len(selected) == len(groups):
        largest_selected = max(
            selected,
            key=lambda key: len(groups[key]),
        )
        selected.remove(largest_selected)

    return selected


def build_split(
    rows: list[dict[str, Any]],
    groups: dict[str, list[dict[str, Any]]],
    val_groups: set[str],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []

    for sample in rows:
        group_key = get_group_key(sample)

        if group_key in val_groups:
            val.append(sample)
        else:
            train.append(sample)

    return train, val


def assert_no_leakage(
    train: list[dict[str, Any]],
    val: list[dict[str, Any]],
) -> None:
    train_groups = {
        get_group_key(sample)
        for sample in train
    }

    val_groups = {
        get_group_key(sample)
        for sample in val
    }

    overlap = train_groups & val_groups

    if overlap:
        raise ValueError(
            "GROUP_LEAKAGE_DETECTED: "
            + ",".join(sorted(overlap))
        )

    train_ids = {
        str(sample.get("sample_id"))
        for sample in train
    }

    val_ids = {
        str(sample.get("sample_id"))
        for sample in val
    }

    sample_overlap = train_ids & val_ids

    if sample_overlap:
        raise ValueError(
            "SAMPLE_ID_LEAKAGE_DETECTED: "
            + ",".join(sorted(sample_overlap))
        )


def build_manifest(
    *,
    split_name: str,
    rows: list[dict[str, Any]],
    output_path: Path,
    dataset_version: str,
) -> dict[str, Any]:
    groups = Counter()
    scenarios = Counter()
    classes = Counter()
    maps = Counter()
    teacher_models = Counter()
    teacher_shas = Counter()

    for sample in rows:
        metadata = get_metadata(sample)

        groups[
            str(metadata.get("group_key"))
        ] += 1

        scenarios[
            str(metadata.get("scenario_id"))
        ] += 1

        maps[
            str(metadata.get("map"))
        ] += 1

        teacher_models[
            str(metadata.get("teacher_model_id"))
        ] += 1

        teacher_shas[
            str(metadata.get("teacher_git_sha"))
        ] += 1

        sample_class = sample.get("sample_class") or {}

        if isinstance(sample_class, dict):
            classes[
                str(sample_class.get("primary"))
            ] += 1

    manifest = {
        "manifest_schema_version": SPLIT_SCHEMA_VERSION,
        "dataset_version": dataset_version,
        "split": split_name,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "file": str(output_path),
        "sha256": sha256_file(output_path),
        "counts": {
            "samples": len(rows),
            "groups": len(groups),
            "scenarios": len(scenarios),
        },
        "distribution": {
            "groups": dict(groups),
            "scenarios": dict(scenarios),
            "maps": dict(maps),
            "sample_classes": dict(classes),
        },
        "teacher": {
            "model_ids": dict(teacher_models),
            "git_shas": dict(teacher_shas),
        },
    }

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.20,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20260911,
    )

    parser.add_argument(
        "--dataset-version",
        default="teacher_distill_v0.1_smoke",
    )

    args = parser.parse_args()

    if not 0.05 <= args.val_ratio <= 0.50:
        raise SystemExit(
            "--val-ratio must be between 0.05 and 0.50"
        )

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    rows = read_jsonl(input_path)

    if len(rows) < 2:
        raise SystemExit(
            "dataset must contain at least 2 samples"
        )

    groups = validate_groups(rows)

    val_groups = choose_val_groups(
        groups,
        args.val_ratio,
        args.seed,
    )

    train, val = build_split(
        rows,
        groups,
        val_groups,
    )

    if not train:
        raise SystemExit(
            "Train split is empty"
        )

    if not val:
        raise SystemExit(
            "Val split is empty"
        )

    assert_no_leakage(
        train,
        val,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"

    write_jsonl(
        train_path,
        train,
    )

    write_jsonl(
        val_path,
        val,
    )

    train_manifest = build_manifest(
        split_name="train",
        rows=train,
        output_path=train_path,
        dataset_version=args.dataset_version,
    )

    val_manifest = build_manifest(
        split_name="val",
        rows=val,
        output_path=val_path,
        dataset_version=args.dataset_version,
    )

    write_json(
        output_dir / "train_manifest.json",
        train_manifest,
    )

    write_json(
        output_dir / "val_manifest.json",
        val_manifest,
    )

    train_groups = sorted(
        {
            get_group_key(sample)
            for sample in train
        }
    )

    val_groups_sorted = sorted(
        {
            get_group_key(sample)
            for sample in val
        }
    )

    split_manifest = {
        "split_schema_version": SPLIT_SCHEMA_VERSION,
        "dataset_version": args.dataset_version,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_dataset": str(input_path),
        "source_sha256": sha256_file(input_path),
        "seed": args.seed,
        "requested_val_ratio": args.val_ratio,
        "actual_val_ratio": (
            len(val) / len(rows)
        ),
        "group_definition": [
            "scenario_family",
            "map",
            "route_hash",
            "seed",
        ],
        "counts": {
            "total_samples": len(rows),
            "total_groups": len(groups),
            "train_samples": len(train),
            "train_groups": len(train_groups),
            "val_samples": len(val),
            "val_groups": len(val_groups_sorted),
        },
        "train_group_keys": train_groups,
        "val_group_keys": val_groups_sorted,
        "leakage_checks": {
            "group_overlap": 0,
            "sample_id_overlap": 0,
            "passed": True,
        },
    }

    write_json(
        output_dir / "split_manifest.json",
        split_manifest,
    )

    print(f"TOTAL_SAMPLES={len(rows)}")
    print(f"TOTAL_GROUPS={len(groups)}")
    print(f"TRAIN_SAMPLES={len(train)}")
    print(f"TRAIN_GROUPS={len(train_groups)}")
    print(f"VAL_SAMPLES={len(val)}")
    print(f"VAL_GROUPS={len(val_groups_sorted)}")
    print(
        "ACTUAL_VAL_RATIO="
        f"{len(val) / len(rows):.4f}"
    )

    print()
    print("TRAIN_CLASSES")

    for key, value in sorted(
        group_class_counts(train).items()
    ):
        print(f"{key}={value}")

    print()
    print("VAL_CLASSES")

    for key, value in sorted(
        group_class_counts(val).items()
    ):
        print(f"{key}={value}")

    print()
    print("GROUP_LEAKAGE=0")
    print("SAMPLE_ID_LEAKAGE=0")
    print("SPLIT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
