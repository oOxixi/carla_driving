from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from challenge.benchmark.policy_manifest import (
    PolicyManifestError,
    build_policy_manifest,
    canonical_policy_manifest_json,
    load_benchmark_policy_config,
    policy_manifest_sha256,
    write_policy_manifest,
)


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = (
    ROOT
    / "challenge"
    / "benchmark"
    / "benchmark_config.yaml"
)


def _complete_config() -> dict:
    config = load_benchmark_policy_config(
        CONFIG_PATH
    )

    config = copy.deepcopy(config)

    config["formal_policy"] = {
        "status": "FROZEN",
        "policy_version": "b2-policy-test-v1",
        "slice_minimum_denominators": {
            "seen": 1,
            "variant": 1,
            "unseen": 1,
        },
        "multi_run_merge_rule": (
            "pool_numerators_and_denominators"
        ),
    }

    return config


def test_current_repository_policy_fails_closed_until_completed() -> None:
    config = load_benchmark_policy_config(
        CONFIG_PATH
    )

    with pytest.raises(
        PolicyManifestError,
        match="formal policy",
    ):
        build_policy_manifest(config)


def test_complete_policy_builds_manifest() -> None:
    manifest = build_policy_manifest(
        _complete_config()
    )

    assert manifest["schema_version"] == "1.0"
    assert manifest["policy_version"] == (
        "b2-policy-test-v1"
    )

    assert manifest[
        "multi_run_merge_rule"
    ] == "pool_numerators_and_denominators"

    assert manifest[
        "slice_minimum_denominators"
    ] == {
        "seen": 1,
        "variant": 1,
        "unseen": 1,
    }

    assert (
        manifest["gate_metric_policy"][
            "success_only_filter_allowed"
        ]
        is False
    )


def test_policy_manifest_digest_is_deterministic() -> None:
    manifest = build_policy_manifest(
        _complete_config()
    )

    reordered = dict(
        reversed(
            list(manifest.items())
        )
    )

    assert canonical_policy_manifest_json(
        manifest
    ) == canonical_policy_manifest_json(
        reordered
    )

    assert policy_manifest_sha256(
        manifest
    ) == policy_manifest_sha256(
        reordered
    )


def test_writer_hash_matches_exact_file_bytes(
    tmp_path,
) -> None:
    manifest = build_policy_manifest(
        _complete_config()
    )

    path = tmp_path / "policy_manifest.json"

    digest = write_policy_manifest(
        path,
        manifest,
    )

    payload = path.read_bytes()

    assert digest == hashlib.sha256(
        payload
    ).hexdigest()

    assert digest == policy_manifest_sha256(
        manifest
    )

    assert json.loads(
        payload.decode("utf-8")
    ) == manifest

    assert payload.endswith(b"\n")
    assert b"\r\n" not in payload