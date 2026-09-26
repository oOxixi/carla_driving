"""Canonical B2 benchmark-manifest construction and hashing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class BenchmarkManifestError(ValueError):
    """Raised when a formal B2 benchmark identity cannot be signed."""


def build_benchmark_manifest(
    config: Mapping[str, Any],
    case_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Build a formal benchmark manifest from a frozen case manifest.

    Current WAITING_FOR_INDEPENDENT_VALIDATION configuration must fail
    closed. A formal manifest may be built only after the benchmark and
    case-set identity have both been frozen.
    """
    if not isinstance(config, Mapping):
        raise BenchmarkManifestError(
            "benchmark config must be an object"
        )

    if config.get("status") != "FROZEN":
        raise BenchmarkManifestError(
            "benchmark configuration is not frozen"
        )

    dataset = _required_mapping(
        config,
        "dataset",
    )

    case_manifest_path = _required_text(
        dataset.get("case_manifest_path"),
        "dataset.case_manifest_path",
    )

    if dataset.get("independence_required") is not True:
        raise BenchmarkManifestError(
            "formal benchmark must require independence"
        )

    if dataset.get("development_val_allowed") is not False:
        raise BenchmarkManifestError(
            "Development Val must remain forbidden"
        )

    if dataset.get("frozen_test_allowed") is not False:
        raise BenchmarkManifestError(
            "Frozen Test must remain forbidden for A3 FP32 Gate"
        )

    if not isinstance(case_manifest, Mapping):
        raise BenchmarkManifestError(
            "case manifest must be an object"
        )

    benchmark_id = _required_text(
        config.get("benchmark_id"),
        "benchmark_id",
    )
    dataset_version = _required_text(
        dataset.get("dataset_version"),
        "dataset.dataset_version",
    )
    split = _required_text(
        dataset.get("split"),
        "dataset.split",
    )
    purpose = _required_text(
        config.get("purpose"),
        "purpose",
    )

    case_benchmark_id = _required_text(
        case_manifest.get("benchmark_id"),
        "case_manifest.benchmark_id",
    )
    case_dataset_version = _required_text(
        case_manifest.get("dataset_version"),
        "case_manifest.dataset_version",
    )

    if case_benchmark_id != benchmark_id:
        raise BenchmarkManifestError(
            "case manifest benchmark_id does not match benchmark config"
        )

    if case_dataset_version != dataset_version:
        raise BenchmarkManifestError(
            "case manifest dataset_version does not match benchmark config"
        )

    benchmark_kind = _required_text(
        case_manifest.get("benchmark_kind"),
        "case_manifest.benchmark_kind",
    )

    if benchmark_kind not in {
        "independent_validation",
        "frozen_test",
    }:
        raise BenchmarkManifestError(
            "unsupported benchmark_kind"
        )

    if (
        purpose == "A3_FP32_GATE"
        and benchmark_kind != "independent_validation"
    ):
        raise BenchmarkManifestError(
            "A3 FP32 Gate requires independent_validation"
        )

    benchmark_version = _required_text(
        case_manifest.get("benchmark_version"),
        "case_manifest.benchmark_version",
    )

    sample_count = _positive_int(
        case_manifest.get("sample_count"),
        "case_manifest.sample_count",
    )

    case_set_digest = _required_hex(
        case_manifest.get("case_set_digest"),
        64,
        "case_manifest.case_set_digest",
    )

    rgb_set_sha256 = _required_hex(
        case_manifest.get("rgb_set_sha256"),
        64,
        "case_manifest.rgb_set_sha256",
    )

    cohort_counts = _count_mapping(
        case_manifest.get("cohort_counts"),
        (
            "seen",
            "variant",
            "unseen",
        ),
        "case_manifest.cohort_counts",
    )

    if sum(cohort_counts.values()) != sample_count:
        raise BenchmarkManifestError(
            "cohort_counts must sum to sample_count"
        )

    risk_denominators = _count_mapping(
        case_manifest.get(
            "risk_category_denominators"
        ),
        (
            "normal",
            "complex",
            "safety_critical",
        ),
        "case_manifest.risk_category_denominators",
    )

    if sum(risk_denominators.values()) != sample_count:
        raise BenchmarkManifestError(
            "risk_category_denominators must sum to sample_count"
        )

    return {
        "schema_version": "1.0",
        "benchmark_id": benchmark_id,
        "benchmark_version": benchmark_version,
        "benchmark_kind": benchmark_kind,
        "purpose": purpose,
        "dataset_version": dataset_version,
        "split": split,
        "case_manifest_path": case_manifest_path,
        "case_set_digest": case_set_digest,
        "sample_count": sample_count,
        "rgb_set_sha256": rgb_set_sha256,
        "split_rule": _required_text(
            case_manifest.get("split_rule"),
            "case_manifest.split_rule",
        ),
        "group_rule": _required_text(
            case_manifest.get("group_rule"),
            "case_manifest.group_rule",
        ),
        "cohort_counts": cohort_counts,
        "risk_category_denominators": risk_denominators,
        "frozen_at_utc": _required_text(
            case_manifest.get("frozen_at_utc"),
            "case_manifest.frozen_at_utc",
        ),
        "independence": {
            "required": True,
            "development_val_allowed": False,
            "frozen_test_allowed": False,
        },
    }


