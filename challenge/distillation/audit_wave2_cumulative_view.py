"""Read-only audit for the prepared D2 + D3 Wave1 + D3 Wave2 A3 view."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from typing import Any

from challenge.dataset.build_a3_cumulative_view import build_cumulative_view, canonical_json_sha256
from challenge.dataset.build_a3_d2_view import _rows
from challenge.dataset.build_a3_wave2_cumulative_view import (
    DEFAULT_D2_RELEASE,
    DEFAULT_D3_WAVE2_RELEASE,
    DEFAULT_OUTPUT,
    WAVE2_CUMULATIVE_VIEW_VERSION,
)
from challenge.dataset.validate_d2_release import canonical_text_sha256
from challenge.dataset.validate_d3_wave2_release import validate_d3_release


POLICIES = {
    "reserved_test_used": False,
    "frozen_test_used": False,
    "d3_wave1_hard_negative_used_for_training": False,
    "d3_wave2_hard_negative_used_for_training": False,
    "d3_wave2_is_additive_development_not_independent_test": True,
    "current_v3_candidate_identity_unchanged": True,
}


def audit_wave2_cumulative_view(
    d2_release_dir: Path,
    d3_wave1_release_dir: Path,
    d3_wave2_release_dir: Path,
    view_dir: Path,
    *,
    check_images: bool = True,
) -> dict[str, Any]:
    d2_release_dir = d2_release_dir.resolve()
    d3_wave1_release_dir = d3_wave1_release_dir.resolve()
    d3_wave2_release_dir = d3_wave2_release_dir.resolve()
    view_dir = view_dir.resolve()
    repo = d2_release_dir.parents[3]

    with tempfile.TemporaryDirectory(prefix="a3-wave2-audit-") as temporary:
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
        base_excluded = _rows(base_dir / "excluded_sample_ids.jsonl")

    wave2_check = validate_d3_release(d3_wave2_release_dir, check_images=check_images)
    if not wave2_check["valid"]:
        raise ValueError("B1 D3 Wave2 detached-signature integrity gate failed")

    manifest_path = view_dir / "a3_cumulative_view_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("view_version") != WAVE2_CUMULATIVE_VIEW_VERSION:
        raise ValueError("A3 Wave2 cumulative view version mismatch")
    if manifest.get("source_evidence_sha256") != canonical_json_sha256(
        manifest.get("source_evidence")
    ):
        raise ValueError("A3 Wave2 source evidence digest mismatch")
    sources = manifest["source_evidence"]
    if sources["base"].get("source_evidence_sha256") != base_manifest[
        "source_evidence_sha256"
    ]:
        raise ValueError("A3 Wave2 view does not bind the current base cumulative view")
    for name, details in base_manifest["files"].items():
        if sources["base"]["derived_file_sha256"].get(name) != details["sha256"]:
            raise ValueError(f"base cumulative derivation changed: {name}")
    expected_wave2_path = d3_wave2_release_dir.relative_to(repo).as_posix()
    if sources["d3_wave2"].get("release_dir") != expected_wave2_path:
        raise ValueError("A3 Wave2 source path is not portable")
    for field, expected in wave2_check["evidence"].items():
        if sources["d3_wave2"].get(field) != expected:
            raise ValueError(f"A3 Wave2 evidence mismatch: {field}")

    for name, details in manifest["files"].items():
        path = view_dir / name
        if canonical_text_sha256(path) != details["sha256"]:
            raise ValueError(f"A3 Wave2 view file changed: {name}")
        if len(path.read_bytes().replace(b"\r\n", b"\n")) != details["bytes"]:
            raise ValueError(f"A3 Wave2 view file size changed: {name}")
    for relative, expected_sha in manifest["cohort_manifest_shas"].items():
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo) or canonical_text_sha256(path) != expected_sha:
            raise ValueError(f"Teacher cohort manifest changed: {relative}")

    split_ids: dict[str, set[str]] = {}
    split_groups: dict[str, set[str]] = {}
    for split in ("train", "val"):
        rows = _rows(view_dir / f"{split}.jsonl")
        ids = [str(row["sample_id"]) for row in rows]
        groups = [str(row.get("metadata", {}).get("group_key") or "") for row in rows]
        wave2_name = "train_addition.jsonl" if split == "train" else "val_addition.jsonl"
        expected_ids = {str(row["sample_id"]) for row in base_rows[split]} | {
            str(row["sample_id"]) for row in _rows(d3_wave2_release_dir / wave2_name)
        }
        if len(ids) != len(set(ids)) or set(ids) != expected_ids:
            raise ValueError(f"Wave2 cumulative {split} does not exactly partition inputs")
        if not all(groups):
            raise ValueError(f"missing Wave2 cumulative {split} group key")
        if any(
            row.get("metadata", {}).get("dataset_version")
            != WAVE2_CUMULATIVE_VIEW_VERSION
            or row.get("metadata", {}).get("split") != split
            for row in rows
        ):
            raise ValueError(f"Wave2 cumulative {split} version/split label mismatch")
        if len(rows) != manifest["counts"][split]:
            raise ValueError(f"Wave2 cumulative {split} count differs from manifest")
        split_ids[split] = set(ids)
        split_groups[split] = set(groups)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("Wave2 cumulative Train/Validation sample IDs overlap")
    if split_groups["train"] & split_groups["val"]:
        raise ValueError("Wave2 cumulative Train/Validation group keys overlap")

    excluded = _rows(view_dir / "excluded_sample_ids.jsonl")
    expected_excluded = {str(row["sample_id"]) for row in base_excluded} | {
        str(row["sample_id"])
        for row in _rows(d3_wave2_release_dir / "hard_negative_addition.jsonl")
    }
    excluded_ids = [str(row["sample_id"]) for row in excluded]
    if len(excluded_ids) != len(set(excluded_ids)) or set(excluded_ids) != expected_excluded:
        raise ValueError("Wave2 cumulative excluded IDs do not exactly partition inputs")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("Wave2 cumulative excluded sample reentered supervision")
    if manifest.get("policies") != POLICIES:
        raise ValueError("Wave2 cumulative data-use policy changed")
    return {
        "status": "PASS",
        "view_version": WAVE2_CUMULATIVE_VIEW_VERSION,
        "view_manifest_sha256": canonical_text_sha256(manifest_path),
        "source_evidence_sha256": manifest["source_evidence_sha256"],
        "counts": manifest["counts"],
        "images_checked": {
            "d3_wave2": wave2_check["images_checked"] if check_images else 0,
        },
        "note": (
            "Development input integrity only; the current v3 candidate and B2 Gate "
            "identity are unchanged."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit prepared A3 Wave2 cumulative view")
    parser.add_argument("--d2-release-dir", type=Path, default=Path(DEFAULT_D2_RELEASE))
    parser.add_argument(
        "--d3-wave1-release-dir", type=Path,
        default=Path("challenge/dataset/releases/d3_wave1_addon_v1"),
    )
    parser.add_argument(
        "--d3-wave2-release-dir", type=Path, default=Path(DEFAULT_D3_WAVE2_RELEASE),
    )
    parser.add_argument("--view-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_wave2_cumulative_view(
        args.d2_release_dir,
        args.d3_wave1_release_dir,
        args.d3_wave2_release_dir,
        args.view_dir,
        check_images=not args.skip_images,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
