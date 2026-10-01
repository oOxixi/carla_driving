"""Build the A3 strict-positive view bound to B1 data closeout v1.

The B1 governed inventory contains 6,037 Train and 1,158 development rows.
Optimizer supervision remains strict-positive: the prior 5,826/1,104 view is
extended only with the 30/4 successful MS34 rows.  The one failed MS34 run is
retained as audit-only evidence and never relabelled as success.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from challenge.dataset.build_a3_cumulative_view import (
    _relative,
    _rows,
    _write_jsonl,
    canonical_json_sha256,
)
from challenge.dataset.build_a3_final_cumulative_view import (
    DEFAULT_D2_RELEASE,
    DEFAULT_D3_RELEASE,
    DEFAULT_D3_WAVE2_RELEASE,
    DEFAULT_GAP300_RELEASE,
    DEFAULT_TARGETED_GAP_RELEASE,
    DEFAULT_TURN_GAP_RELEASE,
    FINAL_VIEW_VERSION,
    build_final_cumulative_view,
)
from challenge.dataset.validate_d2_release import canonical_text_sha256
CLOSEOUT_VIEW_VERSION = "b1_governed_closeout_v1_a3_strict_positive_v1"
MS34_VERSION = "b1_ms34_supplement_v1"
DEFAULT_MS34_RELEASE = "challenge/dataset/releases/b1_ms34_supplement_v1"
DEFAULT_CLOSEOUT = "challenge/dataset/governance/b1_closeout_v1"
DEFAULT_OUTPUT = "artifacts/a3_b1_closeout_positive_view_v1"
MS34_ADDENDUM = (
    "challenge/dataset/governance/b1_closeout_v1/attestations/"
    "ms34_teacher_provenance_addendum.json"
)
TEACHER_REGISTRY = (
    "challenge/dataset/governance/b1_closeout_v1/teacher_provenance_registry.json"
)
GOVERNED_MANIFEST = (
    "challenge/dataset/governance/b1_closeout_v1/governed_release_manifest.json"
)
EXPECTED_SEQUENCES = {
    3: ("AVOID_OBSTACLE", "RETURN_TO_LANE", "KEEP_LANE"),
    4: ("YIELD", "AVOID_OBSTACLE", "RETURN_TO_LANE", "KEEP_LANE"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_size(path: Path) -> int:
    return len(path.read_bytes().replace(b"\r\n", b"\n"))


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _verify_closeout(repo: Path, closeout_dir: Path) -> dict[str, Any]:
    """Verify B1's signed-by-ledger closeout without importing A2/torch code."""
    ledger_path = closeout_dir / "SHA256SUMS"
    ledger: dict[str, str] = {}
    for line_number, raw in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.strip().split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError(f"invalid B1 closeout ledger line {line_number}")
        digest, name = parts
        relative = Path(name.strip())
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe B1 closeout ledger path: {name}")
        path = (closeout_dir / relative).resolve()
        if not path.is_relative_to(closeout_dir) or not path.is_file():
            raise ValueError(f"missing B1 closeout ledger target: {name}")
        if canonical_text_sha256(path) != digest:
            raise ValueError(f"B1 closeout ledger SHA mismatch: {name}")
        ledger[relative.as_posix()] = digest
    required = {
        "B1_CLOSEOUT_REPORT.json",
        "governed_release_manifest.json",
        "leakage_audit.json",
        "teacher_provenance_registry.json",
        "attestations/ms34_teacher_provenance_addendum.json",
    }
    if not required.issubset(ledger):
        raise ValueError(f"B1 closeout ledger is incomplete: {sorted(required - set(ledger))}")
    report = _read_object(closeout_dir / "B1_CLOSEOUT_REPORT.json")
    governed = _read_object(closeout_dir / "governed_release_manifest.json")
    leakage = _read_object(closeout_dir / "leakage_audit.json")
    registry = _read_object(closeout_dir / "teacher_provenance_registry.json")
    addendum = _read_object(closeout_dir / "attestations/ms34_teacher_provenance_addendum.json")
    if report.get("status") != "PASS" or report.get("b1_state", {}).get("B1_DATA_CLOSEOUT") != "PASS":
        raise ValueError("B1 data closeout is not PASS")
    if governed.get("status") != "B1_GOVERNED_RELEASE_SET":
        raise ValueError("B1 governed release set is not frozen")
    if leakage.get("status") != "PASS" or not all(leakage.get("checks", {}).values()):
        raise ValueError("B1 closeout leakage audit is not PASS")
    if registry.get("status") != "PASS":
        raise ValueError("B1 Teacher provenance registry is not PASS")
    if addendum.get("status") != "PASS_WITH_RUNTIME_IDENTITY_LIMITATION":
        raise ValueError("B1 MS34 provenance limitation is not preserved")
    if addendum.get("historical_release_mutated") is not False or addendum.get("sample_rows_rewritten") is not False:
        raise ValueError("B1 MS34 historical rows were unexpectedly rewritten")
    counts = governed.get("aggregate_counts")
    if counts != report.get("governed_counts"):
        raise ValueError("B1 closeout governed counts disagree")
    return {
        "closeout_id": report.get("closeout_id"),
        "dataset_version": governed.get("dataset_version"),
        "governed_counts": counts,
        "governed_release": governed,
        "governed_release_manifest_sha256": ledger["governed_release_manifest.json"],
    }


