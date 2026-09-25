from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from challenge.dataset.validate_d2_release import canonical_text_sha256


REPO = Path(__file__).resolve().parents[2]

TARGET_REPO = Path(
    "/home/dcase_task2/dongfeng_voice/carla_targeted_collection_dev"
)

RGB_SOURCE_REPO = Path(
    "/home/dcase_task2/dongfeng_voice/"
    "carla_driving_challenge_b1_d3_wave2"
)

SOURCE_ROOT = TARGET_REPO / (
    "artifacts/targeted_gap_batch_v1/canonical_strict_v1"
)

SOURCE_DATASET = SOURCE_ROOT / "d2_valid.jsonl"
SOURCE_REJECTED = SOURCE_ROOT / "d2_rejected.jsonl"
SOURCE_MANIFEST = SOURCE_ROOT / "release_source_manifest.json"

RELEASE_REL = Path(
    "challenge/dataset/releases/d3_targeted_gap_strict_v1"
)
RELEASE = REPO / RELEASE_REL

DATASET_VERSION = "b1_d3_targeted_gap_strict_v1"
SOURCE_DATASET_VERSION = (
    "teacher_distill_v0.6_targeted_gap_strict_v1"
)

EXPECTED_ROWS = 660
EXPECTED_RUNS = 280

EXPECTED_FAMILIES = {
    "TC_E01": 120,
    "TC_F01": 450,
    "ACC_C04": 20,
    "SUP_C07": 20,
    "TC_G01": 50,
}

EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "67c51c9c5fe43f9df77fe5a01d9b294"
    "776a418a25bc4495208323bc4ab53dd2b"
)

EXPECTED_CANONICAL_SHA256 = (
    "9541807a3aa9b668363e452c8983c3bf"
    "f06c6ec2dfd87a9565f53b2bef7b66d4"
)

EXPECTED_IMAGE_SET_SHA256 = (
    "5ef12507ac09e39f8bc44ec076c6f0f9"
    "e8a2521b93e883a2670c6ba0cd11e6e3"
)

EXPECTED_COLLECTOR_SHA256 = (
    "792528d5564130ed8982f552e1207e3fa"
    "97eaaea3b992cdaaeea0370de002485"
)


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
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception as exc:
                raise RuntimeError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                ) from exc
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


def write_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
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

    for prefix in EXPECTED_FAMILIES:
        if sid.startswith(prefix):
            return prefix

    return "UNKNOWN"


