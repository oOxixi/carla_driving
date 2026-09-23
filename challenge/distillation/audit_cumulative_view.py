"""Read-only audit for the signed D2+D3 A3 cumulative development view."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from typing import Any

from challenge.dataset.build_a3_cumulative_view import (
    CUMULATIVE_VIEW_VERSION,
    canonical_json_sha256,
)
from challenge.dataset.build_a3_d2_view import build_view as build_d2_view
from challenge.dataset.validate_d2_release import canonical_text_sha256, validate_release
from challenge.dataset.validate_d3_release import validate_d3_release

from .dataset import load_jsonl


def audit_cumulative_view(
    d2_release_dir: Path,
    d3_release_dir: Path,
    view_dir: Path,
    *,
    check_images: bool = True,
) -> dict[str, Any]:
    d2_release_dir = d2_release_dir.resolve()
    d3_release_dir = d3_release_dir.resolve()
    view_dir = view_dir.resolve()
    repo = d2_release_dir.parents[3]
    d2_check = validate_release(d2_release_dir, check_images=check_images)
    if not d2_check["valid"]:
        raise ValueError("B1 D2 release integrity gate failed")
    d3_check = validate_d3_release(d3_release_dir, check_images=check_images)
    if not d3_check["valid"]:
        raise ValueError("B1 D3 detached-signature integrity gate failed")
    manifest_path = view_dir / "a3_cumulative_view_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("view_version") != CUMULATIVE_VIEW_VERSION:
        raise ValueError("A3 cumulative view version mismatch")
    if manifest.get("source_evidence_sha256") != canonical_json_sha256(
        manifest.get("source_evidence")
    ):
        raise ValueError("A3 cumulative source evidence digest mismatch")
    sources = manifest["source_evidence"]
    if sources["d2"].get("release_manifest_sha256") != canonical_text_sha256(
        d2_release_dir / "release_manifest.json"
    ):
        raise ValueError("A3 cumulative view does not bind this D2 release")
    for field, expected in d3_check["evidence"].items():
        if sources["d3"].get(field) != expected:
            raise ValueError(f"A3 cumulative view D3 evidence mismatch: {field}")
    expected_paths = {
        "d2": d2_release_dir.relative_to(repo).as_posix(),
        "d3": d3_release_dir.relative_to(repo).as_posix(),
    }
    if sources["d2"].get("release_dir") != expected_paths["d2"]:
        raise ValueError("A3 cumulative D2 source path is not portable")
    if sources["d3"].get("release_dir") != expected_paths["d3"]:
        raise ValueError("A3 cumulative D3 source path is not portable")
    for name, details in manifest["files"].items():
        path = view_dir / name
        if canonical_text_sha256(path) != details["sha256"]:
            raise ValueError(f"A3 cumulative view file changed: {name}")
        if len(path.read_bytes().replace(b"\r\n", b"\n")) != details["bytes"]:
            raise ValueError(f"A3 cumulative view file size changed: {name}")
    for relative, expected_sha in manifest["cohort_manifest_shas"].items():
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo) or canonical_text_sha256(path) != expected_sha:
            raise ValueError(f"Teacher cohort manifest changed: {relative}")

    with tempfile.TemporaryDirectory(prefix="a3-d2-audit-") as temporary:
        temporary_path = Path(temporary)
        d2_view = build_d2_view(d2_release_dir, temporary_path)
        for name in ("train.jsonl", "val.jsonl", "excluded_sample_ids.jsonl"):
            if sources["d2"]["derived_file_sha256"].get(name) != d2_view["files"][name]["sha256"]:
                raise ValueError(f"D2 strict-positive derivation changed: {name}")
        d2_rows = {
            split: load_jsonl(temporary_path / f"{split}.jsonl") for split in ("train", "val")
        }
        d2_excluded = load_jsonl(temporary_path / "excluded_sample_ids.jsonl")

    split_ids: dict[str, set[str]] = {}
    group_keys: dict[str, set[str]] = {}
    for split in ("train", "val"):
        rows = load_jsonl(view_dir / f"{split}.jsonl")
        ids = [str(row["sample_id"]) for row in rows]
        groups = [str(row.get("metadata", {}).get("group_key") or "") for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate cumulative {split} sample ID")
        if not all(groups):
            raise ValueError(f"missing cumulative {split} group key")
        if any(
            row.get("metadata", {}).get("dataset_version") != CUMULATIVE_VIEW_VERSION
            or row.get("metadata", {}).get("split") != split
            for row in rows
        ):
            raise ValueError(f"cumulative {split} version/split label mismatch")
        d3_name = "train_addition.jsonl" if split == "train" else "val_addition.jsonl"
        expected_ids = {
            str(row["sample_id"]) for row in d2_rows[split]
        } | {
            str(row["sample_id"]) for row in load_jsonl(d3_release_dir / d3_name)
        }
        if set(ids) != expected_ids:
            raise ValueError(f"cumulative {split} does not exactly partition signed inputs")
        if len(rows) != manifest["counts"][split]:
            raise ValueError(f"cumulative {split} count differs from manifest")
        split_ids[split] = set(ids)
        group_keys[split] = set(groups)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("cumulative Train/Validation sample IDs overlap")
    if group_keys["train"] & group_keys["val"]:
        raise ValueError("cumulative Train/Validation group keys overlap")

    excluded = load_jsonl(view_dir / "excluded_sample_ids.jsonl")
    excluded_ids = [str(row["sample_id"]) for row in excluded]
    expected_excluded = {str(row["sample_id"]) for row in d2_excluded} | {
        str(row["sample_id"])
        for row in load_jsonl(d3_release_dir / "hard_negative_addition.jsonl")
    }
    if len(excluded_ids) != len(set(excluded_ids)) or set(excluded_ids) != expected_excluded:
        raise ValueError("cumulative excluded IDs do not exactly partition audit-only inputs")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("cumulative excluded sample reentered supervision")
    if len(excluded) != manifest["counts"]["excluded"]:
        raise ValueError("cumulative excluded count differs from manifest")
    if manifest.get("policies") != {
        "reserved_test_used": False,
        "d3_hard_negative_used_for_training": False,
        "d3_is_development_coverage_not_unseen_test": True,
    }:
        raise ValueError("cumulative data-use policy changed")
    return {
        "status": "PASS",
        "view_version": CUMULATIVE_VIEW_VERSION,
        "view_manifest_sha256": canonical_text_sha256(manifest_path),
        "source_evidence_sha256": manifest["source_evidence_sha256"],
        "counts": manifest["counts"],
        "images_checked": {
            "d2": d2_check["referenced_images"] if check_images else 0,
            "d3": d3_check["images_checked"],
        },
        "note": "Input integrity only; no Student accuracy or generalization claim is implied.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit D2+D3 A3 cumulative view")
    parser.add_argument("--d2-release-dir", type=Path, default=Path("challenge/dataset/releases/d2_v1_1"))
    parser.add_argument("--d3-release-dir", type=Path, default=Path("challenge/dataset/releases/d3_wave1_addon_v1"))
    parser.add_argument("--view-dir", type=Path, default=Path("artifacts/a3_d2_d3_cumulative_positive_view_v1"))
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_cumulative_view(
        args.d2_release_dir, args.d3_release_dir, args.view_dir,
        check_images=not args.skip_images,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