def _verify_binding(repo: Path, binding: Mapping[str, Any]) -> str:
    if binding.get("available") is not True:
        raise ValueError("B1 governed MS34 binding is unavailable")
    relative = str(binding.get("path") or "")
    path = repo / relative
    if not path.is_file():
        raise ValueError(f"B1 governed MS34 binding is missing: {relative}")
    expected_sha = str(binding.get("sha256") or "")
    if canonical_text_sha256(path) != expected_sha:
        raise ValueError(f"B1 governed MS34 binding SHA mismatch: {relative}")
    if _canonical_size(path) != binding.get("size_bytes"):
        raise ValueError(f"B1 governed MS34 binding size mismatch: {relative}")
    return expected_sha


def _verify_ms34_release(
    repo: Path,
    release_dir: Path,
    governed: Mapping[str, Any],
    *,
    check_images: bool,
) -> dict[str, Any]:
    releases = governed.get("releases")
    if not isinstance(releases, list):
        raise ValueError("B1 governed release manifest has no releases")
    matches = [
        item for item in releases
        if isinstance(item, Mapping) and item.get("release_id") == MS34_VERSION
    ]
    if len(matches) != 1:
        raise ValueError("B1 governed release manifest must contain exactly one MS34 release")
    entry = matches[0]
    if entry.get("role") != "TRAIN_DEV_ADDON":
        raise ValueError("B1 governed MS34 role is not TRAIN_DEV_ADDON")
    if entry.get("counts") != {"dev": 4, "hard_negative": 1, "train": 30}:
        raise ValueError("B1 governed MS34 counts changed")
    if (repo / str(entry.get("release_path"))).resolve() != release_dir:
        raise ValueError("B1 governed MS34 release path mismatch")

    bindings = entry.get("bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("B1 governed MS34 bindings are missing")
    binding_shas = {
        name: _verify_binding(repo, bindings[name])
        for name in (
            "content_bound_pass",
            "governance_report",
            "provenance_manifest",
            "release_manifest",
            "split_manifest",
        )
    }
    release = _read_object(release_dir / "release_manifest.json")
    governance = _read_object(release_dir / "governance_report.json")
    content_pass = _read_object(release_dir / "B1_CONTENT_BOUND_PASS.json")
    if release.get("dataset_version") != MS34_VERSION:
        raise ValueError("MS34 release version mismatch")
    if governance.get("status") != "PASS" or content_pass.get("status") != "PASS":
        raise ValueError("MS34 release governance is not PASS")
    if release.get("counts") != {
        "hard_negative_addition": 1,
        "images": 35,
        "source_runs": 35,
        "strict_positive_runs": 34,
        "strict_positive_samples": 34,
        "train_addition": 30,
        "val_addition": 4,
    }:
        raise ValueError("MS34 release manifest counts changed")

    for name, record in release.get("files", {}).items():
        path = release_dir / str(name)
        if not path.is_file():
            raise ValueError(f"MS34 release file is missing: {name}")
        if canonical_text_sha256(path) != record.get("sha256"):
            raise ValueError(f"MS34 release file SHA mismatch: {name}")
        if _canonical_size(path) != record.get("size_bytes"):
            raise ValueError(f"MS34 release file size mismatch: {name}")
    if check_images:
        entries = release.get("image_set", {}).get("entries", {})
        if len(entries) != 35:
            raise ValueError("MS34 image inventory changed")
        for name, expected_sha in entries.items():
            path = release_dir / "images" / str(name)
            if not path.is_file() or _sha256(path) != expected_sha:
                raise ValueError(f"MS34 RGB integrity failure: {name}")
    return {
        "release_manifest_sha256": binding_shas["release_manifest"],
        "binding_shas": binding_shas,
        "content_binding_sha256": content_pass["binding"]["sha256"],
        "signature_status": content_pass["signature_status"],
    }


def _restamp_base(row: dict[str, Any], *, split: str) -> dict[str, Any]:
    metadata = dict(row["metadata"])
    metadata["dataset_version"] = CLOSEOUT_VIEW_VERSION
    metadata["split"] = split
    derived = dict(row)
    derived["metadata"] = metadata
    return derived


def _derive_ms34(row: dict[str, Any], *, split: str, repo: Path) -> dict[str, Any]:
    quality = row.get("quality") or {}
    closed_loop = row.get("closed_loop_quality") or {}
    if quality.get("training_role") != "POSITIVE" or quality.get("valid_for_training") is not True:
        raise ValueError(f"{row.get('sample_id')}: non-positive MS34 row entered supervision")
    required_terminal = {
        "run_status": "SUCCEEDED",
        "command_terminal_status": "SUCCEEDED",
        "plan_terminal_state": "SUCCEEDED",
        "scenario_acceptance_passed": True,
        "route_deviation_count": 0,
    }
    for field, expected in required_terminal.items():
        if closed_loop.get(field) != expected:
            raise ValueError(f"{row.get('sample_id')}: MS34 terminal field {field} failed")
    metadata = dict(row.get("metadata") or {})
    if metadata.get("teacher_model_id") != "Qwen/Qwen3.5-2B":
        raise ValueError(f"{row.get('sample_id')}: MS34 Teacher model mismatch")
    if metadata.get("teacher_mode") != "planner_v2":
        raise ValueError(f"{row.get('sample_id')}: MS34 Teacher mode mismatch")
    steps = list((row.get("teacher_plan") or {}).get("steps") or ())
    expected_sequence = EXPECTED_SEQUENCES.get(len(steps))
    actual_sequence = tuple(str(step.get("behavior")) for step in steps)
    if expected_sequence is None or actual_sequence != expected_sequence:
        raise ValueError(f"{row.get('sample_id')}: unexpected MS34 plan sequence")
    metadata.update({
        "source_dataset_version": str(row.get("dataset_version") or MS34_VERSION),
        "source_view_version": MS34_VERSION,
        "dataset_version": CLOSEOUT_VIEW_VERSION,
        "split": split,
        "teacher_provenance_class": "HISTORICAL_RUNTIME_IDENTITY_CONTENT_BOUND",
        "teacher_provenance_addendum": MS34_ADDENDUM,
        "teacher_provenance_addendum_sha256": canonical_text_sha256(repo / MS34_ADDENDUM),
    })
    derived = dict(row)
    derived["metadata"] = metadata
    return derived


def build_closeout_cumulative_view(
    d2_release_dir: Path,
    d3_wave1_release_dir: Path,
    d3_wave2_release_dir: Path,
    targeted_gap_release_dir: Path,
    turn_gap_release_dir: Path,
    gap300_release_dir: Path,
    ms34_release_dir: Path,
    closeout_dir: Path,
    output_dir: Path,
    *,
    check_images: bool = True,
) -> dict[str, Any]:
    source_dirs = [
        path.resolve() for path in (
            d2_release_dir,
            d3_wave1_release_dir,
            d3_wave2_release_dir,
            targeted_gap_release_dir,
            turn_gap_release_dir,
            gap300_release_dir,
            ms34_release_dir,
        )
    ]
    repo = source_dirs[0].parents[3]
    if any(path.parents[3] != repo for path in source_dirs[1:]):
        raise ValueError("all closeout source releases must belong to the same repository")
    closeout_dir = closeout_dir.resolve()
    if closeout_dir != (repo / DEFAULT_CLOSEOUT).resolve():
        raise ValueError("A3 formal closeout view must use canonical b1_closeout_v1")
    closeout = _verify_closeout(repo, closeout_dir)
    governed_counts = closeout["governed_counts"]
    if governed_counts.get("train") != 6037 or governed_counts.get("dev") != 1158:
        raise ValueError("B1 governed Train/Dev counts changed")
    ms34_evidence = _verify_ms34_release(
        repo, source_dirs[-1], closeout["governed_release"], check_images=check_images,
    )

    with tempfile.TemporaryDirectory(prefix="a3-closeout-base-") as temporary:
        base_dir = Path(temporary)
        base_manifest = build_final_cumulative_view(
            *source_dirs[:-1], base_dir, check_images=check_images,
        )
        base_rows = {
            split: _rows(base_dir / f"{split}.jsonl") for split in ("train", "val")
        }
        excluded = _rows(base_dir / "excluded_sample_ids.jsonl")
        base_manifest_sha = canonical_text_sha256(base_dir / "a3_final_view_manifest.json")

    kept: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    cohort_counts: Counter[str] = Counter()
    plan_lengths: Counter[int] = Counter()
    for split in ("train", "val"):
        for row in base_rows[split]:
            derived = _restamp_base(row, split=split)
            kept[split].append(derived)
            cohort_counts[f"{split}:{derived['metadata']['source_dataset_version']}"] += 1
            plan_lengths[len(derived["teacher_plan"]["steps"])] += 1
        name = "train_addition.jsonl" if split == "train" else "val_addition.jsonl"
        for row in _rows(source_dirs[-1] / name):
            derived = _derive_ms34(row, split=split, repo=repo)
            kept[split].append(derived)
            cohort_counts[f"{split}:{MS34_VERSION}"] += 1
            plan_lengths[len(derived["teacher_plan"]["steps"])] += 1

    hard_rows = _rows(source_dirs[-1] / "hard_negative_addition.jsonl")
    if len(hard_rows) != 1:
        raise ValueError("MS34 hard-negative count changed")
    hard = hard_rows[0]
    quality = hard.get("quality") or {}
    closed_loop = hard.get("closed_loop_quality") or {}
    if (
        quality.get("training_role") != "HARD_NEGATIVE"
        or quality.get("valid_for_training") is not False
        or closed_loop.get("run_status") != "FAILED"
        or closed_loop.get("route_deviation_count", 0) < 1
        or closed_loop.get("scenario_acceptance_passed") is not False
    ):
        raise ValueError("MS34 hard negative lost its failed closed-loop evidence")
    excluded.append({
        "dataset_version": CLOSEOUT_VIEW_VERSION,
        "reason": "B1_MS34_CLOSED_LOOP_ROUTE_DEVIATION",
        "sample_id": str(hard["sample_id"]),
        "source_dataset_version": MS34_VERSION,
        "split": "audit_only",
    })

    split_ids: dict[str, set[str]] = {}
    split_groups: dict[str, set[str]] = {}
    for split, rows in kept.items():
        ids = [str(row["sample_id"]) for row in rows]
        groups = [str(row["metadata"].get("group_key") or "") for row in rows]
        if len(ids) != len(set(ids)) or not all(groups):
            raise ValueError(f"invalid or duplicate {split} identity in closeout view")
        split_ids[split] = set(ids)
        split_groups[split] = set(groups)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("closeout Train and Validation sample IDs overlap")
    if split_groups["train"] & split_groups["val"]:
        raise ValueError("closeout Train and Validation groups overlap")
    excluded_ids = [str(row["sample_id"]) for row in excluded]
    if len(excluded_ids) != len(set(excluded_ids)):
        raise ValueError("duplicate excluded sample ID in closeout view")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("audit-only sample reentered closeout supervision")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "train": output_dir / "train.jsonl",
        "val": output_dir / "val.jsonl",
        "excluded": output_dir / "excluded_sample_ids.jsonl",
    }
    _write_jsonl(paths["train"], kept["train"])
    _write_jsonl(paths["val"], kept["val"])
    _write_jsonl(paths["excluded"], excluded)

    closeout_files = (
        "challenge/dataset/governance/b1_closeout_v1/B1_CLOSEOUT_REPORT.json",
        GOVERNED_MANIFEST,
        "challenge/dataset/governance/b1_closeout_v1/leakage_audit.json",
        TEACHER_REGISTRY,
        MS34_ADDENDUM,
        "challenge/dataset/governance/b1_closeout_v1/SHA256SUMS",
    )
    ms34_files = (
        "B1_CONTENT_BOUND_PASS.json",
        "governance_report.json",
        "provenance_manifest.json",
        "release_manifest.json",
        "split_manifest.json",
        "train_addition.jsonl",
        "val_addition.jsonl",
        "hard_negative_addition.jsonl",
    )
    manifests = dict(base_manifest["cohort_manifest_shas"])
    manifests.update({relative: canonical_text_sha256(repo / relative) for relative in closeout_files})
    manifests.update({
        _relative(repo, source_dirs[-1] / name): canonical_text_sha256(source_dirs[-1] / name)
        for name in ms34_files
    })
    source_evidence = {
        "prior_final_view": {
            "view_version": FINAL_VIEW_VERSION,
            "view_manifest_sha256": base_manifest_sha,
            "source_evidence_sha256": base_manifest["source_evidence_sha256"],
            "d2_release_manifest_sha256": canonical_text_sha256(
                source_dirs[0] / "release_manifest.json"
            ),
            "gap300_teacher_attestation_sha256": base_manifest["source_evidence"][
                "gap300"
            ]["teacher_attestation_sha256"],
            "derived_file_sha256": {
                name: base_manifest["files"][name]["sha256"]
                for name in ("train.jsonl", "val.jsonl", "excluded_sample_ids.jsonl")
            },
        },
        "b1_closeout": {
            "closeout_id": closeout["closeout_id"],
            "dataset_version": closeout["dataset_version"],
            "governed_counts": governed_counts,
            "governed_release_manifest_path": GOVERNED_MANIFEST,
            "governed_release_manifest_sha256": closeout[
                "governed_release_manifest_sha256"
            ],
            "teacher_provenance_registry_path": TEACHER_REGISTRY,
            "teacher_provenance_registry_sha256": canonical_text_sha256(repo / TEACHER_REGISTRY),
        },
        "ms34": {
            "release_dir": _relative(repo, source_dirs[-1]),
            **ms34_evidence,
            "teacher_provenance_addendum_path": MS34_ADDENDUM,
            "teacher_provenance_addendum_sha256": canonical_text_sha256(repo / MS34_ADDENDUM),
            "teacher_provenance_status": "PASS_WITH_RUNTIME_IDENTITY_LIMITATION",
        },
    }
    result = {
        "schema_version": "1.0",
        "view_version": CLOSEOUT_VIEW_VERSION,
        "source_evidence": source_evidence,
        "source_evidence_sha256": canonical_json_sha256(source_evidence),
        "cohort_manifest_shas": dict(sorted(manifests.items())),
        "counts": {
            "raw_governed_train": governed_counts["train"],
            "raw_governed_dev": governed_counts["dev"],
            "train": len(kept["train"]),
            "val": len(kept["val"]),
            "excluded": len(excluded),
            "ms34_train_addition": 30,
            "ms34_val_addition": 4,
            "ms34_hard_negative": 1,
        },
        "count_policy": {
            "raw_release_rows_are_not_optimizer_rows": True,
            "governed_train_rows_excluded_from_optimizer": governed_counts["train"] - len(kept["train"]),
            "governed_dev_rows_excluded_from_optimizer": governed_counts["dev"] - len(kept["val"]),
            "all_hard_negatives_audit_only": True,
        },
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "plan_length_sample_counts": {
            str(length): plan_lengths[length] for length in (1, 2, 3, 4)
        },
        "files": {
            path.name: {"sha256": canonical_text_sha256(path), "bytes": _canonical_size(path)}
            for path in paths.values()
        },
        "policies": {
            "calibration_used": False,
            "independent_validation_used": False,
            "reserved_test_used": False,
            "frozen_test_used": False,
            "ms34_hard_negative_used_for_supervision": False,
            "ms34_runtime_identity_limitation_preserved": True,
            "historical_rows_rewritten": False,
        },
    }
    expected_counts = {"train": 5856, "val": 1108, "excluded": 540}
    for key, expected in expected_counts.items():
        if result["counts"][key] != expected:
            raise ValueError(f"closeout view {key} count changed: {result['counts'][key]} != {expected}")
    if result["plan_length_sample_counts"]["3"] != 17:
        raise ValueError("closeout view must contain exactly 17 three-step samples")
    if result["plan_length_sample_counts"]["4"] != 17:
        raise ValueError("closeout view must contain exactly 17 four-step samples")
    (output_dir / "a3_closeout_view_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d2-release-dir", type=Path, default=Path(DEFAULT_D2_RELEASE))
    parser.add_argument("--d3-wave1-release-dir", type=Path, default=Path(DEFAULT_D3_RELEASE))
    parser.add_argument("--d3-wave2-release-dir", type=Path, default=Path(DEFAULT_D3_WAVE2_RELEASE))
    parser.add_argument("--targeted-gap-release-dir", type=Path, default=Path(DEFAULT_TARGETED_GAP_RELEASE))
    parser.add_argument("--turn-gap-release-dir", type=Path, default=Path(DEFAULT_TURN_GAP_RELEASE))
    parser.add_argument("--gap300-release-dir", type=Path, default=Path(DEFAULT_GAP300_RELEASE))
    parser.add_argument("--ms34-release-dir", type=Path, default=Path(DEFAULT_MS34_RELEASE))
    parser.add_argument("--closeout-dir", type=Path, default=Path(DEFAULT_CLOSEOUT))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--skip-images", action="store_true")
    args = parser.parse_args()
    report = build_closeout_cumulative_view(
        args.d2_release_dir,
        args.d3_wave1_release_dir,
        args.d3_wave2_release_dir,
        args.targeted_gap_release_dir,
        args.turn_gap_release_dir,
        args.gap300_release_dir,
        args.ms34_release_dir,
        args.closeout_dir,
        args.output_dir,
        check_images=not args.skip_images,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
