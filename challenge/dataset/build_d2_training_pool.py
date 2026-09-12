#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from challenge.dataset import collect_d1_200 as base

TRAINING_POOL_VERSION = "b1_d2_training_pool_v0"
SOURCE_D1_CANONICAL_SHA256 = "2415cbd1ff5d1dd35af6740e4ebd2cd0ef8eb3feca5ce3ced3c931ca9c0b0eea"
SOURCE_D1_MANIFEST_SHA256 = "06f3d015efe0ff84e8c2b41c9a12ba1fa9b7b9936483bde16340fdc74ff7fd1f"
EXPECTED_STUDENT_CONTRACT = "student_v0_r3"
EXPECTED_MAX_TARGETS = 8
EXPECTED_NO_TARGET_INDEX = 8


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def get_meta(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("metadata")
    return value if isinstance(value, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--canonical",
        default="artifacts/b1_d1_delivery_v0/dataset_sample_228.jsonl",
    )
    ap.add_argument(
        "--d1-manifest",
        default="artifacts/b1_d1_delivery_v0/dataset_manifest_v0.json",
    )
    ap.add_argument(
        "--output-dir",
        default="artifacts/b1_d2_training_pool_v0",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-uncommitted-code", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    canonical_path = (repo / args.canonical).resolve()
    d1_manifest_path = (repo / args.d1_manifest).resolve()

    if not canonical_path.is_file():
        raise RuntimeError(f"canonical dataset missing: {canonical_path}")
    if not d1_manifest_path.is_file():
        raise RuntimeError(f"D1 manifest missing: {d1_manifest_path}")

    canonical_sha = sha256_file(canonical_path)
    manifest_sha = sha256_file(d1_manifest_path)

    if canonical_sha != SOURCE_D1_CANONICAL_SHA256:
        raise RuntimeError(
            "D1 canonical SHA mismatch: "
            f"expected={SOURCE_D1_CANONICAL_SHA256} actual={canonical_sha}"
        )
    if manifest_sha != SOURCE_D1_MANIFEST_SHA256:
        raise RuntimeError(
            "D1 manifest SHA mismatch: "
            f"expected={SOURCE_D1_MANIFEST_SHA256} actual={manifest_sha}"
        )

    builder_rel = "challenge/dataset/build_d2_training_pool.py"
    contract_rel = "challenge/dataset/collect_d1_200.py"

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

    contract_identity = base.verify_tracked_file_matches_head(repo, contract_rel)

    rows = base.read_jsonl(canonical_path)
    if len(rows) != 228:
        raise RuntimeError(f"expected 228 D1 canonical samples, got {len(rows)}")

    eligible_canonical: list[dict[str, Any]] = []
    eligible_student: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []

    reasons: Counter[str] = Counter()
    affected_groups: defaultdict[str, list[str]] = defaultdict(list)

    seen_sample_ids: set[str] = set()
    eligible_ids: set[str] = set()

    for sample in rows:
        sample_id = sample.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise RuntimeError("canonical sample missing sample_id")
        if sample_id in seen_sample_ids:
            raise RuntimeError(f"duplicate canonical sample_id: {sample_id}")
        seen_sample_ids.add(sample_id)

        view, reason = base.student_view_or_reason(sample)

        if reason is None:
            if view is None:
                raise RuntimeError(f"student view unexpectedly missing: {sample_id}")

            policy = view.get("training_policy")
            if not isinstance(policy, dict):
                raise RuntimeError(f"training_policy missing in rebuilt view: {sample_id}")
            if policy.get("train_eligible") is not True:
                raise RuntimeError(f"rebuilt view is not train eligible: {sample_id}")

            meta = view.get("metadata")
            if not isinstance(meta, dict):
                raise RuntimeError(f"rebuilt view metadata missing: {sample_id}")
            if meta.get("student_contract") != EXPECTED_STUDENT_CONTRACT:
                raise RuntimeError(
                    f"student contract mismatch for {sample_id}: "
                    f"{meta.get('student_contract')!r}"
                )
            if meta.get("student_max_targets") != EXPECTED_MAX_TARGETS:
                raise RuntimeError(f"student_max_targets mismatch: {sample_id}")
            if meta.get("student_no_target_index") != EXPECTED_NO_TARGET_INDEX:
                raise RuntimeError(f"student_no_target_index mismatch: {sample_id}")

            request = view.get("input")
            if not isinstance(request, dict):
                raise RuntimeError(f"student input missing: {sample_id}")

            targets = request.get("targets")
            if not isinstance(targets, list):
                targets = []
            if len(targets) > EXPECTED_MAX_TARGETS:
                raise RuntimeError(f"student target overflow: {sample_id}")

            teacher = view.get("teacher")
            plan = teacher.get("maneuver_plan") if isinstance(teacher, dict) else None
            if not isinstance(plan, dict):
                raise RuntimeError(f"teacher maneuver plan missing: {sample_id}")

            if sample_id in eligible_ids:
                raise RuntimeError(f"duplicate eligible sample_id: {sample_id}")
            eligible_ids.add(sample_id)

            eligible_canonical.append(sample)
            eligible_student.append(view)
            continue

        reasons[reason] += 1
        meta = get_meta(sample)
        group_key = meta.get("group_key")
        if group_key:
            affected_groups[str(group_key)].append(sample_id)

        quarantine.append({
            "sample_id": sample_id,
            "reason": reason,
            "group_key": group_key,
            "scenario_id": meta.get("scenario_id"),
            "scenario_family": meta.get("scenario_family"),
            "source_bucket": meta.get("source_bucket"),
            "seed": meta.get("seed"),
            "command_id": meta.get("command_id"),
            "collection_repo_git_sha": meta.get("collection_repo_git_sha"),
            "canonical_sample": sample,
        })

    if len(eligible_canonical) != 214:
        raise RuntimeError(
            f"expected 214 current-contract eligible canonical samples, "
            f"got {len(eligible_canonical)}"
        )
    if len(eligible_student) != 214:
        raise RuntimeError(
            f"expected 214 current-contract student views, got {len(eligible_student)}"
        )
    if len(quarantine) != 14:
        raise RuntimeError(
            f"expected 14 current-contract quarantined samples, got {len(quarantine)}"
        )

    expected_reasons = {
        "COMMAND_TERMINAL_NOT_SUCCEEDED": 11,
        "CLOSED_LOOP_EVIDENCE_MISSING": 3,
    }
    if dict(reasons) != expected_reasons:
        raise RuntimeError(
            "contract quarantine reasons changed: "
            + json.dumps(dict(reasons), ensure_ascii=False, sort_keys=True)
        )

    if len(affected_groups) != 13:
        raise RuntimeError(
            f"expected 13 affected groups, got {len(affected_groups)}"
        )

    canonical_ids = {r["sample_id"] for r in eligible_canonical}
    student_ids = {r["sample_id"] for r in eligible_student}
    if canonical_ids != student_ids:
        raise RuntimeError("eligible canonical/student sample-id sets differ")

    source_counts = Counter(
        get_meta(r).get("source_bucket")
        for r in eligible_canonical
    )
    class_counts = Counter(
        (r.get("sample_class") or {}).get("primary")
        for r in eligible_canonical
    )
    family_counts = Counter(
        get_meta(r).get("scenario_family")
        for r in eligible_canonical
    )

    group_members: defaultdict[str, int] = defaultdict(int)
    for r in eligible_canonical:
        g = get_meta(r).get("group_key")
        if not g:
            raise RuntimeError(f"eligible sample missing group_key: {r['sample_id']}")
        group_members[str(g)] += 1

    print("TRAINING_POOL_VERSION=" + TRAINING_POOL_VERSION)
    print("REPO_HEAD=" + base.current_head(repo))
    print("BUILDER_SHA256=" + builder_identity["sha256"])
    print("CONTRACT_SHA256=" + contract_identity["sha256"])
    print("SOURCE_CANONICAL_SHA256=" + canonical_sha)
    print("SOURCE_D1_MANIFEST_SHA256=" + manifest_sha)
    print("CANONICAL_INPUT=228")
    print("ELIGIBLE_CANONICAL=" + str(len(eligible_canonical)))
    print("ELIGIBLE_STUDENT=" + str(len(eligible_student)))
    print("CONTRACT_QUARANTINE=" + str(len(quarantine)))
    print("AFFECTED_GROUPS=" + str(len(affected_groups)))
    print("ELIGIBLE_GROUPS=" + str(len(group_members)))
    print("REASONS=" + json.dumps(dict(reasons), sort_keys=True))
    print("SOURCE_BUCKETS=" + json.dumps(dict(source_counts), sort_keys=True))
    print("SAMPLE_CLASSES=" + json.dumps(dict(class_counts), sort_keys=True))
    print("FAMILIES=" + json.dumps(dict(family_counts), sort_keys=True))

    if args.dry_run:
        print("B1_D2_TRAINING_POOL_DRY_RUN=PASS")
        return 0

    out = (repo / args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    canonical_out = out / "canonical_eligible.jsonl"
    student_out = out / "student_eligible.jsonl"
    quarantine_out = out / "contract_quarantine.jsonl"
    manifest_out = out / "training_pool_manifest.json"
    report_out = out / "training_pool_quality_report.md"

    write_jsonl(canonical_out, eligible_canonical)
    write_jsonl(student_out, eligible_student)
    write_jsonl(quarantine_out, quarantine)

    artifact_hashes = {
        canonical_out.name: sha256_file(canonical_out),
        student_out.name: sha256_file(student_out),
        quarantine_out.name: sha256_file(quarantine_out),
    }

    mixed_groups = 0
    fully_bad_groups = 0
    by_group_all: defaultdict[str, int] = defaultdict(int)
    by_group_bad: defaultdict[str, int] = defaultdict(int)

    for r in rows:
        g = get_meta(r).get("group_key")
        if g:
            by_group_all[str(g)] += 1
    for q in quarantine:
        g = q.get("group_key")
        if g:
            by_group_bad[str(g)] += 1

    for g, bad_count in by_group_bad.items():
        total = by_group_all[g]
        if bad_count == total:
            fully_bad_groups += 1
        else:
            mixed_groups += 1

    manifest = {
        "schema_version": "1.0",
        "training_pool_version": TRAINING_POOL_VERSION,
        "status": "D2_CURRENT_STUDENT_CONTRACT_FROZEN",
        "repo_git_sha": base.current_head(repo),
        "branch": base.current_branch(repo),
        "formal_code_gate": formal_code_gate,
        "builder_identity": builder_identity,
        "student_contract_identity": contract_identity,
        "source": {
            "d1_canonical_path": str(canonical_path.relative_to(repo)),
            "d1_canonical_sha256": canonical_sha,
            "d1_manifest_path": str(d1_manifest_path.relative_to(repo)),
            "d1_manifest_sha256": manifest_sha,
            "d1_canonical_count": len(rows),
        },
        "student_contract": {
            "name": EXPECTED_STUDENT_CONTRACT,
            "max_targets": EXPECTED_MAX_TARGETS,
            "no_target_index": EXPECTED_NO_TARGET_INDEX,
            "eligibility_function": "challenge.dataset.collect_d1_200.student_view_or_reason",
        },
        "counts": {
            "eligible_canonical": len(eligible_canonical),
            "eligible_student": len(eligible_student),
            "contract_quarantine": len(quarantine),
            "eligible_groups": len(group_members),
            "affected_groups": len(affected_groups),
            "mixed_affected_groups": mixed_groups,
            "fully_bad_groups": fully_bad_groups,
        },
        "quarantine_reason_counts": dict(reasons),
        "source_bucket_counts": dict(source_counts),
        "sample_class_counts": dict(class_counts),
        "scenario_family_counts": dict(family_counts),
        "affected_group_keys": sorted(affected_groups),
        "artifacts_sha256": artifact_hashes,
        "policy": {
            "d1_artifacts_immutable": True,
            "eligibility_unit": "sample",
            "split_unit": "group_key",
            "mixed_group_good_samples_preserved": True,
            "failed_samples_never_promoted": True,
        },
    }
    write_json(manifest_out, manifest)

    report = f"""# B1 D2 Training Pool Quality Report

## Source

- Frozen D1 canonical samples: 228
- Source canonical SHA256: `{canonical_sha}`
- Source D1 manifest SHA256: `{manifest_sha}`

## Current Student contract

- Contract: `{EXPECTED_STUDENT_CONTRACT}`
- Max targets: {EXPECTED_MAX_TARGETS}
- No-target index: {EXPECTED_NO_TARGET_INDEX}
- Contract code SHA256: `{contract_identity["sha256"]}`

## Eligibility result

- Eligible canonical samples: {len(eligible_canonical)}
- Eligible Student views: {len(eligible_student)}
- Contract quarantine: {len(quarantine)}
- Eligible groups: {len(group_members)}
- Affected groups: {len(affected_groups)}
- Mixed affected groups: {mixed_groups}
- Fully bad groups: {fully_bad_groups}

## Quarantine reasons

```json
{json.dumps(dict(reasons), indent=2, sort_keys=True)}
```

D1 artifacts remain immutable. This D2 pool is a derived layer under the
current Student contract. Eligibility is evaluated per sample; group_key
remains the downstream split unit. Good samples in a mixed group are retained,
while failed command-level samples remain quarantined.
"""
    report_out.write_text(report, encoding="utf-8")

    if len(base.read_jsonl(canonical_out)) != 214:
        raise RuntimeError("eligible canonical reread count mismatch")
    if len(base.read_jsonl(student_out)) != 214:
        raise RuntimeError("eligible student reread count mismatch")
    if len(base.read_jsonl(quarantine_out)) != 14:
        raise RuntimeError("quarantine reread count mismatch")

    print("CANONICAL_ELIGIBLE_SHA256=" + sha256_file(canonical_out))
    print("STUDENT_ELIGIBLE_SHA256=" + sha256_file(student_out))
    print("CONTRACT_QUARANTINE_SHA256=" + sha256_file(quarantine_out))
    print("TRAINING_POOL_MANIFEST_SHA256=" + sha256_file(manifest_out))
    print("B1_D2_TRAINING_POOL_BUILD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
