from __future__ import annotations

import copy
import hashlib
import json

import pytest

pytest.importorskip("torch")

from challenge.benchmark.evaluation_package import (
    EvaluationPackageError,
    write_student_evidence_package,
    write_teacher_evidence_package,
)
from challenge.distillation.dataset import build_mock_records


def _success_record(case: dict) -> dict:
    return {
        "sample_id": case["sample_id"],
        "status": "SUCCESS",
        "prediction": copy.deepcopy(
            case["teacher"]["maneuver_plan"]
        ),
        "error": None,
    }


def _write_package(tmp_path):
    cases = copy.deepcopy(
        build_mock_records(5)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    destination = (
        tmp_path / "b2_evaluation" / "teacher-test-001"
    )

    result = write_teacher_evidence_package(
        destination,
        cases,
        records,
        evaluation_id="teacher-test-001",
        dataset_version="test-dataset-v1",
        benchmark_manifest_sha256="a" * 64,
        policy_manifest_sha256="b" * 64,
        case_set_digest="c" * 64,
        evaluator_git_sha="d" * 40,
    )

    return destination, result


def test_teacher_package_binds_raw_predictions_to_evaluation(
    tmp_path,
) -> None:
    destination, result = _write_package(
        tmp_path
    )

    assert sorted(
        path.name
        for path in destination.iterdir()
    ) == [
        "predictions.sha256",
        "teacher_evaluation.json",
        "teacher_predictions.jsonl",
    ]

    predictions = (
        destination / "teacher_predictions.jsonl"
    ).read_bytes()

    actual_sha256 = hashlib.sha256(
        predictions
    ).hexdigest()

    evaluation = json.loads(
        (
            destination / "teacher_evaluation.json"
        ).read_text(encoding="utf-8")
    )

    assert evaluation["predictions_sha256"] == (
        actual_sha256
    )
    assert result["predictions_sha256"] == (
        actual_sha256
    )

    assert result["teacher_evaluation_sha256"] == (
        hashlib.sha256(
            (
                destination / "teacher_evaluation.json"
            ).read_bytes()
        ).hexdigest()
    )


def test_prediction_checksum_file_is_exact_and_lf_terminated(
    tmp_path,
) -> None:
    destination, result = _write_package(
        tmp_path
    )

    checksum = (
        destination / "predictions.sha256"
    ).read_bytes()

    assert checksum == (
        (
            f"{result['predictions_sha256']}"
            "  teacher_predictions.jsonl\n"
        ).encode("ascii")
    )

    assert b"\r\n" not in checksum


def test_existing_package_is_never_overwritten(
    tmp_path,
) -> None:
    destination, _ = _write_package(
        tmp_path
    )

    marker = destination / "marker.txt"
    marker.write_text(
        "keep",
        encoding="utf-8",
    )

    cases = copy.deepcopy(
        build_mock_records(5)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    with pytest.raises(
        EvaluationPackageError,
        match="destination already exists",
    ):
        write_teacher_evidence_package(
            destination,
            cases,
            records,
            evaluation_id="teacher-test-001",
            dataset_version="test-dataset-v1",
            benchmark_manifest_sha256="a" * 64,
            policy_manifest_sha256="b" * 64,
            case_set_digest="c" * 64,
            evaluator_git_sha="d" * 40,
        )

    assert marker.read_text(
        encoding="utf-8"
    ) == "keep"


def test_invalid_evidence_does_not_publish_partial_package(
    tmp_path,
) -> None:
    cases = copy.deepcopy(
        build_mock_records(2)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    destination = (
        tmp_path / "b2_evaluation" / "invalid"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="cannot build Teacher evaluation package",
    ):
        write_teacher_evidence_package(
            destination,
            cases,
            records,
            evaluation_id="invalid",
            dataset_version="test-dataset-v1",
            benchmark_manifest_sha256="a" * 64,
            policy_manifest_sha256="b" * 64,
            case_set_digest="c" * 64,
            evaluator_git_sha="d" * 40,
        )

    assert not destination.exists()
    assert not destination.with_name(
        destination.name + ".tmp"
    ).exists()

def _write_student_package(tmp_path):
    cases = copy.deepcopy(
        build_mock_records(5)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    destination = (
        tmp_path / "b2_evaluation" / "student-test-001"
    )

    result = write_student_evidence_package(
        destination,
        cases,
        records,
        evaluation_id="student-test-001",
        dataset_version="test-dataset-v1",
        benchmark_manifest_sha256="a" * 64,
        policy_manifest_sha256="b" * 64,
        case_set_digest="c" * 64,
        evaluator_git_sha="d" * 40,
        model_id="student-v0-r3-fp32",
        config_id="student-v0-r3-structure-test",
        weights_sha256="e" * 64,
    )

    return destination, result


def test_student_package_binds_raw_predictions_and_identity(
    tmp_path,
) -> None:
    destination, result = _write_student_package(
        tmp_path
    )

    assert sorted(
        path.name
        for path in destination.iterdir()
    ) == [
        "predictions.sha256",
        "student_evaluation.json",
        "student_predictions.jsonl",
    ]

    predictions = (
        destination / "student_predictions.jsonl"
    ).read_bytes()

    actual_sha256 = hashlib.sha256(
        predictions
    ).hexdigest()

    evaluation = json.loads(
        (
            destination / "student_evaluation.json"
        ).read_text(encoding="utf-8")
    )

    assert evaluation["evaluation_role"] == "student"
    assert evaluation["model_id"] == (
        "student-v0-r3-fp32"
    )
    assert evaluation["config_id"] == (
        "student-v0-r3-structure-test"
    )
    assert evaluation["weights_sha256"] == "e" * 64

    assert evaluation["predictions_sha256"] == (
        actual_sha256
    )
    assert result["predictions_sha256"] == (
        actual_sha256
    )

    assert result["student_evaluation_sha256"] == (
        hashlib.sha256(
            (
                destination / "student_evaluation.json"
            ).read_bytes()
        ).hexdigest()
    )


def test_student_prediction_checksum_is_exact(
    tmp_path,
) -> None:
    destination, result = _write_student_package(
        tmp_path
    )

    checksum = (
        destination / "predictions.sha256"
    ).read_bytes()

    assert checksum == (
        (
            f"{result['predictions_sha256']}"
            "  student_predictions.jsonl\n"
        ).encode("ascii")
    )

    assert b"\r\n" not in checksum


def test_invalid_student_identity_does_not_publish_package(
    tmp_path,
) -> None:
    cases = copy.deepcopy(
        build_mock_records(5)
    )
    records = [
        _success_record(case)
        for case in cases
    ]

    destination = (
        tmp_path / "b2_evaluation" / "invalid-student"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="cannot build Student evaluation package",
    ):
        write_student_evidence_package(
            destination,
            cases,
            records,
            evaluation_id="invalid-student",
            dataset_version="test-dataset-v1",
            benchmark_manifest_sha256="a" * 64,
            policy_manifest_sha256="b" * 64,
            case_set_digest="c" * 64,
            evaluator_git_sha="d" * 40,
            model_id="student-v0-r3-fp32",
            config_id="student-v0-r3-structure-test",
            weights_sha256="not-a-sha",
        )

    assert not destination.exists()
    assert not destination.with_name(
        destination.name + ".tmp"
    ).exists()