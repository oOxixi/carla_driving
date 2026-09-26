from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from challenge.benchmark.benchmark_manifest import (
    BenchmarkManifestError,
    benchmark_manifest_sha256,
    build_benchmark_manifest,
    canonical_benchmark_manifest_json,
    write_benchmark_manifest,
)


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = (
    ROOT
    / "challenge"
    / "benchmark"
    / "benchmark_config.yaml"
)


def _repository_config() -> dict:
    return yaml.safe_load(
        CONFIG_PATH.read_text(
            encoding="utf-8"
        )
    )


def _frozen_config() -> dict:
    config = copy.deepcopy(
        _repository_config()
    )

    config["status"] = "FROZEN"
    config["dataset"]["case_manifest_path"] = (
        "frozen/independent_validation_v1.json"
    )

    return config


def _case_manifest() -> dict:
    config = _repository_config()

    return {
        "benchmark_id": config["benchmark_id"],
        "benchmark_version": "1.0",
        "benchmark_kind": "independent_validation",
        "dataset_version": (
            config["dataset"]["dataset_version"]
        ),
        "sample_count": 6,
        "case_set_digest": "a" * 64,
        "rgb_set_sha256": "b" * 64,
        "split_rule": (
            "template_scenario_group_disjoint"
        ),
        "group_rule": (
            "no_group_key_cross_split_overlap"
        ),
        "cohort_counts": {
            "seen": 2,
            "variant": 2,
            "unseen": 2,
        },
        "risk_category_denominators": {
            "normal": 2,
            "complex": 2,
            "safety_critical": 2,
        },
        "frozen_at_utc": (
            "2026-09-24T00:00:00Z"
        ),
    }


def test_current_repository_benchmark_fails_closed() -> None:
    with pytest.raises(
        BenchmarkManifestError,
        match="not frozen",
    ):
        build_benchmark_manifest(
            _repository_config(),
            _case_manifest(),
        )


def test_complete_frozen_benchmark_builds_manifest() -> None:
    manifest = build_benchmark_manifest(
        _frozen_config(),
        _case_manifest(),
    )

    assert manifest["benchmark_kind"] == (
        "independent_validation"
    )
    assert manifest["sample_count"] == 6

    assert manifest["cohort_counts"] == {
        "seen": 2,
        "variant": 2,
        "unseen": 2,
    }

    assert manifest[
        "risk_category_denominators"
    ] == {
        "normal": 2,
        "complex": 2,
        "safety_critical": 2,
    }


def test_a3_gate_rejects_frozen_test_identity() -> None:
    case_manifest = _case_manifest()
    case_manifest["benchmark_kind"] = (
        "frozen_test"
    )

    with pytest.raises(
        BenchmarkManifestError,
        match="requires independent_validation",
    ):
        build_benchmark_manifest(
            _frozen_config(),
            case_manifest,
        )


def test_cohort_counts_must_cover_exact_case_set() -> None:
    case_manifest = _case_manifest()
    case_manifest["cohort_counts"]["unseen"] = 1

    with pytest.raises(
        BenchmarkManifestError,
        match="cohort_counts must sum",
    ):
        build_benchmark_manifest(
            _frozen_config(),
            case_manifest,
        )


def test_manifest_digest_is_deterministic() -> None:
    manifest = build_benchmark_manifest(
        _frozen_config(),
        _case_manifest(),
    )

    reordered = dict(
        reversed(
            list(manifest.items())
        )
    )

    assert canonical_benchmark_manifest_json(
        manifest
    ) == canonical_benchmark_manifest_json(
        reordered
    )

    assert benchmark_manifest_sha256(
        manifest
    ) == benchmark_manifest_sha256(
        reordered
    )


def test_writer_hash_matches_exact_file_bytes(
    tmp_path,
) -> None:
    manifest = build_benchmark_manifest(
        _frozen_config(),
        _case_manifest(),
    )

    path = tmp_path / "benchmark_manifest.json"

    digest = write_benchmark_manifest(
        path,
        manifest,
    )

    payload = path.read_bytes()

    assert digest == hashlib.sha256(
        payload
    ).hexdigest()

    assert digest == benchmark_manifest_sha256(
        manifest
    )

    assert json.loads(
        payload.decode("utf-8")
    ) == manifest

    assert payload.endswith(b"\n")
    assert b"\r\n" not in payload