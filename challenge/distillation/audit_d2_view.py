"""Read-only label and coverage audit for the signed B1 D2 A3 view."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

from challenge.dataset.build_a3_d2_view import VIEW_VERSION
from challenge.dataset.validate_d2_release import canonical_text_sha256, validate_release

from .dataset import _sample_class, load_jsonl
from .label_encoder import (
    BEHAVIORS, COMPLETION_TYPES, FAILURE_ACTIONS, TARGET_LANES,
    DistillationLabelEncoder,
)


def summarize_split(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Count training labels without reading protected Test candidates."""
    encoder = DistillationLabelEncoder()
    classes: Counter[str] = Counter()
    families: Counter[str] = Counter()
    scenario_ids: Counter[str] = Counter()
    maps: Counter[str] = Counter()
    cohorts: Counter[str] = Counter()
    behaviors: Counter[str] = Counter()
    target_lanes: Counter[str] = Counter()
    completion_types: Counter[str] = Counter()
    failure_actions: Counter[str] = Counter()
    plan_lengths: Counter[str] = Counter()
    class_family: Counter[str] = Counter()
    class_scenario: Counter[str] = Counter()
    active_steps = speed_labels = pointer_labels = replan_labels = 0
    for row in rows:
        metadata = row["metadata"]
        sample_class = _sample_class(row)
        if sample_class not in {"normal", "complex", "safety_critical"}:
            raise ValueError(f"unsupported sample class: {sample_class}")
        request = row.get("input", row.get("model_request"))
        teacher = row.get("teacher")
        plan = teacher.get("maneuver_plan") if isinstance(teacher, Mapping) else None
        plan = plan or row.get("teacher_plan") or row.get("maneuver_plan")
        labels = encoder.encode(request, plan)
        family = str(metadata.get("scenario_family") or "UNKNOWN")
        scenario_id = str(metadata.get("scenario_id") or "UNKNOWN")
        classes[sample_class] += 1
        families[family] += 1
        scenario_ids[scenario_id] += 1
        maps[str(metadata.get("map") or "UNKNOWN")] += 1
        cohorts[str(metadata.get("source_dataset_version") or "UNKNOWN")] += 1
        class_family[f"{sample_class}:{family}"] += 1
        class_scenario[f"{sample_class}:{scenario_id}"] += 1
        length = sum(labels["step_mask"])
        plan_lengths[str(length)] += 1
        active_steps += length
        for index, active in enumerate(labels["step_mask"]):
            if not active:
                continue
            behaviors[BEHAVIORS[labels["behavior"][index]]] += 1
            target_lanes[TARGET_LANES[labels["target_lane"][index]]] += 1
            completion_types[COMPLETION_TYPES[labels["completion_type"][index]]] += 1
            failure_actions[FAILURE_ACTIONS[labels["on_failure"][index]]] += 1
            speed_labels += int(labels["target_speed_mask"][index])
            pointer_labels += int(labels["target_pointer"][index] != encoder.max_targets)
        replan_labels += sum(bool(value) for value in labels["replan_conditions"])
    return {
        "samples": len(rows),
        "sample_classes": dict(sorted(classes.items())),
        "scenario_families": dict(sorted(families.items())),
        "scenario_ids": dict(sorted(scenario_ids.items())),
        "maps": dict(sorted(maps.items())),
        "source_cohorts": dict(sorted(cohorts.items())),
        "class_by_family": dict(sorted(class_family.items())),
        "class_by_scenario": dict(sorted(class_scenario.items())),
        "plan_lengths": dict(sorted(plan_lengths.items())),
        "behavior_steps": dict(sorted(behaviors.items())),
        "missing_behavior_labels": sorted(set(BEHAVIORS) - set(behaviors)),
        "target_lane_steps": dict(sorted(target_lanes.items())),
        "missing_target_lane_labels": sorted(set(TARGET_LANES) - set(target_lanes)),
        "completion_type_steps": dict(sorted(completion_types.items())),
        "missing_completion_type_labels": sorted(set(COMPLETION_TYPES) - set(completion_types)),
        "failure_action_steps": dict(sorted(failure_actions.items())),
        "missing_failure_action_labels": sorted(set(FAILURE_ACTIONS) - set(failure_actions)),
        "active_steps": active_steps,
        "speed_labeled_steps": speed_labels,
        "grounded_pointer_steps": pointer_labels,
        "positive_replan_conditions": replan_labels,
    }


