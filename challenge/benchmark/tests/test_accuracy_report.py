from __future__ import annotations

import copy

import pytest

from challenge.benchmark.accuracy_report import (
    AccuracyReportError,
    accuracy_report_sha256,
    verify_accuracy_report,
    write_accuracy_report,
)
from challenge.benchmark.comparison_artifact import (
    write_model_comparison_csv,
)
from challenge.benchmark.gate_decision import (
    build_gate_decision,
)
from challenge.benchmark.policy_manifest import (
    policy_manifest_sha256,
)
from challenge.benchmark.tests.test_comparison import (
    _artifact,
)
from challenge.benchmark.tests.test_gate_decision import (
    _policy_manifest,
)


def _evidence():
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _artifact("teacher")
    student = _artifact("student")

    teacher["policy_manifest_sha256"] = policy_sha
    student["policy_manifest_sha256"] = policy_sha

    teacher["schema_validity"] = 1.0
    student["schema_validity"] = 1.0

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    return teacher, student, decision


def _write_comparison(tmp_path, teacher, student):
    path = tmp_path / "model_comparison.csv"

    write_model_comparison_csv(
        path,
        teacher_evaluation=teacher,
        student_evaluation=student,
    )

    return path


def test_accuracy_report_is_deterministic_and_verifiable(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()
    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    report = tmp_path / "accuracy_report.md"

    result = write_accuracy_report(
        report,
        gate_decision=decision,
        model_comparison_path=comparison,
    )

    payload = report.read_text("utf-8")

    assert "# B2 Accuracy Report" in payload
    assert f"**{decision['gate_status']}**" in payload
    assert "Percentage-point drop" in payload
    assert "Relative drop" in payload
    assert result["sha256"] == accuracy_report_sha256(report)

    verified = verify_accuracy_report(
        report,
        gate_decision=decision,
        model_comparison_path=comparison,
    )

    assert verified["valid"] is True
    assert verified["sha256"] == result["sha256"]


def test_accuracy_report_is_byte_deterministic_across_directories(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()

    left_csv = _write_comparison(
        left,
        teacher,
        student,
    )
    right_csv = _write_comparison(
        right,
        teacher,
        student,
    )

    left_report = left / "accuracy_report.md"
    right_report = right / "accuracy_report.md"

    write_accuracy_report(
        left_report,
        gate_decision=decision,
        model_comparison_path=left_csv,
    )
    write_accuracy_report(
        right_report,
        gate_decision=decision,
        model_comparison_path=right_csv,
    )

    assert left_report.read_bytes() == right_report.read_bytes()


def test_accuracy_report_refuses_existing_destination(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()
    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    report = tmp_path / "accuracy_report.md"
    report.write_bytes(b"keep-me")

    with pytest.raises(
        AccuracyReportError,
        match="destination already exists",
    ):
        write_accuracy_report(
            report,
            gate_decision=decision,
            model_comparison_path=comparison,
        )

    assert report.read_bytes() == b"keep-me"


def test_accuracy_report_rejects_tampered_comparison_csv(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()
    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    comparison.write_text(
        comparison.read_text("utf-8") + "tampered\n",
        encoding="utf-8",
        newline="\n",
    )

    report = tmp_path / "accuracy_report.md"

    with pytest.raises(
        AccuracyReportError,
        match="model comparison verification failed",
    ):
        write_accuracy_report(
            report,
            gate_decision=decision,
            model_comparison_path=comparison,
        )

    assert not report.exists()


def test_accuracy_report_rejects_gate_identity_tamper(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()
    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    tampered = copy.deepcopy(decision)
    tampered["case_set_digest"] = "f" * 64

    report = tmp_path / "accuracy_report.md"

    with pytest.raises(
        AccuracyReportError,
        match="case_set_digest does not match comparison",
    ):
        write_accuracy_report(
            report,
            gate_decision=tampered,
            model_comparison_path=comparison,
        )

    assert not report.exists()


def test_accuracy_report_verifier_rejects_modified_report(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()
    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    report = tmp_path / "accuracy_report.md"

    write_accuracy_report(
        report,
        gate_decision=decision,
        model_comparison_path=comparison,
    )

    report.write_text(
        report.read_text("utf-8").replace(
            "# B2 Accuracy Report",
            "# Modified Accuracy Report",
        ),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(
        AccuracyReportError,
        match="does not match gate decision",
    ):
        verify_accuracy_report(
            report,
            gate_decision=decision,
            model_comparison_path=comparison,
        )

def test_accuracy_report_rejects_tampered_metric_check(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()
    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    tampered = copy.deepcopy(decision)

    metric_check = next(
        check
        for check in tampered["checks"]
        if check["name"] != "schema_validity"
    )
    metric_check["absolute_drop"] = 0.123

    report = tmp_path / "accuracy_report.md"

    with pytest.raises(
        AccuracyReportError,
        match="does not match comparison",
    ):
        write_accuracy_report(
            report,
            gate_decision=tampered,
            model_comparison_path=comparison,
        )

    assert not report.exists()


def test_accuracy_report_rejects_missing_metric_check(
    tmp_path,
) -> None:
    teacher, student, decision = _evidence()
    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    tampered = copy.deepcopy(decision)

    metric_name = next(
        check["name"]
        for check in tampered["checks"]
        if check["name"] != "schema_validity"
    )

    tampered["checks"] = [
        check
        for check in tampered["checks"]
        if check["name"] != metric_name
    ]

    report = tmp_path / "accuracy_report.md"

    with pytest.raises(
        AccuracyReportError,
        match="does not contain every metric check",
    ):
        write_accuracy_report(
            report,
            gate_decision=tampered,
            model_comparison_path=comparison,
        )

    assert not report.exists()


def test_accuracy_report_renders_zero_teacher_relative_drop_as_na(
    tmp_path,
) -> None:
    teacher, student, _ = _evidence()

    metric = next(iter(teacher["metrics"]))
    teacher["metrics"][metric] = 0.0
    student["metrics"][metric] = 0.0

    from challenge.benchmark.tests.test_gate_decision import (
        _policy_manifest,
    )

    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher["policy_manifest_sha256"] = policy_sha
    student["policy_manifest_sha256"] = policy_sha

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    report = tmp_path / "accuracy_report.md"

    write_accuracy_report(
        report,
        gate_decision=decision,
        model_comparison_path=comparison,
    )

    text = report.read_text("utf-8")

    row = next(
        line
        for line in text.splitlines()
        if line.startswith(f"| {metric} |")
    )

    assert "N/A" in row


def test_accuracy_report_preserves_fail_gate_status(
    tmp_path,
) -> None:
    teacher, student, _ = _evidence()

    metric = next(iter(student["metrics"]))
    student["metrics"][metric] = 0.0

    from challenge.benchmark.tests.test_gate_decision import (
        _policy_manifest,
    )

    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher["policy_manifest_sha256"] = policy_sha
    student["policy_manifest_sha256"] = policy_sha

    decision = build_gate_decision(
        teacher,
        student,
        policy,
    )

    assert decision["gate_status"] == "FAIL"

    comparison = _write_comparison(
        tmp_path,
        teacher,
        student,
    )

    report = tmp_path / "accuracy_report.md"

    result = write_accuracy_report(
        report,
        gate_decision=decision,
        model_comparison_path=comparison,
    )

    assert result["gate_status"] == "FAIL"
    assert "Gate status: **FAIL**" in report.read_text("utf-8")
