from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DATASET_VERSION = "b1_ms34_supplement_v1"

MAT = ROOT / "artifacts/b1_ms34_materialized_v1"

TRAIN_SRC = MAT / "train_candidates.jsonl"
VAL_SRC = MAT / "val_candidates.jsonl"
HARD_SRC = MAT / "excluded_accidentally_accepted.jsonl"

RELEASE_REL = Path(
    "challenge/dataset/releases/b1_ms34_supplement_v1"
)
RELEASE = ROOT / RELEASE_REL
IMAGES = RELEASE / "images"

EXPECTED_TRAIN = 30
EXPECTED_VAL = 4
EXPECTED_HARD = 1
EXPECTED_TOTAL = 35

EXPECTED_TRAIN_GROUPS = 2
EXPECTED_VAL_GROUPS = 4

EXPECTED3 = [
    "AVOID_OBSTACLE",
    "RETURN_TO_LANE",
    "KEEP_LANE",
]

EXPECTED4 = [
    "YIELD",
    "AVOID_OBSTACLE",
    "RETURN_TO_LANE",
    "KEEP_LANE",
]


def canonical_json(obj: Any) -> str:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"missing source: {path}")

    rows = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            raise RuntimeError(
                f"{path}:{line_no}: invalid JSON: {exc}"
            ) from exc
    return rows


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
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(canonical_json(row) + "\n")


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def group_record(
    key: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    first = rows[0]
    md = first["metadata"]

    return {
        "group_id": key,
        "map": md.get("map"),
        "route_hash": md.get("route_hash"),
        "sample_count": len(rows),
        "scenario_family": md.get("scenario_family"),
        "scenario_id": md.get("scenario_id"),
        "seed": md.get("seed"),
    }


def validate_positive(
    row: dict[str, Any],
    where: str,
) -> None:
    sid = str(row.get("sample_id") or "")
    q = row.get("quality") or {}
    c = row.get("closed_loop_quality") or {}
    plan = row.get("teacher_plan") or {}
    req = row.get("model_request") or {}

    if not sid:
        raise RuntimeError(f"{where}: missing sample_id")

    if row.get("dataset_version") != DATASET_VERSION:
        raise RuntimeError(
            f"{where}:{sid}: dataset_version mismatch"
        )

    if q.get("training_role") != "POSITIVE":
        raise RuntimeError(
            f"{where}:{sid}: not POSITIVE"
        )

    if q.get("valid_for_training") is not True:
        raise RuntimeError(
            f"{where}:{sid}: invalid for training"
        )

    if q.get("training_exclusion_reasons") not in ([], None):
        raise RuntimeError(
            f"{where}:{sid}: exclusion reasons present"
        )

    for key in (
        "request_id_match",
        "command_id_match",
        "rgb_exists",
        "structurally_valid",
    ):
        if q.get(key) is not True:
            raise RuntimeError(
                f"{where}:{sid}: quality.{key} != true"
            )

    if c.get("run_status") != "SUCCEEDED":
        raise RuntimeError(
            f"{where}:{sid}: run_status != SUCCEEDED"
        )

    if c.get("scenario_acceptance_passed") is not True:
        raise RuntimeError(
            f"{where}:{sid}: scenario acceptance failed"
        )

    if c.get("command_terminal_status") != "SUCCEEDED":
        raise RuntimeError(
            f"{where}:{sid}: command terminal failed"
        )

    if c.get("plan_terminal_state") != "SUCCEEDED":
        raise RuntimeError(
            f"{where}:{sid}: plan terminal failed"
        )

    if int(c.get("collision_count") or 0) != 0:
        raise RuntimeError(
            f"{where}:{sid}: collision"
        )

    if int(c.get("route_deviation_count") or 0) != 0:
        raise RuntimeError(
            f"{where}:{sid}: route deviation"
        )

    if plan.get("schema_version") != "2.0":
        raise RuntimeError(
            f"{where}:{sid}: bad Teacher schema"
        )

    if plan.get("plan_type") != "MANEUVER_SEQUENCE":
        raise RuntimeError(
            f"{where}:{sid}: bad plan_type"
        )

    if req.get("request_id") != plan.get("request_id"):
        raise RuntimeError(
            f"{where}:{sid}: request_id mismatch"
        )

    if req.get("command_id") != plan.get("command_id"):
        raise RuntimeError(
            f"{where}:{sid}: command_id mismatch"
        )

    behaviors = [
        x.get("behavior")
        for x in plan.get("steps") or []
    ]

    if behaviors not in (EXPECTED3, EXPECTED4):
        raise RuntimeError(
            f"{where}:{sid}: unexpected plan {behaviors}"
        )


def validate_hard(row: dict[str, Any]) -> None:
    sid = str(row.get("sample_id") or "")
    md = row.get("metadata") or {}
    q = row.get("quality") or {}
    c = row.get("closed_loop_quality") or {}

    if md.get("seed") != 253002:
        raise RuntimeError(
            f"{sid}: hard-negative seed != 253002"
        )

    if q.get("training_role") != "HARD_NEGATIVE":
        raise RuntimeError(
            f"{sid}: expected HARD_NEGATIVE"
        )

    if q.get("valid_for_training") is not False:
        raise RuntimeError(
            f"{sid}: hard negative unexpectedly trainable"
        )

    reasons = q.get("training_exclusion_reasons") or []
    if "CLOSED_LOOP_ROUTE_DEVIATION" not in reasons:
        raise RuntimeError(
            f"{sid}: route-deviation exclusion missing"
        )

    if c.get("scenario_acceptance_passed") is not False:
        raise RuntimeError(
            f"{sid}: scenario acceptance unexpectedly passed"
        )

    if c.get("run_status") != "FAILED":
        raise RuntimeError(
            f"{sid}: hard-negative run_status != FAILED"
        )

    if int(c.get("route_deviation_count") or 0) < 1:
        raise RuntimeError(
            f"{sid}: route_deviation_count < 1"
        )


def source_dataset_sha(
    rows: list[dict[str, Any]],
) -> str:
    payload = "\n".join(
        canonical_json(x)
        for x in sorted(
            rows,
            key=lambda r: str(r.get("sample_id") or ""),
        )
    ) + "\n"

    return sha256_bytes(payload.encode("utf-8"))


def materialize_images(
    rows: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    rewritten = []
    mapping: dict[str, dict[str, Any]] = {}

    for original in rows:
        row = json.loads(json.dumps(original))

        sid = str(row["sample_id"])
        visual = row.get("visual_input") or {}
        request = row.get("model_request") or {}

        source_ref = visual.get("rgb_ref")

        if not isinstance(source_ref, str) or not source_ref:
            raise RuntimeError(
                f"{sid}: missing source rgb_ref"
            )

        if request.get("rgb_ref") != source_ref:
            raise RuntimeError(
                f"{sid}: ModelRequest/visual rgb_ref differ"
            )

        src = ROOT / source_ref

        if not src.is_file():
            raise RuntimeError(
                f"{sid}: source image missing: {src}"
            )

        source_sha = sha256_file(src)
        source_size = src.stat().st_size

        if source_sha != visual.get("rgb_sha256"):
            raise RuntimeError(
                f"{sid}: source RGB SHA mismatch"
            )

        if source_size != visual.get("size_bytes"):
            raise RuntimeError(
                f"{sid}: source RGB size mismatch"
            )

        suffix = src.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            raise RuntimeError(
                f"{sid}: unsupported image suffix {suffix}"
            )

        dst_name = f"{sid}{suffix}"
        dst = IMAGES / dst_name
        shutil.copy2(src, dst)

        if sha256_file(dst) != source_sha:
            raise RuntimeError(
                f"{sid}: copied RGB SHA mismatch"
            )

        release_ref = str(
            RELEASE_REL / "images" / dst_name
        )

        request["rgb_ref"] = release_ref
        visual["rgb_ref"] = release_ref
        visual["resolved_path"] = release_ref

        row["model_request"] = request
        row["visual_input"] = visual

        mapping[sid] = {
            "release_rgb_ref": release_ref,
            "sha256": source_sha,
            "size_bytes": source_size,
            "source_rgb_ref": source_ref,
        }

        rewritten.append(row)

    return rewritten, mapping


def main() -> None:
    train = load_jsonl(TRAIN_SRC)
    val = load_jsonl(VAL_SRC)
    hard = load_jsonl(HARD_SRC)

    if len(train) != EXPECTED_TRAIN:
        raise SystemExit(
            f"train count {len(train)} != {EXPECTED_TRAIN}"
        )

    if len(val) != EXPECTED_VAL:
        raise SystemExit(
            f"val count {len(val)} != {EXPECTED_VAL}"
        )

    if len(hard) != EXPECTED_HARD:
        raise SystemExit(
            f"hard count {len(hard)} != {EXPECTED_HARD}"
        )

    for row in train:
        validate_positive(row, "train")

    for row in val:
        validate_positive(row, "val")

    validate_hard(hard[0])

    positive = train + val
    all_rows = positive + hard

    sample_ids = [
        str(x.get("sample_id") or "")
        for x in all_rows
    ]

    if len(sample_ids) != len(set(sample_ids)):
        raise SystemExit("duplicate sample_id")

    positive_run_ids = [
        str((x.get("metadata") or {}).get("run_id") or "")
        for x in positive
    ]

    if len(set(positive_run_ids)) != 34:
        raise SystemExit(
            "expected 34 unique positive run_ids"
        )

    train_groups_raw: dict[
        str, list[dict[str, Any]]
    ] = defaultdict(list)

    val_groups_raw: dict[
        str, list[dict[str, Any]]
    ] = defaultdict(list)

    hard_groups_raw: dict[
        str, list[dict[str, Any]]
    ] = defaultdict(list)

    for row in train:
        train_groups_raw[
            str(row["metadata"]["group_key"])
        ].append(row)

    for row in val:
        val_groups_raw[
            str(row["metadata"]["group_key"])
        ].append(row)

    for row in hard:
        hard_groups_raw[
            str(row["metadata"]["group_key"])
        ].append(row)

    train_group_keys = set(train_groups_raw)
    val_group_keys = set(val_groups_raw)
    hard_group_keys = set(hard_groups_raw)

    if len(train_group_keys) != EXPECTED_TRAIN_GROUPS:
        raise SystemExit(
            f"train groups {len(train_group_keys)} != 2"
        )

    if len(val_group_keys) != EXPECTED_VAL_GROUPS:
        raise SystemExit(
            f"val groups {len(val_group_keys)} != 4"
        )

    if train_group_keys & val_group_keys:
        raise SystemExit("train/val group leakage")

    if (
        hard_group_keys
        & (train_group_keys | val_group_keys)
    ):
        raise SystemExit(
            "hard-negative group overlaps positive supervision"
        )

    train_steps = Counter(
        len((x.get("teacher_plan") or {}).get("steps") or [])
        for x in train
    )

    val_steps = Counter(
        len((x.get("teacher_plan") or {}).get("steps") or [])
        for x in val
    )

    if train_steps != Counter({3: 15, 4: 15}):
        raise SystemExit(
            f"bad train plan counts: {dict(train_steps)}"
        )

    if val_steps != Counter({3: 2, 4: 2}):
        raise SystemExit(
            f"bad val plan counts: {dict(val_steps)}"
        )

    source_sha = source_dataset_sha(all_rows)

    collector = ROOT / "challenge/dataset/collector.py"
    collector_sha = sha256_file(collector)

    collector_commit = git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        "challenge/dataset/collector.py",
    )

    teacher_git_shas = {
        str(
            (x.get("metadata") or {}).get(
                "teacher_git_sha"
            )
            or ""
        )
        for x in all_rows
    }

    teacher_model_ids = {
        str(
            (x.get("metadata") or {}).get(
                "teacher_model_id"
            )
            or ""
        )
        for x in all_rows
    }

    teacher_modes = {
        str(
            (x.get("metadata") or {}).get(
                "teacher_mode"
            )
            or ""
        )
        for x in all_rows
    }

    if "" in teacher_git_shas or len(teacher_git_shas) != 1:
        raise SystemExit(
            f"teacher_git_sha mismatch: {teacher_git_shas}"
        )

    if "" in teacher_model_ids or len(teacher_model_ids) != 1:
        raise SystemExit(
            f"teacher_model_id mismatch: {teacher_model_ids}"
        )

    if "" in teacher_modes or len(teacher_modes) != 1:
        raise SystemExit(
            f"teacher_mode mismatch: {teacher_modes}"
        )

    teacher_git_sha = next(iter(teacher_git_shas))
    teacher_model_id = next(iter(teacher_model_ids))
    teacher_mode = next(iter(teacher_modes))

    # Source artifacts remain under artifacts/. Only the temporary
    # release copy is removed.
    if RELEASE.exists():
        shutil.rmtree(RELEASE)

    IMAGES.mkdir(parents=True)

    train_out, train_map = materialize_images(train)
    val_out, val_map = materialize_images(val)
    hard_out, hard_map = materialize_images(hard)

    rgb_mapping = {
        **train_map,
        **val_map,
        **hard_map,
    }

    if len(rgb_mapping) != EXPECTED_TOTAL:
        raise SystemExit(
            f"RGB mapping {len(rgb_mapping)} != 35"
        )

    write_jsonl(
        RELEASE / "train_addition.jsonl",
        train_out,
    )
    write_jsonl(
        RELEASE / "val_addition.jsonl",
        val_out,
    )
    write_jsonl(
        RELEASE / "hard_negative_addition.jsonl",
        hard_out,
    )

    write_json(
        RELEASE / "rgb_mapping.json",
        rgb_mapping,
    )

    train_group_records = [
        group_record(key, train_groups_raw[key])
        for key in sorted(train_groups_raw)
    ]

    val_group_records = [
        group_record(key, val_groups_raw[key])
        for key in sorted(val_groups_raw)
    ]

    hard_group_records = [
        group_record(key, hard_groups_raw[key])
        for key in sorted(hard_groups_raw)
    ]

    split_manifest = {
        "counts": {
            "group_overlap": 0,
            "groups": 6,
            "hard_negative_groups": 1,
            "hard_negative_samples": 1,
            "total_positive": 34,
            "train_addition": 30,
            "train_groups": 2,
            "val_addition": 4,
            "val_groups": 4,
        },
        "dataset_version": DATASET_VERSION,
        "groups": {
            "hard_negative_addition": hard_group_records,
            "train_addition": train_group_records,
            "val_addition": val_group_records,
        },
        "schema_version": "1.0",
        "split_policy": {
            "group_fields": [
                "metadata.scenario_family",
                "metadata.map",
                "metadata.route_hash",
                "metadata.seed",
            ],
            "selection": {
                "train": (
                    "The original 30-run targeted acquisition: "
                    "15 repeated 3-step runs at seed 253000 and "
                    "15 repeated 4-step runs at seed 253001."
                ),
                "validation": (
                    "Four separately acquired successful holdout "
                    "groups: 3-step seeds 253003/253006 and "
                    "4-step seeds 253004/253005."
                ),
                "hard_negative": (
                    "3-step seed 253002; excluded from positive "
                    "supervision due to closed-loop route deviation."
                ),
            },
            "type": "group_aware_fixed_holdout",
        },
    }

    write_json(
        RELEASE / "split_manifest.json",
        split_manifest,
    )

    scenario_counts = Counter(
        str(
            (x.get("metadata") or {}).get("scenario_id")
            or "UNKNOWN"
        )
        for x in positive
    )

    provenance = {
        "acquisition": {
            "source_runs": 35,
            "strict_positive_runs": 34,
            "hard_negative_runs": 1,
            "main_targeted_runs": 30,
            "validation_holdout_runs": 4,
            "failed_holdout_runs_retained_as_hard_negative": 1,
            "teacher_git_sha": teacher_git_sha,
        },
        "base_release": "d3_gap300_strict_v1",
        "canonicalization": {
            "canonical_samples": 35,
            "collector_last_change_commit": collector_commit,
            "collector_sha256": collector_sha,
            "hard_negative_samples": 1,
            "source_dataset_sha256": source_sha,
            "strict_positive_samples": 34,
        },
        "dataset_version": DATASET_VERSION,
        "families": dict(sorted(scenario_counts.items())),
        "raw_source_immutable": True,
        "release_type": "additive_targeted_supplement",
        "schema_version": "1.0",
        "selection_policy": (
            "Publish 34 strict-positive single-call multi-step "
            "Teacher samples. The seed-253002 run is retained only "
            "as HARD_NEGATIVE evidence because closed-loop route "
            "deviation caused scenario acceptance failure."
        ),
        "teacher": {
            "git_sha": teacher_git_sha,
            "mode": teacher_mode,
            "model_id": teacher_model_id,
        },
    }

    write_json(
        RELEASE / "provenance_manifest.json",
        provenance,
    )

    governance = {
        "dataset_version": DATASET_VERSION,
        "family_counts": dict(sorted(scenario_counts.items())),
        "gates": {
            "canonical_sample_ids_unique": True,
            "group_split_leakage_zero": True,
            "hard_negative_excluded_from_positive_supervision": True,
            "hard_negative_route_deviation_evidence": True,
            "positive_closed_loop_strict_pass": True,
            "positive_plan_sequences_exact": True,
            "rgb_integrity": True,
            "sample_overlap_zero": True,
        },
        "hard_negative_samples": 1,
        "immutability": {
            "prior_releases_modified": False,
            "raw_acquisition": True,
            "release_immutable_after_publish": True,
        },
        "schema_version": "1.0",
        "source_runs": 35,
        "status": "PASS",
        "strict_positive_runs": 34,
        "strict_positive_samples": 34,
        "train_positive_samples": 30,
        "val_positive_samples": 4,
    }

    write_json(
        RELEASE / "governance_report.json",
        governance,
    )

    binding_payload = {
        "canonical_samples": 35,
        "canonical_source_sha256": source_sha,
        "collector_commit": collector_commit,
        "collector_sha256": collector_sha,
        "dataset_version": DATASET_VERSION,
        "hard_negative_samples": 1,
        "strict_positive_runs": 34,
        "strict_positive_samples": 34,
        "teacher_git_sha": teacher_git_sha,
        "teacher_model_id": teacher_model_id,
    }

    content_bound = {
        "binding": {
            "algorithm": "SHA256",
            "payload": binding_payload,
            "sha256": sha256_bytes(
                canonical_json(binding_payload).encode("utf-8")
            ),
        },
        "dataset_version": DATASET_VERSION,
        "schema_version": "1.0",
        "signature_status": "CONTENT_BOUND_UNSIGNED",
        "status": "PASS",
    }

    write_json(
        RELEASE / "B1_CONTENT_BOUND_PASS.json",
        content_bound,
    )

    readme = f"""# B1 MS34 Targeted Supplemental Release

Dataset version: `{DATASET_VERSION}`

This additive release contains **34 strict-positive single-call
multi-step Teacher samples** and **1 hard-negative closed-loop
route-deviation sample** derived from 35 CARLA runs.

Positive supervision:

- 3-step AVOID_OBSTACLE -> RETURN_TO_LANE -> KEEP_LANE:
  17 samples
- 4-step YIELD -> AVOID_OBSTACLE -> RETURN_TO_LANE -> KEEP_LANE:
  17 samples

Split:

- train: 30 positive samples / 2 groups
- validation: 4 positive samples / 4 groups
- hard negative: 1 sample / 1 group
- train/validation group overlap: 0

The original 30-run targeted acquisition consists of two fixed
scenario/seed groups repeated 15 times each. Four additional
successful groups were acquired specifically as validation holdout.

Seed 253002 is not positive supervision. It is published only in
`hard_negative_addition.jsonl` because closed-loop route deviation
caused scenario acceptance failure.

Teacher:

- model: `{teacher_model_id}`
- mode: `{teacher_mode}`
- acquisition Git SHA: `{teacher_git_sha}`

Canonicalization:

- collector commit: `{collector_commit}`
- collector SHA256: `{collector_sha}`
- canonical source SHA256: `{source_sha}`

This release is additive and does not mutate any previously frozen
release.
"""

    (RELEASE / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    locked_names = [
        "B1_CONTENT_BOUND_PASS.json",
        "README.md",
        "governance_report.json",
        "hard_negative_addition.jsonl",
        "provenance_manifest.json",
        "rgb_mapping.json",
        "split_manifest.json",
        "train_addition.jsonl",
        "val_addition.jsonl",
    ]

    files = {}

    for name in locked_names:
        p = RELEASE / name
        files[name] = {
            "sha256": sha256_file(p),
            "size_bytes": p.stat().st_size,
        }

    image_entries = {}

    for p in sorted(IMAGES.iterdir()):
        if not p.is_file():
            continue
        image_entries[p.name] = sha256_file(p)

    release_manifest = {
        "counts": {
            "hard_negative_addition": 1,
            "images": len(image_entries),
            "source_runs": 35,
            "strict_positive_runs": 34,
            "strict_positive_samples": 34,
            "train_addition": 30,
            "val_addition": 4,
        },
        "dataset_version": DATASET_VERSION,
        "files": files,
        "image_set": {
            "count": len(image_entries),
            "entries": image_entries,
        },
        "release_type": "additive_targeted_supplement",
        "schema_version": "1.0",
        "status": "B1_RELEASE_CANDIDATE",
    }

    write_json(
        RELEASE / "release_manifest.json",
        release_manifest,
    )

    # Final self-audit after all writes.
    if len(list(IMAGES.iterdir())) != 35:
        raise SystemExit("final image count != 35")

    release_train = load_jsonl(
        RELEASE / "train_addition.jsonl"
    )
    release_val = load_jsonl(
        RELEASE / "val_addition.jsonl"
    )
    release_hard = load_jsonl(
        RELEASE / "hard_negative_addition.jsonl"
    )

    if (
        len(release_train),
        len(release_val),
        len(release_hard),
    ) != (30, 4, 1):
        raise SystemExit("final JSONL count mismatch")

    release_positive_ids = {
        x["sample_id"]
        for x in release_train + release_val
    }

    release_hard_ids = {
        x["sample_id"]
        for x in release_hard
    }

    if release_positive_ids & release_hard_ids:
        raise SystemExit(
            "positive/hard-negative sample overlap"
        )

    for row in release_train + release_val + release_hard:
        sid = row["sample_id"]
        ref = row["visual_input"]["rgb_ref"]

        if row["model_request"]["rgb_ref"] != ref:
            raise SystemExit(
                f"{sid}: release rgb_ref mismatch"
            )

        p = ROOT / ref
        if not p.is_file():
            raise SystemExit(
                f"{sid}: release RGB missing"
            )

        if sha256_file(p) != row["visual_input"]["rgb_sha256"]:
            raise SystemExit(
                f"{sid}: final RGB SHA mismatch"
            )

    print("===== B1 MS34 RELEASE BUILD =====")
    print("dataset_version      =", DATASET_VERSION)
    print("train positives      =", 30)
    print("val positives        =", 4)
    print("hard negatives       =", 1)
    print("canonical total      =", 35)
    print("train groups         =", 2)
    print("val groups           =", 4)
    print("group overlap        =", 0)
    print("images               =", len(image_entries))
    print("collector_commit     =", collector_commit)
    print("collector_sha256     =", collector_sha)
    print("source_sha256        =", source_sha)
    print("RELEASE_BUILD        = PASS")


if __name__ == "__main__":
    main()
