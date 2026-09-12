#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from challenge.dataset import collect_d1_200 as base

DELIVERY_VERSION = "b1_d1_delivery_v0"
EXPECTED_TEACHER_MODEL_ID = "Qwen/Qwen3.5-2B"
EXPECTED_TEACHER_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
EXPECTED_TEACHER_ARTIFACT = "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
EXPECTED_TEACHER_BASELINE_SHA = "a05c8b76efcd4c176965223c661f40b153cb1836"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def get_meta(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("metadata")
    return value if isinstance(value, dict) else {}


def validate_teacher_identity(rows: list[dict[str, Any]]) -> dict[str, str]:
    expected = {
        "teacher_model_id": EXPECTED_TEACHER_MODEL_ID,
        "teacher_model_revision": EXPECTED_TEACHER_REVISION,
        "teacher_model_artifact_sha256": EXPECTED_TEACHER_ARTIFACT,
        "teacher_baseline_git_sha": EXPECTED_TEACHER_BASELINE_SHA,
    }
    for key, wanted in expected.items():
        values = {get_meta(r).get(key) for r in rows}
        if values != {wanted}:
            raise RuntimeError(f"{key} mismatch: {values!r}")
    return expected


def audit_groups(base_rows, ext_rows):
    base_groups = {
        get_meta(r).get("group_key")
        for r in base_rows
        if get_meta(r).get("group_key")
    }
    owners = defaultdict(set)
    for r in ext_rows:
        meta = get_meta(r)
        g = meta.get("group_key")
        eid = meta.get("extension_id")
        if not g or not eid:
            raise RuntimeError("extension sample missing group_key/extension_id")
        owners[str(g)].add(str(eid))
    overlap = base_groups & set(owners)
    if overlap:
        raise RuntimeError(f"base/extension overlap: {sorted(overlap)}")
    bad = {g: sorted(v) for g, v in owners.items() if len(v) != 1}
    if bad:
        raise RuntimeError(f"multi-owner extension groups: {bad}")
    counts = Counter(
        str(get_meta(r).get("group_key"))
        for r in (base_rows + ext_rows)
        if get_meta(r).get("group_key")
    )
    return {
        "group_count": len(counts),
        "multi_sample_groups": sum(v > 1 for v in counts.values()),
        "max_samples_per_group": max(counts.values()),
        "base_extension_overlap_count": 0,
        "extension_multi_owner_group_count": 0,
    }


def schema_markdown() -> str:
    return """# B1 D1 Dataset Schema

This delivery freezes the B1 D1 Teacher-distillation sample set.

Each canonical JSONL record contains the full ModelRequest V1, pinned Teacher
ManeuverPlan V2, closed-loop evidence, actual visual-input reference, sample
class, and provenance metadata. The canonical dataset preserves the complete
ModelRequest target list.

Important metadata include scenario_id, scenario_family, map, route_hash, seed,
group_key, source_bucket, policy_class, teacher_model_id,
teacher_model_revision, teacher_model_artifact_sha256,
teacher_baseline_git_sha, collection_repo_git_sha, and teacher_profile.

Extension records additionally contain extension_id, extension_type,
parent_scenario_id, parent_scenario_path, base_seed, extension_seed,
extension_plan_canonical_sha256, and extension_config_id.

`group_key` is the split unit. Multiple command-level samples may share one
group_key; all samples in a group must stay in the same split.

`dataset_student_228.jsonl` is the Student-compatible view. Student V0 limits:
maximum steps 4, maximum targets 8, no-target index 8.

`quarantine.jsonl` is excluded from training.
"""


def quality_markdown(counts, group_audit, source_counts, class_counts,
                     quarantine_counts, collection_sha_counts, failures) -> str:
    return f"""# B1 D1 Dataset Quality Report

## Counts

- Canonical: {counts["canonical"]}
- Student eligible: {counts["student_eligible"]}
- Quarantine: {counts["quarantine"]}
- Groups: {group_audit["group_count"]}
- Multi-sample groups: {group_audit["multi_sample_groups"]}
- Max samples/group: {group_audit["max_samples_per_group"]}
- Base/extension group overlap: 0
- Extension multi-owner groups: 0

## Source buckets

```json
{json.dumps(dict(source_counts), ensure_ascii=False, indent=2, sort_keys=True)}
```

## Sample classes

```json
{json.dumps(dict(class_counts), ensure_ascii=False, indent=2, sort_keys=True)}
```

## Collection repository SHAs

```json
{json.dumps(dict(collection_sha_counts), ensure_ascii=False, indent=2, sort_keys=True)}
```

## Quarantine reasons

```json
{json.dumps(dict(quarantine_counts), ensure_ascii=False, indent=2, sort_keys=True)}
```

## Process failures

```json
{json.dumps(failures, ensure_ascii=False, indent=2)}
```

All canonical sample IDs are unique. Canonical and Student-eligible sample-id
sets are identical. Teacher identity is uniform and pinned. Reserved UNSEEN
test candidates are excluded.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-canonical", default="artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl")
    ap.add_argument("--base-student", default="artifacts/b1_d1_pinned_formal/dataset/d1_student_eligible.jsonl")
    ap.add_argument("--base-provenance", default="artifacts/b1_d1_pinned_formal/provenance_manifest.json")
    ap.add_argument("--extension-canonical", default="artifacts/b1_d1_extension_final/dataset/extension_valid.jsonl")
    ap.add_argument("--extension-student", default="artifacts/b1_d1_extension_final/dataset/extension_student_eligible.jsonl")
    ap.add_argument("--extension-quarantine", default="artifacts/b1_d1_extension_final/dataset/extension_quarantine.jsonl")
    ap.add_argument("--extension-finalization-summary", default="artifacts/b1_d1_extension_final/finalization_summary.json")
    ap.add_argument("--extension-finalization-provenance", default="artifacts/b1_d1_extension_final/finalization_provenance.json")
    ap.add_argument("--extension-run-state", default="artifacts/b1_d1_extension_formal/run_state.json")
    ap.add_argument("--output-dir", default="artifacts/b1_d1_delivery_v0")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-uncommitted-code", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    raw_paths = {
        "base_canonical": args.base_canonical,
        "base_student": args.base_student,
        "base_provenance": args.base_provenance,
        "extension_canonical": args.extension_canonical,
        "extension_student": args.extension_student,
        "extension_quarantine": args.extension_quarantine,
        "extension_finalization_summary": args.extension_finalization_summary,
        "extension_finalization_provenance": args.extension_finalization_provenance,
        "extension_run_state": args.extension_run_state,
    }
    paths = {k: (repo / v).resolve() for k, v in raw_paths.items()}
    for name, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"missing input: {name}={path}")

    rel = "challenge/dataset/build_d1_delivery.py"
    if args.allow_uncommitted_code:
        builder_identity = {
            "path": rel,
            "sha256": sha256_file(repo / rel),
            "matches_head": None,
            "development_override": True,
        }
        formal_code_gate = False
        print("FORMAL_CODE_GATE=BYPASSED_FOR_DEVELOPMENT")
    else:
        builder_identity = base.verify_tracked_file_matches_head(repo, rel)
        formal_code_gate = True
        print("FORMAL_CODE_GATE=PASS")

    base_canonical = base.read_jsonl(paths["base_canonical"])
    base_student = base.read_jsonl(paths["base_student"])
    ext_canonical = base.read_jsonl(paths["extension_canonical"])
    ext_student = base.read_jsonl(paths["extension_student"])
    quarantine = base.read_jsonl(paths["extension_quarantine"])

    canonical = base_canonical + ext_canonical
    student = base_student + ext_student

    if len(canonical) != 228 or len(student) != 228:
        raise RuntimeError(f"expected 228/228, got {len(canonical)}/{len(student)}")

    canonical_ids = [r.get("sample_id") for r in canonical]
    student_ids = [r.get("sample_id") for r in student]
    if None in canonical_ids or None in student_ids:
        raise RuntimeError("missing sample_id")
    if len(canonical_ids) != len(set(canonical_ids)):
        raise RuntimeError("duplicate canonical sample_id")
    if len(student_ids) != len(set(student_ids)):
        raise RuntimeError("duplicate student sample_id")
    if set(canonical_ids) != set(student_ids):
        raise RuntimeError("canonical/student sample-id sets differ")

    teacher_identity = validate_teacher_identity(canonical)
    group_audit = audit_groups(base_canonical, ext_canonical)

    source_counts = Counter(get_meta(r).get("source_bucket") for r in canonical)
    if set(source_counts) - {"SEEN", "VARIANT"}:
        raise RuntimeError(f"unexpected source buckets: {dict(source_counts)}")

    class_counts = Counter(
        (r.get("sample_class") or {}).get("primary")
        for r in canonical
    )
    collection_sha_counts = Counter(
        get_meta(r).get("collection_repo_git_sha")
        for r in canonical
    )
    quarantine_counts = Counter(r.get("reason") for r in quarantine)
    if set(quarantine_counts) - {"COMMAND_TERMINAL_NOT_SUCCEEDED"}:
        raise RuntimeError(f"unexpected quarantine reasons: {dict(quarantine_counts)}")

    final_summary = base.read_json(paths["extension_finalization_summary"])
    if final_summary.get("combined_valid") != 228:
        raise RuntimeError("combined_valid != 228")
    if final_summary.get("minimum_reached") is not True:
        raise RuntimeError("minimum_reached != true")
    if final_summary.get("target_reached") is not True:
        raise RuntimeError("target_reached != true")

    final_prov = base.read_json(paths["extension_finalization_provenance"])
    if final_prov.get("formal_code_gate") is not True:
        raise RuntimeError("finalization provenance is not formal")

    run_state = base.read_json(paths["extension_run_state"])
    failures = sorted(
        eid for eid, item in (run_state.get("runs") or {}).items()
        if isinstance(item, dict) and item.get("status") == "FAILED"
    )
    expected_failures = {
        "ROUTE_GEN_TOWN03_DESTINATION__seed_1000061",
        "DEV_S2_P3_PEDESTRIAN_OVERTAKE_TARGETED__seed_1000065",
        "DEV_S2_BICYCLE_FOLLOW_TARGETED__seed_1000066",
        "DEV_S2_SPECIFIC_EVENTS_COMPACT__seed_1000067",
    }
    if set(failures) != expected_failures:
        raise RuntimeError(f"process failure set changed: {failures}")

    input_hashes = {
        str(path.relative_to(repo)): sha256_file(path)
        for path in paths.values()
    }

    print("DELIVERY_VERSION=" + DELIVERY_VERSION)
    print("REPO_HEAD=" + base.current_head(repo))
    print("BUILDER_SHA256=" + builder_identity["sha256"])
    print("CANONICAL_COUNT=228")
    print("STUDENT_COUNT=228")
    print("QUARANTINE_COUNT=" + str(len(quarantine)))
    print("GROUP_COUNT=" + str(group_audit["group_count"]))
    print("PROCESS_FAILURE_COUNT=" + str(len(failures)))
    print("TEACHER_MODEL_ID=" + teacher_identity["teacher_model_id"])
    print("TEACHER_MODEL_REVISION=" + teacher_identity["teacher_model_revision"])
    print("TEACHER_ARTIFACT_SHA256=" + teacher_identity["teacher_model_artifact_sha256"])

    if args.dry_run:
        print("B1_D1_DELIVERY_DRY_RUN=PASS")
        return 0

    out = (repo / args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    canonical_out = out / "dataset_sample_228.jsonl"
    student_out = out / "dataset_student_228.jsonl"
    quarantine_out = out / "quarantine.jsonl"
    schema_out = out / "dataset_schema.md"
    quality_out = out / "dataset_quality_report.md"
    manifest_out = out / "dataset_manifest_v0.json"

    write_jsonl(canonical_out, canonical)
    write_jsonl(student_out, student)
    write_jsonl(quarantine_out, quarantine)
    schema_out.write_text(schema_markdown(), encoding="utf-8")

    counts = {
        "canonical": len(canonical),
        "student_eligible": len(student),
        "quarantine": len(quarantine),
        "groups": group_audit["group_count"],
    }
    quality_out.write_text(
        quality_markdown(
            counts, group_audit, source_counts, class_counts,
            quarantine_counts, collection_sha_counts, failures
        ),
        encoding="utf-8",
    )

    artifact_hashes = {
        canonical_out.name: sha256_file(canonical_out),
        student_out.name: sha256_file(student_out),
        quarantine_out.name: sha256_file(quarantine_out),
        schema_out.name: sha256_file(schema_out),
        quality_out.name: sha256_file(quality_out),
    }

    manifest = {
        "schema_version": "1.0",
        "dataset_version": DELIVERY_VERSION,
        "delivery_status": "D1_200_PLUS_FROZEN",
        "delivery_repo_git_sha": base.current_head(repo),
        "delivery_branch": base.current_branch(repo),
        "builder_identity": builder_identity,
        "formal_code_gate": formal_code_gate,
        "counts": counts,
        "teacher": {
            "model_id": teacher_identity["teacher_model_id"],
            "model_revision": teacher_identity["teacher_model_revision"],
            "artifact_sha256": teacher_identity["teacher_model_artifact_sha256"],
            "baseline_git_sha": teacher_identity["teacher_baseline_git_sha"],
            "profile": "b1-pinned-teacher-v1",
            "mode": "planner_v2",
        },
        "collection_repo_git_sha_counts": dict(collection_sha_counts),
        "source_bucket_counts": dict(source_counts),
        "sample_class_counts": dict(class_counts),
        "group_audit": group_audit,
        "quarantine_reason_counts": dict(quarantine_counts),
        "process_failures": failures,
        "input_artifact_sha256": input_hashes,
        "finalization": {
            "repo_git_sha": final_prov.get("finalization_repo_git_sha"),
            "finalizer_identity": final_prov.get("finalizer_identity"),
            "parent_collection_repo_git_sha": final_prov.get("parent_collection_repo_git_sha"),
            "parent_extension_config_id": final_prov.get("parent_extension_config_id"),
            "correction_policy": final_prov.get("correction_policy"),
        },
        "artifacts_sha256": artifact_hashes,
        "split_policy": {
            "split_unit": "group_key",
            "same_group_must_remain_in_same_split": True,
            "random_sample_or_adjacent_frame_split": False,
            "unseen_reserved_test_candidates_included": False,
        },
    }
    write_json(manifest_out, manifest)

    manifest_sha = sha256_file(manifest_out)
    (out / "dataset_manifest_v0.sha256").write_text(
        f"{manifest_sha}  {manifest_out.name}\n",
        encoding="utf-8",
    )

    if len(base.read_jsonl(canonical_out)) != 228:
        raise RuntimeError("canonical reread mismatch")
    if len(base.read_jsonl(student_out)) != 228:
        raise RuntimeError("student reread mismatch")
    if len(base.read_jsonl(quarantine_out)) != len(quarantine):
        raise RuntimeError("quarantine reread mismatch")

    print("DATASET_SAMPLE_SHA256=" + sha256_file(canonical_out))
    print("DATASET_STUDENT_SHA256=" + sha256_file(student_out))
    print("QUARANTINE_SHA256=" + sha256_file(quarantine_out))
    print("MANIFEST_SHA256=" + manifest_sha)
    print("B1_D1_DELIVERY_BUILD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