def canonical_benchmark_manifest_json(
    manifest: Mapping[str, Any],
) -> bytes:
    if not isinstance(manifest, Mapping) or not manifest:
        raise BenchmarkManifestError(
            "benchmark manifest must be a non-empty object"
        )

    try:
        encoded = json.dumps(
            dict(manifest),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise BenchmarkManifestError(
            "benchmark manifest is not canonical JSON"
        ) from error

    return (encoded + "\n").encode("utf-8")


def benchmark_manifest_sha256(
    manifest: Mapping[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_benchmark_manifest_json(
            manifest
        )
    ).hexdigest()


def write_benchmark_manifest(
    path: str | Path,
    manifest: Mapping[str, Any],
) -> str:
    destination = Path(path)
    payload = canonical_benchmark_manifest_json(
        manifest
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_name(
        destination.name + ".tmp"
    )

    temporary.write_bytes(payload)
    temporary.replace(destination)

    return hashlib.sha256(payload).hexdigest()


def _required_mapping(
    mapping: Mapping[str, Any],
    field: str,
) -> Mapping[str, Any]:
    value = mapping.get(field)

    if not isinstance(value, Mapping):
        raise BenchmarkManifestError(
            f"{field} must be an object"
        )

    return value


def _required_text(
    value: Any,
    field: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkManifestError(
            f"{field} must be a non-empty string"
        )

    return value.strip()


def _required_hex(
    value: Any,
    length: int,
    field: str,
) -> str:
    text = _required_text(
        value,
        field,
    ).lower()

    if len(text) != length:
        raise BenchmarkManifestError(
            f"{field} must be {length} hex characters"
        )

    try:
        int(text, 16)
    except ValueError as error:
        raise BenchmarkManifestError(
            f"{field} must be hexadecimal"
        ) from error

    return text


def _positive_int(
    value: Any,
    field: str,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
    ):
        raise BenchmarkManifestError(
            f"{field} must be a positive integer"
        )

    return value


def _count_mapping(
    value: Any,
    fields: tuple[str, ...],
    label: str,
) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise BenchmarkManifestError(
            f"{label} must be an object"
        )

    result: dict[str, int] = {}

    for field in fields:
        count = value.get(field)

        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
        ):
            raise BenchmarkManifestError(
                f"{label}.{field} must be a non-negative integer"
            )

        result[field] = count

    return result


__all__ = [
    "BenchmarkManifestError",
    "benchmark_manifest_sha256",
    "build_benchmark_manifest",
    "canonical_benchmark_manifest_json",
    "write_benchmark_manifest",
]