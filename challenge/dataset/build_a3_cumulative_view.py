"""Build the signed D2 + detached-signed D3 strict-positive A3 view."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
from typing import Any

from challenge.dataset.build_a3_d2_view import (
    VIEW_VERSION as D2_VIEW_VERSION,
    _cohort_identity,
    _rows,
    _write_jsonl,
    build_view as build_d2_view,
)
from challenge.dataset.validate_d2_release import canonical_text_sha256
from challenge.dataset.validate_d3_release import (
    D3_DATASET_VERSION,
    validate_d3_release,
)


CUMULATIVE_VIEW_VERSION = "b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1"
DEFAULT_D2_RELEASE = "challenge/dataset/releases/d2_v1_1"
DEFAULT_D3_RELEASE = "challenge/dataset/releases/d3_wave1_addon_v1"


def _relative(repo: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(repo):
        raise ValueError(f"source path is outside repository: {path}")
    return resolved.relative_to(repo).as_posix()


def _derive(row: dict[str, Any], *, split: str, repo: Path, source_view: str) -> dict[str, Any]:
    identity = _cohort_identity(repo, row)
    quality = row.get("quality") or {}
    loop = row.get("closed_loop_quality") or {}
    if quality.get("training_role") == "HARD_NEGATIVE" or quality.get("valid_for_training") is not True:
        raise ValueError(f"{row['sample_id']}: non-positive row entered cumulative supervision")
    if (
        loop.get("run_status") != "SUCCEEDED"
        or loop.get("command_terminal_status") != "SUCCEEDED"
        or loop.get("plan_terminal_state") != "SUCCEEDED"
        or loop.get("scenario_acceptance_passed") is not True
    ):
        raise ValueError(f"{row['sample_id']}: terminal non-success entered cumulative supervision")
    metadata = dict(row["metadata"])
    source_dataset = str(metadata.get("source_dataset_version") or row["dataset_version"])
    metadata.update({
        "source_dataset_version": source_dataset,
        "source_view_version": source_view,
        "dataset_version": CUMULATIVE_VIEW_VERSION,
        "split": split,
        "teacher_baseline_git_sha": identity["baseline_sha"],
        "teacher_model_revision": identity["model_revision"],
        "teacher_artifact_fingerprint_sha256": identity["artifact_fingerprint_sha256"],
        "teacher_provenance_manifest": identity["manifest_path"],
        "teacher_provenance_manifest_sha256": identity["manifest_sha256"],
    })
    derived = dict(row)
    derived["metadata"] = metadata
    return derived


def build_cumulative_view(
    d2_release_dir: Path,
    d3_release_dir: Path,
    output_dir: Path,
    *,
    check_d3_images: bool = True,
) -> dict[str, Any]:
    d2_release_dir = d2_release_dir.resolve()
    d3_release_dir = d3_release_dir.resolve()
    repo = d2_release_dir.parents[3]
    if d3_release_dir.parents[3] != repo:
        raise ValueError("D2 and D3 releases must belong to the same repository")
    d3_check = validate_d3_release(d3_release_dir, check_images=check_d3_images)
    if not d3_check["valid"]:
        first = d3_check["errors"][0] if d3_check["errors"] else "unknown"
        raise ValueError(f"B1 signed D3 release integrity gate failed: {first}")

    with tempfile.TemporaryDirectory(prefix="a3-d2-view-") as temporary:
        temporary_path = Path(temporary)
        d2_manifest = build_d2_view(d2_release_dir, temporary_path)
        d2_rows = {
            split: _rows(temporary_path / f"{split}.jsonl") for split in ("train", "val")
        }
        excluded = _rows(temporary_path / "excluded_sample_ids.jsonl")

    kept: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    cohort_counts: Counter[str] = Counter()
    manifests: dict[str, str] = dict(d2_manifest["cohort_manifest_shas"])
    for split in ("train", "val"):
        for row in d2_rows[split]:
            derived = _derive(row, split=split, repo=repo, source_view=D2_VIEW_VERSION)
            kept[split].append(derived)
            cohort_counts[f"{split}:{derived['metadata']['source_dataset_version']}"] += 1
            manifests[
                derived["metadata"]["teacher_provenance_manifest"]
            ] = derived["metadata"]["teacher_provenance_manifest_sha256"]

        d3_filename = "train_addition.jsonl" if split == "train" else "val_addition.jsonl"
        for row in _rows(d3_release_dir / d3_filename):
            derived = _derive(
                row, split=split, repo=repo, source_view=D3_DATASET_VERSION,
            )
            kept[split].append(derived)
            cohort_counts[f"{split}:{derived['metadata']['source_dataset_version']}"] += 1
            manifests[
                derived["metadata"]["teacher_provenance_manifest"]
            ] = derived["metadata"]["teacher_provenance_manifest_sha256"]

    hard_negative_rows = _rows(d3_release_dir / "hard_negative_addition.jsonl")
    for row in hard_negative_rows:
        excluded.append({
            "sample_id": row["sample_id"],
            "split": "d3_hard_negative",
            "reason": "B1_D3_HARD_NEGATIVE",
        })

    split_ids: dict[str, set[str]] = {}
    split_groups: dict[str, set[str]] = {}
    for split, rows in kept.items():
        ids = [str(row["sample_id"]) for row in rows]
        groups = [str(row["metadata"].get("group_key") or "") for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {split} sample ID in cumulative view")
        if not all(groups):
            raise ValueError(f"missing {split} group key in cumulative view")
        split_ids[split] = set(ids)
        split_groups[split] = set(groups)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("cumulative Train and Validation sample IDs overlap")
    if split_groups["train"] & split_groups["val"]:
        raise ValueError("cumulative Train and Validation group keys overlap")
    excluded_ids = [str(row["sample_id"]) for row in excluded]
    if len(excluded_ids) != len(set(excluded_ids)):
        raise ValueError("duplicate excluded sample ID in cumulative view")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("excluded sample reentered cumulative supervision")

    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"
    excluded_path = output_dir / "excluded_sample_ids.jsonl"
    _write_jsonl(train_path, kept["train"])
    _write_jsonl(val_path, kept["val"])
    _write_jsonl(excluded_path, excluded)
    d2_release_sha = canonical_text_sha256(d2_release_dir / "release_manifest.json")
    source_evidence = {
        "d2": {
            "release_dir": _relative(repo, d2_release_dir),
            "release_manifest_sha256": d2_release_sha,
            "derived_view_version": D2_VIEW_VERSION,
            "derived_file_sha256": {
                name: d2_manifest["files"][name]["sha256"]
                for name in ("train.jsonl", "val.jsonl", "excluded_sample_ids.jsonl")
            },
        },
        "d3": {
            "release_dir": _relative(repo, d3_release_dir),
            **d3_check["evidence"],
        },
    }
    source_evidence_sha = canonical_json_sha256(source_evidence)
    result = {
        "schema_version": "1.0",
        "view_version": CUMULATIVE_VIEW_VERSION,
        "source_evidence": source_evidence,
        "source_evidence_sha256": source_evidence_sha,
        "cohort_manifest_shas": dict(sorted(manifests.items())),
        "counts": {
            "train": len(kept["train"]),
            "val": len(kept["val"]),
            "excluded": len(excluded),
            "d3_hard_negative_audit_only": len(hard_negative_rows),
        },
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "files": {
            path.name: {
                "sha256": canonical_text_sha256(path),
                "bytes": len(path.read_bytes().replace(b"\r\n", b"\n")),
            }
            for path in (train_path, val_path, excluded_path)
        },
        "policies": {
            "reserved_test_used": False,
            "d3_hard_negative_used_for_training": False,
            "d3_is_development_coverage_not_unseen_test": True,
        },
    }
    manifest_path = output_dir / "a3_cumulative_view_manifest.json"
    manifest_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def canonical_json_sha256(value: Any) -> str:
    import hashlib

    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build signed D2+D3 A3 cumulative view")
    parser.add_argument("--d2-release-dir", type=Path, default=Path(DEFAULT_D2_RELEASE))
    parser.add_argument("--d3-release-dir", type=Path, default=Path(DEFAULT_D3_RELEASE))
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("artifacts/a3_d2_d3_cumulative_positive_view_v1"),
    )
    parser.add_argument(
        "--skip-d3-images", action="store_true",
        help="Metadata-only developer check; forbidden by the formal training gate.",
    )
    args = parser.parse_args()
    result = build_cumulative_view(
        args.d2_release_dir, args.d3_release_dir, args.output_dir,
        check_d3_images=not args.skip_d3_images,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
