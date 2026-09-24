from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

pytest.importorskip("torch")

from challenge.benchmark.evaluation_package import (
    EvaluationPackageError,
)
from challenge.benchmark.formal_bundle import (
    write_formal_teacher_bundle,
)
from challenge.distillation.dataset import (
    build_mock_records,
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


def _complete_config() -> dict:
    config = copy.deepcopy(
        _repository_config()
    )

    config["status"] = "FROZEN"
    config["dataset"]["case_manifest_path"] = (
        "frozen/independent_validation_v1.json"
    )

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


def _case_manifest(
    *,
    sample_count: int = 5,
) -> dict:
    config = _repository_config()

    return {
        "benchmark_id": config["benchmark_id"],
        "benchmark_version": "1.0",
        "benchmark_kind": "independent_validation",
        "dataset_version": (
            config["dataset"]["dataset_version"]
        ),
        "sample_count": sample_count,
        "case_set_digest": "a" * 64,
        "rgb_set_sha256": "b" * 64,
        "split_rule": (
            "template_scenario_group_disjoint"
        ),
        "group_rule": (
            "no_group_key_cross_split_overlap"
        ),
        "cohort_counts": {
            "seen": sample_count,
            "variant": 0,
            "unseen": 0,
        },
        "risk_category_denominators": {
            "normal": sample_count - 1,
            "complex": 0,
            "safety_critical": 1,
        },
        "frozen_at_utc": (
            "2026-09-24T00:00:00Z"
        ),
    }


def _records(
    cases: list[dict],
) -> list[dict]:
    return [
        {
            "sample_id": case["sample_id"],
            "status": "SUCCESS",
            "prediction": copy.deepcopy(
                case["teacher"]["maneuver_plan"]
            ),
            "error": None,
        }
        for case in cases
    ]


def test_formal_bundle_binds_real_manifest_hashes(
    tmp_path,
) -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "formal-test"
    )

    result = write_formal_teacher_bundle(
        destination,
        cases,
        _records(cases),
        evaluation_id="formal-test",
        benchmark_config=_complete_config(),
        case_manifest=_case_manifest(),
        evaluator_git_sha="d" * 40,
    )

    assert sorted(
        path.name
        for path in destination.iterdir()
    ) == [
        "benchmark_manifest.json",
        "policy_manifest.json",
        "predictions.sha256",
        "teacher_evaluation.json",
        "teacher_predictions.jsonl",
    ]

    benchmark_bytes = (
        destination / "benchmark_manifest.json"
    ).read_bytes()

    policy_bytes = (
        destination / "policy_manifest.json"
    ).read_bytes()

    benchmark_sha256 = hashlib.sha256(
        benchmark_bytes
    ).hexdigest()

    policy_sha256 = hashlib.sha256(
        policy_bytes
    ).hexdigest()

    evaluation = json.loads(
        (
            destination / "teacher_evaluation.json"
        ).read_text(encoding="utf-8")
    )

    assert result[
        "benchmark_manifest_sha256"
    ] == benchmark_sha256

    assert result[
        "policy_manifest_sha256"
    ] == policy_sha256

    assert evaluation[
        "benchmark_manifest_sha256"
    ] == benchmark_sha256

    assert evaluation[
        "policy_manifest_sha256"
    ] == policy_sha256

    assert evaluation["case_set_digest"] == (
        "a" * 64
    )


def test_current_repository_state_cannot_publish_formal_bundle(
    tmp_path,
) -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "blocked"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="formal manifests",
    ):
        write_formal_teacher_bundle(
            destination,
            cases,
            _records(cases),
            evaluation_id="blocked",
            benchmark_config=_repository_config(),
            case_manifest=_case_manifest(),
            evaluator_git_sha="d" * 40,
        )

    assert not destination.exists()


def test_manifest_sample_count_must_match_actual_evaluation(
    tmp_path,
) -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "count-mismatch"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="sample_count does not match",
    ):
        write_formal_teacher_bundle(
            destination,
            cases,
            _records(cases),
            evaluation_id="count-mismatch",
            benchmark_config=_complete_config(),
            case_manifest=_case_manifest(
                sample_count=6
            ),
            evaluator_git_sha="d" * 40,
        )

    assert not destination.exists()
    assert not destination.with_name(
        destination.name + ".formal.tmp"
    ).exists()