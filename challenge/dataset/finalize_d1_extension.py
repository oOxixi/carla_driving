#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from challenge.dataset import collect_d1_200 as base


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            )


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--base-dataset",
        default=(
            "artifacts/b1_d1_pinned_formal/"
            "dataset/d1_valid.jsonl"
        ),
    )

    ap.add_argument(
        "--extension-dir",
        default="artifacts/b1_d1_extension_formal",
    )

    ap.add_argument(
        "--output-dir",
        default="artifacts/b1_d1_extension_final",
    )

    ap.add_argument(
        "--runner-python",
        default="/home/dcase_task2/miniconda3/envs/voice/bin/python",
    )

    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]

    base_path = repo / args.base_dataset
    ext_dir = repo / args.extension_dir
    out = repo / args.output_dir

    finalizer_relpath = (
        "challenge/dataset/finalize_d1_extension.py"
    )

    finalizer_identity = (
        base.verify_tracked_file_matches_head(
            repo,
            finalizer_relpath,
        )
    )

    print("FORMAL_CODE_GATE=PASS")
    print(
        "FINALIZER_SHA256="
        + finalizer_identity["sha256"]
    )
    print(
        "REPO_HEAD="
        + base.current_head(repo)
    )

    valid_path = ext_dir / "dataset/extension_valid.jsonl"
    student_path = (
        ext_dir
        / "dataset/extension_student_eligible.jsonl"
    )
    quarantine_path = (
        ext_dir
        / "dataset/extension_quarantine.jsonl"
    )
    provenance_path = ext_dir / "provenance_manifest.json"
    summary_path = ext_dir / "extension_summary.json"

    for p in (
        base_path,
        valid_path,
        student_path,
        quarantine_path,
        provenance_path,
        summary_path,
    ):
        if not p.is_file():
            raise RuntimeError(f"required file missing: {p}")

    base_rows = base.read_jsonl(base_path)
    valid_rows = base.read_jsonl(valid_path)
    quarantine_rows = base.read_jsonl(quarantine_path)

    base_groups = {
        (r.get("metadata") or {}).get("group_key")
        for r in base_rows
        if (r.get("metadata") or {}).get("group_key")
    }

    group_owners = {}

    for r in valid_rows:
        m = r.get("metadata") or {}

        g = m.get("group_key")
        eid = m.get("extension_id")

        if not g or not eid:
            raise RuntimeError(
                "existing valid sample missing group/extension id"
            )

        if g in base_groups:
            raise RuntimeError(
                f"base-extension group overlap: {g}"
            )

        owner = group_owners.get(g)

        if owner is not None and owner != eid:
            raise RuntimeError(
                f"group {g} has owners {owner} and {eid}"
            )

        group_owners[g] = eid

    recovered = []
    retained_quarantine = []

    for q in quarantine_rows:
        reason = q.get("reason")
        sample = q.get("canonical_sample") or {}
        meta = sample.get("metadata") or {}

        if reason != "GROUP_OVERLAP_WITH_EXTENSION":
            retained_quarantine.append(q)
            continue

        g = meta.get("group_key")
        eid = q.get("extension_id")

        if not g or not eid:
            retained_quarantine.append(q)
            continue

        if g in base_groups:
            raise RuntimeError(
                "attempted recovery overlaps base group: "
                + str(g)
            )

        owner = group_owners.get(g)

        if owner is None:
            group_owners[g] = eid

        elif owner != eid:
            retained_quarantine.append({
                **q,
                "reason":
                    "GROUP_OWNED_BY_DIFFERENT_EXTENSION",
            })
            continue

        view, student_reason = base.student_view_or_reason(
            sample
        )

        if student_reason is not None:
            retained_quarantine.append({
                **q,
                "reason": student_reason,
            })
            continue

        recovered.append((sample, view))

    final_valid = valid_rows + [
        x[0] for x in recovered
    ]

    original_student = base.read_jsonl(student_path)

    final_student = original_student + [
        x[1] for x in recovered
    ]

    sample_ids = [
        r.get("sample_id")
        for r in final_valid
    ]

    if len(sample_ids) != len(set(sample_ids)):
        raise RuntimeError(
            "duplicate sample_id after finalization"
        )

    if len(final_valid) != len(final_student):
        raise RuntimeError(
            "canonical/student count mismatch"
        )

    out_dataset = out / "dataset"

    write_jsonl(
        out_dataset / "extension_valid.jsonl",
        final_valid,
    )

    write_jsonl(
        out_dataset
        / "extension_student_eligible.jsonl",
        final_student,
    )

    write_jsonl(
        out_dataset / "extension_quarantine.jsonl",
        retained_quarantine,
    )

    rejected_src = (
        ext_dir / "dataset/extension_rejected.jsonl"
    )

    rejected_rows = (
        base.read_jsonl(rejected_src)
        if rejected_src.is_file()
        else []
    )

    write_jsonl(
        out_dataset / "extension_rejected.jsonl",
        rejected_rows,
    )

    combined = len(base_rows) + len(final_valid)

    reasons = Counter(
        r.get("reason")
        for r in retained_quarantine
    )

    final_summary = {
        "schema_version": "1.0",
        "base_dataset_count": len(base_rows),
        "original_extension_valid":
            len(valid_rows),
        "recovered_same_group_samples":
            len(recovered),
        "extension_valid":
            len(final_valid),
        "extension_student_eligible":
            len(final_student),
        "extension_quarantined":
            len(retained_quarantine),
        "extension_rejected":
            len(rejected_rows),
        "combined_valid": combined,
        "minimum_total": 200,
        "minimum_reached": combined >= 200,
        "target_total": 220,
        "target_reached": combined >= 220,
        "remaining_quarantine_reasons":
            dict(reasons),
    }

    (out / "finalization_summary.json").write_text(
        json.dumps(
            final_summary,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    original_prov = json.loads(
        provenance_path.read_text(encoding="utf-8")
    )

    final_prov = {
        "schema_version": "1.0",
        "finalization_type":
            "GROUP_OWNERSHIP_CORRECTION",
        "finalization_repo_git_sha":
            base.current_head(repo),
        "finalization_branch":
            base.current_branch(repo),
        "finalizer_identity":
            finalizer_identity,
        "formal_code_gate":
            True,
        "parent_extension_provenance":
            str(
                provenance_path.relative_to(repo)
            ),
        "parent_extension_provenance_sha256":
            sha256_file(provenance_path),
        "parent_extension_valid_sha256":
            sha256_file(valid_path),
        "parent_extension_quarantine_sha256":
            sha256_file(quarantine_path),
        "base_dataset_sha256":
            sha256_file(base_path),
        "parent_collection_repo_git_sha":
            original_prov.get(
                "collection_repo_git_sha"
            ),
        "parent_extension_config_id":
            original_prov.get(
                "extension_config_id"
            ),
        "teacher_model_id":
            original_prov.get(
                "teacher_model_id"
            ),
        "teacher_model_revision":
            original_prov.get(
                "teacher_model_revision"
            ),
        "teacher_model_artifact_sha256":
            original_prov.get(
                "teacher_model_artifact_sha256"
            ),
        "correction_policy": (
            "recover GROUP_OVERLAP_WITH_EXTENSION "
            "only when group owner is the same "
            "extension_id; preserve all other "
            "quarantine reasons"
        ),
    }

    (out / "finalization_provenance.json").write_text(
        json.dumps(
            final_prov,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    base.validate_canonical(
        repo,
        args.runner_python,
        out_dataset / "extension_valid.jsonl",
    )

    print("CANONICAL_VALIDATION=PASS")

    print(
        "ORIGINAL_EXTENSION_VALID="
        + str(len(valid_rows))
    )
    print(
        "RECOVERED_SAME_GROUP_SAMPLES="
        + str(len(recovered))
    )
    print(
        "FINAL_EXTENSION_VALID="
        + str(len(final_valid))
    )
    print(
        "FINAL_QUARANTINE="
        + str(len(retained_quarantine))
    )
    print(
        "COMBINED_VALID="
        + str(combined)
    )
    print(
        "MINIMUM_REACHED="
        + str(combined >= 200)
    )
    print(
        "TARGET_REACHED="
        + str(combined >= 220)
    )
    print(
        "REMAINING_REASONS="
        + json.dumps(
            dict(reasons),
            sort_keys=True,
        )
    )

    print("B1_D1_EXTENSION_FINALIZE=PASS")


if __name__ == "__main__":
    main()
