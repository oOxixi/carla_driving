"""Validate frozen B1 Calibration v1.

Checks:
- fixed 300/300 calibration cardinality
- exact partition of the D2 v1.1 540-row reserved pool
- zero sample/group leakage into current A3 train/dev
- selection assignments remain bound to D2 source assignments
- RGB bytes match the published D2 visual_input contract
- manifest/coverage counts
- hashes.sha256 covers every release file
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASES = REPO_ROOT / "challenge/dataset/releases"

TRAIN_FILES = (
    "d2_v1_1/train.jsonl",
    "d3_wave1_addon_v1/train_addition.jsonl",
    "d3_wave2_safe_short_v1/train_addition.jsonl",
    "d3_targeted_gap_strict_v1/train_addition.jsonl",
    "d3_turn_gap_60_strict_v1/train_addition.jsonl",
    "d3_gap300_strict_v1/train_addition.jsonl",
)

DEV_FILES = (
    "d2_v1_1/val.jsonl",
    "d3_wave1_addon_v1/val_addition.jsonl",
    "d3_wave2_safe_short_v1/val_addition.jsonl",
    "d3_targeted_gap_strict_v1/val_addition.jsonl",
    "d3_turn_gap_60_strict_v1/val_addition.jsonl",
    "d3_gap300_strict_v1/val_addition.jsonl",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_published_text(path: Path) -> str:
    """Hash the canonical LF representation used by the release ledger.

    Older Windows checkouts may have materialized the committed text as CRLF
    before ``calibration_v1`` was pinned in ``.gitattributes``.  Accepting only
    the LF-normalized representation keeps the published digest portable while
    still detecting every content change other than checkout line endings.
    """
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for raw in f:
            if raw.strip():
                rows.append(json.loads(raw))
    return rows


def ids_groups(
    rows: list[dict[str, Any]],
) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    groups: set[str] = set()

    for row in rows:
        sid = str(row.get("sample_id") or "")
        group = str(
            (row.get("metadata") or {}).get("group_key")
            or ""
        )
        if sid:
            ids.add(sid)
        if group:
            groups.add(group)

    return ids, groups


def validate(
    calibration_dir: Path,
) -> dict[str, Any]:
    cal = calibration_dir.resolve()
    d2 = RELEASES / "d2_v1_1"

    errors: list[str] = []

    required = {
        "README.md",
        "calibration.jsonl",
        "calibration_manifest.json",
        "calibration_coverage_report.json",
        "selection_assignments.jsonl",
        "rgb_manifest.json",
        "unallocated_reserved_sample_ids.txt",
        "hashes.sha256",
    }

    actual_files = {
        p.name for p in cal.iterdir()
        if p.is_file()
    } if cal.is_dir() else set()

    missing = sorted(required - actual_files)
    if missing:
        errors.append(
            f"required files missing: {missing}"
        )

    if errors:
        return {
            "valid": False,
            "error_count": len(errors),
            "errors": errors,
        }

    calibration = load_jsonl(
        cal / "calibration.jsonl"
    )
    selection = load_jsonl(
        cal / "selection_assignments.jsonl"
    )
    reserved = load_jsonl(
        d2 / "reserved_test_candidates.jsonl"
    )
    assignment_rows = load_jsonl(
        d2 / "source_split_assignments.jsonl"
    )

    assignments = {
        str(r["sample_id"]): r
        for r in assignment_rows
    }

    train: list[dict[str, Any]] = []
    for rel in TRAIN_FILES:
        train.extend(
            load_jsonl(RELEASES / rel)
        )

    dev: list[dict[str, Any]] = []
    for rel in DEV_FILES:
        dev.extend(
            load_jsonl(RELEASES / rel)
        )

    cal_ids, cal_groups = ids_groups(calibration)
    reserved_ids, _ = ids_groups(reserved)
    train_ids, train_groups = ids_groups(train)
    dev_ids, dev_groups = ids_groups(dev)

    selection_ids = {
        str(r.get("sample_id") or "")
        for r in selection
    }
    selection_groups = {
        str(r.get("group_key") or "")
        for r in selection
    }

    unallocated = {
        x.strip()
        for x in (
            cal / "unallocated_reserved_sample_ids.txt"
        ).read_text(encoding="utf-8").splitlines()
        if x.strip()
    }

    if len(calibration) != 300:
        errors.append(
            f"calibration rows={len(calibration)} != 300"
        )
    if len(cal_ids) != 300:
        errors.append(
            f"calibration IDs={len(cal_ids)} != 300"
        )
    if len(cal_groups) != 300:
        errors.append(
            f"calibration groups={len(cal_groups)} != 300"
        )
    if len(selection) != 300:
        errors.append(
            f"selection rows={len(selection)} != 300"
        )
    if len(unallocated) != 240:
        errors.append(
            f"unallocated={len(unallocated)} != 240"
        )

    if cal_ids & unallocated:
        errors.append(
            "calibration/unallocated sample overlap"
        )

    if (cal_ids | unallocated) != reserved_ids:
        errors.append(
            "calibration + unallocated does not exactly "
            "partition D2 reserved pool"
        )

    if cal_ids & train_ids:
        errors.append("train sample leakage")
    if cal_ids & dev_ids:
        errors.append("dev sample leakage")
    if cal_groups & train_groups:
        errors.append("train group leakage")
    if cal_groups & dev_groups:
        errors.append("dev group leakage")

    if selection_ids != cal_ids:
        errors.append(
            "selection/calibration sample mismatch"
        )
    if selection_groups != cal_groups:
        errors.append(
            "selection/calibration group mismatch"
        )

    for row in selection:
        sid = str(row.get("sample_id") or "")
        source = assignments.get(sid)

        if source is None:
            errors.append(
                f"missing D2 assignment: {sid}"
            )
            continue

        checks = (
            ("group_key", "group_key"),
            ("source", "source"),
            ("scenario_family", "scenario_family"),
            ("scenario_id", "scenario_id"),
            ("seed", "seed"),
            (
                "assignment_training_role",
                "training_role",
            ),
        )

        for local_key, source_key in checks:
            if row.get(local_key) != source.get(source_key):
                errors.append(
                    f"{sid}: {local_key} source mismatch"
                )

    rgb_manifest = json.loads(
        (cal / "rgb_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    if set(rgb_manifest) != cal_ids:
        errors.append(
            "RGB manifest sample set mismatch"
        )

    calibration_by_id = {
        str(r["sample_id"]): r
        for r in calibration
    }

    rgb_checked = 0

    for sid in sorted(cal_ids):
        row = calibration_by_id[sid]
        visual = row.get("visual_input") or {}

        rgb_ref = str(
            visual.get("rgb_ref") or ""
        )

        path = REPO_ROOT / rgb_ref

        if not rgb_ref or not path.is_file():
            errors.append(
                f"{sid}: RGB missing"
            )
            continue

        actual_sha = sha256(path)
        actual_size = path.stat().st_size

        if actual_sha != visual.get("rgb_sha256"):
            errors.append(
                f"{sid}: visual RGB SHA mismatch"
            )
        if actual_size != visual.get("size_bytes"):
            errors.append(
                f"{sid}: visual RGB size mismatch"
            )

        mapped = rgb_manifest.get(sid) or {}

        if actual_sha != mapped.get("sha256"):
            errors.append(
                f"{sid}: calibration RGB SHA mismatch"
            )
        if actual_size != mapped.get("size_bytes"):
            errors.append(
                f"{sid}: calibration RGB size mismatch"
            )

        rgb_checked += 1

    manifest = json.loads(
        (cal / "calibration_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    if manifest.get("dataset_version") != "b1_calibration_v1":
        errors.append("dataset_version mismatch")
    if manifest.get("status") != "FROZEN_CALIBRATION":
        errors.append("release status mismatch")
    if manifest.get("target_count") != 300:
        errors.append("target_count mismatch")

    counts = manifest.get("counts") or {}
    if counts.get("source_pool") != 540:
        errors.append("source_pool count mismatch")
    if counts.get("calibration") != 300:
        errors.append("calibration count mismatch")
    if counts.get("unallocated_reserved") != 240:
        errors.append("unallocated count mismatch")

    coverage = json.loads(
        (
            cal / "calibration_coverage_report.json"
        ).read_text(encoding="utf-8")
    )

    expected_coverage = {
        "pool_samples": 540,
        "pool_groups": 540,
        "selected_samples": 300,
        "selected_groups": 300,
        "unallocated_samples": 240,
        "unallocated_groups": 240,
    }

    for key, expected in expected_coverage.items():
        if coverage.get(key) != expected:
            errors.append(
                f"coverage {key} mismatch"
            )

    listed: dict[str, str] = {}
    for raw in (
        cal / "hashes.sha256"
    ).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, name = raw.split(None, 1)
        listed[name.strip()] = digest

    expected_hashed = {
        p.name
        for p in cal.iterdir()
        if p.is_file()
        and p.name != "hashes.sha256"
    }

    if set(listed) != expected_hashed:
        errors.append(
            "hash manifest file coverage mismatch"
        )

    for name, expected in listed.items():
        path = cal / name
        if sha256(path) != expected and sha256_published_text(path) != expected:
            errors.append(
                f"content hash mismatch: {name}"
            )

    return {
        "valid": not errors,
        "dataset_version": manifest.get(
            "dataset_version"
        ),
        "calibration_samples": len(calibration),
        "calibration_groups": len(cal_groups),
        "unallocated_reserved": len(unallocated),
        "train_sample_overlap": len(cal_ids & train_ids),
        "dev_sample_overlap": len(cal_ids & dev_ids),
        "train_group_overlap": len(cal_groups & train_groups),
        "dev_group_overlap": len(cal_groups & dev_groups),
        "rgb_checked": rgb_checked,
        "error_count": len(errors),
        "errors": errors[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=(
            RELEASES / "calibration_v1"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    args = parser.parse_args()

    report = validate(args.release_dir)

    text = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    print(text, end="")

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            text,
            encoding="utf-8",
        )

    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
