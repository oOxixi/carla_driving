"""Read-only integrity gate for the portable B1 D2 release.

This checks the published files, not the original server-side acquisition roots.
It never uses reserved Test candidates for training or model selection.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


SPLITS = ("train", "val", "reserved_test_candidates")
REPORT_SPLITS = {
    "train": "TRAIN",
    "val": "VAL",
    "reserved_test_candidates": "RESERVED_TEST_CANDIDATE",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_text_bytes(path: Path) -> bytes:
    """Match Git's LF-normalized text blob on both Windows and Linux."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(_canonical_text_bytes(path)).hexdigest()


def validate_release(release_dir: Path, *, check_images: bool = True) -> dict[str, Any]:
    release_dir = release_dir.resolve()
    repo_root = release_dir.parents[3]
    signed_manifest_path = release_dir / "release_manifest.json"
    manifest_path = signed_manifest_path if signed_manifest_path.is_file() else release_dir / "split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    split_report = None
    if manifest_path.name == "split_manifest.json":
        split_report = json.loads((release_dir / "split_report.json").read_text(encoding="utf-8"))
    images_dir = (release_dir / "images").resolve()
    errors: list[str] = []
    stats: dict[str, Any] = {}
    ids_by_split: dict[str, set[str]] = {}
    groups_by_split: dict[str, set[str]] = {}
    referenced_images: set[Path] = set()

    for name, expected in manifest["files"].items():
        path = release_dir / name
        if not path.is_file():
            errors.append(f"manifest file missing: {name}")
            continue
        content = _canonical_text_bytes(path)
        actual_sha = hashlib.sha256(content).hexdigest()
        actual_bytes = len(content)
        if actual_sha != expected["sha256"] or actual_bytes != expected["bytes"]:
            errors.append(
                f"published {name} differs from split_manifest.json (LF-normalized): "
                f"sha256={actual_sha} bytes={actual_bytes}, "
                f"expected_sha256={expected['sha256']} expected_bytes={expected['bytes']}"
            )

    for name in SPLITS:
        path = release_dir / f"{name}.jsonl"
        ids: set[str] = set()
        groups: set[str] = set()
        versions: Counter[str] = Counter()
        teachers: Counter[str] = Counter()
        roles: Counter[str] = Counter()
        count = 0
        with path.open("r", encoding="utf-8") as stream:
            for line_no, raw in enumerate(stream, 1):
                row = json.loads(raw)
                count += 1
                sample_id = str(row.get("sample_id") or "")
                group = str(row.get("metadata", {}).get("group_key") or "")
                if not sample_id or sample_id in ids:
                    errors.append(f"{name}:{line_no}: missing/duplicate sample_id {sample_id!r}")
                if not group:
                    errors.append(f"{name}:{line_no}: missing group_key")
                ids.add(sample_id)
                groups.add(group)
                versions[str(row.get("dataset_version"))] += 1
                teachers[str(row.get("metadata", {}).get("teacher_git_sha"))] += 1
                role = row.get("quality", {}).get("training_role") or "LEGACY_D1"
                roles[str(role)] += 1
                visual = row.get("visual_input") or {}
                rgb_ref = visual.get("rgb_ref")
                request_ref = (row.get("model_request") or {}).get("rgb_ref")
                if not rgb_ref or rgb_ref != request_ref:
                    errors.append(f"{name}:{line_no}: RGB reference mismatch")
                    continue
                image_path = (repo_root / rgb_ref).resolve()
                if not image_path.is_relative_to(images_dir):
                    errors.append(f"{name}:{line_no}: RGB path escapes release images")
                    continue
                referenced_images.add(image_path)
                if check_images:
                    if not image_path.is_file():
                        errors.append(f"{name}:{line_no}: RGB missing: {rgb_ref}")
                    elif (
                        _sha256(image_path) != visual.get("rgb_sha256")
                        or image_path.stat().st_size != visual.get("size_bytes")
                    ):
                        errors.append(f"{name}:{line_no}: RGB hash/size mismatch: {rgb_ref}")
        ids_by_split[name] = ids
        groups_by_split[name] = groups
        stats[name] = {
            "samples": count,
            "groups": len(groups),
            "dataset_versions": dict(sorted(versions.items())),
            "teacher_git_shas": dict(sorted(teachers.items())),
            "training_roles": dict(sorted(roles.items())),
        }
        expected_count = (
            manifest["counts"][name]
            if split_report is None
            else split_report["counts"]["splits"][REPORT_SPLITS[name]]["samples"]
        )
        if count != expected_count:
            errors.append(f"{name}: count {count} != manifest/report {expected_count}")

    for index, left in enumerate(SPLITS):
        for right in SPLITS[index + 1 :]:
            if ids_by_split[left] & ids_by_split[right]:
                errors.append(f"sample_id overlap: {left}/{right}")
            if groups_by_split[left] & groups_by_split[right]:
                errors.append(f"group_key overlap: {left}/{right}")

    if check_images:
        published_images = set(images_dir.glob("*.jpg"))
        if published_images != referenced_images:
            errors.append(
                f"published/referenced image mismatch: published={len(published_images)} "
                f"referenced={len(referenced_images)}"
            )
        if "image_set" in manifest:
            canonical = "".join(
                f"{path.name}\t{_sha256(path)}\n"
                for path in sorted(published_images, key=lambda p: p.name)
            ).encode("utf-8")
            actual_set_sha = hashlib.sha256(canonical).hexdigest()
            if (
                len(published_images) != manifest["image_set"]["count"]
                or actual_set_sha != manifest["image_set"]["canonical_sha256"]
            ):
                errors.append("published image set differs from release_manifest.json")

    quarantine_path = release_dir / "quarantine" / "d1_terminal_state_anomalies.jsonl"
    quarantined: set[str] = set()
    if quarantine_path.is_file():
        with quarantine_path.open(encoding="utf-8") as stream:
            quarantined = {json.loads(raw)["sample_id"] for raw in stream if raw.strip()}
        if "counts" in manifest and len(quarantined) != manifest["counts"].get("quarantined"):
            errors.append("quarantine count differs from release_manifest.json")
        for name in SPLITS:
            if quarantined & ids_by_split[name]:
                errors.append(f"quarantined sample leaked into {name}")

    return {
        "valid": not errors,
        "release_dir": str(release_dir),
        "authoritative_manifest": manifest_path.name,
        "image_check_enabled": check_images,
        "splits": stats,
        "referenced_images": len(referenced_images),
        "quarantined_samples": len(quarantined),
        "error_count": len(errors),
        "errors": errors[:30],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate published B1 D2 dataset")
    parser.add_argument(
        "--release-dir", default="challenge/dataset/releases/d2_v1_1", type=Path
    )
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_release(args.release_dir, check_images=not args.skip_images)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
