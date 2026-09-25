"""Fail-closed validation for B1's detached-signed D3 Wave2 safe-short add-on.

The immutable release manifest remains a ``B1_RELEASE_CANDIDATE``.  B1's
separate ``B1_SIGNED_PASS.json`` is the authority that promotes those exact
bytes, so consumers must validate both documents and their hash chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from challenge.dataset.validate_d2_release import canonical_text_sha256


D3_DATASET_VERSION = "b1_d3_wave2_safe_short_v1"
D3_COHORT_VERSION = "teacher_distill_v0.6_d3_expansion_wave2_targeted_v4_sync_v1"
POSITIVE_FILES = {"train": "train_addition.jsonl", "val": "val_addition.jsonl"}
TEACHER_MANIFEST = "challenge/teacher_pinned_manifest_wave2_sync_v1.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _teacher_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "teacher_profile": manifest["teacher_profile"],
        "teacher_git_sha": manifest["teacher_git_sha"],
        "model_id": manifest["model_id"],
        "model_revision": manifest["model_revision"],
        "artifact_fingerprint": manifest["model_artifact_sha256"],
        "quantization": manifest.get("quantization"),
        "dtype": manifest["dtype"],
    }


def validate_d3_release(
    release_dir: Path, *, check_images: bool = True,
) -> dict[str, Any]:
    """Validate the detached signature, published bytes, rows and RGB set."""
    release_dir = release_dir.resolve()
    repo = release_dir.parents[3]
    errors: list[str] = []
    required = (
        "release_manifest.json", "B1_SIGNED_PASS.json",
        "b1_release_integrity_report.json", "b1_release_lock.sha256",
        "rgb_mapping.json", "train_addition.jsonl", "val_addition.jsonl",
        "hard_negative_addition.jsonl",
    )
    for name in required:
        if not (release_dir / name).is_file():
            errors.append(f"required release file missing: {name}")
    if errors:
        return _report(release_dir, check_images, errors, {}, 0)

    release = _load(release_dir / "release_manifest.json")
    signature = _load(release_dir / "B1_SIGNED_PASS.json")
    integrity = _load(release_dir / "b1_release_integrity_report.json")
    mapping = _load(release_dir / "rgb_mapping.json")
    teacher_manifest_path = repo / TEACHER_MANIFEST
    if not teacher_manifest_path.is_file():
        errors.append(f"Teacher manifest missing: {TEACHER_MANIFEST}")
        expected_teacher = None
    else:
        expected_teacher = _teacher_identity(_load(teacher_manifest_path))

    release_sha = canonical_text_sha256(release_dir / "release_manifest.json")
    integrity_sha = canonical_text_sha256(release_dir / "b1_release_integrity_report.json")
    lock_sha = canonical_text_sha256(release_dir / "b1_release_lock.sha256")
    if signature.get("gate") != "B1_SIGNED_PASS" or signature.get("status") != "PASS":
        errors.append("detached B1 signature is not PASS")
    if release.get("status") != "B1_RELEASE_CANDIDATE":
        errors.append("immutable D3 release manifest status changed")
    if release.get("dataset_version") != D3_DATASET_VERSION:
        errors.append("D3 release dataset_version mismatch")
    if signature.get("dataset_version") != D3_DATASET_VERSION:
        errors.append("D3 signature dataset_version mismatch")
    if signature.get("release_manifest_sha256") != release_sha:
        errors.append("detached signature does not bind release_manifest.json")
    if signature.get("integrity_report_sha256") != integrity_sha:
        errors.append("detached signature does not bind integrity report")
    if signature.get("release_lock_sha256") != lock_sha:
        errors.append("detached signature does not bind release lock")
    if integrity.get("status") != "PASS" or integrity.get("release_manifest_sha256") != release_sha:
        errors.append("B1 integrity report is not PASS for this release manifest")
    if expected_teacher is not None and signature.get("teacher") != expected_teacher:
        errors.append("B1 signature Teacher identity differs from pinned Teacher v4")
    if expected_teacher is not None and integrity.get("teacher") != expected_teacher:
        errors.append("B1 integrity Teacher identity differs from pinned Teacher v4")

    lock_entries: dict[str, str] = {}
    for line in (release_dir / "b1_release_lock.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, separator, name = line.partition("  ")
        if not separator or name in lock_entries:
            errors.append("malformed or duplicate release lock entry")
            continue
        lock_entries[name] = digest
    for name, digest in lock_entries.items():
        path = release_dir / name
        if not path.is_file() or canonical_text_sha256(path) != digest:
            errors.append(f"release lock mismatch: {name}")

    for name, expected in release.get("files", {}).items():
        path = release_dir / name
        if not path.is_file():
            errors.append(f"manifest file missing: {name}")
            continue
        if canonical_text_sha256(path) != expected.get("sha256"):
            errors.append(f"manifest hash mismatch: {name}")
        if len(path.read_bytes().replace(b"\r\n", b"\n")) != expected.get("size_bytes"):
            errors.append(f"manifest size mismatch: {name}")

    ids: dict[str, set[str]] = {}
    groups: dict[str, set[str]] = {}
    referenced: set[str] = set()
    stats: dict[str, Any] = {}
    expected_roles = {
        "train": "POSITIVE", "val": "POSITIVE", "hard_negative": "HARD_NEGATIVE",
    }
    files = {**POSITIVE_FILES, "hard_negative": "hard_negative_addition.jsonl"}
    for split, filename in files.items():
        split_ids: set[str] = set()
        split_groups: set[str] = set()
        count = 0
        with (release_dir / filename).open(encoding="utf-8") as stream:
            for line_no, raw in enumerate(stream, 1):
                if not raw.strip():
                    continue
                row = json.loads(raw)
                count += 1
                sample_id = str(row.get("sample_id") or "")
                group = str(row.get("metadata", {}).get("group_key") or "")
                if not sample_id or sample_id in split_ids:
                    errors.append(f"{filename}:{line_no}: missing/duplicate sample_id")
                if not group:
                    errors.append(f"{filename}:{line_no}: missing group_key")
                if row.get("dataset_version") != D3_COHORT_VERSION:
                    errors.append(f"{filename}:{line_no}: source cohort mismatch")
                quality = row.get("quality") or {}
                if quality.get("training_role") != expected_roles[split]:
                    errors.append(f"{filename}:{line_no}: training role mismatch")
                if split in POSITIVE_FILES and quality.get("valid_for_training") is not True:
                    errors.append(f"{filename}:{line_no}: positive row is not trainable")
                visual = row.get("visual_input") or {}
                rgb_ref = visual.get("rgb_ref")
                if rgb_ref != (row.get("model_request") or {}).get("rgb_ref"):
                    errors.append(f"{filename}:{line_no}: RGB reference mismatch")
                if not isinstance(rgb_ref, str):
                    errors.append(f"{filename}:{line_no}: RGB reference missing")
                else:
                    referenced.add(sample_id)
                    item = mapping.get(sample_id)
                    if not isinstance(item, dict) or item.get("release_rgb_ref") != rgb_ref:
                        errors.append(f"{filename}:{line_no}: RGB mapping mismatch")
                    elif (
                        item.get("sha256") != visual.get("rgb_sha256")
                        or item.get("size_bytes") != visual.get("size_bytes")
                    ):
                        errors.append(f"{filename}:{line_no}: RGB metadata mismatch")
                split_ids.add(sample_id)
                split_groups.add(group)
        ids[split] = split_ids
        groups[split] = split_groups
        stats[split] = {"samples": count, "groups": len(split_groups)}

    for left, right in (("train", "val"), ("train", "hard_negative"), ("val", "hard_negative")):
        if ids[left] & ids[right]:
            errors.append(f"sample_id overlap: {left}/{right}")
    if groups["train"] & groups["val"]:
        errors.append("group_key overlap: train/val")
    expected_counts = release.get("counts", {})
    for split, key in (
        ("train", "train_addition"), ("val", "val_addition"),
        ("hard_negative", "hard_negative_addition"),
    ):
        if stats[split]["samples"] != expected_counts.get(key):
            errors.append(f"{split} count differs from release manifest")
    if set(mapping) != referenced:
        errors.append(
            f"RGB mapping/reference mismatch: mapping={len(mapping)} referenced={len(referenced)}"
        )

    images_checked = 0
    if check_images:
        canonical_lines: list[str] = []
        images_dir = (release_dir / "images").resolve()
        for sample_id, item in sorted(mapping.items()):
            image_path = (repo / str(item.get("release_rgb_ref"))).resolve()
            if not image_path.is_relative_to(images_dir):
                errors.append(f"RGB path escapes release images: {sample_id}")
                continue
            if not image_path.is_file():
                errors.append(f"RGB missing: {sample_id}")
                continue
            actual_sha = _sha256(image_path)
            if actual_sha != item.get("sha256") or image_path.stat().st_size != item.get("size_bytes"):
                errors.append(f"RGB hash/size mismatch: {sample_id}")
            canonical_lines.append(f"{image_path.name}\t{actual_sha}\n")
            images_checked += 1
        canonical_sha = hashlib.sha256("".join(canonical_lines).encode("utf-8")).hexdigest()
        if images_checked != release.get("image_set", {}).get("count"):
            errors.append("published image count differs from release manifest")
        if canonical_sha != release.get("image_set", {}).get("canonical_sha256"):
            errors.append("published image set digest differs from release manifest")
        if canonical_sha != signature.get("image_set_canonical_sha256"):
            errors.append("published image set digest differs from B1 signature")

    evidence = {
        "release_manifest_sha256": release_sha,
        "b1_signature_sha256": canonical_text_sha256(release_dir / "B1_SIGNED_PASS.json"),
        "integrity_report_sha256": integrity_sha,
        "release_lock_sha256": lock_sha,
        "teacher_manifest_path": TEACHER_MANIFEST,
        "teacher_manifest_sha256": (
            canonical_text_sha256(teacher_manifest_path) if teacher_manifest_path.is_file() else None
        ),
    }
    return _report(release_dir, check_images, errors, stats, images_checked, evidence)


def _report(
    release_dir: Path,
    check_images: bool,
    errors: list[str],
    splits: dict[str, Any],
    images_checked: int,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "valid": not errors,
        "release_dir": str(release_dir),
        "dataset_version": D3_DATASET_VERSION,
        "image_check_enabled": check_images,
        "images_checked": images_checked,
        "splits": splits,
        "evidence": evidence or {},
        "error_count": len(errors),
        "errors": errors[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate detached-signed B1 D3 Wave2 safe-short add-on")
    parser.add_argument(
        "--release-dir", type=Path,
        default=Path("challenge/dataset/releases/d3_wave2_safe_short_v1"),
    )
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_d3_release(args.release_dir, check_images=not args.skip_images)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
