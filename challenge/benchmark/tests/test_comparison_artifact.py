from __future__ import annotations

import csv
import hashlib

import pytest

from challenge.benchmark.comparison import ComparisonError
from challenge.benchmark.comparison_artifact import (
    CSV_FIELDS,
    ComparisonArtifactError,
    model_comparison_csv_sha256,
    verify_model_comparison_csv,
    write_model_comparison_csv,
)
from challenge.benchmark.metric_evidence import GATE_METRICS
from challenge.benchmark.tests.test_comparison import (
    _artifact,
)

from challenge.benchmark.gate_decision import build_gate_decision
from challenge.benchmark.tests.test_gate_decision import (
    _policy_manifest,
)
from challenge.benchmark.policy_manifest import (
    policy_manifest_sha256,
)

def _evidence() -> tuple[dict, dict]:
    teacher = _artifact("teacher")
    student = _artifact("student")

    for metric in GATE_METRICS:
        teacher["metrics"][metric] = 0.9
        student["metrics"][metric] = 0.885

    return teacher, student


def test_model_comparison_csv_has_deterministic_schema_and_order(
    tmp_path,
) -> None:
    teacher, student = _evidence()
    destination = tmp_path / "model_comparison.csv"

    result = write_model_comparison_csv(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    with destination.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert tuple(rows[0]) == CSV_FIELDS
    assert [row["metric"] for row in rows] == list(
        GATE_METRICS
    )
    assert len(rows) == len(GATE_METRICS)
    assert result["row_count"] == len(GATE_METRICS)

    first = rows[0]
    assert float(first["teacher_value"]) == pytest.approx(
        0.9
    )
    assert float(first["student_value"]) == pytest.approx(
        0.885
    )
    assert float(first["absolute_drop"]) == pytest.approx(
        0.015
    )
    assert float(
        first["percentage_point_drop"]
    ) == pytest.approx(1.5)
    assert float(first["relative_drop"]) == pytest.approx(
        0.015 / 0.9
    )


def test_model_comparison_csv_sha_matches_exact_disk_bytes(
    tmp_path,
) -> None:
    teacher, student = _evidence()
    destination = tmp_path / "model_comparison.csv"

    result = write_model_comparison_csv(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    payload = destination.read_bytes()

    assert payload.endswith(b"\n")
    assert b"\r\n" not in payload

    expected_sha = hashlib.sha256(payload).hexdigest()

    assert result["sha256"] == expected_sha
    assert (
        model_comparison_csv_sha256(destination)
        == expected_sha
    )


def test_model_comparison_csv_is_byte_deterministic(
    tmp_path,
) -> None:
    teacher, student = _evidence()

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    first_result = write_model_comparison_csv(
        first / "model_comparison.csv",
        teacher_evaluation=teacher,
        student_evaluation=student,
    )
    second_result = write_model_comparison_csv(
        second / "model_comparison.csv",
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    assert (
        (first / "model_comparison.csv").read_bytes()
        == (second / "model_comparison.csv").read_bytes()
    )
    assert first_result["sha256"] == second_result["sha256"]


def test_model_comparison_csv_uses_empty_relative_drop_for_zero_teacher(
    tmp_path,
) -> None:
    teacher = _artifact("teacher")
    student = _artifact("student")

    for metric in GATE_METRICS:
        teacher["metrics"][metric] = 0.0
        student["metrics"][metric] = 0.0

    destination = tmp_path / "model_comparison.csv"

    write_model_comparison_csv(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    with destination.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert all(
        row["relative_drop"] == ""
        for row in rows
    )


def test_model_comparison_csv_refuses_existing_destination(
    tmp_path,
) -> None:
    teacher, student = _evidence()
    destination = tmp_path / "model_comparison.csv"
    destination.write_bytes(b"keep-me")

    with pytest.raises(
        ComparisonArtifactError,
        match="destination already exists",
    ):
        write_model_comparison_csv(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
        )

    assert destination.read_bytes() == b"keep-me"


def test_model_comparison_csv_rejects_mismatched_evidence_without_partial(
    tmp_path,
) -> None:
    teacher, student = _evidence()

    student["case_set_digest"] = "9" * 64

    destination = tmp_path / "model_comparison.csv"
    temporary = tmp_path / ".model_comparison.csv.tmp"

    with pytest.raises(ComparisonError):
        write_model_comparison_csv(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
        )

    assert not destination.exists()
    assert not temporary.exists()
def _gate_evidence() -> tuple[dict, dict, dict]:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _artifact("teacher")
    student = _artifact("student")

    teacher["policy_manifest_sha256"] = policy_sha
    student["policy_manifest_sha256"] = policy_sha

    teacher["schema_validity"] = 1.0
    student["schema_validity"] = 1.0

    return teacher, student, policy


def test_model_comparison_csv_verifier_accepts_gate_decision(
    tmp_path,
) -> None:
    teacher, student, policy = _gate_evidence()

    destination = tmp_path / "model_comparison.csv"

    written = write_model_comparison_csv(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    verified = verify_model_comparison_csv(
        destination,
        gate_decision=decision,
    )

    assert verified["valid"] is True
    assert verified["sha256"] == written["sha256"]
    assert verified["gate_status"] == decision["gate_status"]
    assert (
        verified["case_set_digest"]
        == decision["case_set_digest"]
    )


def test_model_comparison_csv_verifier_rejects_tampered_csv(
    tmp_path,
) -> None:
    teacher, student, policy = _gate_evidence()

    destination = tmp_path / "model_comparison.csv"

    write_model_comparison_csv(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    payload = destination.read_text(encoding="utf-8")
    destination.write_text(
        payload.replace("0.90000000000000002", "0.8", 1),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(
        ComparisonArtifactError,
        match="does not match gate decision",
    ):
        verify_model_comparison_csv(
            destination,
            gate_decision=decision,
        )


def test_model_comparison_csv_verifier_rejects_gate_identity_tamper(
    tmp_path,
) -> None:
    teacher, student, policy = _gate_evidence()

    destination = tmp_path / "model_comparison.csv"

    write_model_comparison_csv(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    decision["case_set_digest"] = "9" * 64

    with pytest.raises(
        ComparisonArtifactError,
        match="case_set_digest does not match comparison",
    ):
        verify_model_comparison_csv(
            destination,
            gate_decision=decision,
        )