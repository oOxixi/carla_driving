from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from challenge.dataset.validate_d2_release import canonical_text_sha256


REPO = Path(__file__).resolve().parents[2]

SOURCE_REPO = Path(
    "/home/dcase_task2/dongfeng_voice/"
    "carla_driving_challenge_b1_d3_wave2"
)

SOURCE_ARTIFACT = SOURCE_REPO / (
    "artifacts/b1_d3_wave2_safe_short_499_exec_v2_v1"
)

SOURCE_DATASET = SOURCE_ARTIFACT / "dataset/d2_valid.jsonl"
SOURCE_PROVENANCE = SOURCE_ARTIFACT / "provenance_manifest.json"
SOURCE_AUDIT = SOURCE_REPO / "artifacts/audit_d3_wave2_safe_short_499_v1"
SOURCE_SELECTION = SOURCE_REPO / (
    "artifacts/b1_d3_wave2_selection_safe_short_v2/"
    "safe_short_selection.json"
)
SOURCE_PLAN = SOURCE_REPO / (
    "artifacts/b1_d3_wave2_execution_plan_v2/"
    "d3_wave2_execution_plan_v2.json"
)

TEACHER_MANIFEST = REPO / (
    "challenge/teacher_pinned_manifest_wave2_sync_v1.json"
)

RELEASE_REL = Path(
    "challenge/dataset/releases/d3_wave2_safe_short_v1"
)
RELEASE = REPO / RELEASE_REL

DATASET_VERSION = "b1_d3_wave2_safe_short_v1"
COHORT_VERSION = (
    "teacher_distill_v0.6_"
    "d3_expansion_wave2_targeted_v4_sync_v1"
)

EXPECTED_TEACHER_SHA = (
    "252984d37e49ddc11eaddcde2bfb26d0d6f2086b"
)

EXPECTED_COUNTS = {
    "A01": 114,
    "A06": 114,
    "CX01": 146,
    "CX02": 125,
}

PUBLISH_FAMILIES = {"A01", "A06", "CX01"}


def raw_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_size(path: Path) -> int:
    return len(path.read_bytes().replace(b"\r\n", b"\n"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception as exc:
                raise RuntimeError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                )
    return out


def write_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )


def family_of(row: dict[str, Any]) -> str:
    sid = str(
        (row.get("metadata") or {}).get("scenario_id") or ""
    )

    if sid.startswith("ACC_A01_"):
        return "A01"
    if sid.startswith("ACC_A06_"):
        return "A06"
    if sid.startswith("CX01_"):
        return "CX01"
    if sid.startswith("CX02_"):
        return "CX02"

    return "UNKNOWN"


def teacher_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "teacher_profile": manifest["teacher_profile"],
        "teacher_git_sha": manifest["teacher_git_sha"],
        "model_id": manifest["model_id"],
        "model_revision": manifest["model_revision"],
        "artifact_fingerprint": manifest[
            "model_artifact_sha256"
        ],
        "quantization": manifest.get("quantization"),
        "dtype": manifest["dtype"],
    }


def strict_positive(row: dict[str, Any]) -> bool:
    q = row.get("quality") or {}
    c = row.get("closed_loop_quality") or {}

    return (
        q.get("training_role") == "POSITIVE"
        and q.get("valid_for_training") is True
        and c.get("run_status") == "SUCCEEDED"
        and c.get("scenario_acceptance_passed") is True
        and c.get("command_terminal_status") == "SUCCEEDED"
        and c.get("plan_terminal_state") == "SUCCEEDED"
    )


def group_record(row: dict[str, Any]) -> dict[str, Any]:
    md = row["metadata"]
    return {
        "group_id": md["group_key"],
        "scenario_family": md["scenario_family"],
        "map": md["map"],
        "route_hash": md["route_hash"],
        "seed": md["seed"],
    }


