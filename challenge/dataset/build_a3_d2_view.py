"""Derive strict positive A3 supervision from B1's signed D2 v1.1 release.

The signed B1 files remain immutable. The derived view records every exclusion
and the manifest used to fill cohort-level pinned model provenance.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from challenge.dataset.validate_d2_release import canonical_text_sha256, validate_release


VIEW_VERSION = "b1_d2_v1_1_a3_strict_positive_v1"
COHORTS = {
    "teacher_distill_v0.2_d1_pinned": (
        "2f04764d7eb08ed78ef81eadca8ddeae3c427392",
        "challenge/teacher_baseline_manifest.json",
    ),
    "teacher_distill_v0.3_d2_expansion_wave1_v3": (
        "1a363c15b9b1790534358c11acbd100a3011fa93",
        "challenge/teacher_pinned_manifest.json",
    ),
    "teacher_distill_v0.4_d2_expansion_wave2_v4": (
        "95e97b00def8ec36f12937da34ce8bb9082c4a04",
        "challenge/teacher_pinned_manifest_v4.json",
    ),
    "teacher_distill_v0.5_d3_expansion_wave1_v4": (
        "95e97b00def8ec36f12937da34ce8bb9082c4a04",
        "challenge/teacher_pinned_manifest_v4.json",
    ),
    "teacher_distill_v0.6_d3_expansion_wave2_targeted_v4_sync_v1": (
        "252984d37e49ddc11eaddcde2bfb26d0d6f2086b",
        "challenge/teacher_pinned_manifest_wave2_sync_v1.json",
    ),
}


def _rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")


def _cohort_identity(repo: Path, row: dict[str, Any]) -> dict[str, str]:
    version = str(row.get("dataset_version"))
    if version not in COHORTS:
        raise ValueError(f"unsupported source cohort: {version}")
    collection_sha, manifest_rel = COHORTS[version]
    metadata = row["metadata"]
    if metadata.get("teacher_git_sha") != collection_sha:
        raise ValueError(f"{row['sample_id']}: collection Teacher SHA mismatch")
    manifest_path = repo / manifest_rel
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    baseline_sha = manifest.get("git_sha") or manifest.get("teacher_git_sha")
    model_id = manifest["model_id"]
    revision = manifest["model_revision"]
    fingerprint = manifest.get("artifact_fingerprint_sha256") or manifest["model_artifact_sha256"]
    if metadata.get("teacher_baseline_git_sha", baseline_sha) != baseline_sha:
        raise ValueError(f"{row['sample_id']}: baseline Teacher SHA mismatch")
    if (metadata.get("teacher_model_id") or row["teacher_plan"].get("model_id")) != model_id:
        raise ValueError(f"{row['sample_id']}: Teacher model ID mismatch")
    if metadata.get("teacher_model_revision", revision) != revision:
        raise ValueError(f"{row['sample_id']}: Teacher model revision mismatch")
    recorded_fingerprint = (
        metadata.get("teacher_artifact_fingerprint_sha256")
        or metadata.get("teacher_model_artifact_sha256")
    )
    if recorded_fingerprint is not None and recorded_fingerprint != fingerprint:
        raise ValueError(f"{row['sample_id']}: Teacher artifact fingerprint mismatch")
    return {
        "baseline_sha": baseline_sha,
        "model_id": model_id,
        "model_revision": revision,
        "artifact_fingerprint_sha256": fingerprint,
        "manifest_path": manifest_rel,
        "manifest_sha256": canonical_text_sha256(manifest_path),
    }


def _exclusion_reason(row: dict[str, Any]) -> str | None:
    quality = row.get("quality") or {}
    if quality.get("training_role") == "HARD_NEGATIVE" or quality.get("valid_for_training") is False:
        return "B1_HARD_NEGATIVE"
    if quality.get("valid_for_training") is not True:
        raise ValueError(f"{row['sample_id']}: missing positive training eligibility")
    loop = row.get("closed_loop_quality") or {}
    if (
        loop.get("run_status") != "SUCCEEDED"
        or loop.get("command_terminal_status") != "SUCCEEDED"
        or loop.get("plan_terminal_state") != "SUCCEEDED"
        or loop.get("scenario_acceptance_passed") is not True
    ):
        return "A3_STRICT_TERMINAL_NON_SUCCESS"
    return None


def build_view(release_dir: Path, output_dir: Path) -> dict[str, Any]:
    release_dir = release_dir.resolve()
    repo = release_dir.parents[3]
    release_check = validate_release(release_dir)
    if not release_check["valid"] or release_check["authoritative_manifest"] != "release_manifest.json":
        raise ValueError("B1 signed release integrity gate must pass before A3 view generation")
    release_manifest_path = release_dir / "release_manifest.json"
    kept: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    excluded: list[dict[str, str]] = []
    cohort_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    manifest_sources: dict[str, str] = {}
    for split in ("train", "val"):
        for row in _rows(release_dir / f"{split}.jsonl"):
            identity = _cohort_identity(repo, row)
            reason = _exclusion_reason(row)
            if reason is not None:
                excluded.append({"sample_id": row["sample_id"], "split": split, "reason": reason})
                reason_counts[f"{split}:{reason}"] += 1
                continue
            metadata = dict(row["metadata"])
            metadata["source_dataset_version"] = row["dataset_version"]
            metadata["dataset_version"] = VIEW_VERSION
            metadata["split"] = split
            metadata["teacher_baseline_git_sha"] = identity["baseline_sha"]
            metadata["teacher_model_revision"] = identity["model_revision"]
            metadata["teacher_artifact_fingerprint_sha256"] = identity["artifact_fingerprint_sha256"]
            metadata["teacher_provenance_manifest"] = identity["manifest_path"]
            metadata["teacher_provenance_manifest_sha256"] = identity["manifest_sha256"]
            derived = dict(row)
            derived["metadata"] = metadata
            kept[split].append(derived)
            cohort_counts[f"{split}:{row['dataset_version']}"] += 1
            manifest_sources[identity["manifest_path"]] = identity["manifest_sha256"]
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"
    excluded_path = output_dir / "excluded_sample_ids.jsonl"
    _write_jsonl(train_path, kept["train"])
    _write_jsonl(val_path, kept["val"])
    _write_jsonl(excluded_path, excluded)
    result = {
        "view_version": VIEW_VERSION,
        "source_release_manifest_sha256": canonical_text_sha256(release_manifest_path),
        "source_release_dir": str(release_dir),
        "cohort_manifest_shas": dict(sorted(manifest_sources.items())),
        "counts": {
            "train": len(kept["train"]), "val": len(kept["val"]),
            "excluded": len(excluded),
        },
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "exclusion_reasons": dict(sorted(reason_counts.items())),
        "files": {
            path.name: {"sha256": canonical_text_sha256(path), "bytes": path.stat().st_size}
            for path in (train_path, val_path, excluded_path)
        },
    }
    (output_dir / "a3_view_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build A3 strict-positive D2 view")
    parser.add_argument("--release-dir", type=Path, default=Path("challenge/dataset/releases/d2_v1_1"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/a3_d2_v1_1_positive_view_v1"))
    args = parser.parse_args()
    print(json.dumps(build_view(args.release_dir, args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
