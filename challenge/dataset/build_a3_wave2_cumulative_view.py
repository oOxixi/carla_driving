"""Build a versioned A3 development view including B1 D3 Wave2 safe-short.

The current v3 candidate remains bound to the D2 + D3 Wave1 view.  This module
creates a new, non-overwriting input identity for a possible later candidate.
It accepts only strict-positive rows from B1's detached-signed Wave2 release;
reserved/Frozen Test data is never an input.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
from typing import Any

from challenge.dataset.build_a3_cumulative_view import (
    CUMULATIVE_VIEW_VERSION,
    DEFAULT_D2_RELEASE,
    DEFAULT_D3_RELEASE,
    _derive,
    _relative,
    _rows,
    _write_jsonl,
    build_cumulative_view,
    canonical_json_sha256,
)
from challenge.dataset.validate_d2_release import canonical_text_sha256
from challenge.dataset.validate_d3_wave2_release import (
    D3_DATASET_VERSION as D3_WAVE2_DATASET_VERSION,
    validate_d3_release as validate_d3_wave2_release,
)


WAVE2_CUMULATIVE_VIEW_VERSION = (
    "b1_d2_v1_1_plus_d3_wave1_plus_d3_wave2_safe_short_"
    "a3_strict_positive_v1"
)
DEFAULT_D3_WAVE2_RELEASE = "challenge/dataset/releases/d3_wave2_safe_short_v1"
DEFAULT_OUTPUT = "artifacts/a3_d2_d3_wave2_cumulative_positive_view_v1"


def _restamp(row: dict[str, Any], *, split: str) -> dict[str, Any]:
    metadata = dict(row["metadata"])
    metadata["dataset_version"] = WAVE2_CUMULATIVE_VIEW_VERSION
    metadata["split"] = split
    derived = dict(row)
    derived["metadata"] = metadata
    return derived


def build_wave2_cumulative_view(
    d2_release_dir: Path,
    d3_wave1_release_dir: Path,
    d3_wave2_release_dir: Path,
    output_dir: Path,
    *,
    check_images: bool = True,
) -> dict[str, Any]:
    """Build the exact D2 + D3 Wave1 + D3 Wave2 strict-positive partition."""
    d2_release_dir = d2_release_dir.resolve()
    d3_wave1_release_dir = d3_wave1_release_dir.resolve()
    d3_wave2_release_dir = d3_wave2_release_dir.resolve()
    repo = d2_release_dir.parents[3]
    if any(path.parents[3] != repo for path in (d3_wave1_release_dir, d3_wave2_release_dir)):
        raise ValueError("all source releases must belong to the same repository")

    with tempfile.TemporaryDirectory(prefix="a3-wave2-base-") as temporary:
        base_dir = Path(temporary)
        base_manifest = build_cumulative_view(
            d2_release_dir,
            d3_wave1_release_dir,
            base_dir,
            check_d3_images=check_images,
        )
        base_rows = {
            split: _rows(base_dir / f"{split}.jsonl") for split in ("train", "val")
        }
        excluded = _rows(base_dir / "excluded_sample_ids.jsonl")

    wave2_check = validate_d3_wave2_release(
        d3_wave2_release_dir, check_images=check_images,
    )
    if not wave2_check["valid"]:
        first = wave2_check["errors"][0] if wave2_check["errors"] else "unknown"
        raise ValueError(f"B1 signed D3 Wave2 integrity gate failed: {first}")

    kept: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    cohort_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    manifests = dict(base_manifest["cohort_manifest_shas"])
    for split in ("train", "val"):
        for row in base_rows[split]:
            derived = _restamp(row, split=split)
            kept[split].append(derived)
            cohort_counts[f"{split}:{derived['metadata']['source_dataset_version']}"] += 1

        wave2_name = "train_addition.jsonl" if split == "train" else "val_addition.jsonl"
        for row in _rows(d3_wave2_release_dir / wave2_name):
            derived = _derive(
                row,
                split=split,
                repo=repo,
                source_view=D3_WAVE2_DATASET_VERSION,
            )
            derived = _restamp(derived, split=split)
            kept[split].append(derived)
            metadata = derived["metadata"]
            cohort_counts[f"{split}:{metadata['source_dataset_version']}"] += 1
            family = str(metadata.get("scenario_family") or metadata.get("family") or "UNKNOWN")
            family_counts[f"{split}:{family}"] += 1
            manifests[metadata["teacher_provenance_manifest"]] = metadata[
                "teacher_provenance_manifest_sha256"
            ]

    wave2_hard_negative = _rows(d3_wave2_release_dir / "hard_negative_addition.jsonl")
    for row in wave2_hard_negative:
        excluded.append({
            "sample_id": row["sample_id"],
            "split": "d3_wave2_hard_negative",
            "reason": "B1_D3_WAVE2_HARD_NEGATIVE",
        })

    split_ids: dict[str, set[str]] = {}
    split_groups: dict[str, set[str]] = {}
    for split, rows in kept.items():
        ids = [str(row["sample_id"]) for row in rows]
        groups = [str(row["metadata"].get("group_key") or "") for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {split} sample ID in Wave2 cumulative view")
        if not all(groups):
            raise ValueError(f"missing {split} group key in Wave2 cumulative view")
        split_ids[split] = set(ids)
        split_groups[split] = set(groups)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("Wave2 cumulative Train and Validation sample IDs overlap")
    if split_groups["train"] & split_groups["val"]:
        raise ValueError("Wave2 cumulative Train and Validation group keys overlap")
    excluded_ids = [str(row["sample_id"]) for row in excluded]
    if len(excluded_ids) != len(set(excluded_ids)):
        raise ValueError("duplicate excluded sample ID in Wave2 cumulative view")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("excluded sample reentered Wave2 cumulative supervision")

    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"
    excluded_path = output_dir / "excluded_sample_ids.jsonl"
    _write_jsonl(train_path, kept["train"])
    _write_jsonl(val_path, kept["val"])
    _write_jsonl(excluded_path, excluded)

    source_evidence = {
        "base": {
            "view_version": CUMULATIVE_VIEW_VERSION,
            "source_evidence": base_manifest["source_evidence"],
            "source_evidence_sha256": base_manifest["source_evidence_sha256"],
            "derived_file_sha256": {
                name: base_manifest["files"][name]["sha256"]
                for name in ("train.jsonl", "val.jsonl", "excluded_sample_ids.jsonl")
            },
        },
        "d3_wave2": {
            "release_dir": _relative(repo, d3_wave2_release_dir),
            **wave2_check["evidence"],
        },
    }
    result = {
        "schema_version": "1.0",
        "view_version": WAVE2_CUMULATIVE_VIEW_VERSION,
        "source_evidence": source_evidence,
        "source_evidence_sha256": canonical_json_sha256(source_evidence),
        "cohort_manifest_shas": dict(sorted(manifests.items())),
        "counts": {
            "train": len(kept["train"]),
            "val": len(kept["val"]),
            "excluded": len(excluded),
            "d3_wave2_train_addition": wave2_check["splits"]["train"]["samples"],
            "d3_wave2_val_addition": wave2_check["splits"]["val"]["samples"],
            "d3_wave2_hard_negative_audit_only": len(wave2_hard_negative),
        },
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "d3_wave2_family_counts": dict(sorted(family_counts.items())),
        "files": {
            path.name: {
                "sha256": canonical_text_sha256(path),
                "bytes": len(path.read_bytes().replace(b"\r\n", b"\n")),
            }
            for path in (train_path, val_path, excluded_path)
        },
        "policies": {
            "reserved_test_used": False,
            "frozen_test_used": False,
            "d3_wave1_hard_negative_used_for_training": False,
            "d3_wave2_hard_negative_used_for_training": False,
            "d3_wave2_is_additive_development_not_independent_test": True,
            "current_v3_candidate_identity_unchanged": True,
        },
    }
    manifest_path = output_dir / "a3_cumulative_view_manifest.json"
    manifest_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build signed D2+D3 Wave1+D3 Wave2 A3 development view",
    )
    parser.add_argument("--d2-release-dir", type=Path, default=Path(DEFAULT_D2_RELEASE))
    parser.add_argument(
        "--d3-wave1-release-dir", type=Path, default=Path(DEFAULT_D3_RELEASE),
    )
    parser.add_argument(
        "--d3-wave2-release-dir", type=Path, default=Path(DEFAULT_D3_WAVE2_RELEASE),
    )
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument(
        "--skip-images", action="store_true",
        help="Metadata-only preparation check; forbidden as formal training evidence.",
    )
    args = parser.parse_args()
    result = build_wave2_cumulative_view(
        args.d2_release_dir,
        args.d3_wave1_release_dir,
        args.d3_wave2_release_dir,
        args.output_dir,
        check_images=not args.skip_images,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
