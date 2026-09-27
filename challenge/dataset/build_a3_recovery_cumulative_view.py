"""Build a new A3 view through Wave2, targeted-gap and TURN-gap recovery.

The frozen v3 candidate is not changed.  This builder accepts only validated
strict-positive development rows and produces a separately versioned input for
a possible later candidate.
"""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import tempfile
from typing import Any

from challenge.dataset.build_a3_cumulative_view import (
    _derive,
    _relative,
    _rows,
    _write_jsonl,
    canonical_json_sha256,
)
from challenge.dataset.build_a3_wave2_cumulative_view import (
    DEFAULT_D2_RELEASE,
    DEFAULT_D3_RELEASE,
    DEFAULT_D3_WAVE2_RELEASE,
    WAVE2_CUMULATIVE_VIEW_VERSION,
    build_wave2_cumulative_view,
)
from challenge.dataset.validate_d2_release import canonical_text_sha256
from challenge.dataset.validate_d3_turn_gap_release import (
    DATASET_VERSION as TURN_GAP_VERSION,
    DEFAULT_RELEASE as DEFAULT_TURN_GAP_RELEASE,
    validate_turn_gap_release,
)


RECOVERY_VIEW_VERSION = (
    "b1_d2_v1_1_plus_d3_wave1_plus_d3_wave2_plus_targeted_gap_plus_"
    "turn_gap_a3_strict_positive_v1"
)
TARGETED_GAP_VERSION = "b1_d3_targeted_gap_strict_v1"
DEFAULT_TARGETED_GAP_RELEASE = "challenge/dataset/releases/d3_targeted_gap_strict_v1"
DEFAULT_OUTPUT = "artifacts/a3_d2_d3_recovery_cumulative_positive_view_v1"


