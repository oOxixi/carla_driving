"""Deterministic A2 calibration release builder and tensor loader.

The checked-in D2 Train split is sufficient for a development PTQ smoke run.
It is not a B1/B2-signed formal Calibration release, so this module labels the
derived package accordingly and never silently promotes it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import numpy as np

from challenge.student.preprocess import StudentPreprocessor


PROTECTED_SPLIT_MARKERS = ("test", "reserved", "benchmark", "official_like")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSONL at {path}:{number}: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"record at {path}:{number} must be an object")
            rows.append(value)
    return rows


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, values: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
            for value in values
        ),
        encoding="utf-8",
    )


def _request_of(record: Mapping[str, Any]) -> Mapping[str, Any]:
    request = record.get("model_request", record.get("input"))
    if not isinstance(request, Mapping):
        raise ValueError(f"sample {record.get('sample_id')} has no ModelRequest object")
    return request


def _primary_class(record: Mapping[str, Any]) -> str:
    value = record.get("sample_class", "UNKNOWN")
    if isinstance(value, Mapping):
        value = value.get("primary", "UNKNOWN")
    return str(value).upper()


def _first_behavior(record: Mapping[str, Any]) -> str:
    plan = record.get("teacher_plan")
    if not isinstance(plan, Mapping):
        teacher = record.get("teacher")
        if isinstance(teacher, Mapping):
            plan = teacher.get("maneuver_plan")
    if isinstance(plan, Mapping):
        steps = plan.get("steps")
        if isinstance(steps, list) and steps and isinstance(steps[0], Mapping):
            return str(steps[0].get("behavior", "UNKNOWN")).upper()
    return "UNKNOWN"


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    return True


def _rank(seed: int, sample_id: str) -> str:
    return hashlib.sha256(f"{seed}:{sample_id}".encode("utf-8")).hexdigest()


def _round_robin_strata(
    rows: Sequence[dict[str, Any]], count: int, seed: int
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in rows:
        request = _request_of(record)
        summary = request.get("scene_summary")
        risk = str(summary.get("risk_level", "UNKNOWN")) if isinstance(summary, Mapping) else "UNKNOWN"
        buckets[(_primary_class(record), risk.upper(), _first_behavior(record))].append(record)
    for values in buckets.values():
        values.sort(key=lambda item: _rank(seed, str(item["sample_id"])))
    ordered_keys = sorted(buckets, key=lambda item: _rank(seed, "|".join(item)))
    selected: list[dict[str, Any]] = []
    while len(selected) < count:
        progressed = False
        for key in ordered_keys:
            if buckets[key]:
                selected.append(buckets[key].pop(0))
                progressed = True
                if len(selected) == count:
                    break
        if not progressed:
            break
    return selected


def build_development_calibration(
    repo_root: str | Path,
    *,
    source_jsonl: str | Path,
    output_directory: str | Path,
    count: int = 400,
    seed: int = 20260923,
) -> dict[str, Any]:
    """Build a reproducible Train-only development calibration candidate."""
    repo = Path(repo_root).resolve()
    source = (repo / source_jsonl).resolve() if not Path(source_jsonl).is_absolute() else Path(source_jsonl)
    relative_source = source.relative_to(repo).as_posix()
    if any(marker in relative_source.lower() for marker in PROTECTED_SPLIT_MARKERS):
        raise ValueError("calibration source must not be Test/reserved/benchmark data")
    rows = _read_jsonl(source)
    if count < 1 or count > len(rows):
        raise ValueError(f"count must be within 1..{len(rows)}")

    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in rows:
        sample_id = str(record.get("sample_id", "")).strip()
        reasons: list[str] = []
        if not sample_id or sample_id in seen:
            reasons.append("MISSING_OR_DUPLICATE_SAMPLE_ID")
        seen.add(sample_id)
        if not _finite(record):
            reasons.append("NON_FINITE_VALUE")
        try:
            request = _request_of(record)
            rgb_ref = request.get("rgb_ref")
            rgb_path = (repo / str(rgb_ref)).resolve() if rgb_ref else None
            if rgb_path is None or not rgb_path.is_file():
                reasons.append("RGB_MISSING")
            else:
                expected = (record.get("visual_input") or {}).get("rgb_sha256")
                if expected and sha256_file(rgb_path) != expected:
                    reasons.append("RGB_SHA256_MISMATCH")
        except (TypeError, ValueError):
            reasons.append("INVALID_MODEL_REQUEST")
        if reasons:
            rejected.append({"sample_id": sample_id, "reasons": ",".join(reasons)})
        else:
            valid.append(record)
    if len(valid) < count:
        raise ValueError(f"only {len(valid)} valid records remain; requested {count}")

    selected = _round_robin_strata(valid, count, seed)
    output = (repo / output_directory).resolve() if not Path(output_directory).is_absolute() else Path(output_directory)
    data_path = output / "calibration.jsonl"
    _write_jsonl(data_path, selected)
    source_release = source.parent / "release_manifest.json"
    class_counts = Counter(_primary_class(item) for item in selected)
    behavior_counts = Counter(_first_behavior(item) for item in selected)
    scenario_counts = Counter(str((item.get("metadata") or {}).get("scenario_family", "UNKNOWN")) for item in selected)
    risk_counts = Counter(str(_request_of(item).get("scene_summary", {}).get("risk_level", "UNKNOWN")) for item in selected)
    manifest = {
        "schema_version": "1.0",
        "calibration_id": f"a2-dev-calibration-{count}-seed-{seed}",
        "status": "A2_DEVELOPMENT_CALIBRATION_CANDIDATE",
        "formal_release": False,
        "scope_note": "Derived only from B1 D2 Train for PTQ development. Requires B1/B2 sign-off before formal use.",
        "source": {
            "jsonl": relative_source,
            "jsonl_sha256": sha256_file(source),
            "release_manifest": source_release.relative_to(repo).as_posix() if source_release.is_file() else None,
            "release_manifest_sha256": sha256_file(source_release) if source_release.is_file() else None,
            "protected_split_used": False,
        },
        "selection": {
            "algorithm": "deterministic_round_robin(sample_class,risk_level,first_behavior)",
            "seed": seed,
            "requested": count,
            "selected": len(selected),
            "valid_source_records": len(valid),
            "rejected_source_records": len(rejected),
        },
        "coverage": {
            "sample_class": dict(sorted(class_counts.items())),
            "first_behavior": dict(sorted(behavior_counts.items())),
            "risk_level": dict(sorted(risk_counts.items())),
            "scenario_family": dict(sorted(scenario_counts.items())),
        },
        "calibration_jsonl": data_path.relative_to(repo).as_posix(),
        "calibration_jsonl_sha256": sha256_file(data_path),
        "sample_ids": [str(item["sample_id"]) for item in selected],
        "rejections": rejected,
    }
    _write_json(output / "calibration_manifest.json", manifest)
    return manifest


@dataclass
class CalibrationDataset:
    """Load calibration JSONL through the exact production preprocessor."""

    repo_root: Path
    jsonl_path: Path
    records: list[dict[str, Any]]

    @classmethod
    def open(cls, repo_root: str | Path, jsonl_path: str | Path) -> "CalibrationDataset":
        repo = Path(repo_root).resolve()
        path = (repo / jsonl_path).resolve() if not Path(jsonl_path).is_absolute() else Path(jsonl_path)
        return cls(repo, path, _read_jsonl(path))

    def requests(self) -> Iterator[dict[str, Any]]:
        for record in self.records:
            request = deepcopy(dict(_request_of(record)))
            rgb_ref = request.get("rgb_ref")
            if not rgb_ref:
                raise ValueError(f"sample {record.get('sample_id')} has no rgb_ref")
            rgb_path = (self.repo_root / str(rgb_ref)).resolve()
            if not rgb_path.is_file():
                raise ValueError(f"sample {record.get('sample_id')} RGB missing: {rgb_ref}")
            request["rgb_ref"] = str(rgb_path)
            yield request

    def feeds(self) -> Iterator[dict[str, np.ndarray]]:
        preprocessor = StudentPreprocessor()
        for request in self.requests():
            tensors = preprocessor(request)
            yield {
                "rgb": tensors.rgb.numpy().astype(np.float32, copy=False),
                "text_tokens": tensors.text_tokens.numpy().astype(np.float32, copy=False),
                "targets": tensors.targets.numpy().astype(np.float32, copy=False),
                "state": tensors.state.numpy().astype(np.float32, copy=False),
            }


class OrtCalibrationReader:
    """Minimal onnxruntime CalibrationDataReader implementation."""

    def __init__(self, dataset: CalibrationDataset) -> None:
        self._dataset = dataset
        self.rewind()

    def get_next(self) -> dict[str, np.ndarray] | None:
        return next(self._iterator, None)

    def rewind(self) -> None:
        self._iterator = iter(self._dataset.feeds())


__all__ = [
    "CalibrationDataset", "OrtCalibrationReader", "build_development_calibration", "sha256_file",
]
