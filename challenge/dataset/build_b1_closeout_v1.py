from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

OUT_REL = Path("challenge/dataset/governance/b1_closeout_v1")
OUT = ROOT / OUT_REL
IV = OUT / "independent_validation_v1"
ATTEST = OUT / "attestations"

GOVERNED_VERSION = "b1_governed_dataset_closeout_v1"
IV_VERSION = "b1_independent_validation_v1"

D2 = ROOT / "challenge/dataset/releases/d2_v1_1"
CAL = ROOT / "challenge/dataset/releases/calibration_v1"

D2_RESERVED = D2 / "reserved_test_candidates.jsonl"
D2_TRAIN = D2 / "train.jsonl"
D2_VAL = D2 / "val.jsonl"

CAL_ROWS = CAL / "calibration.jsonl"
CAL_ASSIGN = CAL / "selection_assignments.jsonl"
CAL_MANIFEST = CAL / "calibration_manifest.json"

PINNED_TEACHER = ROOT / "challenge/teacher_pinned_manifest_v4.json"

GAP_RELEASE = ROOT / "challenge/dataset/releases/d3_gap300_strict_v1"
GAP_ADDENDUM = (
    ROOT
    / "challenge/dataset/attestations/"
      "d3_gap300_strict_v1_provenance_addendum_v1/"
      "gap300_provenance_addendum.json"
)
GAP_TEACHER_ATTEST = (
    ROOT
    / "challenge/dataset/attestations/"
      "d3_gap300_strict_v1_teacher_provenance_v1/"
      "teacher_provenance_attestation.json"
)

MS34 = ROOT / "challenge/dataset/releases/b1_ms34_supplement_v1"