def _targeted_gap_audit(
    repo: Path, release_dir: Path, *, check_images: bool,
) -> dict[str, Any]:
    path = repo / "challenge/distillation/audit_targeted_gap_intake.py"
    spec = importlib.util.spec_from_file_location("a3_targeted_gap_intake", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load targeted-gap intake audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_targeted_gap_intake(
        release_dir, repo=repo, check_rgb=check_images,
    )


def _restamp(row: dict[str, Any], *, split: str) -> dict[str, Any]:
    metadata = dict(row["metadata"])
    metadata["dataset_version"] = RECOVERY_VIEW_VERSION
    metadata["split"] = split
    derived = dict(row)
    derived["metadata"] = metadata
    return derived


def build_recovery_cumulative_view(
    d2_release_dir: Path,
    d3_wave1_release_dir: Path,
    d3_wave2_release_dir: Path,
    targeted_gap_release_dir: Path,
    turn_gap_release_dir: Path,
    output_dir: Path,
    *,
    check_images: bool = True,
) -> dict[str, Any]:
    source_dirs = [
        path.resolve() for path in (
            d2_release_dir,
            d3_wave1_release_dir,
            d3_wave2_release_dir,
            targeted_gap_release_dir,
            turn_gap_release_dir,
        )
    ]
    (
        d2_release_dir,
        d3_wave1_release_dir,
        d3_wave2_release_dir,
        targeted_gap_release_dir,
        turn_gap_release_dir,
    ) = source_dirs
    repo = d2_release_dir.parents[3]
    if any(path.parents[3] != repo for path in source_dirs[1:]):
        raise ValueError("all source releases must belong to the same repository")

    with tempfile.TemporaryDirectory(prefix="a3-recovery-base-") as temporary:
        base_dir = Path(temporary)
        base_manifest = build_wave2_cumulative_view(
            d2_release_dir,
            d3_wave1_release_dir,
            d3_wave2_release_dir,
            base_dir,
            check_images=check_images,
        )
        base_rows = {
            split: _rows(base_dir / f"{split}.jsonl") for split in ("train", "val")
        }
        excluded = _rows(base_dir / "excluded_sample_ids.jsonl")

    targeted = _targeted_gap_audit(
        repo, targeted_gap_release_dir, check_images=check_images,
    )
    if targeted["status"] != "READY" or not targeted["eligible_for_a3_derived_view"]:
        raise ValueError("targeted-gap release is not eligible for A3")
    turn = validate_turn_gap_release(
        turn_gap_release_dir, repo=repo, check_rgb=check_images,
    )
    if not turn["valid"]:
        first = turn["errors"][0] if turn["errors"] else "unknown"
        raise ValueError(f"TURN-gap release validation failed: {first}")

    kept: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    cohort_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    manifests = dict(base_manifest["cohort_manifest_shas"])
    additions = (
        ("targeted_gap", targeted_gap_release_dir, TARGETED_GAP_VERSION),
        ("turn_gap", turn_gap_release_dir, TURN_GAP_VERSION),
    )
    for split in ("train", "val"):
        for row in base_rows[split]:
            derived = _restamp(row, split=split)
            kept[split].append(derived)
            cohort_counts[f"{split}:{derived['metadata']['source_dataset_version']}"] += 1
        filename = "train_addition.jsonl" if split == "train" else "val_addition.jsonl"
        for source_name, release_dir, version in additions:
            for row in _rows(release_dir / filename):
                derived = _restamp(
                    _derive(row, split=split, repo=repo, source_view=version),
                    split=split,
                )
                kept[split].append(derived)
                metadata = derived["metadata"]
                cohort_counts[f"{split}:{metadata['source_dataset_version']}"] += 1
                family = str(metadata.get("scenario_id") or metadata.get("scenario_family") or "UNKNOWN")
                family_counts[f"{source_name}:{split}:{family}"] += 1
                manifests[metadata["teacher_provenance_manifest"]] = metadata[
                    "teacher_provenance_manifest_sha256"
                ]

    for source_name, release_dir, _ in additions:
        for row in _rows(release_dir / "hard_negative_addition.jsonl"):
            excluded.append({
                "sample_id": row["sample_id"],
                "split": f"{source_name}_hard_negative",
                "reason": f"B1_{source_name.upper()}_HARD_NEGATIVE",
            })

    split_ids: dict[str, set[str]] = {}
    split_groups: dict[str, set[str]] = {}
    for split, rows in kept.items():
        ids = [str(row["sample_id"]) for row in rows]
        groups = [str(row["metadata"].get("group_key") or "") for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {split} sample ID in recovery view")
        if not all(groups):
            raise ValueError(f"missing {split} group key in recovery view")
        split_ids[split] = set(ids)
        split_groups[split] = set(groups)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("recovery Train and Validation sample IDs overlap")
    if split_groups["train"] & split_groups["val"]:
        raise ValueError("recovery Train and Validation group keys overlap")
    excluded_ids = [str(row["sample_id"]) for row in excluded]
    if len(excluded_ids) != len(set(excluded_ids)):
        raise ValueError("duplicate excluded sample ID in recovery view")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("excluded sample reentered recovery supervision")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "train": output_dir / "train.jsonl",
        "val": output_dir / "val.jsonl",
        "excluded": output_dir / "excluded_sample_ids.jsonl",
    }
    _write_jsonl(paths["train"], kept["train"])
    _write_jsonl(paths["val"], kept["val"])
    _write_jsonl(paths["excluded"], excluded)

    targeted_attestation = targeted["teacher_provenance"]["immutable_attestation"]
    source_evidence = {
        "base_wave2": {
            "view_version": WAVE2_CUMULATIVE_VIEW_VERSION,
            "source_evidence_sha256": base_manifest["source_evidence_sha256"],
            "derived_file_sha256": {
                name: base_manifest["files"][name]["sha256"]
                for name in ("train.jsonl", "val.jsonl", "excluded_sample_ids.jsonl")
            },
        },
        "targeted_gap": {
            "release_dir": _relative(repo, targeted_gap_release_dir),
            "release_manifest_sha256": targeted_attestation["source_release_manifest_sha256"],
            "release_lock_sha256": targeted_attestation["source_release_lock_sha256"],
            "teacher_attestation_path": targeted_attestation["path"],
            "teacher_attestation_sha256": targeted_attestation["attestation_sha256"],
            "teacher_content_binding_sha256": targeted_attestation["content_binding_sha256"],
            "signature_status": targeted_attestation["signature_status"],
        },
        "turn_gap": {
            "release_dir": _relative(repo, turn_gap_release_dir),
            **turn["evidence"],
        },
    }
    result = {
        "schema_version": "1.0",
        "view_version": RECOVERY_VIEW_VERSION,
        "source_evidence": source_evidence,
        "source_evidence_sha256": canonical_json_sha256(source_evidence),
        "cohort_manifest_shas": dict(sorted(manifests.items())),
        "counts": {
            "train": len(kept["train"]),
            "val": len(kept["val"]),
            "excluded": len(excluded),
            "targeted_gap_train_addition": targeted["release_integrity"]["counts"]["train"],
            "targeted_gap_val_addition": targeted["release_integrity"]["counts"]["val"],
            "turn_gap_train_addition": turn["counts"]["train"],
            "turn_gap_val_addition": turn["counts"]["val"],
        },
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "recovery_family_counts": dict(sorted(family_counts.items())),
        "files": {
            path.name: {
                "sha256": canonical_text_sha256(path),
                "bytes": len(path.read_bytes().replace(b"\r\n", b"\n")),
            }
            for path in paths.values()
        },
        "policies": {
            "reserved_test_used": False,
            "frozen_test_used": False,
            "all_hard_negatives_audit_only": True,
            "all_additions_are_development_not_independent_test": True,
            "content_bound_unsigned_provenance_accepted": True,
            "current_v3_candidate_identity_unchanged": True,
        },
    }
    (output_dir / "a3_cumulative_view_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d2-release-dir", type=Path, default=Path(DEFAULT_D2_RELEASE))
    parser.add_argument("--d3-wave1-release-dir", type=Path, default=Path(DEFAULT_D3_RELEASE))
    parser.add_argument("--d3-wave2-release-dir", type=Path, default=Path(DEFAULT_D3_WAVE2_RELEASE))
    parser.add_argument("--targeted-gap-release-dir", type=Path, default=Path(DEFAULT_TARGETED_GAP_RELEASE))
    parser.add_argument("--turn-gap-release-dir", type=Path, default=Path(DEFAULT_TURN_GAP_RELEASE))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--skip-images", action="store_true")
    args = parser.parse_args()
    report = build_recovery_cumulative_view(
        args.d2_release_dir,
        args.d3_wave1_release_dir,
        args.d3_wave2_release_dir,
        args.targeted_gap_release_dir,
        args.turn_gap_release_dir,
        args.output_dir,
        check_images=not args.skip_images,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
