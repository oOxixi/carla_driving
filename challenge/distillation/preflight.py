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
    max_errors: int = 100,
) -> dict[str, Any]:
    """Return an auditable report; callers must reject ``valid == False``."""
    if max_errors < 1:
        raise ValueError("max_errors must be positive")
    encoder = DistillationLabelEncoder(max_steps=max_steps, max_targets=max_targets)
    train = _scan_path(
        Path(train_path), "train", encoder, expected_version, max_errors,
    )
    validation = _scan_path(
        Path(val_path), "validation", encoder, expected_version, max_errors,
    )
    errors = [*train.pop("errors"), *validation.pop("errors")]
    warnings = [*train.pop("warnings"), *validation.pop("warnings")]

    for field, label in (
        ("sample_ids", "sample_id"),
        ("request_ids", "request_id"),
        ("record_hashes", "canonical record"),
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
                inspected = _inspect_record(record, split, encoder, expected_version)
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
    version = str(metadata.get("dataset_version", "UNKNOWN"))
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
    if not isinstance(plan, Mapping):
        raise ValueError("record.teacher.maneuver_plan must contain ManeuverPlan V2")
    labels = encoder.encode(request, plan)
    quality = record.get("quality", {})
    if isinstance(quality, Mapping) and quality.get("schema_valid") is False:
        raise ValueError("quality.schema_valid is false")
    if isinstance(quality, Mapping) and quality.get("closed_loop_success") is False:
        warnings.append({
            "code": "CLOSED_LOOP_FAILURE",
            "message": "quality.closed_loop_success is false; review before training",
        })
    sample_class = str(metadata.get("sample_class") or (
        "safety_critical"
        if isinstance(quality, Mapping) and quality.get("safety_critical") is True
        else "normal"
    ))
    if sample_class not in {"normal", "complex", "safety_critical"}:
        raise ValueError(f"unsupported sample_class: {sample_class!r}")
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
        if key not in {"sample_ids", "request_ids", "record_hashes"}
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate A3 Train/Validation JSONL")
    parser.add_argument("--train", required=True)
    parser.add_argument("--val", required=True)
    parser.add_argument("--dataset-version")
    parser.add_argument("--max-steps", type=int, default=4)
    parser.add_argument("--max-targets", type=int, default=8)
    parser.add_argument("--max-errors", type=int, default=100)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = preflight_datasets(
        args.train, args.val, max_steps=args.max_steps, max_targets=args.max_targets,
        expected_version=args.dataset_version, max_errors=args.max_errors,
    )
    if args.output:
        write_preflight_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["is_protected_split", "preflight_datasets", "write_preflight_report"]
