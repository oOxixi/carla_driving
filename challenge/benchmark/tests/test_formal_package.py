from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("torch")

from challenge.benchmark.evaluation_package import (
    EvaluationPackageError,
)
from challenge.benchmark.formal_package import (
    write_policy_bound_teacher_package,
)
from challenge.benchmark.policy_manifest import (
    load_benchmark_policy_config,
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


def _complete_policy_config() -> dict:
    config = copy.deepcopy(
        load_benchmark_policy_config(
            CONFIG_PATH
        )
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


def _records(cases: list[dict]) -> list[dict]:
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


def test_policy_bound_package_uses_actual_manifest_digest(
    tmp_path,
) -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "teacher-policy-test"
    )

    result = write_policy_bound_teacher_package(
        destination,
        cases,
        _records(cases),
        evaluation_id="teacher-policy-test",
        dataset_version="test-dataset-v1",
        benchmark_manifest_sha256="a" * 64,
        case_set_digest="c" * 64,
        evaluator_git_sha="d" * 40,
        policy_config=_complete_policy_config(),
    )

    assert sorted(
        path.name
        for path in destination.iterdir()
    ) == [
        "policy_manifest.json",
        "predictions.sha256",
        "teacher_evaluation.json",
        "teacher_predictions.jsonl",
    ]

    policy_bytes = (
        destination / "policy_manifest.json"
    ).read_bytes()

    actual_policy_sha256 = hashlib.sha256(
        policy_bytes
    ).hexdigest()

    evaluation = json.loads(
        (
            destination / "teacher_evaluation.json"
        ).read_text(encoding="utf-8")
    )

    assert result["policy_manifest_sha256"] == (
        actual_policy_sha256
    )
    assert evaluation["policy_manifest_sha256"] == (
        actual_policy_sha256
    )


def test_current_repository_policy_cannot_publish_formal_package(
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

    current_config = load_benchmark_policy_config(
        CONFIG_PATH
    )

    with pytest.raises(
        EvaluationPackageError,
        match="formal policy",
    ):
        write_policy_bound_teacher_package(
            destination,
            cases,
            _records(cases),
            evaluation_id="blocked",
            dataset_version="test-dataset-v1",
            benchmark_manifest_sha256="a" * 64,
            case_set_digest="c" * 64,
            evaluator_git_sha="d" * 40,
            policy_config=current_config,
        )

    assert not destination.exists()
    assert not destination.with_name(
        destination.name + ".policy.tmp"
    ).exists()


def test_existing_destination_is_not_overwritten(
    tmp_path,
) -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "existing"
    )

    destination.mkdir(
        parents=True
    )

    marker = destination / "marker.txt"
    marker.write_text(
        "keep",
        encoding="utf-8",
    )

    with pytest.raises(
        EvaluationPackageError,
        match="destination already exists",
    ):
        write_policy_bound_teacher_package(
            destination,
            cases,
            _records(cases),
            evaluation_id="existing",
            dataset_version="test-dataset-v1",
            benchmark_manifest_sha256="a" * 64,
            case_set_digest="c" * 64,
            evaluator_git_sha="d" * 40,
            policy_config=_complete_policy_config(),
        )

    assert marker.read_text(
        encoding="utf-8"
    ) == "keep"