RELEASE_SPECS = [
    {
        "id": "d2_v1_1",
        "path": "challenge/dataset/releases/d2_v1_1",
        "train_key": "train",
        "val_key": "val",
        "hard_key": None,
        "role": "BASE_TRAIN_DEV",
    },
    {
        "id": "d3_wave1_addon_v1",
        "path": "challenge/dataset/releases/d3_wave1_addon_v1",
        "train_key": "train_addition",
        "val_key": "val_addition",
        "hard_key": "hard_negative_addition",
        "role": "TRAIN_DEV_ADDON",
    },
    {
        "id": "d3_wave2_safe_short_v1",
        "path": "challenge/dataset/releases/d3_wave2_safe_short_v1",
        "train_key": "train_addition",
        "val_key": "val_addition",
        "hard_key": "hard_negative_addition",
        "role": "TRAIN_DEV_ADDON",
    },
    {
        "id": "d3_targeted_gap_strict_v1",
        "path": "challenge/dataset/releases/d3_targeted_gap_strict_v1",
        "train_key": "train_addition",
        "val_key": "val_addition",
        "hard_key": "hard_negative_addition",
        "role": "TRAIN_DEV_ADDON",
    },
    {
        "id": "d3_turn_gap_60_strict_v1",
        "path": "challenge/dataset/releases/d3_turn_gap_60_strict_v1",
        "train_key": "train_addition",
        "val_key": "val_addition",
        "hard_key": "hard_negative_addition",
        "role": "TRAIN_DEV_ADDON",
    },
    {
        "id": "d3_gap300_strict_v1",
        "path": "challenge/dataset/releases/d3_gap300_strict_v1",
        "train_key": "train_addition",
        "val_key": "val_addition",
        "hard_key": "hard_negative_addition",
        "role": "TRAIN_DEV_ADDON",
    },
    {
        "id": "b1_ms34_supplement_v1",
        "path": "challenge/dataset/releases/b1_ms34_supplement_v1",
        "train_key": "train_addition",
        "val_key": "val_addition",
        "hard_key": "hard_negative_addition",
        "role": "TRAIN_DEV_ADDON",
    },
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


def json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl_load(path: Path) -> list[dict[str, Any]]:
    rows = []
    for n, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            raise RuntimeError(
                f"{path}:{n}: invalid JSON: {exc}"
            ) from exc
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(canonical_json(row) + "\n")


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def file_binding(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "available": False,
            "reason": "HISTORICAL_SCHEMA_VARIANT_OR_NOT_APPLICABLE",
        }
    return {
        "available": True,
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def sample_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {str(x.get("sample_id") or "") for x in rows}


def group_keys(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str((x.get("metadata") or {}).get("group_key") or "")
        for x in rows
    }


def sample_identity_sha(row: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(row).encode("utf-8"))


def release_identity(spec: dict[str, Any]) -> dict[str, Any]:
    rel = ROOT / spec["path"]
    rm_path = rel / "release_manifest.json"

    if not rm_path.is_file():
        raise RuntimeError(
            f"missing release_manifest for governed release {spec['id']}"
        )

    rm = json_load(rm_path)
    counts = rm.get("counts") or {}

    train_count = int(counts.get(spec["train_key"], 0))
    val_count = int(counts.get(spec["val_key"], 0))

    hard_count = 0
    if spec["hard_key"]:
        hard_count = int(counts.get(spec["hard_key"], 0))

    return {
        "release_id": spec["id"],
        "dataset_version": rm.get("dataset_version") or spec["id"],
        "release_path": spec["path"],
        "role": spec["role"],
        "counts": {
            "train": train_count,
            "dev": val_count,
            "hard_negative": hard_count,
        },
        "status": rm.get("status"),
        "immutability": "FROZEN_EXISTING_RELEASE",
        "bindings": {
            "release_manifest": file_binding(rm_path),
            "provenance_manifest": file_binding(
                rel / "provenance_manifest.json"
            ),
            "governance_report": file_binding(
                rel / "governance_report.json"
            ),
            "split_manifest": file_binding(
                rel / "split_manifest.json"
            ),
            "content_bound_pass": file_binding(
                rel / "B1_CONTENT_BOUND_PASS.json"
            ),
        },
    }


def current_teacher_policy() -> dict[str, Any]:
    if not PINNED_TEACHER.is_file():
        raise RuntimeError(
            f"missing pinned Teacher manifest: {PINNED_TEACHER}"
        )

    d = json_load(PINNED_TEACHER)

    # Preserve the actual manifest, but expose common identity keys
    # without guessing absent field names.
    return {
        "manifest_path": str(PINNED_TEACHER.relative_to(ROOT)),
        "manifest_sha256": sha256_file(PINNED_TEACHER),
        "manifest": d,
    }


def build_independent_validation() -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    reserved = jsonl_load(D2_RESERVED)
    calibration = jsonl_load(CAL_ROWS)
    cal_assign = jsonl_load(CAL_ASSIGN)

    if len(reserved) != 540:
        raise RuntimeError(
            f"reserved pool {len(reserved)} != 540"
        )
    if len(calibration) != 300:
        raise RuntimeError(
            f"calibration {len(calibration)} != 300"
        )
    if len(cal_assign) != 300:
        raise RuntimeError(
            f"cal assignments {len(cal_assign)} != 300"
        )

    reserved_ids = sample_ids(reserved)
    cal_ids = sample_ids(calibration)
    cal_assignment_ids = sample_ids(cal_assign)

    if cal_ids != cal_assignment_ids:
        raise RuntimeError(
            "calibration rows and assignments disagree"
        )

    if not cal_ids <= reserved_ids:
        raise RuntimeError(
            "calibration contains sample outside reserved pool"
        )

    remaining = [
        row for row in reserved
        if str(row["sample_id"]) not in cal_ids
    ]

    if len(remaining) != 240:
        raise RuntimeError(
            f"remaining reserved = {len(remaining)}, expected 240"
        )

    remaining_ids = sample_ids(remaining)
    remaining_groups = group_keys(remaining)

    if "" in remaining_groups:
        raise RuntimeError("independent validation missing group_key")

    if len(remaining_groups) != 240:
        raise RuntimeError(
            f"Independent Validation groups={len(remaining_groups)}, "
            "expected 240"
        )

    train = jsonl_load(D2_TRAIN)
    val = jsonl_load(D2_VAL)

    train_ids = sample_ids(train)
    val_ids = sample_ids(val)
    train_groups = group_keys(train)
    val_groups = group_keys(val)
    cal_groups = group_keys(calibration)

    checks = {
        "independent_sample_count_240": len(remaining) == 240,
        "independent_group_count_240": len(remaining_groups) == 240,
        "independent_vs_calibration_sample_overlap_zero":
            not (remaining_ids & cal_ids),
        "independent_vs_calibration_group_overlap_zero":
            not (remaining_groups & cal_groups),
        "independent_vs_d2_train_sample_overlap_zero":
            not (remaining_ids & train_ids),
        "independent_vs_d2_dev_sample_overlap_zero":
            not (remaining_ids & val_ids),
        "independent_vs_d2_train_group_overlap_zero":
            not (remaining_groups & train_groups),
        "independent_vs_d2_dev_group_overlap_zero":
            not (remaining_groups & val_groups),
    }

    if not all(checks.values()):
        bad = [k for k, v in checks.items() if not v]
        raise RuntimeError(
            f"Independent Validation leakage: {bad}"
        )

    cases = []
    for row in sorted(
        remaining,
        key=lambda x: str(x["sample_id"]),
    ):
        sid = str(row["sample_id"])
        md = row.get("metadata") or {}
        vis = row.get("visual_input") or {}

        rgb_ref = vis.get("rgb_ref")
        if not isinstance(rgb_ref, str) or not rgb_ref:
            raise RuntimeError(f"{sid}: missing rgb_ref")

        rgb_path = ROOT / rgb_ref
        if not rgb_path.is_file():
            raise RuntimeError(
                f"{sid}: RGB missing: {rgb_ref}"
            )

        actual_rgb_sha = sha256_file(rgb_path)
        if actual_rgb_sha != vis.get("rgb_sha256"):
            raise RuntimeError(
                f"{sid}: RGB SHA mismatch"
            )

        case_payload = {
            "sample_id": sid,
            "group_key": md.get("group_key"),
            "scenario_family": md.get("scenario_family"),
            "scenario_id": md.get("scenario_id"),
            "seed": md.get("seed"),
            "map": md.get("map"),
            "route_hash": md.get("route_hash"),
            "source_release": "d2_v1_1",
            "source_split": "reserved_test_candidates",
            "sample_content_sha256": sample_identity_sha(row),
            "rgb_ref": rgb_ref,
            "rgb_sha256": actual_rgb_sha,
            "rgb_size_bytes": rgb_path.stat().st_size,
        }

        case_id = (
            "iv1_"
            + sha256_bytes(
                canonical_json(case_payload).encode("utf-8")
            )[:20]
        )

        cases.append({
            "case_id": case_id,
            **case_payload,
        })

    digest_payload = {
        "dataset_version": IV_VERSION,
        "case_count": len(cases),
        "group_count": len(remaining_groups),
        "cases": cases,
    }
    case_set_digest = sha256_bytes(
        canonical_json(digest_payload).encode("utf-8")
    )

    write_jsonl(IV / "cases.jsonl", remaining)

    write_json(
        IV / "case_manifest.json",
        {
            "schema_version": "1.0",
            "dataset_version": IV_VERSION,
            "status": "FROZEN_INDEPENDENT_VALIDATION",
            "case_count": len(cases),
            "group_count": len(remaining_groups),
            "source_release": "d2_v1_1",
            "source_pool": (
                "challenge/dataset/releases/d2_v1_1/"
                "reserved_test_candidates.jsonl"
            ),
            "cases": cases,
        },
    )

    write_json(
        IV / "case_set_digest.json",
        {
            "schema_version": "1.0",
            "dataset_version": IV_VERSION,
            "algorithm": "SHA256",
            "canonicalization": (
                "UTF-8 canonical JSON; sorted keys; compact separators; "
                "cases ordered by sample_id"
            ),
            "case_count": len(cases),
            "group_count": len(remaining_groups),
            "sha256": case_set_digest,
        },
    )

    source_binding = {
        "schema_version": "1.0",
        "dataset_version": IV_VERSION,
        "source_release": "d2_v1_1",
        "source_release_manifest": file_binding(
            D2 / "release_manifest.json"
        ),
        "reserved_pool": file_binding(D2_RESERVED),
        "calibration_manifest": file_binding(CAL_MANIFEST),
        "calibration_assignments": file_binding(CAL_ASSIGN),
        "selection_rule": (
            "Independent Validation v1 is exactly the set difference "
            "D2 v1.1 reserved_test_candidates minus Calibration v1 "
            "selected sample_ids. No additional ranking or relabeling."
        ),
        "source_release_mutated": False,
    }

    write_json(
        IV / "source_release_binding.json",
        source_binding,
    )

    dataset_identity = {
        "schema_version": "1.0",
        "dataset_version": IV_VERSION,
        "role": "INDEPENDENT_VALIDATION",
        "status": "FROZEN",
        "counts": {
            "samples": 240,
            "groups": 240,
        },
        "governance": {
            "training": False,
            "development": False,
            "calibration": False,
            "frozen_test": False,
            "independent_validation": True,
            "labels_must_not_be_used_for_A3_training_or_tuning": True,
            "frozen_test_assignment": "NOT_ASSIGNED_BY_B1",
        },
        "case_manifest_sha256": sha256_file(
            IV / "case_manifest.json"
        ),
        "case_set_digest_sha256": case_set_digest,
        "source_release_binding_sha256": sha256_file(
            IV / "source_release_binding.json"
        ),
        "leakage_checks": checks,
    }

    write_json(
        IV / "dataset_identity.json",
        dataset_identity,
    )

    (IV / "README.md").write_text(
        f"""# B1 Independent Validation v1

Dataset version: `{IV_VERSION}`

This frozen Independent Validation set contains the **240 samples /
240 groups** remaining from the D2 v1.1 reserved pool after the
300-sample Calibration v1 allocation.

Identity rule:

`D2 v1.1 reserved pool (540) - Calibration v1 (300) = Independent Validation v1 (240)`

This set is **not training data**, **not development data**,
**not calibration data**, and is **not designated Frozen Test by B1**.

The case identities are frozen in `case_manifest.json` and bound by
`case_set_digest.json`.

A3 must not use these cases or labels for training, model selection,
hyperparameter tuning, or error-driven iteration.
""",
        encoding="utf-8",
    )

    return remaining, {
        "checks": checks,
        "case_set_digest": case_set_digest,
        "sample_ids": remaining_ids,
        "group_keys": remaining_groups,
    }


def build_gap300_binding() -> dict[str, Any]:
    required = [
        GAP_ADDENDUM,
        GAP_TEACHER_ATTEST,
        GAP_RELEASE / "release_manifest.json",
        GAP_RELEASE / "provenance_manifest.json",
        GAP_RELEASE / "governance_report.json",
        GAP_RELEASE / "split_manifest.json",
        GAP_RELEASE / "B1_CONTENT_BOUND_PASS.json",
    ]

    for p in required:
        if not p.is_file():
            raise RuntimeError(
                f"Gap300 binding source missing: {p}"
            )

    obj = {
        "schema_version": "1.0",
        "dataset_version": "b1_d3_gap300_strict_v1",
        "status": "PASS",
        "historical_release_mutated": False,
        "purpose": (
            "Bind the immutable Gap300 release to its external "
            "provenance addendum and Teacher provenance attestation."
        ),
        "bindings": {
            "release_manifest": file_binding(
                GAP_RELEASE / "release_manifest.json"
            ),
            "provenance_manifest": file_binding(
                GAP_RELEASE / "provenance_manifest.json"
            ),
            "governance_report": file_binding(
                GAP_RELEASE / "governance_report.json"
            ),
            "split_manifest": file_binding(
                GAP_RELEASE / "split_manifest.json"
            ),
            "content_bound_pass": file_binding(
                GAP_RELEASE / "B1_CONTENT_BOUND_PASS.json"
            ),
            "provenance_addendum": file_binding(GAP_ADDENDUM),
            "teacher_provenance_attestation":
                file_binding(GAP_TEACHER_ATTEST),
        },
    }

    write_json(
        ATTEST / "gap300_provenance_binding.json",
        obj,
    )
    return obj


def build_ms34_teacher_addendum(
    teacher_policy: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    for name in (
        "train_addition.jsonl",
        "val_addition.jsonl",
        "hard_negative_addition.jsonl",
    ):
        rows.extend(jsonl_load(MS34 / name))

    if len(rows) != 35:
        raise RuntimeError(
            f"MS34 canonical rows={len(rows)}, expected 35"
        )

    model_ids = Counter(
        str((r.get("metadata") or {}).get("teacher_model_id"))
        for r in rows
    )
    modes = Counter(
        str((r.get("metadata") or {}).get("teacher_mode"))
        for r in rows
    )
    recorded_git = Counter(
        str((r.get("metadata") or {}).get("teacher_git_sha"))
        for r in rows
    )
    service_urls = Counter(
        str((r.get("metadata") or {}).get("teacher_service_url"))
        for r in rows
    )

    obj = {
        "schema_version": "1.0",
        "attestation_type":
            "MS34_PROVENANCE_ADDENDUM_CONTENT_BOUND_UNSIGNED",
        "dataset_version": "b1_ms34_supplement_v1",
        "status": "PASS_WITH_RUNTIME_IDENTITY_LIMITATION",
        "historical_release_mutated": False,
        "sample_rows_rewritten": False,
        "release_binding": {
            "release_manifest": file_binding(
                MS34 / "release_manifest.json"
            ),
            "provenance_manifest": file_binding(
                MS34 / "provenance_manifest.json"
            ),
            "governance_report": file_binding(
                MS34 / "governance_report.json"
            ),
            "split_manifest": file_binding(
                MS34 / "split_manifest.json"
            ),
            "content_bound_pass": file_binding(
                MS34 / "B1_CONTENT_BOUND_PASS.json"
            ),
        },
        "sample_level_observed_identity": {
            "canonical_rows": len(rows),
            "teacher_model_id_counts": dict(model_ids),
            "teacher_mode_counts": dict(modes),
            "recorded_teacher_git_sha_counts": dict(recorded_git),
            "teacher_service_url_counts": dict(service_urls),
        },
        "field_semantics": {
            "metadata.teacher_git_sha": (
                "Recorded acquisition/runtime repository checkout "
                "identity. It must not be silently reinterpreted as "
                "the canonical pinned Teacher-model identity."
            )
        },
        "current_pinned_teacher_policy": teacher_policy,
        "evidence_scope": {
            "verified_from_ms34_rows": [
                "teacher_model_id distribution",
                "teacher_mode distribution",
                "runtime/acquisition Git identity distribution",
                "Teacher service endpoint distribution",
            ],
            "not_retroactively_asserted_from_ms34_rows": [
                "pinned profile identity unless directly present",
                "model revision unless directly present",
                "artifact fingerprint unless directly present",
                "dtype unless directly present",
                "quantization unless directly present",
            ],
            "policy": (
                "Do not rewrite the immutable MS34 release. "
                "Current pinned Teacher policy governs future formal "
                "Teacher work; historical/runtime evidence is preserved "
                "as recorded."
            ),
        },
    }

    write_json(
        ATTEST / "ms34_teacher_provenance_addendum.json",
        obj,
    )
    return obj


def build_calibration_identity(
    independent_info: dict[str, Any],
) -> dict[str, Any]:
    cal_rows = jsonl_load(CAL_ROWS)
    cal_ids = sample_ids(cal_rows)
    cal_groups = group_keys(cal_rows)

    if len(cal_rows) != 300:
        raise RuntimeError("Calibration row count != 300")
    if len(cal_groups) != 300:
        raise RuntimeError(
            f"Calibration group count={len(cal_groups)}, expected 300"
        )

    if cal_ids & independent_info["sample_ids"]:
        raise RuntimeError(
            "Calibration/Independent sample overlap"
        )
    if cal_groups & independent_info["group_keys"]:
        raise RuntimeError(
            "Calibration/Independent group overlap"
        )

    obj = {
        "schema_version": "1.0",
        "dataset_version": "b1_calibration_v1",
        "status": "FROZEN_CALIBRATION",
        "purpose": "PTQ_CALIBRATION_ONLY",
        "counts": {
            "samples": 300,
            "groups": 300,
        },
        "bindings": {
            "calibration_manifest": file_binding(CAL_MANIFEST),
            "calibration_rows": file_binding(CAL_ROWS),
            "selection_assignments": file_binding(CAL_ASSIGN),
            "coverage_report": file_binding(
                CAL / "calibration_coverage_report.json"
            ),
            "rgb_manifest": file_binding(
                CAL / "rgb_manifest.json"
            ),
        },
        "governance": {
            "training": False,
            "development": False,
            "independent_validation": False,
            "frozen_test": False,
            "calibration": True,
            "independent_validation_sample_overlap": 0,
            "independent_validation_group_overlap": 0,
        },
    }

    write_json(
        OUT / "calibration_identity.json",
        obj,
    )
    return obj


def build_governed_manifest() -> dict[str, Any]:
    releases = [
        release_identity(spec)
        for spec in RELEASE_SPECS
    ]

    total_train = sum(
        x["counts"]["train"] for x in releases
    )
    total_dev = sum(
        x["counts"]["dev"] for x in releases
    )
    total_hard = sum(
        x["counts"]["hard_negative"] for x in releases
    )

    if total_train != 6037:
        raise RuntimeError(
            f"governed train={total_train}, expected 6037"
        )
    if total_dev != 1158:
        raise RuntimeError(
            f"governed dev={total_dev}, expected 1158"
        )

    obj = {
        "schema_version": "1.0",
        "dataset_version": GOVERNED_VERSION,
        "status": "B1_GOVERNED_RELEASE_SET",
        "policy": {
            "historical_releases_immutable": True,
            "new_release_identity_is_additive": True,
            "temporary_jsonl_not_governed_input": True,
        },
        "aggregate_counts": {
            "train": total_train,
            "dev": total_dev,
            "hard_negative_published": total_hard,
            "calibration": 300,
            "independent_validation": 240,
            "frozen_test": 0,
        },
        "releases": releases,
        "auxiliary_dataset_identities": {
            "calibration_v1":
                "challenge/dataset/governance/b1_closeout_v1/"
                "calibration_identity.json",
            "independent_validation_v1":
                "challenge/dataset/governance/b1_closeout_v1/"
                "independent_validation_v1/dataset_identity.json",
        },
    }

    write_json(
        OUT / "governed_release_manifest.json",
        obj,
    )
    return obj


def build_teacher_registry(
    teacher_policy: dict[str, Any],
) -> dict[str, Any]:
    obj = {
        "schema_version": "1.0",
        "status": "PASS",
        "policy": {
            "historical_release_provenance":
                "PRESERVE_AS_RECORDED",
            "future_formal_teacher_work":
                "USE_CURRENT_PINNED_TEACHER_POLICY",
        },
        "current_pinned_teacher_policy": teacher_policy,
        "special_attestations": {
            "gap300": file_binding(GAP_TEACHER_ATTEST),
            "gap300_provenance_addendum":
                file_binding(GAP_ADDENDUM),
            "ms34_provenance_addendum": file_binding(
                ATTEST / "ms34_teacher_provenance_addendum.json"
            ),
        },
        "release_provenance_sources": {
            spec["id"]: file_binding(
                ROOT / spec["path"] / "provenance_manifest.json"
            )
            for spec in RELEASE_SPECS
        },
    }

    write_json(
        OUT / "teacher_provenance_registry.json",
        obj,
    )
    return obj


def build_global_leakage_audit(
    independent_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    governed_train = []
    governed_dev = []

    # Load actual governed training/dev rows.
    governed_train.extend(jsonl_load(D2 / "train.jsonl"))
    governed_dev.extend(jsonl_load(D2 / "val.jsonl"))

    for spec in RELEASE_SPECS[1:]:
        rel = ROOT / spec["path"]
        governed_train.extend(
            jsonl_load(rel / "train_addition.jsonl")
        )
        governed_dev.extend(
            jsonl_load(rel / "val_addition.jsonl")
        )

    calibration = jsonl_load(CAL_ROWS)

    train_ids = sample_ids(governed_train)
    dev_ids = sample_ids(governed_dev)
    cal_ids = sample_ids(calibration)
    ind_ids = sample_ids(independent_rows)

    train_groups = group_keys(governed_train)
    dev_groups = group_keys(governed_dev)
    cal_groups = group_keys(calibration)
    ind_groups = group_keys(independent_rows)

    checks = {
        "train_sample_ids_unique":
            len(train_ids) == len(governed_train),
        "dev_sample_ids_unique":
            len(dev_ids) == len(governed_dev),
        "train_dev_sample_overlap_zero":
            not (train_ids & dev_ids),
        "calibration_train_sample_overlap_zero":
            not (cal_ids & train_ids),
        "calibration_dev_sample_overlap_zero":
            not (cal_ids & dev_ids),
        "independent_train_sample_overlap_zero":
            not (ind_ids & train_ids),
        "independent_dev_sample_overlap_zero":
            not (ind_ids & dev_ids),
        "independent_calibration_sample_overlap_zero":
            not (ind_ids & cal_ids),
        "independent_train_group_overlap_zero":
            not (ind_groups & train_groups),
        "independent_dev_group_overlap_zero":
            not (ind_groups & dev_groups),
        "independent_calibration_group_overlap_zero":
            not (ind_groups & cal_groups),
    }

    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise RuntimeError(
            f"global leakage audit failed: {failed}"
        )

    obj = {
        "schema_version": "1.0",
        "dataset_version": GOVERNED_VERSION,
        "status": "PASS",
        "counts": {
            "train": len(governed_train),
            "dev": len(governed_dev),
            "calibration": len(calibration),
            "independent_validation": len(independent_rows),
            "train_groups": len(train_groups),
            "dev_groups": len(dev_groups),
            "calibration_groups": len(cal_groups),
            "independent_validation_groups": len(ind_groups),
        },
        "checks": checks,
        "overlap_counts": {
            "train_dev_samples": len(train_ids & dev_ids),
            "calibration_train_samples":
                len(cal_ids & train_ids),
            "calibration_dev_samples":
                len(cal_ids & dev_ids),
            "independent_train_samples":
                len(ind_ids & train_ids),
            "independent_dev_samples":
                len(ind_ids & dev_ids),
            "independent_calibration_samples":
                len(ind_ids & cal_ids),
            "independent_train_groups":
                len(ind_groups & train_groups),
            "independent_dev_groups":
                len(ind_groups & dev_groups),
            "independent_calibration_groups":
                len(ind_groups & cal_groups),
        },
    }

    write_json(
        OUT / "leakage_audit.json",
        obj,
    )
    return obj


def build_closeout_report(
    governed: dict[str, Any],
    leakage: dict[str, Any],
    independent_info: dict[str, Any],
) -> None:
    report = {
        "schema_version": "1.0",
        "closeout_id": "b1_closeout_v1",
        "status": "PASS",
        "b1_state": {
            "B1_DATA_CLOSEOUT": "PASS",
            "DATA_COLLECTION": "PAUSED",
            "HISTORICAL_RELEASES": "IMMUTABLE",
            "CALIBRATION_V1": "FROZEN",
            "INDEPENDENT_VALIDATION": "FROZEN",
            "FROZEN_TEST": "NOT_ASSIGNED_BY_B1",
            "GOVERNED_DATASET": "FROZEN",
        },
        "governed_counts": governed["aggregate_counts"],
        "independent_validation": {
            "dataset_version": IV_VERSION,
            "samples": 240,
            "groups": 240,
            "case_set_digest":
                independent_info["case_set_digest"],
        },
        "required_b1_artifacts": {
            "governed_release_manifest": True,
            "gap300_provenance_binding": True,
            "ms34_teacher_provenance_addendum": True,
            "teacher_provenance_registry": True,
            "calibration_identity": True,
            "independent_validation_case_manifest": True,
            "independent_validation_case_set_digest": True,
            "leakage_audit": leakage["status"] == "PASS",
        },
        "scope_note": (
            "This closes B1 data/provenance/governance work only. "
            "No B2 evaluation or gate decision is asserted."
        ),
    }

    write_json(
        OUT / "B1_CLOSEOUT_REPORT.json",
        report,
    )


def write_handoff() -> None:
    text = f"""# B1 Data Closeout Handoff

## Status

`B1_DATA_CLOSEOUT = PASS`

B1 data collection is paused. Historical releases remain immutable.

## Governed identities

- Governed Train: **6037**
- Governed Dev: **1158**
- Calibration v1: **300 samples / 300 groups**
- Independent Validation v1: **240 samples / 240 groups**
- Frozen Test: **NOT_ASSIGNED_BY_B1**

## Independent Validation

Dataset version: `{IV_VERSION}`

The set is exactly:

`D2 v1.1 reserved_test_candidates (540) - Calibration v1 (300)`

No additional ranking, relabeling, or sampling was applied.

It must not be used for A3 training, development tuning,
hyperparameter selection, or error-driven iteration.

## Gap300

The immutable Gap300 release is not modified.

Its historical provenance is supplemented through the existing
Gap300 provenance addendum and Teacher provenance attestation.
`attestations/gap300_provenance_binding.json` binds those artifacts
to the release hashes.

## MS34 3-step / 4-step supplement

`b1_ms34_supplement_v1` is included in the governed dataset:

- Train positive: 30
- Dev positive: 4
- Hard negative: 1
- 3-step positives: 17
- 4-step positives: 17

Its release remains immutable. A separate Teacher provenance
addendum clarifies that recorded `metadata.teacher_git_sha` is the
acquisition/runtime checkout identity and is not silently rewritten
as the canonical pinned Teacher identity.

## Teacher policy

Historical releases preserve their recorded provenance.

Future formal Teacher work must use the current pinned Teacher policy
bound by `challenge/teacher_pinned_manifest_v4.json`.

## Primary files

- `governed_release_manifest.json`
- `teacher_provenance_registry.json`
- `calibration_identity.json`
- `leakage_audit.json`
- `independent_validation_v1/case_manifest.json`
- `independent_validation_v1/case_set_digest.json`
- `independent_validation_v1/dataset_identity.json`
- `B1_CLOSEOUT_REPORT.json`
- `SHA256SUMS`

This handoff makes no B2 accuracy or gate claim.
"""
    (OUT / "B1_HANDOFF.md").write_text(
        text,
        encoding="utf-8",
    )


def write_hashes() -> None:
    files = sorted(
        p for p in OUT.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS"
    )

    lines = []
    for p in files:
        rel = p.relative_to(OUT)
        lines.append(f"{sha256_file(p)}  {rel}")

    (OUT / "SHA256SUMS").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)

    IV.mkdir(parents=True)
    ATTEST.mkdir(parents=True)

    teacher_policy = current_teacher_policy()

    independent_rows, independent_info = (
        build_independent_validation()
    )

    build_gap300_binding()
    build_ms34_teacher_addendum(teacher_policy)
    build_calibration_identity(independent_info)

    governed = build_governed_manifest()
    build_teacher_registry(teacher_policy)

    leakage = build_global_leakage_audit(
        independent_rows
    )

    build_closeout_report(
        governed,
        leakage,
        independent_info,
    )

    write_handoff()
    write_hashes()

    # Final existence/content gate
    required = [
        OUT / "governed_release_manifest.json",
        OUT / "teacher_provenance_registry.json",
        OUT / "calibration_identity.json",
        OUT / "leakage_audit.json",
        OUT / "B1_CLOSEOUT_REPORT.json",
        OUT / "B1_HANDOFF.md",
        OUT / "SHA256SUMS",
        ATTEST / "gap300_provenance_binding.json",
        ATTEST / "ms34_teacher_provenance_addendum.json",
        IV / "cases.jsonl",
        IV / "case_manifest.json",
        IV / "case_set_digest.json",
        IV / "dataset_identity.json",
        IV / "source_release_binding.json",
        IV / "README.md",
    ]

    missing = [
        str(p.relative_to(ROOT))
        for p in required
        if not p.is_file()
    ]

    if missing:
        raise RuntimeError(
            f"missing closeout artifacts: {missing}"
        )

    print("===== B1 CLOSEOUT V1 BUILD =====")
    print("governed train              = 6037")
    print("governed dev                = 1158")
    print("calibration samples         = 300")
    print("calibration groups          = 300")
    print("independent validation      = 240")
    print("independent groups          = 240")
    print("frozen test                 = NOT_ASSIGNED_BY_B1")
    print("Gap300 provenance binding   = PASS")
    print("MS34 provenance addendum    = PASS")
    print("global leakage audit        = PASS")
    print(
        "case_set_digest             =",
        independent_info["case_set_digest"],
    )
    print("B1_DATA_CLOSEOUT            = PASS")
    print("BUILD                       = PASS")


if __name__ == "__main__":
    main()
