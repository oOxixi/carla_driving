from __future__ import annotations

import copy

import pytest

pytest.importorskip("torch")

from challenge.benchmark.evaluation_artifact import (
    EvaluationArtifactError,
    build_teacher_evaluation,
    canonical_evaluation_json,
    evaluation_artifact_sha256,
    write_evaluation_artifact,
)
from challenge.benchmark.raw_predictions import (
    prediction_records_sha256,
)
from challenge.distillation.artifacts import (
    FORMAL_GATE_TEACHER_V4,
)
from challenge.distillation.dataset import build_mock_records

import hashlib
import json

def _success_record(case: dict) -> dict:
    return {
        "sample_id": case["sample_id"],
        "status": "SUCCESS",
        "prediction": copy.deepcopy(
            case["teacher"]["maneuver_plan"]
        ),
        "error": None,
    }


def _build(cases: list[dict]) -> dict:
    records = [
        _success_record(case)
        for case in cases
    ]

    return build_teacher_evaluation(
        cases,
        records,
        evaluation_id="b2-teacher-test-001",
        dataset_version="test-dataset-v1",
        benchmark_manifest_sha256="a" * 64,
        policy_manifest_sha256="b" * 64,
        case_set_digest="c" * 64,
        evaluator_git_sha="d" * 40,
        evidence_bindings={
            "release_manifest_sha256": "e" * 64,
            "a3_view_manifest_sha256": "f" * 64,
        },
    )


def test_teacher_artifact_exposes_a3_flat_metrics_and_b2_evidence() -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )

    artifact = _build(cases)

    assert artifact["evaluation_id"] == (
        "b2-teacher-test-001"
    )
    assert artifact["split"] == "validation"
    assert artifact["sample_count"] == 5

    for field, expected in FORMAL_GATE_TEACHER_V4.items():
        assert artifact[field] == expected

    for name, value in artifact["metrics"].items():
        assert value == 1.0

        evidence = artifact["metric_evidence"][name]

        assert evidence["numerator"] == (
            evidence["denominator"]
        )
        assert evidence["denominator"] > 0
        assert evidence["value"] == value

    assert artifact["coverage"]["success_count"] == 5
    assert artifact["coverage"]["failed_count"] == 0


def test_predictions_sha_is_derived_from_raw_records() -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    artifact = build_teacher_evaluation(
        cases,
        records,
        evaluation_id="b2-teacher-test-002",
        dataset_version="test-dataset-v1",
        benchmark_manifest_sha256="a" * 64,
        policy_manifest_sha256="b" * 64,
        case_set_digest="c" * 64,
        evaluator_git_sha="d" * 40,
    )

    assert artifact["predictions_sha256"] == (
        prediction_records_sha256(records)
    )


def test_empty_gate_denominator_fails_closed() -> None:
    # Two mock normal cases contain no safety-critical opportunity.
    cases = copy.deepcopy(
        build_mock_records(2)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    with pytest.raises(
        EvaluationArtifactError,
        match="empty denominator",
    ):
        build_teacher_evaluation(
            cases,
            records,
            evaluation_id="b2-teacher-test-003",
            dataset_version="test-dataset-v1",
            benchmark_manifest_sha256="a" * 64,
            policy_manifest_sha256="b" * 64,
            case_set_digest="c" * 64,
            evaluator_git_sha="d" * 40,
        )


def test_invalid_identity_hash_fails_closed() -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    with pytest.raises(
        EvaluationArtifactError,
        match="benchmark_manifest_sha256",
    ):
        build_teacher_evaluation(
            cases,
            records,
            evaluation_id="b2-teacher-test-004",
            dataset_version="test-dataset-v1",
            benchmark_manifest_sha256="not-a-sha",
            policy_manifest_sha256="b" * 64,
            case_set_digest="c" * 64,
            evaluator_git_sha="d" * 40,
        )


def test_formal_source_evidence_bindings_are_preserved() -> None:
    artifact = _build(
        copy.deepcopy(
            build_mock_records(5)
        )
    )

    assert artifact["release_manifest_sha256"] == (
        "e" * 64
    )
    assert artifact["a3_view_manifest_sha256"] == (
        "f" * 64
    )

def test_writer_round_trips_exact_teacher_evaluation_bytes(
    tmp_path,
) -> None:
    artifact = _build(
        copy.deepcopy(
            build_mock_records(5)
        )
    )
    path = tmp_path / "teacher_evaluation.json"

    digest = write_evaluation_artifact(
        path,
        artifact,
    )

    payload = path.read_bytes()

    assert payload == canonical_evaluation_json(
        artifact
    )
    assert digest == hashlib.sha256(
        payload
    ).hexdigest()
    assert digest == evaluation_artifact_sha256(
        artifact
    )

    assert json.loads(
        payload.decode("utf-8")
    ) == artifact

    assert payload.endswith(b"\n")
    assert b"\r\n" not in payload


def test_evaluation_digest_ignores_mapping_key_order() -> None:
    artifact = _build(
        copy.deepcopy(
            build_mock_records(5)
        )
    )

    reordered = dict(
        reversed(
            list(artifact.items())
        )
    )

    assert canonical_evaluation_json(
        artifact
    ) == canonical_evaluation_json(
        reordered
    )

    assert evaluation_artifact_sha256(
        artifact
    ) == evaluation_artifact_sha256(
        reordered
    )


def test_non_json_value_does_not_overwrite_existing_artifact(
    tmp_path,
) -> None:
    path = tmp_path / "teacher_evaluation.json"
    original = b"existing-artifact\n"

    path.write_bytes(original)

    with pytest.raises(
        EvaluationArtifactError,
        match="not canonical JSON",
    ):
        write_evaluation_artifact(
            path,
            {
                "metric": float("nan"),
            },
        )

    assert path.read_bytes() == original


def test_empty_evaluation_artifact_fails_closed() -> None:
    with pytest.raises(
        EvaluationArtifactError,
        match="must be a non-empty object",
    ):
        canonical_evaluation_json({})