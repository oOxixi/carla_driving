"""Build the governed A3 Final FP32 development view through Gap300.

The published B1 releases stay immutable.  The raw governed release inputs
contain 6,007 Train and 1,154 development rows, but 231 D2 hard negatives are
kept audit-only.  The optimizer-facing strict-positive view therefore contains
5,826 Train and 1,104 development rows.
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
    _relative,
    _rows,
    _write_jsonl,
    canonical_json_sha256,
)
from challenge.dataset.build_a3_recovery_cumulative_view import (
    DEFAULT_D2_RELEASE,
    DEFAULT_D3_RELEASE,
    DEFAULT_D3_WAVE2_RELEASE,
    DEFAULT_TARGETED_GAP_RELEASE,
    DEFAULT_TURN_GAP_RELEASE,
    RECOVERY_VIEW_VERSION,
    build_recovery_cumulative_view,
)
from challenge.dataset.validate_d2_release import canonical_text_sha256


FINAL_VIEW_VERSION = (
    "b1_d2_v1_1_plus_d3_wave1_plus_d3_wave2_plus_targeted_gap_plus_"
    "turn_gap_plus_gap300_a3_strict_positive_v1"
)
GAP300_VERSION = "b1_d3_gap300_strict_v1"
DEFAULT_GAP300_RELEASE = "challenge/dataset/releases/d3_gap300_strict_v1"
DEFAULT_OUTPUT = "artifacts/a3_d2_d3_final_cumulative_positive_view_v1"
TEACHER_V4_GIT_SHA = "95e97b00def8ec36f12937da34ce8bb9082c4a04"
TEACHER_V4_MODEL_ID = "Qwen/Qwen3.5-2B"
TEACHER_V4_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
TEACHER_V4_FINGERPRINT = (
    "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
)
GAP300_ATTESTATION = (
    "challenge/dataset/attestations/"
    "d3_gap300_strict_v1_teacher_provenance_v1/"
    "teacher_provenance_attestation.json"
)
PINNED_V4_MANIFEST = "challenge/teacher_pinned_manifest_v4.json"


def _gap300_audit(repo: Path, release_dir: Path, *, check_images: bool) -> dict[str, Any]:
    path = repo / "challenge/distillation/audit_gap300_intake.py"
    spec = importlib.util.spec_from_file_location("a3_gap300_intake", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Gap300 intake audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_gap300_intake(
        release_dir, repo=repo, check_rgb=check_images,
    )


def _restamp(row: dict[str, Any], *, split: str) -> dict[str, Any]:
    metadata = dict(row["metadata"])
    metadata["dataset_version"] = FINAL_VIEW_VERSION
    metadata["split"] = split
    derived = dict(row)
    derived["metadata"] = metadata
    return derived


def _derive_gap300(
    row: dict[str, Any], *, split: str, repo: Path,
) -> dict[str, Any]:
    quality = row.get("quality") or {}
    loop = row.get("closed_loop_quality") or {}
    if (
        quality.get("training_role") != "POSITIVE"
        or quality.get("valid_for_training") is not True
    ):
        raise ValueError(f"{row['sample_id']}: non-positive Gap300 row entered supervision")
    if (
        loop.get("run_status") != "SUCCEEDED"
        or loop.get("command_terminal_status") != "SUCCEEDED"
        or loop.get("plan_terminal_state") != "SUCCEEDED"
        or loop.get("scenario_acceptance_passed") is not True
    ):
        raise ValueError(f"{row['sample_id']}: failed Gap300 terminal state entered supervision")
    metadata = dict(row["metadata"])
    if metadata.get("teacher_model_id") != TEACHER_V4_MODEL_ID:
        raise ValueError(f"{row['sample_id']}: Gap300 Teacher model mismatch")
    metadata.update({
        "source_dataset_version": str(row.get("dataset_version") or GAP300_VERSION),
        "source_view_version": GAP300_VERSION,
        "dataset_version": FINAL_VIEW_VERSION,
        "split": split,
        "teacher_baseline_git_sha": TEACHER_V4_GIT_SHA,
        "teacher_model_revision": TEACHER_V4_REVISION,
        "teacher_artifact_fingerprint_sha256": TEACHER_V4_FINGERPRINT,
        "teacher_provenance_manifest": GAP300_ATTESTATION,
        "teacher_provenance_manifest_sha256": canonical_text_sha256(
            repo / GAP300_ATTESTATION
        ),
    })
    derived = dict(row)
    derived["metadata"] = metadata
    return derived


def build_final_cumulative_view(
    d2_release_dir: Path,
    d3_wave1_release_dir: Path,
    d3_wave2_release_dir: Path,
    targeted_gap_release_dir: Path,
    turn_gap_release_dir: Path,
    gap300_release_dir: Path,
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
            gap300_release_dir,
        )
    ]
    (
        d2_release_dir,
        d3_wave1_release_dir,
        d3_wave2_release_dir,
        targeted_gap_release_dir,
        turn_gap_release_dir,
        gap300_release_dir,
    ) = source_dirs
    repo = d2_release_dir.parents[3]
    if any(path.parents[3] != repo for path in source_dirs[1:]):
        raise ValueError("all source releases must belong to the same repository")

    with tempfile.TemporaryDirectory(prefix="a3-final-base-") as temporary:
        base_dir = Path(temporary)
        base_manifest = build_recovery_cumulative_view(
            d2_release_dir,
            d3_wave1_release_dir,
            d3_wave2_release_dir,
            targeted_gap_release_dir,
            turn_gap_release_dir,
            base_dir,
            check_images=check_images,
        )
        base_rows = {
            split: _rows(base_dir / f"{split}.jsonl") for split in ("train", "val")
        }
        excluded = _rows(base_dir / "excluded_sample_ids.jsonl")

    gap300 = _gap300_audit(repo, gap300_release_dir, check_images=check_images)
    if gap300["status"] != "READY" or not gap300["eligible_for_a3_final_view"]:
        first = gap300["blockers"][0] if gap300["blockers"] else "unknown"
        raise ValueError(f"Gap300 release is not eligible for A3: {first}")

    kept: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    cohort_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    manifests = dict(base_manifest["cohort_manifest_shas"])
    manifests[GAP300_ATTESTATION] = canonical_text_sha256(repo / GAP300_ATTESTATION)
    manifests[PINNED_V4_MANIFEST] = canonical_text_sha256(repo / PINNED_V4_MANIFEST)

    for split in ("train", "val"):
        for row in base_rows[split]:
            derived = _restamp(row, split=split)
            kept[split].append(derived)
            cohort_counts[f"{split}:{derived['metadata']['source_dataset_version']}"] += 1
        filename = "train_addition.jsonl" if split == "train" else "val_addition.jsonl"
        for row in _rows(gap300_release_dir / filename):
            derived = _derive_gap300(row, split=split, repo=repo)
            kept[split].append(derived)
            metadata = derived["metadata"]
            cohort_counts[f"{split}:{metadata['source_dataset_version']}"] += 1
            family = str(metadata.get("scenario_id") or metadata.get("scenario_family") or "UNKNOWN")
            family_counts[f"{split}:{family}"] += 1

    split_ids: dict[str, set[str]] = {}
    split_groups: dict[str, set[str]] = {}
    for split, rows in kept.items():
        ids = [str(row["sample_id"]) for row in rows]
        groups = [str(row["metadata"].get("group_key") or "") for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {split} sample ID in final view")
        if not all(groups):
            raise ValueError(f"missing {split} group key in final view")
        split_ids[split] = set(ids)
        split_groups[split] = set(groups)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("final Train and Validation sample IDs overlap")
    if split_groups["train"] & split_groups["val"]:
        raise ValueError("final Train and Validation group keys overlap")
    excluded_ids = [str(row["sample_id"]) for row in excluded]
    if len(excluded_ids) != len(set(excluded_ids)):
        raise ValueError("duplicate excluded sample ID in final view")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("excluded sample reentered final supervision")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "train": output_dir / "train.jsonl",
        "val": output_dir / "val.jsonl",
        "excluded": output_dir / "excluded_sample_ids.jsonl",
    }
    _write_jsonl(paths["train"], kept["train"])
    _write_jsonl(paths["val"], kept["val"])
    _write_jsonl(paths["excluded"], excluded)

    attestation = gap300["teacher_provenance"]["immutable_attestation"]
    source_evidence = {
        "recovery_base": {
            "view_version": RECOVERY_VIEW_VERSION,
            "source_evidence_sha256": base_manifest["source_evidence_sha256"],
            "derived_file_sha256": {
                name: base_manifest["files"][name]["sha256"]
                for name in ("train.jsonl", "val.jsonl", "excluded_sample_ids.jsonl")
            },
        },
        "gap300": {
            "release_dir": _relative(repo, gap300_release_dir),
            "release_manifest_sha256": attestation["source_release_manifest_sha256"],
            "release_lock_sha256": attestation["source_release_lock_sha256"],
            "teacher_attestation_path": attestation["path"],
            "teacher_attestation_sha256": attestation["attestation_sha256"],
            "teacher_content_binding_sha256": attestation["content_binding_sha256"],
            "repository_teacher_manifest_sha256": attestation[
                "repository_teacher_manifest_sha256"
            ],
            "signature_status": attestation["signature_status"],
        },
    }
    raw_counts = {"train": 6007, "val": 1154}
    result = {
        "schema_version": "1.0",
        "view_version": FINAL_VIEW_VERSION,
        "source_evidence": source_evidence,
        "source_evidence_sha256": canonical_json_sha256(source_evidence),
        "cohort_manifest_shas": dict(sorted(manifests.items())),
        "counts": {
            "raw_governed_train": raw_counts["train"],
            "raw_governed_val": raw_counts["val"],
            "train": len(kept["train"]),
            "val": len(kept["val"]),
            "excluded": len(excluded),
            "gap300_train_addition": gap300["strict_positive_counts"]["train"],
            "gap300_val_addition": gap300["strict_positive_counts"]["val"],
        },
        "count_policy": {
            "raw_release_rows_are_not_optimizer_rows": True,
            "d2_hard_negative_train_rows": raw_counts["train"] - len(kept["train"]),
            "d2_hard_negative_val_rows": raw_counts["val"] - len(kept["val"]),
            "all_hard_negatives_audit_only": True,
        },
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "gap300_family_counts": dict(sorted(family_counts.items())),
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
            "all_additions_are_development_not_independent_test": True,
            "gap300_exact_teacher_attestation_required": True,
            "content_bound_unsigned_provenance_accepted": True,
            "current_v3_candidate_identity_unchanged": True,
        },
    }
    expected_counts = {"train": 5826, "val": 1104, "excluded": 539}
    for key, expected in expected_counts.items():
        if result["counts"][key] != expected:
            raise ValueError(
                f"final view {key} count changed: {result['counts'][key]} != {expected}"
            )
    (output_dir / "a3_final_view_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d2-release-dir", type=Path, default=Path(DEFAULT_D2_RELEASE))
    parser.add_argument("--d3-wave1-release-dir", type=Path, default=Path(DEFAULT_D3_RELEASE))
    parser.add_argument("--d3-wave2-release-dir", type=Path, default=Path(DEFAULT_D3_WAVE2_RELEASE))
    parser.add_argument("--targeted-gap-release-dir", type=Path, default=Path(DEFAULT_TARGETED_GAP_RELEASE))
    parser.add_argument("--turn-gap-release-dir", type=Path, default=Path(DEFAULT_TURN_GAP_RELEASE))
    parser.add_argument("--gap300-release-dir", type=Path, default=Path(DEFAULT_GAP300_RELEASE))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--skip-images", action="store_true")
    args = parser.parse_args()
    report = build_final_cumulative_view(
        args.d2_release_dir,
        args.d3_wave1_release_dir,
        args.d3_wave2_release_dir,
        args.targeted_gap_release_dir,
        args.turn_gap_release_dir,
        args.gap300_release_dir,
        args.output_dir,
        check_images=not args.skip_images,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
