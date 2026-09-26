"""Fail-closed A3 intake audit for B1's targeted-gap additive release.

Release integrity and training eligibility are separate decisions.  A release
may have valid locked bytes while still being ineligible for formal A3
distillation when its Teacher revision/fingerprint provenance is not signed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from challenge.hil.harness.release_check.verify_b1_release import (
    check_images,
    check_lock,
    check_signed_pass,
)


DATASET_VERSION = "b1_d3_targeted_gap_strict_v1"
DEFAULT_RELEASE = "challenge/dataset/releases/d3_targeted_gap_strict_v1"
PRIOR_SPLITS = {
    "train": (
        "challenge/dataset/releases/d2_v1_1/train.jsonl",
        "challenge/dataset/releases/d3_wave1_addon_v1/train_addition.jsonl",
        "challenge/dataset/releases/d3_wave2_safe_short_v1/train_addition.jsonl",
    ),
    "val": (
        "challenge/dataset/releases/d2_v1_1/val.jsonl",
        "challenge/dataset/releases/d3_wave1_addon_v1/val_addition.jsonl",
        "challenge/dataset/releases/d3_wave2_safe_short_v1/val_addition.jsonl",
    ),
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _teacher_values(row: dict[str, Any]) -> tuple[str, str, str, str]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    plan = row.get("teacher_plan") if isinstance(row.get("teacher_plan"), dict) else {}
    model_id = str(metadata.get("teacher_model_id") or plan.get("model_id") or "")
    git_sha = str(metadata.get("teacher_git_sha") or "")
    revision = str(metadata.get("teacher_model_revision") or plan.get("model_revision") or "")
    fingerprint = str(
        metadata.get("teacher_artifact_fingerprint_sha256")
        or metadata.get("teacher_model_artifact_sha256")
        or ""
    )
    return model_id, git_sha, revision, fingerprint


def _known_teacher_manifests(repo: Path, git_sha: str) -> list[str]:
    matches: list[str] = []
    for path in sorted((repo / "challenge").glob("teacher*manifest*.json")):
        value = _load(path)
        recorded = str(value.get("teacher_git_sha") or value.get("git_sha") or "")
        if recorded == git_sha:
            matches.append(path.relative_to(repo).as_posix())
    return matches


def _prior_partition(repo: Path) -> dict[str, dict[str, set[str]]]:
    result: dict[str, dict[str, set[str]]] = {}
    for split, relatives in PRIOR_SPLITS.items():
        ids: set[str] = set()
        groups: set[str] = set()
        for relative in relatives:
            for row in _rows(repo / relative):
                ids.add(str(row.get("sample_id") or ""))
                metadata = row.get("metadata") or {}
                groups.add(str(metadata.get("group_key") or ""))
        ids.discard("")
        groups.discard("")
        result[split] = {"ids": ids, "groups": groups}
    return result


def audit_targeted_gap_intake(
    release_dir: Path,
    *,
    repo: Path | None = None,
    check_rgb: bool = True,
) -> dict[str, Any]:
    release_dir = release_dir.resolve()
    repo = (repo or release_dir.parents[3]).resolve()
    if not release_dir.is_relative_to(repo):
        raise ValueError("targeted-gap release must be inside the repository")

    release = _load(release_dir / "release_manifest.json")
    signed = check_signed_pass(release_dir, allow_lf_normalise=True)
    lock = check_lock(release_dir, allow_lf_normalise=True)
    image_report = check_images(release_dir, repo) if check_rgb else None
    integrity_failures = list(lock["failures"]) + list(signed["failures"])
    if image_report is not None:
        integrity_failures.extend(image_report["failures"])

    split_rows = {
        "train": _rows(release_dir / "train_addition.jsonl"),
        "val": _rows(release_dir / "val_addition.jsonl"),
        "hard_negative": _rows(release_dir / "hard_negative_addition.jsonl"),
    }
    row_errors: list[str] = []
    ids: dict[str, set[str]] = {}
    groups: dict[str, set[str]] = {}
    teacher_models: set[str] = set()
    teacher_git_shas: set[str] = set()
    teacher_revisions: set[str] = set()
    teacher_fingerprints: set[str] = set()
    for split, rows in split_rows.items():
        split_ids: list[str] = []
        split_groups: set[str] = set()
        for index, row in enumerate(rows):
            sample_id = str(row.get("sample_id") or "")
            metadata = row.get("metadata") or {}
            group = str(metadata.get("group_key") or "")
            quality = row.get("quality") or {}
            loop = row.get("closed_loop_quality") or {}
            if not sample_id or not group:
                row_errors.append(f"{split}:{index}: missing sample_id/group_key")
            if row.get("dataset_version") != DATASET_VERSION:
                row_errors.append(f"{split}:{index}: dataset_version mismatch")
            if split != "hard_negative" and (
                quality.get("training_role") != "POSITIVE"
                or quality.get("valid_for_training") is not True
                or loop.get("run_status") != "SUCCEEDED"
                or loop.get("command_terminal_status") != "SUCCEEDED"
                or loop.get("plan_terminal_state") != "SUCCEEDED"
                or loop.get("scenario_acceptance_passed") is not True
            ):
                row_errors.append(f"{split}:{index}: non-strict-positive row")
            model_id, git_sha, revision, fingerprint = _teacher_values(row)
            if model_id:
                teacher_models.add(model_id)
            if git_sha:
                teacher_git_shas.add(git_sha)
            if revision:
                teacher_revisions.add(revision)
            if fingerprint:
                teacher_fingerprints.add(fingerprint)
            split_ids.append(sample_id)
            split_groups.add(group)
        if len(split_ids) != len(set(split_ids)):
            row_errors.append(f"{split}: duplicate sample IDs")
        ids[split] = set(split_ids)
        groups[split] = split_groups
    if ids["train"] & ids["val"]:
        row_errors.append("targeted-gap Train/Validation sample IDs overlap")
    if groups["train"] & groups["val"]:
        row_errors.append("targeted-gap Train/Validation group keys overlap")

    expected = release.get("counts", {})
    actual_counts = {
        "train": len(split_rows["train"]),
        "val": len(split_rows["val"]),
        "hard_negative": len(split_rows["hard_negative"]),
    }
    for split, release_key in (
        ("train", "train_addition"),
        ("val", "val_addition"),
        ("hard_negative", "hard_negative_addition"),
    ):
        if actual_counts[split] != expected.get(release_key):
            row_errors.append(f"{split}: count differs from release manifest")

    prior = _prior_partition(repo)
    all_prior_ids = prior["train"]["ids"] | prior["val"]["ids"]
    all_new_ids = ids["train"] | ids["val"] | ids["hard_negative"]
    overlap = {
        "sample_ids_with_any_prior_release": len(all_prior_ids & all_new_ids),
        "targeted_train_groups_in_prior_val": len(groups["train"] & prior["val"]["groups"]),
        "targeted_val_groups_in_prior_train": len(groups["val"] & prior["train"]["groups"]),
    }
    if any(overlap.values()):
        row_errors.append("targeted-gap release overlaps prior cumulative partition")

    cohort_git_sha = next(iter(teacher_git_shas)) if len(teacher_git_shas) == 1 else ""
    matching_manifests = _known_teacher_manifests(repo, cohort_git_sha) if cohort_git_sha else []
    blockers: list[str] = []
    if not isinstance(signed.get("teacher"), dict):
        blockers.append("B1_SIGNED_PASS.json does not bind a Teacher identity")
    if not matching_manifests:
        blockers.append("no signed repository Teacher manifest matches the acquisition Git SHA")
    if len(teacher_revisions) != 1:
        blockers.append("rows do not provide one exact Teacher model revision")
    if len(teacher_fingerprints) != 1:
        blockers.append("rows do not provide one exact Teacher artifact fingerprint")
    if teacher_models != {"Qwen/Qwen3.5-2B"}:
        blockers.append("rows do not agree on the required Qwen/Qwen3.5-2B model ID")
    if len(teacher_git_shas) != 1:
        blockers.append("rows do not agree on one Teacher acquisition Git SHA")

    release_integrity = not integrity_failures and not row_errors
    eligible = release_integrity and not blockers
    return {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "status": "READY" if eligible else ("BLOCKED" if release_integrity else "INVALID"),
        "eligible_for_a3_derived_view": eligible,
        "release_integrity": {
            "status": "PASS" if release_integrity else "FAIL",
            "lock_files_checked": lock["files_checked"],
            "signed_digests_claimed": signed["claimed_digests"],
            "signed_digests_not_claimed": signed["not_claimed_digests"],
            "images_checked": image_report["images_in_mapping"] if image_report else 0,
            "image_check_skipped": image_report is None,
            "counts": actual_counts,
            "row_errors": row_errors,
            "failure_count": len(integrity_failures) + len(row_errors),
        },
        "teacher_provenance": {
            "model_ids": sorted(teacher_models),
            "acquisition_git_shas": sorted(teacher_git_shas),
            "model_revisions": sorted(teacher_revisions),
            "artifact_fingerprints": sorted(teacher_fingerprints),
            "matching_repository_manifests": matching_manifests,
            "signed_teacher_block": signed.get("teacher"),
        },
        "prior_release_overlap": overlap,
        "blockers": blockers,
        "required_b1_followup": [
            "publish a pinned Teacher manifest for acquisition Git SHA a6743feb52015031f70e2c21a94aef0abae0a65a",
            "record exact model revision and artifact fingerprint without retroactive inference",
            "bind that Teacher manifest/identity in a detached signed release artifact",
            "reissue or add an immutable provenance addendum without rewriting historical rows",
        ],
        "note": (
            "Byte integrity PASS does not authorize A3 training when exact Teacher "
            "provenance is absent."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=Path(DEFAULT_RELEASE))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_targeted_gap_intake(
        args.release_dir,
        repo=args.repo,
        check_rgb=not args.skip_images,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