def strict_positive(row: dict[str, Any]) -> bool:
    q = row.get("quality") or {}
    c = row.get("closed_loop_quality") or {}

    return (
        q.get("training_role") == "POSITIVE"
        and q.get("valid_for_training") is True
        and q.get("rgb_exists") is True
        and c.get("run_status") == "SUCCEEDED"
        and c.get("scenario_acceptance_passed") is True
        and c.get("command_terminal_status") == "SUCCEEDED"
        and c.get("plan_terminal_state") == "SUCCEEDED"
        and int(c.get("collision_count") or 0) == 0
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
        key = str(
            (row.get("metadata") or {}).get("group_key") or ""
        )
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
        raise RuntimeError(
            "group-aware split produced empty split"
        )

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
        SOURCE_REJECTED,
        SOURCE_MANIFEST,
    ):
        if not p.is_file():
            raise SystemExit(f"MISSING REQUIRED SOURCE: {p}")

    if raw_sha256(SOURCE_MANIFEST) != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise SystemExit("SOURCE MANIFEST SHA256 MISMATCH")

    if raw_sha256(SOURCE_DATASET) != EXPECTED_CANONICAL_SHA256:
        raise SystemExit("CANONICAL DATASET SHA256 MISMATCH")

    if SOURCE_REJECTED.stat().st_size != 0:
        raise SystemExit("REJECTED DATASET IS NOT EMPTY")

    source_manifest = load_json(SOURCE_MANIFEST)

    collector_info = (
        source_manifest.get("canonicalization") or {}
    )

    if (
        collector_info.get("collector_sha256")
        != EXPECTED_COLLECTOR_SHA256
    ):
        raise SystemExit("COLLECTOR SHA256 MISMATCH")

    rows = load_jsonl(SOURCE_DATASET)

    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(
            f"expected {EXPECTED_ROWS} rows, got {len(rows)}"
        )

    ids = [str(x.get("sample_id") or "") for x in rows]

    if "" in ids or len(ids) != len(set(ids)):
        raise SystemExit("sample_id missing/duplicate")

    if any(
        x.get("dataset_version") != SOURCE_DATASET_VERSION
        for x in rows
    ):
        raise SystemExit("SOURCE DATASET VERSION MISMATCH")

    families = Counter(family_of(x) for x in rows)

    if dict(families) != EXPECTED_FAMILIES:
        raise SystemExit(
            f"unexpected family counts: {dict(families)}"
        )

    bad = [
        x["sample_id"]
        for x in rows
        if not strict_positive(x)
    ]

    if bad:
        raise SystemExit(
            "non-strict-positive rows found: "
            + repr(bad[:20])
        )

    run_ids = {
        str((x.get("metadata") or {}).get("run_id") or "")
        for x in rows
    }

    if "" in run_ids or len(run_ids) != EXPECTED_RUNS:
        raise SystemExit(
            f"expected {EXPECTED_RUNS} unique runs, "
            f"got {len(run_ids)}"
        )

    group_ids = {
        str((x.get("metadata") or {}).get("group_key") or "")
        for x in rows
    }

    if "" in group_ids or len(group_ids) != EXPECTED_RUNS:
        raise SystemExit(
            f"expected {EXPECTED_RUNS} groups, "
            f"got {len(group_ids)}"
        )

    RELEASE.mkdir(parents=True)
    images_dir = RELEASE / "images"
    images_dir.mkdir()

    rewritten: list[dict[str, Any]] = []
    rgb_mapping: dict[str, dict[str, Any]] = {}

    source_image_lines: list[str] = []

    for original in rows:
        row = json.loads(json.dumps(original))
        sample_id = row["sample_id"]

        visual = row.get("visual_input") or {}
        request = row.get("model_request") or {}

        src_ref = visual.get("rgb_ref")

        if not isinstance(src_ref, str) or not src_ref:
            raise SystemExit(
                f"{sample_id}: missing source rgb_ref"
            )

        if request.get("rgb_ref") != src_ref:
            raise SystemExit(
                f"{sample_id}: source RGB refs differ"
            )

        src_image = RGB_SOURCE_REPO / src_ref

        if not src_image.is_file():
            raise SystemExit(
                f"{sample_id}: source image missing: "
                f"{src_image}"
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

        source_image_lines.append(
            f"{src_ref}\t{actual_size}\t{actual_sha}\n"
        )

        suffix = src_image.suffix.lower()

        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise SystemExit(
                f"{sample_id}: unsupported image suffix "
                f"{suffix}"
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

        row["dataset_version"] = DATASET_VERSION

        row["model_request"]["rgb_ref"] = release_ref

        row["visual_input"]["rgb_ref"] = release_ref
        row["visual_input"]["resolved_path"] = release_ref
        row["visual_input"]["rgb_sha256"] = actual_sha
        row["visual_input"]["size_bytes"] = actual_size
        row["visual_input"]["available"] = True

        rgb_mapping[sample_id] = {
            "original_rgb_ref": src_ref,
            "release_rgb_ref": release_ref,
            "sha256": actual_sha,
            "size_bytes": actual_size,
        }

        rewritten.append(row)

    if len(rgb_mapping) != EXPECTED_ROWS:
        raise SystemExit(
            f"RGB mapping count != {EXPECTED_ROWS}"
        )

    source_image_sha = hashlib.sha256(
        "".join(sorted(source_image_lines)).encode("utf-8")
    ).hexdigest()

    if source_image_sha != EXPECTED_IMAGE_SET_SHA256:
        raise SystemExit(
            "SOURCE IMAGE SET SHA256 MISMATCH\n"
            f"actual={source_image_sha}\n"
            f"expected={EXPECTED_IMAGE_SET_SHA256}"
        )

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

    if len(train) + len(val) != EXPECTED_ROWS:
        raise SystemExit("split lost rows")

    write_jsonl(
        RELEASE / "train_addition.jsonl",
        train,
    )
    write_jsonl(
        RELEASE / "val_addition.jsonl",
        val,
    )

    (
        RELEASE / "hard_negative_addition.jsonl"
    ).write_text("", encoding="utf-8")

    write_json(
        RELEASE / "rgb_mapping.json",
        rgb_mapping,
    )

    split_manifest = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "counts": {
            "strict_positive": EXPECTED_ROWS,
            "source_runs": 500,
            "strict_positive_runs": EXPECTED_RUNS,
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
                "All command-level samples originating from "
                "the same closed-loop run/group remain in the "
                "same split."
            ),
        },
        "groups": {
            "train_addition": train_groups,
            "val_addition": val_groups,
        },
    }

    write_json(
        RELEASE / "split_manifest.json",
        split_manifest,
    )

    provenance = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "release_type": "additive",
        "base_release": "d2_v1_1",
        "prior_addon_releases": [
            "d3_wave1_addon_v1",
            "d3_wave2_safe_short_v1",
        ],
        "raw_source_immutable": True,
        "acquisition_git_sha":
            "a6743feb52015031f70e2c21a94aef0abae0a65a",
        "source_runs": 500,
        "strict_positive_runs": 280,
        "excluded_runs": 220,
        "canonical_samples": 660,
        "source_dataset_version": SOURCE_DATASET_VERSION,
        "source_dataset_sha256":
            raw_sha256(SOURCE_DATASET),
        "source_release_manifest_sha256":
            raw_sha256(SOURCE_MANIFEST),
        "source_image_set_sha256":
            source_image_sha,
        "collector_repo_git_sha":
            collector_info.get("collector_repo_git_sha"),
        "collector_last_change_commit":
            collector_info.get(
                "collector_last_change_commit"
            ),
        "collector_sha256":
            collector_info.get("collector_sha256"),
        "published_families": EXPECTED_FAMILIES,
        "excluded_run_count": 220,
        "selection_policy": (
            "Only contract-aware strict-positive closed-loop "
            "runs are canonicalized and published. Historical "
            "failed runs remain immutable and are not relabeled."
        ),
    }

    write_json(
        RELEASE / "provenance_manifest.json",
        provenance,
    )

    governance = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "source_runs": 500,
        "strict_positive_runs": 280,
        "excluded_runs": 220,
        "source_samples": 660,
        "strict_positive_samples": 660,
        "hard_negative": 0,
        "quarantine": 0,
        "published_family_counts": EXPECTED_FAMILIES,
        "strict_positive_rule": {
            "quality.training_role": "POSITIVE",
            "quality.valid_for_training": True,
            "quality.rgb_exists": True,
            "closed_loop_quality.run_status":
                "SUCCEEDED",
            "closed_loop_quality.scenario_acceptance_passed":
                True,
            "closed_loop_quality.command_terminal_status":
                "SUCCEEDED",
            "closed_loop_quality.plan_terminal_state":
                "SUCCEEDED",
            "closed_loop_quality.collision_count": 0,
        },
        "historical_failure_policy": (
            "The 220 non-positive runs from the frozen "
            "500-run acquisition are excluded. They may only "
            "be recollected under a new recovery cohort after "
            "root-cause fixes; this release does not relabel "
            "their historical evidence."
        ),
    }

    write_json(
        RELEASE / "governance_report.json",
        governance,
    )

    cumulative = {
        "schema_version": "1.0",
        "view_id": (
            "b1_d2_v1_1_plus_d3_wave1_plus_"
            "d3_wave2_plus_d3_targeted_gap_strict_v1"
        ),
        "base_release": {
            "path":
                "challenge/dataset/releases/d2_v1_1",
            "immutable": True,
        },
        "prior_addon_releases": [
            {
                "path": (
                    "challenge/dataset/releases/"
                    "d3_wave1_addon_v1"
                ),
                "immutable": True,
            },
            {
                "path": (
                    "challenge/dataset/releases/"
                    "d3_wave2_safe_short_v1"
                ),
                "immutable": True,
            },
        ],
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
            (
                "challenge/dataset/releases/"
                "d3_wave2_safe_short_v1/"
                "train_addition.jsonl"
            ),
            str(RELEASE_REL / "train_addition.jsonl"),
        ],
        "a3_dev_inputs": [
            "challenge/dataset/releases/d2_v1_1/val.jsonl",
            (
                "challenge/dataset/releases/"
                "d3_wave1_addon_v1/val_addition.jsonl"
            ),
            (
                "challenge/dataset/releases/"
                "d3_wave2_safe_short_v1/"
                "val_addition.jsonl"
            ),
            str(RELEASE_REL / "val_addition.jsonl"),
        ],
        "hard_negative_pool": None,
        "reserved_test_policy": {
            "d2_v1_1_reserved_test_candidates":
                "not used for A3 tuning",
            "d3_targeted_gap_strict_new_test": False,
        },
        "generalization_note": (
            "This is an additive training/development cohort "
            "containing only contract-aware strict-positive "
            "targeted coverage-gap samples."
        ),
    }

    write_json(
        RELEASE / "cumulative_view_manifest.json",
        cumulative,
    )

    readme = f"""# B1 D3 Targeted Gap Strict Additive Release

Dataset version: `{DATASET_VERSION}`.

This release contains **660 strict-positive command-level samples**
derived from **280 strict-positive closed-loop runs** selected from
the frozen 500-run targeted coverage-gap acquisition.

Published sample families:

- TC_E01: 120
- TC_F01: 450
- ACC_C04: 20
- SUP_C07: 20
- TC_G01: 50

Source acquisition:

- total terminal runs: 500
- strict-positive runs: 280
- excluded/non-positive runs: 220
- canonical rejected samples: 0

All 660 source RGB assets were integrity checked before publication.
Train/validation splitting is group-aware so samples from one
closed-loop run remain in one split.

The 220 excluded historical runs remain immutable. They are not
relabeled after later fixes; any recovery must use a new cohort.

This is an additive training/development release and does not replace
D2 v1.1, D3 Wave1, or D3 Wave2.
"""

    (RELEASE / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    canonical_lines: list[str] = []

    for sample_id, item in sorted(rgb_mapping.items()):
        image_path = REPO / item["release_rgb_ref"]
        canonical_lines.append(
            f"{image_path.name}\t{item['sha256']}\n"
        )

    release_image_set_sha = hashlib.sha256(
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
            "source_runs": 500,
            "strict_positive_runs": 280,
            "train_addition": len(train),
            "val_addition": len(val),
            "strict_positive_samples": EXPECTED_ROWS,
            "hard_negative_addition": 0,
            "quarantine": 0,
            "images": EXPECTED_ROWS,
        },
        "files": {
            name: manifest_entry(RELEASE / name)
            for name in core_files
        },
        "image_set": {
            "count": EXPECTED_ROWS,
            "canonical_sha256":
                release_image_set_sha,
        },
    }

    write_json(
        RELEASE / "release_manifest.json",
        release_manifest,
    )

    release_sha = canonical_text_sha256(
        RELEASE / "release_manifest.json"
    )

    integrity = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "status": "PASS",
        "release_manifest_sha256": release_sha,
        "checks": {
            "source_rows": EXPECTED_ROWS,
            "strict_positive_rows": EXPECTED_ROWS,
            "unique_sample_ids": EXPECTED_ROWS,
            "source_runs": EXPECTED_RUNS,
            "source_groups": EXPECTED_RUNS,
            "copied_images": EXPECTED_ROWS,
            "train_val_group_overlap": 0,
            "hard_negative_rows": 0,
            "rejected_canonical_rows": 0,
        },
    }

    write_json(
        RELEASE / "b1_release_integrity_report.json",
        integrity,
    )

    signed_pass = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "status": "PASS",
        "release_manifest_sha256": release_sha,
        "strict_positive_samples": EXPECTED_ROWS,
        "strict_positive_runs": EXPECTED_RUNS,
    }

    write_json(
        RELEASE / "B1_SIGNED_PASS.json",
        signed_pass,
    )

    lock_files = sorted(
        p
        for p in RELEASE.rglob("*")
        if p.is_file()
        and p.name != "b1_release_lock.sha256"
    )

    lock_lines = [
        f"{raw_sha256(p)}  {p.relative_to(RELEASE)}\n"
        for p in lock_files
    ]

    (
        RELEASE / "b1_release_lock.sha256"
    ).write_text(
        "".join(lock_lines),
        encoding="utf-8",
    )

    print("RELEASE =", RELEASE)
    print("SOURCE_ROWS =", len(rows))
    print("STRICT_RUNS =", len(run_ids))
    print("TRAIN =", len(train))
    print("VAL =", len(val))
    print("TRAIN_GROUPS =", len(train_groups))
    print("VAL_GROUPS =", len(val_groups))
    print("IMAGES =", len(rgb_mapping))
    print("SOURCE_IMAGE_SET_SHA256 =", source_image_sha)
    print(
        "RELEASE_IMAGE_SET_SHA256 =",
        release_image_set_sha,
    )
    print("RELEASE_MANIFEST_SHA256 =", release_sha)
    print("BUILD_RELEASE_PASS = True")


if __name__ == "__main__":
    main()
