"""Fail-closed dataset checks before A3 reads production supervision.

The preflight is intentionally independent from training.  It validates every
record against the frozen request/plan contracts, audits split provenance, and
detects identity or byte-for-byte leakage between Train and Validation.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .label_encoder import BEHAVIORS, DistillationLabelEncoder


PROTECTED_SPLIT_TOKENS = ("test", "frozen")


def is_protected_split(value: object) -> bool:
    normalized = str(value or "").strip().lower()
    return any(token in normalized for token in PROTECTED_SPLIT_TOKENS)


def preflight_datasets(
    train_path: str | Path,
    val_path: str | Path,
    *,
    max_steps: int = 4,
    max_targets: int = 8,
    expected_version: str | None = None,
    expected_teacher_git_sha: str | None = None,
    expected_teacher_model_id: str | None = None,
    expected_teacher_model_revision: str | None = None,
    expected_teacher_artifact_fingerprint_sha256: str | None = None,
    asset_root: str | Path | None = None,
    require_rgb: bool = False,
    max_errors: int = 100,
) -> dict[str, Any]:
    """Return an auditable report; callers must reject ``valid == False``."""
    if max_errors < 1:
        raise ValueError("max_errors must be positive")
    encoder = DistillationLabelEncoder(max_steps=max_steps, max_targets=max_targets)
    resolved_assets = Path(asset_root).resolve() if asset_root else None
    train = _scan_path(
        Path(train_path), "train", encoder, expected_version, max_errors,
        expected_teacher_git_sha, expected_teacher_model_id, resolved_assets, require_rgb,
        expected_teacher_model_revision,
        expected_teacher_artifact_fingerprint_sha256,
    )
    validation = _scan_path(
        Path(val_path), "validation", encoder, expected_version, max_errors,
        expected_teacher_git_sha, expected_teacher_model_id, resolved_assets, require_rgb,
        expected_teacher_model_revision,
        expected_teacher_artifact_fingerprint_sha256,
    )
    errors = [*train.pop("errors"), *validation.pop("errors")]
    warnings = [*train.pop("warnings"), *validation.pop("warnings")]

    for field, label in (
        ("sample_ids", "sample_id"),
        ("request_ids", "request_id"),
        ("record_hashes", "canonical record"),
        ("group_keys", "group_key"),
    ):
        overlap = sorted(set(train[field]).intersection(validation[field]))
        if overlap:
            errors.append({
                "code": "CROSS_SPLIT_OVERLAP",
                "message": f"Train/Validation share {len(overlap)} {label}(s)",
                "examples": overlap[:10],
            })

    report = {
        "valid": not errors,
        "train_path": str(Path(train_path).resolve()),
        "validation_path": str(Path(val_path).resolve()),
        "expected_dataset_version": expected_version,
        "expected_teacher_identity": {
            "git_sha": expected_teacher_git_sha,
            "model_id": expected_teacher_model_id,
            "model_revision": expected_teacher_model_revision,
            "artifact_fingerprint_sha256": (
                expected_teacher_artifact_fingerprint_sha256
            ),
        },
        "train": _public_stats(train),
        "validation": _public_stats(validation),
        "errors": errors[:max_errors],
        "error_count": len(errors),
        "warnings": warnings,
        "warning_count": len(warnings),
    }
    return report


def write_preflight_report(path: str | Path, report: Mapping[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(dict(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def _scan_path(
    path: Path,
    split: str,
    encoder: DistillationLabelEncoder,
    expected_version: str | None,
    max_errors: int,
    expected_teacher_git_sha: str | None,
    expected_teacher_model_id: str | None,
    asset_root: Path | None,
    require_rgb: bool,
    expected_teacher_model_revision: str | None,
    expected_teacher_artifact_fingerprint_sha256: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "records": 0,
        "valid_records": 0,
        "sample_classes": Counter(),
        "behaviors": Counter(),
        "plan_lengths": Counter(),
        "target_counts": Counter(),
        "dataset_versions": Counter(),
        "sample_ids": [],
        "request_ids": [],
        "record_hashes": [],
        "group_keys": [],
        "errors": [],
        "warnings": [],
    }
    if is_protected_split(path.name):
        result["errors"].append({
            "code": "PROTECTED_SPLIT_PATH",
            "path": str(path),
            "message": "A3 refuses paths whose filename identifies frozen Test data",
        })
    if not path.is_file():
        result["errors"].append({
            "code": "FILE_NOT_FOUND", "path": str(path), "message": "file not found",
        })
        return result

    seen_sample_ids: set[str] = set()
    seen_request_ids: set[str] = set()
    seen_hashes: set[str] = set()
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, 1):
            if not raw.strip():
                continue
            result["records"] += 1
            if len(result["errors"]) >= max_errors:
                continue
            try:
                record = json.loads(raw)
                if not isinstance(record, dict):
                    raise ValueError("record must be a JSON object")
                inspected = _inspect_record(
                    record, split, encoder, expected_version,
                    expected_teacher_git_sha, expected_teacher_model_id,
                    asset_root, require_rgb,
                    expected_teacher_model_revision,
                    expected_teacher_artifact_fingerprint_sha256,
                )
            except (KeyError, TypeError, ValueError) as error:
                result["errors"].append({
                    "code": "INVALID_RECORD",
                    "path": str(path),
                    "line": line_number,
                    "message": str(error),
                })
                continue
            result["valid_records"] += 1
            for name in (
                "sample_classes", "behaviors", "plan_lengths", "target_counts",
                "dataset_versions",
            ):
                result[name].update(inspected[name])
            for value, seen, field, code in (
                (inspected["sample_id"], seen_sample_ids, "sample_ids", "DUPLICATE_SAMPLE_ID"),
                (inspected["request_id"], seen_request_ids, "request_ids", "DUPLICATE_REQUEST_ID"),
                (inspected["record_hash"], seen_hashes, "record_hashes", "DUPLICATE_RECORD"),
            ):
                if value in seen:
                    result["errors"].append({
                        "code": code, "path": str(path), "line": line_number,
                        "message": f"duplicate value: {value}",
                    })
                seen.add(value)
                result[field].append(value)
            if inspected["group_key"]:
                result["group_keys"].append(inspected["group_key"])
            result["warnings"].extend(
                {"path": str(path), "line": line_number, **item}
                for item in inspected["warnings"]
            )
    if result["records"] == 0:
        result["errors"].append({
            "code": "EMPTY_DATASET", "path": str(path), "message": "no records",
        })
    return result


def _inspect_record(
    record: Mapping[str, Any],
    split: str,
    encoder: DistillationLabelEncoder,
    expected_version: str | None,
    expected_teacher_git_sha: str | None,
    expected_teacher_model_id: str | None,
    asset_root: Path | None,
    require_rgb: bool,
    expected_teacher_model_revision: str | None,
    expected_teacher_artifact_fingerprint_sha256: str | None,
) -> dict[str, Any]:
    sample_id = str(record.get("sample_id", "")).strip()
    if not sample_id:
        raise ValueError("sample_id is required for traceability")
    metadata = record.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata must be an object")
    declared_split = str(metadata.get("split", "")).strip()
    if is_protected_split(declared_split):
        raise ValueError("record metadata identifies frozen Test data")
    warnings = []
    if not declared_split:
        warnings.append({"code": "MISSING_SPLIT", "message": "metadata.split is missing"})
    elif not _split_matches(declared_split, split):
        raise ValueError(
            f"metadata.split={declared_split!r} does not match {split!r} manifest"
        )
    version = str(metadata.get("dataset_version") or record.get("dataset_version") or "UNKNOWN")
    if expected_version and version != expected_version:
        raise ValueError(
            f"dataset_version={version!r} does not match expected {expected_version!r}"
        )
    request = record.get("input", record.get("model_request"))
    if not isinstance(request, Mapping):
        raise ValueError("record.input must contain ModelRequest V1")
    teacher = record.get("teacher")
    plan = teacher.get("maneuver_plan") if isinstance(teacher, Mapping) else None
    if plan is None:
        plan = record.get("maneuver_plan")
    if plan is None:
        plan = record.get("teacher_plan")
    if not isinstance(plan, Mapping):
        raise ValueError("record.teacher.maneuver_plan must contain ManeuverPlan V2")
    labels = encoder.encode(request, plan)
    # New pinned B1 data separates the frozen Teacher baseline from the
    # collection worktree SHA. Prefer that unambiguous field while retaining
    # the historical Smoke field as a compatibility fallback.
    teacher_sha = str(
        metadata.get("teacher_baseline_git_sha")
        or metadata.get("teacher_git_sha")
        or ""
    )
    teacher_model = str(metadata.get("teacher_model_id") or plan.get("model_id") or "")
    provenance = record.get("teacher_provenance", {})
    if not isinstance(provenance, Mapping):
        raise ValueError("teacher_provenance must be an object when present")
    teacher_revision = str(
        metadata.get("teacher_model_revision")
        or provenance.get("model_revision")
        or provenance.get("teacher_model_revision")
        or ""
    )
    teacher_fingerprint = str(
        metadata.get("teacher_artifact_fingerprint_sha256")
        or metadata.get("teacher_model_artifact_sha256")
        or provenance.get("artifact_fingerprint_sha256")
        or provenance.get("model_artifact_sha256")
        or provenance.get("teacher_artifact_fingerprint_sha256")
        or ""
    )
    if expected_teacher_git_sha and teacher_sha != expected_teacher_git_sha:
        raise ValueError(f"teacher_git_sha={teacher_sha!r} does not match expected")
    if expected_teacher_model_id and teacher_model != expected_teacher_model_id:
        raise ValueError(f"teacher_model_id={teacher_model!r} does not match expected")
    if expected_teacher_model_revision and teacher_revision != expected_teacher_model_revision:
        raise ValueError(
            f"teacher_model_revision={teacher_revision!r} does not match expected"
        )
    if (
        expected_teacher_artifact_fingerprint_sha256
        and teacher_fingerprint != expected_teacher_artifact_fingerprint_sha256
    ):
        raise ValueError(
            "teacher_artifact_fingerprint_sha256 does not match expected"
        )
    quality = record.get("quality", {})
    if isinstance(quality, Mapping) and quality.get("schema_valid") is False:
        raise ValueError("quality.schema_valid is false")
    if isinstance(quality, Mapping) and quality.get("valid_for_training") is False:
        raise ValueError("quality.valid_for_training is false")
    policy = record.get("training_policy", {})
    if isinstance(policy, Mapping) and policy and policy.get("train_eligible") is not True:
        raise ValueError("training_policy.train_eligible must be true")
    if isinstance(quality, Mapping) and quality.get("closed_loop_success") is False:
        warnings.append({
            "code": "CLOSED_LOOP_FAILURE",
            "message": "quality.closed_loop_success is false; review before training",
        })
    declared_class = record.get("sample_class")
    if isinstance(declared_class, Mapping):
        declared_class = declared_class.get("primary")
    sample_class = str(declared_class or metadata.get("sample_class") or (
        "safety_critical"
        if isinstance(quality, Mapping) and quality.get("safety_critical") is True
        else "normal"
    ))
    sample_class = sample_class.strip().lower()
    if sample_class not in {"normal", "complex", "safety_critical"}:
        raise ValueError(f"unsupported sample_class: {sample_class!r}")
    _validate_rgb(record, asset_root, require_rgb)
    _validate_recorded_pointers(record, labels)
    active_behaviors = [BEHAVIORS[value] for value, active in zip(
        labels["behavior"], labels["step_mask"], strict=True,
    ) if active]
    canonical = json.dumps(
        dict(record), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return {
        "sample_id": sample_id,
        "request_id": str(request["request_id"]),
        "record_hash": hashlib.sha256(canonical).hexdigest(),
        "group_key": str(metadata.get("group_key", "")).strip(),
        "sample_classes": Counter((sample_class,)),
        "behaviors": Counter(active_behaviors),
        "plan_lengths": Counter((str(sum(labels["step_mask"])),)),
        "target_counts": Counter((str(len(request.get("targets", ()))),)),
        "dataset_versions": Counter((version,)),
        "warnings": warnings,
    }


def _split_matches(declared: str, expected: str) -> bool:
    normalized = declared.strip().lower()
    if expected == "validation":
        return normalized in {"val", "valid", "validation", "dev"}
    return normalized in {"train", "training"}


def _public_stats(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: dict(sorted(item.items())) if isinstance(item, Counter) else item
        for key, item in value.items()
        if key not in {"sample_ids", "request_ids", "record_hashes", "group_keys"}
    }


def _validate_rgb(
    record: Mapping[str, Any], asset_root: Path | None, require_rgb: bool,
) -> None:
    visual = record.get("visual_input")
    if not isinstance(visual, Mapping) or not visual.get("rgb_sha256"):
        if require_rgb:
            raise ValueError("visual_input.rgb_sha256 is required")
        return
    if asset_root is None:
        if require_rgb:
            raise ValueError("asset_root is required for packaged RGB")
        return
    digest = str(visual["rgb_sha256"]).lower()
    candidates = [asset_root / f"{digest}{suffix}" for suffix in (".jpg", ".jpeg", ".png")]
    image = next((candidate for candidate in candidates if candidate.is_file()), None)
    if image is None:
        raise ValueError(f"packaged RGB is missing for sha256={digest}")
    if hashlib.sha256(image.read_bytes()).hexdigest() != digest:
        raise ValueError(f"packaged RGB hash mismatch for {image}")
    if visual.get("size_bytes") is not None and image.stat().st_size != int(visual["size_bytes"]):
        raise ValueError(f"packaged RGB size mismatch for {image}")


def _validate_recorded_pointers(
    record: Mapping[str, Any], labels: Mapping[str, Any],
) -> None:
    targets = record.get("student_targets")
    if not isinstance(targets, Mapping):
        return
    if int(targets.get("target_top_k", 8)) != 8 or int(targets.get("no_target_index", 8)) != 8:
        raise ValueError("B1 target pointer contract does not match A1 max_targets=8")
    recorded = targets.get("steps", ())
    if not isinstance(recorded, list):
        raise ValueError("student_targets.steps must be a list")
    expected = [value for value, active in zip(
        labels["target_pointer"], labels["step_mask"], strict=True,
    ) if active]
    actual = [int(step["target_pointer"]) for step in recorded]
    if actual != expected:
        raise ValueError(f"recorded target pointers {actual} do not match encoded {expected}")
    if targets.get("target_outside_topk") is True or targets.get("invalid_target_id") is True:
        raise ValueError("invalid or outside-TopK target cannot enter ordinary supervision")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate A3 Train/Validation JSONL")
    parser.add_argument("--train", required=True)
    parser.add_argument("--val", required=True)
    parser.add_argument("--dataset-version")
    parser.add_argument("--teacher-git-sha")
    parser.add_argument("--teacher-model-id")
    parser.add_argument("--teacher-model-revision")
    parser.add_argument("--teacher-artifact-fingerprint-sha256")
    parser.add_argument("--asset-root")
    parser.add_argument("--require-rgb", action="store_true")
    parser.add_argument("--max-steps", type=int, default=4)
    parser.add_argument("--max-targets", type=int, default=8)
    parser.add_argument("--max-errors", type=int, default=100)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = preflight_datasets(
        args.train, args.val, max_steps=args.max_steps, max_targets=args.max_targets,
        expected_version=args.dataset_version,
        expected_teacher_git_sha=args.teacher_git_sha,
        expected_teacher_model_id=args.teacher_model_id,
        expected_teacher_model_revision=args.teacher_model_revision,
        expected_teacher_artifact_fingerprint_sha256=(
            args.teacher_artifact_fingerprint_sha256
        ),
        asset_root=args.asset_root, require_rgb=args.require_rgb,
        max_errors=args.max_errors,
    )
    if args.output:
        write_preflight_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["is_protected_split", "preflight_datasets", "write_preflight_report"]
