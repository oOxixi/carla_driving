"""Fail-closed validator for B1's content-bound TURN-gap recovery release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from challenge.hil.harness.release_check.verify_b1_release import (
    check_images,
    check_lock,
)


DATASET_VERSION = "b1_d3_turn_gap_60_strict_v1"
DEFAULT_RELEASE = "challenge/dataset/releases/d3_turn_gap_60_strict_v1"
EXPECTED_TEACHER = {
    "git_sha": "c7ecadf5ce1da1dd569681c458ccc09959c0b5d1",
    "model_id": "Qwen/Qwen3.5-2B",
    "model_revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
    "model_artifact_sha256": "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa",
    "mode": "planner_v2",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _canonical_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_json_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_turn_gap_release(
    release_dir: Path,
    *,
    repo: Path | None = None,
    check_rgb: bool = True,
) -> dict[str, Any]:
    release_dir = release_dir.resolve()
    repo = (repo or release_dir.parents[3]).resolve()
    errors: list[str] = []
    required = (
        "release_manifest.json",
        "B1_CONTENT_BOUND_PASS.json",
        "b1_release_integrity_report.json",
        "b1_release_lock.sha256",
        "governance_report.json",
        "provenance_manifest.json",
        "rgb_mapping.json",
        "split_manifest.json",
        "train_addition.jsonl",
        "val_addition.jsonl",
        "hard_negative_addition.jsonl",
    )
    for name in required:
        if not (release_dir / name).is_file():
            errors.append(f"required release file missing: {name}")
    if errors:
        return {"valid": False, "errors": errors, "error_count": len(errors)}

    release = _load(release_dir / "release_manifest.json")
    content_pass = _load(release_dir / "B1_CONTENT_BOUND_PASS.json")
    integrity = _load(release_dir / "b1_release_integrity_report.json")
    governance = _load(release_dir / "governance_report.json")
    provenance = _load(release_dir / "provenance_manifest.json")
    mapping = _load(release_dir / "rgb_mapping.json")
    lock = check_lock(release_dir, allow_lf_normalise=True)
    errors.extend(item["reason"] + ": " + item["file"] for item in lock["failures"])

    release_sha = _canonical_sha(release_dir / "release_manifest.json")
    if release.get("dataset_version") != DATASET_VERSION:
        errors.append("release dataset_version mismatch")
    if release.get("status") != "B1_RELEASE_CANDIDATE":
        errors.append("release status is not B1_RELEASE_CANDIDATE")
    if integrity.get("status") != "PASS" or integrity.get("release_manifest_sha256") != release_sha:
        errors.append("integrity report does not bind the release manifest")
    if governance.get("status") != "PASS":
        errors.append("governance report is not PASS")
    if content_pass.get("status") != "PASS":
        errors.append("content-bound pass is not PASS")
    if content_pass.get("signature_status") != "CONTENT_BOUND_UNSIGNED":
        errors.append("unexpected content-bound signature policy")
    binding = content_pass.get("binding") or {}
    if binding.get("sha256") != _canonical_json_sha(binding.get("payload") or {}):
        errors.append("content-bound pass canonical digest mismatch")

    teacher = provenance.get("teacher") or {}
    if teacher != EXPECTED_TEACHER:
        errors.append("release Teacher identity mismatch")
    payload = binding.get("payload") or {}
    payload_teacher = {
        "git_sha": payload.get("acquisition_git_sha"),
        "model_id": payload.get("teacher_model_id"),
        "model_revision": payload.get("teacher_model_revision"),
        "model_artifact_sha256": payload.get("teacher_model_artifact_sha256"),
    }
    for field in ("git_sha", "model_id", "model_revision", "model_artifact_sha256"):
        if payload_teacher[field] != EXPECTED_TEACHER[field]:
            errors.append(f"content-bound Teacher mismatch: {field}")

    for name, expected in (release.get("files") or {}).items():
        path = release_dir / name
        if not path.is_file():
            errors.append(f"manifest file missing: {name}")
            continue
        if _canonical_sha(path) != expected.get("sha256"):
            errors.append(f"manifest hash mismatch: {name}")
        if len(path.read_bytes().replace(b"\r\n", b"\n")) != expected.get("size_bytes"):
            errors.append(f"manifest size mismatch: {name}")

    split_rows = {
        "train": _rows(release_dir / "train_addition.jsonl"),
        "val": _rows(release_dir / "val_addition.jsonl"),
        "hard_negative": _rows(release_dir / "hard_negative_addition.jsonl"),
    }
    ids: dict[str, set[str]] = {}
    groups: dict[str, set[str]] = {}
    referenced: set[str] = set()
    family_counts: dict[str, int] = {}
    for split, rows in split_rows.items():
        split_ids: list[str] = []
        split_groups: set[str] = set()
        for index, row in enumerate(rows):
            sample_id = str(row.get("sample_id") or "")
            metadata = row.get("metadata") or {}
            quality = row.get("quality") or {}
            loop = row.get("closed_loop_quality") or {}
            group = str(metadata.get("group_key") or "")
            if not sample_id or not group:
                errors.append(f"{split}:{index}: missing sample_id/group_key")
            if row.get("dataset_version") != DATASET_VERSION:
                errors.append(f"{split}:{index}: dataset version mismatch")
            if split != "hard_negative" and (
                quality.get("training_role") != "POSITIVE"
                or quality.get("valid_for_training") is not True
                or loop.get("run_status") != "SUCCEEDED"
                or loop.get("command_terminal_status") != "SUCCEEDED"
                or loop.get("plan_terminal_state") != "SUCCEEDED"
                or loop.get("scenario_acceptance_passed") is not True
            ):
                errors.append(f"{split}:{index}: non-strict-positive row")
            if metadata.get("teacher_git_sha") != EXPECTED_TEACHER["git_sha"]:
                errors.append(f"{split}:{index}: Teacher Git SHA mismatch")
            if (metadata.get("teacher_model_id") or (row.get("teacher_plan") or {}).get("model_id")) != EXPECTED_TEACHER["model_id"]:
                errors.append(f"{split}:{index}: Teacher model ID mismatch")
            visual = row.get("visual_input") or {}
            rgb_ref = visual.get("rgb_ref")
            entry = mapping.get(sample_id)
            if (
                not isinstance(entry, dict)
                or entry.get("release_rgb_ref") != rgb_ref
                or entry.get("sha256") != visual.get("rgb_sha256")
                or entry.get("size_bytes") != visual.get("size_bytes")
            ):
                errors.append(f"{split}:{index}: RGB mapping mismatch")
            split_ids.append(sample_id)
            split_groups.add(group)
            referenced.add(sample_id)
            family = str(metadata.get("scenario_id") or "UNKNOWN")
            family_counts[family] = family_counts.get(family, 0) + 1
        if len(split_ids) != len(set(split_ids)):
            errors.append(f"{split}: duplicate sample IDs")
        ids[split] = set(split_ids)
        groups[split] = split_groups
    if ids["train"] & ids["val"] or groups["train"] & groups["val"]:
        errors.append("TURN-gap Train/Validation overlap")
    if set(mapping) != referenced:
        errors.append("TURN-gap RGB mapping/reference set mismatch")

    counts = {
        "train": len(split_rows["train"]),
        "val": len(split_rows["val"]),
        "hard_negative": len(split_rows["hard_negative"]),
    }
    expected_counts = release.get("counts") or {}
    if counts != {
        "train": expected_counts.get("train_addition"),
        "val": expected_counts.get("val_addition"),
        "hard_negative": expected_counts.get("hard_negative_addition"),
    }:
        errors.append("TURN-gap split counts differ from release manifest")
    if payload.get("canonical_samples") != counts["train"] + counts["val"]:
        errors.append("content-bound sample count mismatch")

    image_report = check_images(release_dir, repo) if check_rgb else None
    if image_report is not None:
        errors.extend(item["reason"] + ": " + item["sample_id"] for item in image_report["failures"])
    evidence = {
        "release_manifest_sha256": release_sha,
        "release_lock_sha256": _canonical_sha(release_dir / "b1_release_lock.sha256"),
        "content_bound_pass_sha256": _canonical_sha(release_dir / "B1_CONTENT_BOUND_PASS.json"),
        "content_binding_sha256": binding.get("sha256"),
        "teacher_provenance_manifest": release_dir.relative_to(repo).as_posix() + "/provenance_manifest.json",
        "teacher_provenance_manifest_sha256": _canonical_sha(release_dir / "provenance_manifest.json"),
        "signature_status": content_pass.get("signature_status"),
    }
    return {
        "valid": not errors,
        "dataset_version": DATASET_VERSION,
        "counts": counts,
        "groups": {split: len(value) for split, value in groups.items()},
        "families": dict(sorted(family_counts.items())),
        "images_checked": image_report["images_in_mapping"] if image_report else 0,
        "image_check_skipped": image_report is None,
        "locked_files_checked": lock["files_checked"],
        "teacher": teacher,
        "evidence": evidence,
        "error_count": len(errors),
        "errors": errors[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=Path(DEFAULT_RELEASE))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_turn_gap_release(
        args.release_dir, repo=args.repo, check_rgb=not args.skip_images,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