def audit_view(release_dir: Path, view_dir: Path) -> dict[str, Any]:
    """Fail closed on changed inputs; report coverage, not model quality."""
    release_dir = release_dir.resolve()
    view_dir = view_dir.resolve()
    release = validate_release(release_dir)
    if not release["valid"] or release["authoritative_manifest"] != "release_manifest.json":
        raise ValueError("B1 signed release validation failed")
    manifest = json.loads((view_dir / "a3_view_manifest.json").read_text(encoding="utf-8"))
    if json.loads((release_dir / "release_manifest.json").read_text(encoding="utf-8")).get("status") != "B1_SIGNED_PASS":
        raise ValueError("B1 release is not signed")
    if manifest.get("view_version") != VIEW_VERSION:
        raise ValueError("A3 view version mismatch")
    if manifest.get("source_release_manifest_sha256") != canonical_text_sha256(
        release_dir / "release_manifest.json"
    ):
        raise ValueError("A3 view was not derived from this signed B1 release")
    for name, details in manifest["files"].items():
        if canonical_text_sha256(view_dir / name) != details["sha256"]:
            raise ValueError(f"A3 view file changed: {name}")
    repo = release_dir.parents[3]
    for relative, expected_sha in manifest["cohort_manifest_shas"].items():
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo) or canonical_text_sha256(path) != expected_sha:
            raise ValueError(f"Teacher cohort manifest changed: {relative}")

    splits = {}
    split_ids: dict[str, set[str]] = {}
    for split in ("train", "val"):
        rows = load_jsonl(view_dir / f"{split}.jsonl")
        ids = [str(row["sample_id"]) for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate {split} sample ID")
        if any(row.get("metadata", {}).get("split") != split for row in rows):
            raise ValueError(f"A3 {split} contains a mismatched split label")
        if any(row.get("metadata", {}).get("dataset_version") != VIEW_VERSION for row in rows):
            raise ValueError(f"A3 {split} contains a mismatched dataset version")
        if len(rows) != manifest["counts"][split]:
            raise ValueError(f"A3 {split} count differs from view manifest")
        splits[split] = summarize_split(rows)
        split_ids[split] = set(ids)
    if split_ids["train"] & split_ids["val"]:
        raise ValueError("A3 Train and Val sample IDs overlap")
    excluded_rows = load_jsonl(view_dir / "excluded_sample_ids.jsonl")
    excluded_ids = [str(row["sample_id"]) for row in excluded_rows]
    if len(set(excluded_ids)) != len(excluded_ids):
        raise ValueError("duplicate A3 excluded sample ID")
    if set(excluded_ids) & (split_ids["train"] | split_ids["val"]):
        raise ValueError("excluded sample reentered A3 supervision")
    if len(excluded_rows) != manifest["counts"]["excluded"]:
        raise ValueError("excluded count differs from view manifest")
    for split in ("train", "val"):
        release_ids = {
            str(row["sample_id"])
            for row in load_jsonl(release_dir / f"{split}.jsonl")
        }
        excluded_split = {
            str(row["sample_id"]) for row in excluded_rows if row["split"] == split
        }
        if release_ids != split_ids[split] | excluded_split:
            raise ValueError(f"A3 retained/excluded IDs do not partition B1 {split}")
    return {
        "status": "PASS",
        "release_manifest_sha256": manifest["source_release_manifest_sha256"],
        "view_manifest_sha256": canonical_text_sha256(view_dir / "a3_view_manifest.json"),
        "view_version": VIEW_VERSION,
        "splits": splits,
        "excluded_count": len(excluded_rows),
        "exclusion_reasons": manifest["exclusion_reasons"],
        "note": "Coverage only; no Student accuracy or Teacher comparison is implied.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit signed D2 A3 label coverage")
    parser.add_argument("--release-dir", type=Path, default=Path("challenge/dataset/releases/d2_v1_1"))
    parser.add_argument("--view-dir", type=Path, default=Path("artifacts/a3_d2_v1_1_positive_view_v1"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/a3_d2_prep/label_coverage.json"))
    args = parser.parse_args()
    report = audit_view(args.release_dir, args.view_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
