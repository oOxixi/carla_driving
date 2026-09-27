"""Fail-closed A3 intake audit for B1's targeted-gap additive release.

Release integrity and training eligibility are separate decisions.  A release
may have valid locked bytes while still being ineligible for formal A3
distillation when its Teacher revision/fingerprint provenance is not signed.
"""

from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_ATTESTATION = (
    "challenge/dataset/attestations/"
    "d3_targeted_gap_strict_v1_teacher_provenance_v1"
)
EXPECTED_MODEL_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
EXPECTED_ARTIFACT_FINGERPRINT = (
    "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
)
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


def _canonical_text_sha256(path: Path) -> str:
    """Hash repository text bytes independent of Git's CRLF checkout mode."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _validate_attestation(
    repo: Path,
    release_dir: Path,
    *,
    cohort_git_sha: str,
    sample_count: int,
) -> dict[str, Any]:
    """Validate B1's immutable content-bound Teacher provenance supplement."""
    directory = repo / DEFAULT_ATTESTATION
    errors: list[str] = []
    required = (
        "teacher_model_manifest.json",
        "teacher_provenance_attestation.json",
        "attestation_lock.sha256",
    )
    for name in required:
        if not (directory / name).is_file():
            errors.append(f"Teacher attestation file missing: {name}")
    repository_manifest = repo / "challenge/teacher_targeted_gap_manifest.json"
    if not repository_manifest.is_file():
        errors.append("repository targeted-gap Teacher manifest is missing")
    if errors:
        return {"valid": False, "errors": errors, "path": DEFAULT_ATTESTATION}

    lock_entries: dict[str, str] = {}
    for line in (directory / "attestation_lock.sha256").read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if not separator or name in lock_entries:
            errors.append("malformed or duplicate Teacher attestation lock entry")
            continue
        lock_entries[name] = digest
    expected_locked = {"teacher_model_manifest.json", "teacher_provenance_attestation.json"}
    if set(lock_entries) != expected_locked:
        errors.append("Teacher attestation lock file set mismatch")
    for name, digest in lock_entries.items():
        path = directory / name
        if not path.is_file() or _canonical_text_sha256(path) != digest:
            errors.append(f"Teacher attestation lock mismatch: {name}")

    attestation = _load(directory / "teacher_provenance_attestation.json")
    model_artifact = _load(directory / "teacher_model_manifest.json")
    repository_teacher = _load(repository_manifest)
    payload = (attestation.get("binding") or {}).get("payload") or {}
    binding_actual = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if (attestation.get("binding") or {}).get("sha256") != binding_actual:
        errors.append("Teacher attestation canonical content binding mismatch")
    if attestation.get("status") != "PASS":
        errors.append("Teacher attestation is not PASS")
    if attestation.get("signature_status") != "CONTENT_BOUND_UNSIGNED":
        errors.append("unexpected Teacher attestation signature policy")
    if attestation.get("supplements_without_mutating_release") is not True:
        errors.append("Teacher attestation does not preserve the immutable release")

    release_manifest_sha = _canonical_text_sha256(release_dir / "release_manifest.json")
    release_lock_sha = _canonical_text_sha256(release_dir / "b1_release_lock.sha256")
    source = attestation.get("source_release") or {}
    if source.get("release_manifest_sha256") != release_manifest_sha:
        errors.append("Teacher attestation does not bind the source release manifest")
    if source.get("b1_release_lock_sha256") != release_lock_sha:
        errors.append("Teacher attestation does not bind the source release lock")
    repository_block = attestation.get("repository_teacher_manifest") or {}
    if repository_block.get("path") != "challenge/teacher_targeted_gap_manifest.json":
        errors.append("Teacher attestation repository manifest path mismatch")
    if repository_block.get("sha256") != _canonical_text_sha256(repository_manifest):
        errors.append("Teacher attestation repository manifest digest mismatch")

    teacher = attestation.get("teacher") or {}
    expected_identity = {
        "teacher_git_sha": cohort_git_sha,
        "acquisition_git_sha": cohort_git_sha,
        "model_id": "Qwen/Qwen3.5-2B",
        "model_revision": EXPECTED_MODEL_REVISION,
        "artifact_fingerprint_sha256": EXPECTED_ARTIFACT_FINGERPRINT,
        "dtype": "bfloat16",
        "quantization": None,
        "qwen_mode": "planner_v2",
    }
    for field, expected in expected_identity.items():
        if teacher.get(field) != expected:
            errors.append(f"Teacher attestation identity mismatch: {field}")
    coverage = attestation.get("coverage") or {}
    if (
        coverage.get("all_samples_share_teacher_identity") is not True
        or coverage.get("canonical_samples") != sample_count
    ):
        errors.append("Teacher attestation does not cover all canonical samples")
    if payload.get("all_660_samples_share_teacher_identity") is not True:
        errors.append("Teacher attestation payload lacks full-cohort identity binding")

    manifest_identity = {
        "teacher_git_sha": repository_teacher.get("teacher_git_sha"),
        "model_id": repository_teacher.get("model_id"),
        "model_revision": repository_teacher.get("model_revision"),
        "artifact_fingerprint_sha256": repository_teacher.get("model_artifact_sha256"),
    }
    for field, expected in expected_identity.items():
        if field in manifest_identity and manifest_identity[field] != expected:
            errors.append(f"repository Teacher manifest mismatch: {field}")
    if model_artifact.get("model_artifact_sha256") != EXPECTED_ARTIFACT_FINGERPRINT:
        errors.append("Teacher artifact manifest fingerprint mismatch")
    if model_artifact.get("model_revision") != EXPECTED_MODEL_REVISION:
        errors.append("Teacher artifact manifest revision mismatch")

    return {
        "valid": not errors,
        "path": DEFAULT_ATTESTATION,
        "signature_status": attestation.get("signature_status"),
        "cryptographic_signature_present": False,
        "content_binding_sha256": binding_actual,
        "attestation_sha256": _canonical_text_sha256(
            directory / "teacher_provenance_attestation.json"
        ),
        "repository_teacher_manifest_sha256": _canonical_text_sha256(repository_manifest),
        "source_release_manifest_sha256": release_manifest_sha,
        "source_release_lock_sha256": release_lock_sha,
        "teacher": teacher,
        "coverage": coverage,
        "errors": errors,
    }


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
    attestation = _validate_attestation(
        repo,
        release_dir,
        cohort_git_sha=cohort_git_sha,
        sample_count=len(ids["train"] | ids["val"] | ids["hard_negative"]),
    )
    blockers: list[str] = []
    if not matching_manifests:
        blockers.append("no repository Teacher manifest matches the acquisition Git SHA")
    if not attestation["valid"]:
        blockers.extend(attestation["errors"])
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
            "immutable_attestation": attestation,
        },
        "prior_release_overlap": overlap,
        "blockers": blockers,
        "required_b1_followup": [] if eligible else [
            "repair the immutable Teacher provenance attestation without rewriting historical rows",
        ],
        "note": (
            "The historical rows remain unchanged; the independently verified "
            "content-bound addendum supplies their exact cohort Teacher identity."
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
