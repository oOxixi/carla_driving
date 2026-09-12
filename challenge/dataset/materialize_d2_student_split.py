#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from challenge.dataset import collect_d1_200 as base

MATERIALIZATION_VERSION = "b1_d2_student_split_v1"
EXPECTED_CANONICAL_POOL_SHA256 = "388af4f6392f7f12e78161a39363688317ee2d2817d0cc2d55a9f296c410c482"
EXPECTED_STUDENT_POOL_SHA256 = "bf610d441e15bd15b95aa23dbb9fabdb440839ac1674e6a164832020748a0a51"
EXPECTED_POOL_MANIFEST_SHA256 = "48a4d2454e96de386dbb5e7be103200517a67543ddf1c2581e5da4cf198a3c0b"
EXPECTED_DATASET_VERSION = "b1_d2_provisional_v1"
EXPECTED_TRAIN_COUNT = 182
EXPECTED_VAL_COUNT = 32
EXPECTED_TOTAL = 214
EXPECTED_STUDENT_CONTRACT = "student_v0_r3"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise RuntimeError(f"{path}:{line_no}: JSON object required")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--canonical-pool",
        default="artifacts/b1_d2_training_pool_v0/canonical_eligible.jsonl",
    )
    ap.add_argument(
        "--student-pool",
        default="artifacts/b1_d2_training_pool_v0/student_eligible.jsonl",
    )
    ap.add_argument(
        "--pool-manifest",
        default="artifacts/b1_d2_training_pool_v0/training_pool_manifest.json",
    )
    ap.add_argument(
        "--split-dir",
        default="artifacts/b1_d2_split_v1",
    )
    ap.add_argument(
        "--output-dir",
        default="artifacts/b1_d2_student_split_v1",
    )
    ap.add_argument(
        "--dataset-version",
        default=EXPECTED_DATASET_VERSION,
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-uncommitted-code", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]

    canonical_pool = (repo / args.canonical_pool).resolve()
    student_pool = (repo / args.student_pool).resolve()
    pool_manifest = (repo / args.pool_manifest).resolve()
    split_dir = (repo / args.split_dir).resolve()
    train_canonical = split_dir / "train.jsonl"
    val_canonical = split_dir / "val.jsonl"
    split_manifest = split_dir / "split_manifest.json"

    for path in (
        canonical_pool,
        student_pool,
        pool_manifest,
        train_canonical,
        val_canonical,
        split_manifest,
    ):
        if not path.is_file():
            raise RuntimeError(f"required input missing: {path}")

    if sha256_file(canonical_pool) != EXPECTED_CANONICAL_POOL_SHA256:
        raise RuntimeError("canonical training-pool SHA mismatch")
    if sha256_file(student_pool) != EXPECTED_STUDENT_POOL_SHA256:
        raise RuntimeError("student training-pool SHA mismatch")
    if sha256_file(pool_manifest) != EXPECTED_POOL_MANIFEST_SHA256:
        raise RuntimeError("training-pool manifest SHA mismatch")

    builder_rel = "challenge/dataset/materialize_d2_student_split.py"
    if args.allow_uncommitted_code:
        builder_identity = {
            "path": builder_rel,
            "sha256": sha256_file(repo / builder_rel),
            "matches_head": None,
            "development_override": True,
        }
        formal_code_gate = False
        print("FORMAL_CODE_GATE=BYPASSED_FOR_DEVELOPMENT")
    else:
        builder_identity = base.verify_tracked_file_matches_head(repo, builder_rel)
        formal_code_gate = True
        print("FORMAL_CODE_GATE=PASS")

    canonical_rows = read_jsonl(canonical_pool)
    student_rows = read_jsonl(student_pool)
    train_rows = read_jsonl(train_canonical)
    val_rows = read_jsonl(val_canonical)

    if len(canonical_rows) != EXPECTED_TOTAL:
        raise RuntimeError(f"canonical pool count != {EXPECTED_TOTAL}")
    if len(student_rows) != EXPECTED_TOTAL:
        raise RuntimeError(f"student pool count != {EXPECTED_TOTAL}")
    if len(train_rows) != EXPECTED_TRAIN_COUNT:
        raise RuntimeError(f"train count != {EXPECTED_TRAIN_COUNT}")
    if len(val_rows) != EXPECTED_VAL_COUNT:
        raise RuntimeError(f"val count != {EXPECTED_VAL_COUNT}")

    canonical_ids = [r.get("sample_id") for r in canonical_rows]
    student_ids = [r.get("sample_id") for r in student_rows]
    train_ids = [r.get("sample_id") for r in train_rows]
    val_ids = [r.get("sample_id") for r in val_rows]

    for name, ids, expected in (
        ("canonical", canonical_ids, EXPECTED_TOTAL),
        ("student", student_ids, EXPECTED_TOTAL),
        ("train", train_ids, EXPECTED_TRAIN_COUNT),
        ("val", val_ids, EXPECTED_VAL_COUNT),
    ):
        if any(not isinstance(x, str) or not x for x in ids):
            raise RuntimeError(f"{name} contains missing sample_id")
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{name} contains duplicate sample_id")
        if len(ids) != expected:
            raise RuntimeError(f"{name} count mismatch")

    canonical_id_set = set(canonical_ids)
    student_id_set = set(student_ids)
    train_id_set = set(train_ids)
    val_id_set = set(val_ids)

    if canonical_id_set != student_id_set:
        raise RuntimeError("canonical/student pool sample-id sets differ")
    if train_id_set & val_id_set:
        raise RuntimeError("train/val sample-id overlap")
    if train_id_set | val_id_set != canonical_id_set:
        raise RuntimeError("train/val membership does not partition the canonical pool")

    student_by_id = {r["sample_id"]: r for r in student_rows}

    split_manifest_obj = json.loads(split_manifest.read_text(encoding="utf-8"))
    if split_manifest_obj.get("source_sha256") != EXPECTED_CANONICAL_POOL_SHA256:
        raise RuntimeError("split manifest source SHA does not match canonical pool")
    if split_manifest_obj.get("strategy") != "stratified":
        raise RuntimeError("split manifest strategy is not stratified")
    leakage = split_manifest_obj.get("leakage_checks") or {}
    if leakage.get("passed") is not True:
        raise RuntimeError("split manifest leakage check did not pass")

    def materialize(ids_in_order: list[str], split: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for sid in ids_in_order:
            record = json.loads(json.dumps(student_by_id[sid]))
            policy = record.get("training_policy")
            if not isinstance(policy, dict) or policy.get("train_eligible") is not True:
                raise RuntimeError(f"non-eligible Student record: {sid}")
            meta = record.setdefault("metadata", {})
            if not isinstance(meta, dict):
                raise RuntimeError(f"metadata must be object: {sid}")
            if meta.get("student_contract") != EXPECTED_STUDENT_CONTRACT:
                raise RuntimeError(f"Student contract mismatch: {sid}")
            targets = (record.get("input") or {}).get("targets") or []
            if len(targets) > 8:
                raise RuntimeError(f"Student target overflow: {sid}")
            teacher = record.get("teacher")
            plan = teacher.get("maneuver_plan") if isinstance(teacher, dict) else None
            if not isinstance(plan, dict):
                raise RuntimeError(f"teacher.maneuver_plan missing: {sid}")
            meta["dataset_version"] = args.dataset_version
            meta["split"] = split
            record["dataset_version"] = args.dataset_version
            out.append(record)
        return out

    materialized_train = materialize(train_ids, "train")
    materialized_val = materialize(val_ids, "val")

    train_groups = {
        (r.get("metadata") or {}).get("group_key")
        for r in materialized_train
        if (r.get("metadata") or {}).get("group_key")
    }
    val_groups = {
        (r.get("metadata") or {}).get("group_key")
        for r in materialized_val
        if (r.get("metadata") or {}).get("group_key")
    }
    if train_groups & val_groups:
        raise RuntimeError("group_key leakage after materialization")

    train_classes = Counter(
        str((r.get("sample_class") or {}).get("primary") or "UNKNOWN")
        for r in materialized_train
    )
    val_classes = Counter(
        str((r.get("sample_class") or {}).get("primary") or "UNKNOWN")
        for r in materialized_val
    )

    print("MATERIALIZATION_VERSION=" + MATERIALIZATION_VERSION)
    print("REPO_HEAD=" + base.current_head(repo))
    print("BUILDER_SHA256=" + builder_identity["sha256"])
    print("TRAIN_STUDENT=" + str(len(materialized_train)))
    print("VAL_STUDENT=" + str(len(materialized_val)))
    print("SAMPLE_ID_OVERLAP=0")
    print("GROUP_KEY_OVERLAP=0")
    print("TRAIN_CLASSES=" + json.dumps(dict(train_classes), sort_keys=True))
    print("VAL_CLASSES=" + json.dumps(dict(val_classes), sort_keys=True))

    if args.dry_run:
        print("B1_D2_STUDENT_SPLIT_DRY_RUN=PASS")
        return 0

    out_dir = (repo / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    train_out = out_dir / "train.jsonl"
    val_out = out_dir / "val.jsonl"
    manifest_out = out_dir / "student_split_manifest.json"

    write_jsonl(train_out, materialized_train)
    write_jsonl(val_out, materialized_val)

    manifest = {
        "schema_version": "1.0",
        "materialization_version": MATERIALIZATION_VERSION,
        "dataset_version": args.dataset_version,
        "status": "D2_PROVISIONAL_TRAIN_VAL_FROZEN",
        "repo_git_sha": base.current_head(repo),
        "branch": base.current_branch(repo),
        "formal_code_gate": formal_code_gate,
        "builder_identity": builder_identity,
        "source": {
            "canonical_pool_path": str(canonical_pool.relative_to(repo)),
            "canonical_pool_sha256": sha256_file(canonical_pool),
            "student_pool_path": str(student_pool.relative_to(repo)),
            "student_pool_sha256": sha256_file(student_pool),
            "training_pool_manifest_path": str(pool_manifest.relative_to(repo)),
            "training_pool_manifest_sha256": sha256_file(pool_manifest),
            "canonical_train_path": str(train_canonical.relative_to(repo)),
            "canonical_train_sha256": sha256_file(train_canonical),
            "canonical_val_path": str(val_canonical.relative_to(repo)),
            "canonical_val_sha256": sha256_file(val_canonical),
            "split_manifest_path": str(split_manifest.relative_to(repo)),
            "split_manifest_sha256": sha256_file(split_manifest),
        },
        "counts": {
            "train": len(materialized_train),
            "val": len(materialized_val),
            "total": len(materialized_train) + len(materialized_val),
            "train_groups": len(train_groups),
            "val_groups": len(val_groups),
        },
        "student_contract": {
            "name": EXPECTED_STUDENT_CONTRACT,
            "max_targets": 8,
            "no_target_index": 8,
        },
        "classes": {
            "train": dict(train_classes),
            "val": dict(val_classes),
        },
        "leakage_checks": {
            "sample_id_overlap": 0,
            "group_key_overlap": 0,
            "passed": True,
        },
        "artifacts_sha256": {
            "train.jsonl": sha256_file(train_out),
            "val.jsonl": sha256_file(val_out),
        },
    }
    write_json(manifest_out, manifest)

    print("TRAIN_SHA256=" + sha256_file(train_out))
    print("VAL_SHA256=" + sha256_file(val_out))
    print("MANIFEST_SHA256=" + sha256_file(manifest_out))
    print("B1_D2_STUDENT_SPLIT_BUILD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
