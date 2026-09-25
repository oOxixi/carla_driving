from __future__ import annotations

import hashlib
import json

import pytest

from challenge.benchmark.evaluation_artifact import (
    canonical_evaluation_json,
)
from challenge.benchmark.teacher_baseline import (
    TeacherBaselineError,
    write_teacher_baseline,
)
from challenge.benchmark.tests.test_comparison import (
    _artifact,
)


def _teacher_source(tmp_path):
    artifact = _artifact("teacher")
    artifact["schema_version"] = "1.0"
    artifact["schema_validity"] = 1.0
    artifact["predictions_sha256"] = "e" * 64

    payload = canonical_evaluation_json(artifact)
    source = tmp_path / "teacher_evaluation.json"
    source.write_bytes(payload)

    return (
        artifact,
        source,
        hashlib.sha256(payload).hexdigest(),
    )


def test_teacher_baseline_is_exact_teacher_evaluation_bytes(
    tmp_path,
) -> None:
    artifact, source, source_sha = _teacher_source(tmp_path)
    destination = tmp_path / "teacher_baseline.json"

    result = write_teacher_baseline(
        destination,
        teacher_evaluation_path=source,
        teacher_evaluation_sha256=source_sha,
    )

    assert destination.read_bytes() == source.read_bytes()
    assert result["sha256"] == source_sha
    assert result["teacher_evaluation_sha256"] == source_sha
    assert result["evaluation_id"] == artifact["evaluation_id"]
    assert (
        result["case_set_digest"]
        == artifact["case_set_digest"]
    )


def test_teacher_baseline_refuses_existing_destination(
    tmp_path,
) -> None:
    _, source, source_sha = _teacher_source(tmp_path)
    destination = tmp_path / "teacher_baseline.json"
    destination.write_bytes(b"keep-me")

    with pytest.raises(
        TeacherBaselineError,
        match="destination already exists",
    ):
        write_teacher_baseline(
            destination,
            teacher_evaluation_path=source,
            teacher_evaluation_sha256=source_sha,
        )

    assert destination.read_bytes() == b"keep-me"


def test_teacher_baseline_rejects_wrong_source_sha_without_partial(
    tmp_path,
) -> None:
    _, source, _ = _teacher_source(tmp_path)
    destination = tmp_path / "teacher_baseline.json"

    with pytest.raises(
        TeacherBaselineError,
        match="SHA256 does not match",
    ):
        write_teacher_baseline(
            destination,
            teacher_evaluation_path=source,
            teacher_evaluation_sha256="f" * 64,
        )

    assert not destination.exists()
    assert not (
        tmp_path / ".teacher_baseline.json.tmp"
    ).exists()


def test_teacher_baseline_rejects_student_evaluation(
    tmp_path,
) -> None:
    artifact = _artifact("student")
    artifact["schema_version"] = "1.0"

    payload = canonical_evaluation_json(artifact)
    source = tmp_path / "student_evaluation.json"
    source.write_bytes(payload)

    destination = tmp_path / "teacher_baseline.json"

    with pytest.raises(
        TeacherBaselineError,
        match="evaluation_role='teacher'",
    ):
        write_teacher_baseline(
            destination,
            teacher_evaluation_path=source,
            teacher_evaluation_sha256=hashlib.sha256(
                payload
            ).hexdigest(),
        )

    assert not destination.exists()


def test_teacher_baseline_rejects_noncanonical_source(
    tmp_path,
) -> None:
    artifact = _artifact("teacher")

    source = tmp_path / "teacher_evaluation.json"
    source_bytes = json.dumps(
        artifact,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")
    source.write_bytes(source_bytes)

    destination = tmp_path / "teacher_baseline.json"

    with pytest.raises(
        TeacherBaselineError,
        match="bytes are not canonical",
    ):
        write_teacher_baseline(
            destination,
            teacher_evaluation_path=source,
            teacher_evaluation_sha256=hashlib.sha256(
                source_bytes
            ).hexdigest(),
        )

    assert not destination.exists()


def test_teacher_baseline_publishes_from_teacher_evidence_package(
    tmp_path,
) -> None:
    import copy

    from challenge.benchmark.evaluation_package import (
        write_teacher_evidence_package,
    )
    from challenge.benchmark.tests.test_evaluation_artifact import (
        _success_record,
    )
    from challenge.distillation.dataset import (
        build_mock_records,
    )

    cases = copy.deepcopy(build_mock_records(5))
    records = [
        _success_record(case)
        for case in cases
    ]

    package = write_teacher_evidence_package(
        tmp_path / "teacher_package",
        cases,
        records,
        evaluation_id="teacher-baseline-integration",
        dataset_version="test-dataset-v1",
        benchmark_manifest_sha256="a" * 64,
        policy_manifest_sha256="b" * 64,
        case_set_digest="c" * 64,
        evaluator_git_sha="d" * 40,
    )

    destination = tmp_path / "teacher_baseline.json"

    result = write_teacher_baseline(
        destination,
        teacher_evaluation_path=package["teacher_evaluation"],
        teacher_evaluation_sha256=(
            package["teacher_evaluation_sha256"]
        ),
    )

    evaluation_bytes = (
        tmp_path
        / "teacher_package"
        / "teacher_evaluation.json"
    ).read_bytes()

    assert destination.read_bytes() == evaluation_bytes

    assert (
        hashlib.sha256(destination.read_bytes()).hexdigest()
        == package["teacher_evaluation_sha256"]
    )

    assert (
        result["teacher_evaluation_sha256"]
        == package["teacher_evaluation_sha256"]
    )

    published = json.loads(destination.read_text("utf-8"))

    assert published["evaluation_role"] == "teacher"
    assert (
        published["evaluation_id"]
        == "teacher-baseline-integration"
    )
    assert published["benchmark_manifest_sha256"] == "a" * 64
    assert published["policy_manifest_sha256"] == "b" * 64
    assert published["case_set_digest"] == "c" * 64
    assert published["evaluator_git_sha"] == "d" * 40