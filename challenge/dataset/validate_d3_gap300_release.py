"""Fail-closed validation for B1 D3 Gap300 strict additive release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from challenge.dataset.validate_d2_release import canonical_text_sha256


DATASET_VERSION = "b1_d3_gap300_strict_v1"

POSITIVE_FILES = {
    "train": "train_addition.jsonl",
    "val": "val_addition.jsonl",
}

EXPECTED_COUNTS = {
    "source_runs": 300,
    "strict_positive_runs": 280,
    "strict_positive_samples": 820,
    "train_addition": 697,
    "val_addition": 123,
    "hard_negative_addition": 0,
    "images": 820,
}

EXPECTED_FAMILY_COUNTS = {
    "D01": 50,
    "C01": 225,
    "C02": 225,
    "C03": 320,
}

EXPECTED_TOTAL_GROUPS = 280
EXPECTED_TRAIN_GROUPS = 238
EXPECTED_VAL_GROUPS = 42


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _family_of(row: dict[str, Any]) -> str:
    sid = str(
        (row.get("metadata") or {}).get("scenario_id") or ""
    )

    for prefix, family in {
        "TC_D01": "D01",
        "TC_C01": "C01",
        "TC_C02": "C02",
        "TC_C03": "C03",
    }.items():
        if sid.startswith(prefix):
            return family

    return "UNKNOWN"


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
        "dataset_version": DATASET_VERSION,
        "image_check_enabled": check_images,
        "images_checked": images_checked,
        "splits": splits,
        "evidence": evidence or {},
        "error_count": len(errors),
        "errors": errors[:100],
    }


def validate_release(
    release_dir: Path,
    *,
    check_images: bool = True,
) -> dict[str, Any]:
    release_dir = release_dir.resolve()
    repo = release_dir.parents[3]

    errors: list[str] = []

    required = (
        "release_manifest.json",
        "B1_CONTENT_BOUND_PASS.json",
        "b1_release_integrity_report.json",
        "b1_release_lock.sha256",
        "rgb_mapping.json",
        "split_manifest.json",
        "provenance_manifest.json",
        "governance_report.json",
        "cumulative_view_manifest.json",
        "train_addition.jsonl",
        "val_addition.jsonl",
        "hard_negative_addition.jsonl",
    )

    for name in required:
        if not (release_dir / name).is_file():
            errors.append(
                f"required release file missing: {name}"
            )

    if errors:
        return _report(
            release_dir,
            check_images,
            errors,
            {},
            0,
        )

    release = _load(
        release_dir / "release_manifest.json"
    )
    integrity = _load(
        release_dir / "b1_release_integrity_report.json"
    )
    attestation = _load(
        release_dir / "B1_CONTENT_BOUND_PASS.json"
    )
    mapping = _load(
        release_dir / "rgb_mapping.json"
    )
    split_manifest = _load(
        release_dir / "split_manifest.json"
    )
    provenance = _load(
        release_dir / "provenance_manifest.json"
    )
    governance = _load(
        release_dir / "governance_report.json"
    )
    cumulative = _load(
        release_dir / "cumulative_view_manifest.json"
    )

    release_sha = canonical_text_sha256(
        release_dir / "release_manifest.json"
    )

    if release.get("dataset_version") != DATASET_VERSION:
        errors.append(
            "release dataset_version mismatch"
        )

    if release.get("status") != "B1_RELEASE_CANDIDATE":
        errors.append(
            "release manifest status mismatch"
        )

    if attestation.get("dataset_version") != DATASET_VERSION:
        errors.append(
            "attestation dataset_version mismatch"
        )

    if attestation.get("status") != "PASS":
        errors.append(
            "content-bound attestation is not PASS"
        )

    if (
        attestation.get("attestation_type")
        != "CONTENT_BOUND_UNSIGNED"
    ):
        errors.append(
            "attestation type is not CONTENT_BOUND_UNSIGNED"
        )

    if (
        attestation.get("release_manifest_sha256")
        != release_sha
    ):
        errors.append(
            "attestation does not bind release manifest"
        )

    if integrity.get("status") != "PASS":
        errors.append(
            "integrity report is not PASS"
        )

    if (
        integrity.get("release_manifest_sha256")
        != release_sha
    ):
        errors.append(
            "integrity report does not bind release manifest"
        )

    counts = release.get("counts") or {}

    for key, expected in EXPECTED_COUNTS.items():
        if counts.get(key) != expected:
            errors.append(
                f"release count mismatch: "
                f"{key}={counts.get(key)} "
                f"expected={expected}"
            )

    # --------------------------------------------------
    # Verify all manifest-tracked core files.
    # --------------------------------------------------

    for name, expected in (
        release.get("files") or {}
    ).items():
        path = release_dir / name

        if not path.is_file():
            errors.append(
                f"manifest file missing: {name}"
            )
            continue

        actual_sha = canonical_text_sha256(path)
        actual_size = len(
            path.read_bytes().replace(
                b"\r\n",
                b"\n",
            )
        )

        if actual_sha != expected.get("sha256"):
            errors.append(
                f"manifest hash mismatch: {name}"
            )

        if actual_size != expected.get("size_bytes"):
            errors.append(
                f"manifest size mismatch: {name}"
            )

    # --------------------------------------------------
    # Read dataset rows.
    # --------------------------------------------------

    ids: dict[str, set[str]] = {}
    groups: dict[str, set[str]] = {}
    stats: dict[str, Any] = {}
    referenced: set[str] = set()

    family_counts: dict[str, int] = {
        k: 0
        for k in EXPECTED_FAMILY_COUNTS
    }

    files = {
        **POSITIVE_FILES,
        "hard_negative":
            "hard_negative_addition.jsonl",
    }

    expected_roles = {
        "train": "POSITIVE",
        "val": "POSITIVE",
        "hard_negative": "HARD_NEGATIVE",
    }

    for split, filename in files.items():
        split_ids: set[str] = set()
        split_groups: set[str] = set()

        count = 0

        with (
            release_dir / filename
        ).open(encoding="utf-8") as f:
            for line_no, raw in enumerate(f, 1):
                if not raw.strip():
                    continue

                row = json.loads(raw)
                count += 1

                sample_id = str(
                    row.get("sample_id") or ""
                )

                md = row.get("metadata") or {}
                group = str(
                    md.get("group_key") or ""
                )

                if (
                    not sample_id
                    or sample_id in split_ids
                ):
                    errors.append(
                        f"{filename}:{line_no}: "
                        "missing/duplicate sample_id"
                    )

                if not group:
                    errors.append(
                        f"{filename}:{line_no}: "
                        "missing group_key"
                    )

                if (
                    row.get("dataset_version")
                    != DATASET_VERSION
                ):
                    errors.append(
                        f"{filename}:{line_no}: "
                        "dataset_version mismatch"
                    )

                q = row.get("quality") or {}
                c = (
                    row.get("closed_loop_quality")
                    or {}
                )

                if (
                    q.get("training_role")
                    != expected_roles[split]
                ):
                    errors.append(
                        f"{filename}:{line_no}: "
                        "training role mismatch"
                    )

                if split in POSITIVE_FILES:
                    strict = (
                        q.get("valid_for_training")
                        is True
                        and q.get("rgb_exists")
                        is True
                        and c.get("run_status")
                        == "SUCCEEDED"
                        and c.get(
                            "scenario_acceptance_passed"
                        )
                        is True
                        and c.get(
                            "command_terminal_status"
                        )
                        == "SUCCEEDED"
                        and c.get(
                            "plan_terminal_state"
                        )
                        == "SUCCEEDED"
                        and int(
                            c.get("collision_count")
                            or 0
                        )
                        == 0
                    )

                    if not strict:
                        errors.append(
                            f"{filename}:{line_no}: "
                            "positive row fails "
                            "strict-positive contract"
                        )

                    fam = _family_of(row)

                    if fam not in family_counts:
                        errors.append(
                            f"{filename}:{line_no}: "
                            f"unknown family {fam}"
                        )
                    else:
                        family_counts[fam] += 1

                visual = (
                    row.get("visual_input")
                    or {}
                )
                request = (
                    row.get("model_request")
                    or {}
                )

                rgb_ref = visual.get("rgb_ref")

                if rgb_ref != request.get("rgb_ref"):
                    errors.append(
                        f"{filename}:{line_no}: "
                        "RGB reference mismatch"
                    )

                if split in POSITIVE_FILES:
                    referenced.add(sample_id)

                    item = mapping.get(sample_id)

                    if not isinstance(item, dict):
                        errors.append(
                            f"{filename}:{line_no}: "
                            "RGB mapping missing"
                        )

                    elif (
                        item.get("release_rgb_ref")
                        != rgb_ref
                    ):
                        errors.append(
                            f"{filename}:{line_no}: "
                            "RGB mapping/ref mismatch"
                        )

                    elif (
                        item.get("sha256")
                        != visual.get("rgb_sha256")
                        or item.get("size_bytes")
                        != visual.get("size_bytes")
                    ):
                        errors.append(
                            f"{filename}:{line_no}: "
                            "RGB metadata mismatch"
                        )

                split_ids.add(sample_id)
                split_groups.add(group)

        ids[split] = split_ids
        groups[split] = split_groups

        stats[split] = {
            "samples": count,
            "groups": len(split_groups),
        }

    # --------------------------------------------------
    # Dataset split isolation.
    # --------------------------------------------------

    for left, right in (
        ("train", "val"),
        ("train", "hard_negative"),
        ("val", "hard_negative"),
    ):
        if ids[left] & ids[right]:
            errors.append(
                f"sample_id overlap: "
                f"{left}/{right}"
            )

    if groups["train"] & groups["val"]:
        errors.append(
            "group_key overlap: train/val"
        )

    if len(groups["train"]) != EXPECTED_TRAIN_GROUPS:
        errors.append(
            "train group count mismatch"
        )

    if len(groups["val"]) != EXPECTED_VAL_GROUPS:
        errors.append(
            "val group count mismatch"
        )

    if (
        len(groups["train"] | groups["val"])
        != EXPECTED_TOTAL_GROUPS
    ):
        errors.append(
            "total group count mismatch"
        )

    if family_counts != EXPECTED_FAMILY_COUNTS:
        errors.append(
            "family count mismatch: "
            f"{family_counts}"
        )

    if set(mapping) != referenced:
        errors.append(
            "RGB mapping/reference mismatch: "
            f"mapping={len(mapping)} "
            f"referenced={len(referenced)}"
        )

    # --------------------------------------------------
    # Check physical release images.
    # --------------------------------------------------

    images_checked = 0

    if check_images:
        canonical_lines: list[str] = []

        images_dir = (
            release_dir / "images"
        ).resolve()

        for sample_id, item in sorted(
            mapping.items()
        ):
            image_path = (
                repo
                / str(
                    item.get("release_rgb_ref")
                )
            ).resolve()

            if not image_path.is_relative_to(
                images_dir
            ):
                errors.append(
                    f"RGB path escapes release "
                    f"images: {sample_id}"
                )
                continue

            if not image_path.is_file():
                errors.append(
                    f"RGB missing: {sample_id}"
                )
                continue

            sha = _sha256(image_path)
            size = image_path.stat().st_size

            if (
                sha != item.get("sha256")
                or size != item.get("size_bytes")
            ):
                errors.append(
                    f"RGB hash/size mismatch: "
                    f"{sample_id}"
                )

            canonical_lines.append(
                f"{image_path.name}\t{sha}\n"
            )

            images_checked += 1

        image_sha = hashlib.sha256(
            "".join(
                canonical_lines
            ).encode("utf-8")
        ).hexdigest()

        image_set = (
            release.get("image_set")
            or {}
        )

        if (
            images_checked
            != image_set.get("count")
        ):
            errors.append(
                "published image count differs "
                "from release manifest"
            )

        if (
            image_sha
            != image_set.get(
                "canonical_sha256"
            )
        ):
            errors.append(
                "published image-set digest "
                "differs from release manifest"
            )

    # --------------------------------------------------
    # Release lock.
    # --------------------------------------------------

    lock_entries: dict[str, str] = {}

    for line in (
        release_dir
        / "b1_release_lock.sha256"
    ).read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue

        digest, sep, name = line.partition(
            "  "
        )

        if (
            not sep
            or name in lock_entries
        ):
            errors.append(
                "malformed/duplicate release "
                "lock entry"
            )
            continue

        lock_entries[name] = digest

    actual_files = sorted(
        p
        for p in release_dir.rglob("*")
        if p.is_file()
        and p.name
        != "b1_release_lock.sha256"
    )

    if len(lock_entries) != len(actual_files):
        errors.append(
            "release lock file-count mismatch"
        )

    for path in actual_files:
        # Release locks are portable manifests and always use POSIX separators.
        # ``str(Path)`` produces backslashes on Windows and previously turned a
        # valid 820-image release into hundreds of false "missing" failures.
        name = path.relative_to(release_dir).as_posix()

        expected = lock_entries.get(name)

        if expected is None:
            errors.append(
                f"release lock missing: {name}"
            )
            continue

        raw_sha = _sha256(path)
        canonical_sha = canonical_text_sha256(path)
        if raw_sha != expected and canonical_sha != expected:
            errors.append(
                f"release lock mismatch: {name}"
            )

    # --------------------------------------------------
    # Provenance / governance.
    # --------------------------------------------------

    if provenance.get("source_runs") != 300:
        errors.append(
            "provenance source_runs mismatch"
        )

    if (
        provenance.get(
            "strict_positive_runs"
        )
        != 280
    ):
        errors.append(
            "provenance strict run mismatch"
        )

    if provenance.get("excluded_runs") != 20:
        errors.append(
            "provenance excluded mismatch"
        )

    if (
        provenance.get("canonical_samples")
        != 820
    ):
        errors.append(
            "provenance sample mismatch"
        )

    if (
        provenance.get("published_families")
        != EXPECTED_FAMILY_COUNTS
    ):
        errors.append(
            "provenance family mismatch"
        )

    if governance.get("source_runs") != 300:
        errors.append(
            "governance source_runs mismatch"
        )

    if (
        governance.get(
            "strict_positive_runs"
        )
        != 280
    ):
        errors.append(
            "governance strict run mismatch"
        )

    if governance.get("excluded_runs") != 20:
        errors.append(
            "governance excluded mismatch"
        )

    if (
        governance.get(
            "strict_positive_samples"
        )
        != 820
    ):
        errors.append(
            "governance sample mismatch"
        )

    # --------------------------------------------------
    # Cumulative lineage.
    # --------------------------------------------------

    cumulative_text = json.dumps(
        cumulative,
        ensure_ascii=False,
        sort_keys=True,
    )

    for name in (
        "d3_wave1_addon_v1",
        "d3_wave2_safe_short_v1",
        "d3_targeted_gap_strict_v1",
        "d3_turn_gap_60_strict_v1",
        "d3_gap300_strict_v1",
    ):
        if name not in cumulative_text:
            errors.append(
                f"missing cumulative lineage: "
                f"{name}"
            )

    evidence = {
        "release_manifest_sha256":
            release_sha,
        "content_bound_pass_sha256":
            canonical_text_sha256(
                release_dir
                / "B1_CONTENT_BOUND_PASS.json"
            ),
        "integrity_report_sha256":
            canonical_text_sha256(
                release_dir
                / "b1_release_integrity_report.json"
            ),
        "release_lock_sha256":
            canonical_text_sha256(
                release_dir
                / "b1_release_lock.sha256"
            ),
    }

    return _report(
        release_dir,
        check_images,
        errors,
        stats,
        images_checked,
        evidence,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate B1 D3 Gap300 "
            "content-bound additive release"
        )
    )

    parser.add_argument(
        "--release-dir",
        type=Path,
        default=Path(
            "challenge/dataset/releases/"
            "d3_gap300_strict_v1"
        ),
    )

    parser.add_argument(
        "--skip-images",
        action="store_true",
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    args = parser.parse_args()

    report = validate_release(
        args.release_dir,
        check_images=not args.skip_images,
    )

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.output.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
