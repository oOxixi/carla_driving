from __future__ import annotations

import hashlib
import json

import pytest

from challenge.benchmark.gate_decision import GateDecisionError
from challenge.benchmark.gate_decision_artifact import (
    GateDecisionArtifactError,
    gate_decision_artifact_sha256,
    write_gate_decision_artifact,
)
from challenge.benchmark.policy_manifest import (
    policy_manifest_sha256,
)
from challenge.benchmark.tests.test_gate_decision import (
    _evaluation,
    _policy_manifest,
)


def _evidence() -> tuple[dict, dict, dict]:
    policy = _policy_manifest()
    policy_sha = policy_manifest_sha256(policy)

    teacher = _evaluation(
        "teacher",
        policy_sha=policy_sha,
        value=0.95,
    )
    student = _evaluation(
        "student",
        policy_sha=policy_sha,
        value=0.95,
    )

    return teacher, student, policy


def test_gate_decision_artifact_sha_matches_exact_disk_bytes(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decision.json"

    result = write_gate_decision_artifact(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    assert destination.is_file()

    raw = destination.read_bytes()
    expected_sha = hashlib.sha256(raw).hexdigest()

    assert result["sha256"] == expected_sha
    assert gate_decision_artifact_sha256(
        destination
    ) == expected_sha

    # Canonical artifact is newline-terminated JSON.
    assert raw.endswith(b"\n")

    parsed = json.loads(raw)
    assert parsed["gate_status"] == "PASS"
    assert result["gate_status"] == "PASS"


def test_gate_decision_artifact_refuses_existing_destination(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decision.json"
    original = b"do-not-overwrite\n"
    destination.write_bytes(original)

    with pytest.raises(
        GateDecisionArtifactError,
        match="destination already exists",
    ):
        write_gate_decision_artifact(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )

    assert destination.read_bytes() == original


def test_invalid_evidence_leaves_no_destination_or_temp_file(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decision.json"
    temporary = tmp_path / ".gate_decision.json.tmp"

    student["case_set_digest"] = "9" * 64

    with pytest.raises(GateDecisionError):
        write_gate_decision_artifact(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )

    assert not destination.exists()
    assert not temporary.exists()

def test_gate_decision_artifact_is_deterministic_across_destinations(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()

    first = first_dir / "gate_decision.json"
    second = second_dir / "gate_decision.json"

    first_result = write_gate_decision_artifact(
        first,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )
    second_result = write_gate_decision_artifact(
        second,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    assert first.read_bytes() == second.read_bytes()
    assert first_result["sha256"] == second_result["sha256"]
    assert (
        gate_decision_artifact_sha256(first)
        == gate_decision_artifact_sha256(second)
    )