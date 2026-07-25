"""Validate multimodal JSONL records without third-party dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

SCHEMA_VERSION = "1.0.0"
SPLITS = {"train", "val", "test"}
LEVELS = {"command_only", "perception", "decision", "closed_loop"}
ACTIONS = {
    "START",
    "STOP",
    "SET_SPEED",
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "AVOID_OBJECT",
    "EMERGENCY_BRAKE",
    "RETURN_TO_LANE",
    "REQUEST_CONFIRMATION",
}
REQUIRED_TOP_LEVEL = {
    "schema_version",
    "sample_id",
    "sequence_id",
    "split",
    "data_level",
    "source",
    "frame",
    "sensors",
    "language",
    "ego",
    "environment",
    "perception",
    "decision",
    "safety",
    "control",
    "expected",
    "metrics",
    "quality",
    "provenance",
}


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    has_windows_drive = bool(path.parts) and ":" in path.parts[0]
    return (
        bool(value)
        and not path.is_absolute()
        and not has_windows_drive
        and ".." not in path.parts
    )


def _iter_media_paths(record: dict[str, Any]) -> Iterable[tuple[str, str]]:
    sensors = record.get("sensors", {})
    for name in ("rgb_front", "lidar_roof", "audio"):
        ref = sensors.get(name)
        if isinstance(ref, dict) and isinstance(ref.get("path"), str):
            yield f"sensors.{name}.path", ref["path"]
    raw_path = record.get("decision", {}).get("raw_output_path")
    if isinstance(raw_path, str):
        yield "decision.raw_output_path", raw_path


def validate_record(record: Any, line_number: int) -> list[str]:
    prefix = f"line {line_number}"
    if not isinstance(record, dict):
        return [f"{prefix}: record must be an object"]

    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - record.keys())
    if missing:
        errors.append(f"{prefix}: missing top-level fields: {', '.join(missing)}")

    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}: schema_version must be {SCHEMA_VERSION}")
    if not isinstance(record.get("sample_id"), str) or not record.get("sample_id"):
        errors.append(f"{prefix}: sample_id must be a non-empty string")
    if not isinstance(record.get("sequence_id"), str) or not record.get("sequence_id"):
        errors.append(f"{prefix}: sequence_id must be a non-empty string")
    if record.get("split") not in SPLITS:
        errors.append(f"{prefix}: split must be one of {sorted(SPLITS)}")
    if record.get("data_level") not in LEVELS:
        errors.append(f"{prefix}: data_level must be one of {sorted(LEVELS)}")

    frame = record.get("frame", {})
    if not isinstance(frame.get("frame_id"), int) or frame.get("frame_id", -1) < 0:
        errors.append(f"{prefix}: frame.frame_id must be a non-negative integer")
    if not isinstance(frame.get("timestamp_ns"), int) or frame.get("timestamp_ns", -1) < 0:
        errors.append(f"{prefix}: frame.timestamp_ns must be a non-negative integer")

    sensors = record.get("sensors", {})
    presence = sensors.get("presence", {})
    rgb_required = record.get("data_level") in {"perception", "decision", "closed_loop"}
    if rgb_required and not isinstance(sensors.get("rgb_front"), dict):
        errors.append(f"{prefix}: sensors.rgb_front is required")
    for name in ("rgb_front", "lidar_roof", "audio"):
        expected = presence.get(name)
        actual = isinstance(sensors.get(name), dict)
        if not isinstance(expected, bool):
            errors.append(f"{prefix}: sensors.presence.{name} must be boolean")
        elif expected != actual:
            errors.append(f"{prefix}: sensors.presence.{name} does not match media reference")

    for field, value in _iter_media_paths(record):
        if not _safe_relative_path(value):
            errors.append(f"{prefix}: {field} must be a safe relative path")

    language = record.get("language", {})
    confidence = language.get("asr_confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append(f"{prefix}: language.asr_confidence must be in [0, 1]")

    for container_name, field_name in (
        ("decision", "requested_actions"),
        ("control", "final_actions"),
        ("expected", "actions"),
    ):
        actions = record.get(container_name, {}).get(field_name)
        if not isinstance(actions, list):
            errors.append(f"{prefix}: {container_name}.{field_name} must be an array")
            continue
        for index, action in enumerate(actions):
            value = action.get("action") if isinstance(action, dict) else None
            if value not in ACTIONS:
                errors.append(
                    f"{prefix}: {container_name}.{field_name}[{index}] has invalid action {value!r}"
                )

    quality = record.get("quality", {})
    if quality.get("eligible_for_score") and record.get("data_level") != "closed_loop":
        errors.append(f"{prefix}: only closed_loop records may be eligible_for_score")
    if quality.get("eligible_for_score") and not frame.get("synchronized"):
        errors.append(f"{prefix}: scoring records must have synchronized=true")
    return errors


def validate_dataset(
    jsonl_path: Path,
    *,
    dataset_root: Path | None = None,
    check_files: bool = False,
) -> list[str]:
    errors: list[str] = []
    sample_ids: set[str] = set()
    sequence_splits: dict[str, str] = {}

    with jsonl_path.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
                continue

            errors.extend(validate_record(record, line_number))
            if not isinstance(record, dict):
                continue

            sample_id = record.get("sample_id")
            if isinstance(sample_id, str):
                if sample_id in sample_ids:
                    errors.append(f"line {line_number}: duplicate sample_id {sample_id!r}")
                sample_ids.add(sample_id)

            sequence_id = record.get("sequence_id")
            split = record.get("split")
            if isinstance(sequence_id, str) and split in SPLITS:
                previous = sequence_splits.setdefault(sequence_id, split)
                if previous != split:
                    errors.append(
                        f"line {line_number}: sequence {sequence_id!r} leaks across {previous}/{split}"
                    )

            if check_files:
                if dataset_root is None:
                    errors.append("dataset_root is required when check_files is enabled")
                    check_files = False
                else:
                    for field, relative in _iter_media_paths(record):
                        if _safe_relative_path(relative) and not (dataset_root / relative).is_file():
                            errors.append(f"line {line_number}: missing file for {field}: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--check-files", action="store_true")
    args = parser.parse_args()

    errors = validate_dataset(
        args.jsonl,
        dataset_root=args.dataset_root,
        check_files=args.check_files,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print(f"PASS: {args.jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
