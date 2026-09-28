"""Fail-closed A3 intake audit for B1's Gap300 additive release.

Byte integrity, label coverage and formal Teacher provenance are deliberately
separate decisions.  The release may be usable for transport analysis while
remaining ineligible for a new A3 FP32 candidate.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from challenge.dataset.validate_d3_gap300_release import validate_release


DATASET_VERSION = "b1_d3_gap300_strict_v1"
DEFAULT_RELEASE = "challenge/dataset/releases/d3_gap300_strict_v1"
DEFAULT_ATTESTATION = (
    "challenge/dataset/attestations/"
    "d3_gap300_strict_v1_teacher_provenance_v1"
)
EXPECTED_MODEL_ID = "Qwen/Qwen3.5-2B"
EXPECTED_MODEL_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
EXPECTED_ARTIFACT_FINGERPRINT = (
    "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
)
PRIOR_SPLITS = {
    "train": (
        "challenge/dataset/releases/d2_v1_1/train.jsonl",
        "challenge/dataset/releases/d3_wave1_addon_v1/train_addition.jsonl",
        "challenge/dataset/releases/d3_wave2_safe_short_v1/train_addition.jsonl",
        "challenge/dataset/releases/d3_targeted_gap_strict_v1/train_addition.jsonl",
        "challenge/dataset/releases/d3_turn_gap_60_strict_v1/train_addition.jsonl",
    ),
    "val": (
        "challenge/dataset/releases/d2_v1_1/val.jsonl",
        "challenge/dataset/releases/d3_wave1_addon_v1/val_addition.jsonl",
        "challenge/dataset/releases/d3_wave2_safe_short_v1/val_addition.jsonl",
        "challenge/dataset/releases/d3_targeted_gap_strict_v1/val_addition.jsonl",
        "challenge/dataset/releases/d3_turn_gap_60_strict_v1/val_addition.jsonl",
    ),
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _identity(row: dict[str, Any]) -> tuple[str, str, str, str]:
    metadata = row.get("metadata") or {}
    plan = row.get("teacher_plan") or {}
    return (
        str(metadata.get("teacher_model_id") or plan.get("model_id") or ""),
        str(metadata.get("teacher_git_sha") or ""),
        str(metadata.get("teacher_model_revision") or plan.get("model_revision") or ""),
        str(
            metadata.get("teacher_artifact_fingerprint_sha256")
            or metadata.get("teacher_model_artifact_sha256")
            or ""
        ),
    )


def _partition(repo: Path, relatives: tuple[str, ...]) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    groups: set[str] = set()
    for relative in relatives:
        for row in _rows(repo / relative):
            ids.add(str(row.get("sample_id") or ""))
            groups.add(str((row.get("metadata") or {}).get("group_key") or ""))
    ids.discard("")
    groups.discard("")
    return ids, groups


def _matching_teacher_manifests(repo: Path, git_sha: str) -> list[str]:
    matches: list[str] = []
    for path in sorted((repo / "challenge").glob("teacher*manifest*.json")):
        value = _load(path)
        teacher = value.get("teacher") if isinstance(value.get("teacher"), dict) else value
        recorded = str(
            teacher.get("teacher_git_sha")
            or teacher.get("git_sha")
            or teacher.get("acquisition_git_sha")
            or ""
        )
        if recorded == git_sha:
            matches.append(path.relative_to(repo).as_posix())
    return matches


def _validate_attestation(
    repo: Path,
    release_dir: Path,
    observed_git_sha_counts: dict[str, int],
) -> dict[str, Any]:
    directory = repo / DEFAULT_ATTESTATION
    repository_manifest = repo / "challenge/teacher_gap300_manifest.json"
    errors: list[str] = []
    required = (
        "teacher_model_manifest.json",
        "teacher_provenance_attestation.json",
        "attestation_lock.sha256",
    )
    for name in required:
        if not (directory / name).is_file():
            errors.append(f"Teacher attestation file missing: {name}")
    if not repository_manifest.is_file():
        errors.append("repository Gap300 Teacher manifest is missing")
    if errors:
        return {
            "valid": False,
            "path": DEFAULT_ATTESTATION,
            "errors": errors,
        }

    lock_entries: dict[str, str] = {}
    for line in (directory / "attestation_lock.sha256").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, separator, name = line.partition("  ")
        if not separator or name in lock_entries:
            errors.append("malformed or duplicate Teacher attestation lock entry")
            continue
        lock_entries[name] = digest
    expected_locked = {
        "teacher_model_manifest.json",
        "teacher_provenance_attestation.json",
    }
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
    if repository_block.get("path") != "challenge/teacher_gap300_manifest.json":
        errors.append("Teacher attestation repository manifest path mismatch")
    if repository_block.get("sha256") != _canonical_text_sha256(repository_manifest):
        errors.append("Teacher attestation repository manifest digest mismatch")

    teacher = attestation.get("teacher") or {}
    expected_teacher = {
        "model_id": EXPECTED_MODEL_ID,
        "model_revision": EXPECTED_MODEL_REVISION,
        "artifact_fingerprint_sha256": EXPECTED_ARTIFACT_FINGERPRINT,
        "dtype": "bfloat16",
        "quantization": None,
        "qwen_mode": "planner_v2",
    }
    for field, expected in expected_teacher.items():
        if teacher.get(field) != expected:
            errors.append(f"Teacher attestation identity mismatch: {field}")
    coverage = attestation.get("coverage") or {}
    if coverage.get("all_samples_share_teacher_identity") is not True:
        errors.append("Teacher attestation does not assert one model identity")
    if coverage.get("canonical_samples") != 820:
        errors.append("Teacher attestation does not cover all 820 samples")
    if coverage.get("acquisition_git_sha_counts") != observed_git_sha_counts:
        errors.append("Teacher attestation acquisition coverage mismatch")
    if payload.get("all_820_samples_share_teacher_identity") is not True:
        errors.append("Teacher attestation payload lacks full-cohort identity binding")
    if payload.get("acquisition_git_sha_counts") != observed_git_sha_counts:
        errors.append("Teacher attestation payload acquisition coverage mismatch")

    manifest_teacher = (
        repository_teacher.get("teacher")
        if isinstance(repository_teacher.get("teacher"), dict)
        else repository_teacher
    )
    for field, expected in expected_teacher.items():
        manifest_field = (
            "model_artifact_sha256"
            if field == "artifact_fingerprint_sha256"
            else field
        )
        if manifest_teacher.get(manifest_field) != expected:
            errors.append(f"repository Teacher manifest mismatch: {field}")
    if repository_teacher.get("acquisition_git_sha_counts") != observed_git_sha_counts:
        errors.append("repository Teacher manifest acquisition coverage mismatch")
    if model_artifact.get("model_revision") != EXPECTED_MODEL_REVISION:
        errors.append("Teacher artifact manifest revision mismatch")
    if model_artifact.get("model_artifact_sha256") != EXPECTED_ARTIFACT_FINGERPRINT:
        errors.append("Teacher artifact manifest fingerprint mismatch")

    return {
        "valid": not errors,
        "path": DEFAULT_ATTESTATION,
        "signature_status": attestation.get("signature_status"),
        "cryptographic_signature_present": False,
        "attestation_sha256": _canonical_text_sha256(
            directory / "teacher_provenance_attestation.json"
        ),
        "content_binding_sha256": binding_actual,
        "repository_teacher_manifest_sha256": _canonical_text_sha256(
            repository_manifest
        ),
        "source_release_manifest_sha256": release_manifest_sha,
        "source_release_lock_sha256": release_lock_sha,
        "teacher": teacher,
        "coverage": coverage,
        "errors": errors,
    }


def audit_gap300_intake(
    release_dir: Path,
    *,
    repo: Path | None = None,
    check_rgb: bool = True,
) -> dict[str, Any]:
    release_dir = release_dir.resolve()
    repo = (repo or release_dir.parents[3]).resolve()
    integrity = validate_release(release_dir, check_images=check_rgb)

    split_rows = {
        "train": _rows(release_dir / "train_addition.jsonl"),
        "val": _rows(release_dir / "val_addition.jsonl"),
    }
    models: set[str] = set()
    git_shas: set[str] = set()
    revisions: set[str] = set()
    fingerprints: set[str] = set()
    git_sha_counts: Counter[str] = Counter()
    ids: dict[str, set[str]] = {}
    groups: dict[str, set[str]] = {}
    behavior_counts: dict[str, int] = {}
    for split, rows in split_rows.items():
        ids[split] = {str(row.get("sample_id") or "") for row in rows}
        groups[split] = {
            str((row.get("metadata") or {}).get("group_key") or "") for row in rows
        }
        ids[split].discard("")
        groups[split].discard("")
        for row in rows:
            model, git_sha, revision, fingerprint = _identity(row)
            if model:
                models.add(model)
            if git_sha:
                git_shas.add(git_sha)
                git_sha_counts[git_sha] += 1
            if revision:
                revisions.add(revision)
            if fingerprint:
                fingerprints.add(fingerprint)
            for step in (row.get("teacher_plan") or {}).get("steps") or []:
                behavior = str(step.get("behavior") or "")
                if behavior:
                    behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1

    prior_train_ids, prior_train_groups = _partition(repo, PRIOR_SPLITS["train"])
    prior_val_ids, prior_val_groups = _partition(repo, PRIOR_SPLITS["val"])
    overlap = {
        "sample_ids_with_any_prior_release": len(
            (ids["train"] | ids["val"]) & (prior_train_ids | prior_val_ids)
        ),
        "gap300_train_groups_in_prior_val": len(groups["train"] & prior_val_groups),
        "gap300_val_groups_in_prior_train": len(groups["val"] & prior_train_groups),
    }

    attestation = _validate_attestation(
        repo,
        release_dir,
        dict(sorted(git_sha_counts.items())),
    )
    blockers: list[str] = []
    if models != {EXPECTED_MODEL_ID}:
        blockers.append("rows do not agree on Qwen/Qwen3.5-2B")
    matching: list[str] = []
    for git_sha in sorted(git_shas):
        matching.extend(_matching_teacher_manifests(repo, git_sha))
    if not attestation["valid"]:
        blockers.extend(attestation["errors"])
    if any(overlap.values()):
        blockers.append("Gap300 overlaps a prior A3 Train/Validation partition")

    eligible = bool(integrity["valid"] and not blockers)
    return {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "status": "READY" if eligible else ("BLOCKED" if integrity["valid"] else "INVALID"),
        "eligible_for_a3_final_view": eligible,
        "release_integrity": integrity,
        "strict_positive_counts": {
            "train": len(split_rows["train"]),
            "val": len(split_rows["val"]),
        },
        "teacher_provenance": {
            "model_ids": sorted(models),
            "acquisition_git_shas": sorted(git_shas),
            "acquisition_git_sha_counts": dict(sorted(git_sha_counts.items())),
            "model_revisions": sorted(revisions),
            "artifact_fingerprints": sorted(fingerprints),
            "matching_repository_manifests": matching,
            "expected_model_revision": EXPECTED_MODEL_REVISION,
            "expected_artifact_fingerprint": EXPECTED_ARTIFACT_FINGERPRINT,
            "expected_attestation_path": DEFAULT_ATTESTATION,
            "immutable_attestation": attestation,
        },
        "behavior_step_counts": dict(sorted(behavior_counts.items())),
        "prior_release_overlap": overlap,
        "blockers": blockers,
        "required_b1_followup": [] if eligible else [
            "publish an immutable cohort-specific Teacher provenance addendum covering all 820 samples",
            "explain and bind both observed acquisition Git SHAs, exact model revision and artifact fingerprint to the release manifest and lock",
        ],
        "count_policy": {
            "b1_raw_train_rows_after_gap300": 6007,
            "a3_strict_positive_train_rows_after_gap300": 5826,
            "reason_for_difference": "181 D2 hard-negative rows remain audit-only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=Path(DEFAULT_RELEASE))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_gap300_intake(
        args.release_dir,
        repo=args.repo,
        check_rgb=not args.skip_images,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