def split_group_aware(
    rows: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        key = str((row.get("metadata") or {}).get("group_key") or "")
        if not key:
            raise RuntimeError(
                f"missing group_key: {row.get('sample_id')}"
            )
        grouped[key].append(row)

    ordered = sorted(
        grouped,
        key=lambda g: hashlib.sha256(
            g.encode("utf-8")
        ).hexdigest(),
    )

    target = round(len(rows) * 0.85)

    train_keys: list[str] = []
    val_keys: list[str] = []
    train_n = 0

    for key in ordered:
        n = len(grouped[key])

        before = abs(target - train_n)
        after = abs(target - (train_n + n))

        if train_n < target and after <= before:
            train_keys.append(key)
            train_n += n
        else:
            val_keys.append(key)

    if not train_keys or not val_keys:
        raise RuntimeError("group-aware split produced empty split")

    train = [
        row
        for key in train_keys
        for row in grouped[key]
    ]
    val = [
        row
        for key in val_keys
        for row in grouped[key]
    ]

    train_groups = [
        group_record(grouped[k][0])
        for k in train_keys
    ]
    val_groups = [
        group_record(grouped[k][0])
        for k in val_keys
    ]

    return train, val, train_groups, val_groups


def manifest_entry(path: Path) -> dict[str, Any]:
    return {
        "sha256": canonical_text_sha256(path),
        "size_bytes": normalized_size(path),
    }


def main() -> None:
    if RELEASE.exists():
        raise SystemExit(
            f"REFUSING TO OVERWRITE EXISTING RELEASE: {RELEASE}"
        )

    for p in (
        SOURCE_DATASET,
        SOURCE_PROVENANCE,
        SOURCE_SELECTION,
        SOURCE_PLAN,
        TEACHER_MANIFEST,
        SOURCE_AUDIT / "run_audit.json",
        SOURCE_AUDIT / "failed_runs.json",
        SOURCE_AUDIT / "non_positive_samples.json",
    ):
        if not p.is_file():
            raise SystemExit(f"MISSING REQUIRED SOURCE: {p}")

    teacher_manifest = load_json(TEACHER_MANIFEST)

    if (
        teacher_manifest.get("teacher_git_sha")
        != EXPECTED_TEACHER_SHA
    ):
        raise SystemExit("WAVE2 TEACHER SHA MISMATCH")

    teacher = teacher_identity(teacher_manifest)

    rows = load_jsonl(SOURCE_DATASET)

    if len(rows) != 499:
        raise SystemExit(
            f"expected 499 source rows, got {len(rows)}"
        )

    ids = [str(x.get("sample_id") or "") for x in rows]
    if "" in ids or len(ids) != len(set(ids)):
        raise SystemExit("source sample_id missing/duplicate")

    family_counts = Counter(family_of(x) for x in rows)

    if dict(family_counts) != EXPECTED_COUNTS:
        raise SystemExit(
            f"unexpected family counts: {dict(family_counts)}"
        )

    selected = [
        x for x in rows
        if family_of(x) in PUBLISH_FAMILIES
    ]

    if len(selected) != 374:
        raise SystemExit(
            f"expected 374 publish rows, got {len(selected)}"
        )

    if any(family_of(x) == "CX02" for x in selected):
        raise SystemExit("CX02 leaked into publication subset")

    failed_positive = [
        x["sample_id"]
        for x in selected
        if not strict_positive(x)
    ]

    if failed_positive:
        raise SystemExit(
            "non-strict-positive rows in selected subset: "
            + repr(failed_positive[:20])
        )

    run_audit = load_json(SOURCE_AUDIT / "run_audit.json")
    failed_runs = load_json(SOURCE_AUDIT / "failed_runs.json")
    non_positive = load_json(
        SOURCE_AUDIT / "non_positive_samples.json"
    )

    if len(run_audit) != 499:
        raise SystemExit("run_audit count is not 499")

    if len(failed_runs) != 25 or len(non_positive) != 25:
        raise SystemExit(
            "historical audit no longer matches frozen evidence"
        )

    for item in failed_runs + non_positive:
        sid = str(item.get("scenario_id") or "")
        if not sid.startswith("CX02_"):
            raise SystemExit(
                "non-CX02 failure/non-positive found in frozen audit"
            )

    RELEASE.mkdir(parents=True)
    images_dir = RELEASE / "images"
    images_dir.mkdir()

    rewritten: list[dict[str, Any]] = []
    rgb_mapping: dict[str, dict[str, Any]] = {}

    for original in selected:
        row = json.loads(json.dumps(original))
        sample_id = row["sample_id"]

        if row.get("dataset_version") != COHORT_VERSION:
            raise SystemExit(
                f"{sample_id}: unexpected cohort version "
                f"{row.get('dataset_version')}"
            )

        visual = row.get("visual_input") or {}
        model_request = row.get("model_request") or {}

        src_ref = visual.get("rgb_ref")

        if not isinstance(src_ref, str):
            raise SystemExit(
                f"{sample_id}: missing source rgb_ref"
            )

        if model_request.get("rgb_ref") != src_ref:
            raise SystemExit(
                f"{sample_id}: source RGB references differ"
            )

        src_image = SOURCE_REPO / src_ref

        if not src_image.is_file():
            raise SystemExit(
                f"{sample_id}: source image missing: {src_image}"
            )

        actual_sha = raw_sha256(src_image)
        actual_size = src_image.stat().st_size

        if actual_sha != visual.get("rgb_sha256"):
            raise SystemExit(
                f"{sample_id}: source image SHA mismatch"
            )

        if actual_size != visual.get("size_bytes"):
            raise SystemExit(
                f"{sample_id}: source image size mismatch"
            )

        suffix = src_image.suffix.lower()

        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise SystemExit(
                f"{sample_id}: unsupported image suffix {suffix}"
            )

        dst_name = f"{sample_id}{suffix}"
        dst_image = images_dir / dst_name

        shutil.copy2(src_image, dst_image)

        if raw_sha256(dst_image) != actual_sha:
            raise SystemExit(
                f"{sample_id}: copied image SHA mismatch"
            )

        release_ref = str(
            RELEASE_REL / "images" / dst_name
        )

        row["model_request"]["rgb_ref"] = release_ref

        row["visual_input"]["rgb_ref"] = release_ref
        row["visual_input"]["resolved_path"] = release_ref
        row["visual_input"]["rgb_sha256"] = actual_sha
        row["visual_input"]["size_bytes"] = actual_size
        row["visual_input"]["available"] = True

        rgb_mapping[sample_id] = {
            "release_rgb_ref": release_ref,
            "sha256": actual_sha,
            "size_bytes": actual_size,
        }

        rewritten.append(row)

    if len(rgb_mapping) != 374:
        raise SystemExit("RGB mapping count is not 374")

    train, val, train_groups, val_groups = split_group_aware(
        rewritten
    )

    train_group_ids = {
        x["group_id"] for x in train_groups
    }
    val_group_ids = {
        x["group_id"] for x in val_groups
    }

    if train_group_ids & val_group_ids:
        raise SystemExit("train/val group overlap")

    if len(train) + len(val) != 374:
        raise SystemExit("split lost rows")

    write_jsonl(RELEASE / "train_addition.jsonl", train)
    write_jsonl(RELEASE / "val_addition.jsonl", val)

    # Validator requires this file.  This release intentionally has
    # no hard negatives.
    (RELEASE / "hard_negative_addition.jsonl").write_text(
        "",
        encoding="utf-8",
    )

    write_json(RELEASE / "rgb_mapping.json", rgb_mapping)

    split_manifest = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "counts": {
            "strict_positive": 374,
            "train_addition": len(train),
            "val_addition": len(val),
            "hard_negative_addition": 0,
            "quarantine": 0,
        },
        "split_policy": {
            "type": "group_aware",
            "group_fields": [
                "metadata.scenario_family",
                "metadata.map",
                "metadata.route_hash",
                "metadata.seed",
            ],
            "target_ratio": {
                "train_addition": 0.85,
                "val_addition": 0.15,
            },
            "note": (
                "D3 Wave2 safe-short preserves group isolation. "
                "All historical CX02 samples are excluded from "
                "this release and must not be relabeled after "
                "the later CX02 fix."
            ),
        },
        "groups": {
            "train_addition": train_groups,
            "val_addition": val_groups,
        },
    }

    write_json(RELEASE / "split_manifest.json", split_manifest)

    provenance = load_json(SOURCE_PROVENANCE)

    release_provenance = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "release_type": "additive",
        "base_release": "d2_v1_1",
        "prior_addon_release": "d3_wave1_addon_v1",
        "raw_source_immutable": True,
        "source_artifact": (
            "artifacts/"
            "b1_d3_wave2_safe_short_499_exec_v2_v1"
        ),
        "source_dataset_file": str(SOURCE_DATASET),
        "source_selection": str(SOURCE_SELECTION),
        "source_selection_sha256": raw_sha256(SOURCE_SELECTION),
        "source_execution_provenance_sha256": raw_sha256(
            SOURCE_PROVENANCE
        ),
        "source_plan": str(SOURCE_PLAN),
        "source_plan_sha256": raw_sha256(SOURCE_PLAN),
        "teacher_manifest": (
            "challenge/"
            "teacher_pinned_manifest_wave2_sync_v1.json"
        ),
        "teacher_manifest_sha256": raw_sha256(
            TEACHER_MANIFEST
        ),
        "teacher_git_sha": [
            teacher_manifest["teacher_git_sha"]
        ],
        "teacher_model_id": [
            teacher_manifest["model_id"]
        ],
        "teacher_model_revision": (
            teacher_manifest["model_revision"]
        ),
        "teacher_model_artifact_sha256": (
            teacher_manifest["model_artifact_sha256"]
        ),
        "teacher_profile": (
            teacher_manifest["teacher_profile"]
        ),
        "source_dataset_version": provenance.get(
            "dataset_version"
        ),
        "published_families": {
            "A01": 114,
            "A06": 114,
            "CX01": 146,
        },
        "excluded_historical_family": {
            "CX02": 125,
        },
    }

    write_json(
        RELEASE / "provenance_manifest.json",
        release_provenance,
    )

    governance = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "source_runs": 499,
        "source_samples": 499,
        "strict_positive": 374,
        "hard_negative": 0,
        "terminal_inconsistent_positive_quarantined": 0,
        "quarantine_scenarios": {},
        "published_family_counts": {
            "A01": 114,
            "A06": 114,
            "CX01": 146,
        },
        "excluded_family_counts": {
            "CX02": 125,
        },
        "exclusion_policy": (
            "Exclude the entire historical CX02 cohort. "
            "Although 100 historical CX02 rows were positive, "
            "CX02 was subsequently root-cause diagnosed and "
            "fixed. Historical raw data remain immutable and "
            "must not be relabeled using the later fix."
        ),
        "strict_positive_rule": {
            "closed_loop_quality.command_terminal_status":
                "SUCCEEDED",
            "closed_loop_quality.plan_terminal_state":
                "SUCCEEDED",
            "closed_loop_quality.run_status":
                "SUCCEEDED",
            "closed_loop_quality.scenario_acceptance_passed":
                True,
            "quality.training_role":
                "POSITIVE",
            "quality.valid_for_training":
                True,
        },
    }

    write_json(
        RELEASE / "governance_report.json",
        governance,
    )

    cumulative = {
        "schema_version": "1.0",
        "view_id": (
            "b1_d2_v1_1_plus_d3_wave1_plus_"
            "d3_wave2_safe_short_v1"
        ),
        "base_release": {
            "path": (
                "challenge/dataset/releases/d2_v1_1"
            ),
            "immutable": True,
        },
        "prior_addon_release": {
            "path": (
                "challenge/dataset/releases/"
                "d3_wave1_addon_v1"
            ),
            "immutable": True,
        },
        "addon_release": {
            "path": str(RELEASE_REL),
            "immutable_after_publish": True,
        },
        "a3_training_inputs": [
            "challenge/dataset/releases/d2_v1_1/train.jsonl",
            (
                "challenge/dataset/releases/"
                "d3_wave1_addon_v1/train_addition.jsonl"
            ),
            str(RELEASE_REL / "train_addition.jsonl"),
        ],
        "a3_dev_inputs": [
            "challenge/dataset/releases/d2_v1_1/val.jsonl",
            (
                "challenge/dataset/releases/"
                "d3_wave1_addon_v1/val_addition.jsonl"
            ),
            str(RELEASE_REL / "val_addition.jsonl"),
        ],
        "hard_negative_pool": None,
        "reserved_test_policy": {
            "d2_v1_1_reserved_test_candidates":
                "not used for A3 tuning",
            "d3_wave1_new_test": False,
            "d3_wave2_safe_short_new_test": False,
        },
        "generalization_note": (
            "D3 Wave2 safe-short is an additive "
            "training/development cohort. It contains only "
            "historically qualified non-CX02 strict-positive "
            "samples."
        ),
    }

    write_json(
        RELEASE / "cumulative_view_manifest.json",
        cumulative,
    )

    readme = f"""# B1 D3 Wave2 Safe-Short Additive Release

Dataset version: `{DATASET_VERSION}`.

This release contains **374 strict-positive samples** from the
historical D3 Wave2 safe-short execution:

- A01: 114
- A06: 114
- CX01: 146

The entire historical CX02 family (125 runs) is intentionally
excluded.  CX02 was later root-cause diagnosed and fixed; those old
raw runs remain immutable and are not relabeled.

Teacher execution identity:

- profile: `{teacher_manifest["teacher_profile"]}`
- git SHA: `{teacher_manifest["teacher_git_sha"]}`
- model: `{teacher_manifest["model_id"]}`
- revision: `{teacher_manifest["model_revision"]}`

This is an additive training/development release.  It does not replace
D2 v1.1 or D3 Wave1.

The raw source artifact is immutable.
"""

    (RELEASE / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    canonical_lines: list[str] = []

    for sample_id, item in sorted(rgb_mapping.items()):
        path = REPO / item["release_rgb_ref"]
        canonical_lines.append(
            f"{path.name}\t{item['sha256']}\n"
        )

    image_set_sha = hashlib.sha256(
        "".join(canonical_lines).encode("utf-8")
    ).hexdigest()

    core_files = [
        "README.md",
        "cumulative_view_manifest.json",
        "governance_report.json",
        "hard_negative_addition.jsonl",
        "provenance_manifest.json",
        "rgb_mapping.json",
        "split_manifest.json",
        "train_addition.jsonl",
        "val_addition.jsonl",
    ]

    release_manifest = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "release_type": "additive",
        "base_release": "d2_v1_1",
        "status": "B1_RELEASE_CANDIDATE",
        "counts": {
            "train_addition": len(train),
            "val_addition": len(val),
            "hard_negative_addition": 0,
            "quarantine": 0,
            "images": 374,
        },
        "files": {
            name: manifest_entry(RELEASE / name)
            for name in core_files
        },
        "image_set": {
            "count": 374,
            "canonical_sha256": image_set_sha,
        },
    }

    write_json(
        RELEASE / "release_manifest.json",
        release_manifest,
    )

    release_sha = canonical_text_sha256(
        RELEASE / "release_manifest.json"
    )

    file_checks = {
        name: manifest_entry(RELEASE / name)
        for name in core_files
    }

    integrity = {
        "schema_version": "1.0",
        "report_type": "B1_RELEASE_INTEGRITY",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_version": DATASET_VERSION,
        "release_status": "B1_RELEASE_CANDIDATE",
        "teacher": teacher,
        "counts": {
            "source_runs": 499,
            "source_samples": 499,
            "strict_positive": 374,
            "train_addition": len(train),
            "val_addition": len(val),
            "hard_negative_addition": 0,
            "quarantine": 0,
            "images": 374,
        },
        "image_set": {
            "count": 374,
            "canonical_sha256": image_set_sha,
        },
        "file_checks": file_checks,
        "release_manifest_sha256": release_sha,
        "cumulative_view_manifest_sha256":
            canonical_text_sha256(
                RELEASE / "cumulative_view_manifest.json"
            ),
        "release_provenance_sha256":
            canonical_text_sha256(
                RELEASE / "provenance_manifest.json"
            ),
        "teacher_manifest_sha256":
            canonical_text_sha256(TEACHER_MANIFEST),
        "execution_provenance_sha256":
            raw_sha256(SOURCE_PROVENANCE),
        "status": "PASS",
    }

    write_json(
        RELEASE / "b1_release_integrity_report.json",
        integrity,
    )

    # Freeze the immutable published text files.
    # B1_SIGNED_PASS is intentionally excluded to avoid a hash cycle.
    lock_names = [
        *core_files,
        "release_manifest.json",
        "b1_release_integrity_report.json",
    ]

    lock_lines = []

    for name in sorted(lock_names):
        digest = canonical_text_sha256(RELEASE / name)
        lock_lines.append(f"{digest}  {name}\n")

    (RELEASE / "b1_release_lock.sha256").write_text(
        "".join(lock_lines),
        encoding="utf-8",
    )

    lock_sha = canonical_text_sha256(
        RELEASE / "b1_release_lock.sha256"
    )

    integrity_sha = canonical_text_sha256(
        RELEASE / "b1_release_integrity_report.json"
    )

    signature = {
        "schema_version": "1.0",
        "gate": "B1_SIGNED_PASS",
        "status": "PASS",
        "dataset_version": DATASET_VERSION,
        "signed_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "release_manifest_sha256": release_sha,
        "image_set_canonical_sha256": image_set_sha,
        "integrity_report_sha256": integrity_sha,
        "release_lock_sha256": lock_sha,
        "teacher": teacher,
    }

    write_json(
        RELEASE / "B1_SIGNED_PASS.json",
        signature,
    )

    print("===== BUILD COMPLETE =====")
    print("release =", RELEASE)
    print("source_rows =", len(rows))
    print("published_rows =", len(rewritten))
    print("family_counts =", dict(family_counts))
    print("train =", len(train))
    print("val =", len(val))
    print("train_groups =", len(train_groups))
    print("val_groups =", len(val_groups))
    print("hard_negative =", 0)
    print("images =", len(rgb_mapping))
    print("CX02_published =", 0)
    print("image_set_sha256 =", image_set_sha)
    print("release_manifest_sha256 =", release_sha)
    print("integrity_report_sha256 =", integrity_sha)
    print("release_lock_sha256 =", lock_sha)


if __name__ == "__main__":
    main()
