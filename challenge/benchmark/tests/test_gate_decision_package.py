from __future__ import annotations

import hashlib
import json

import pytest

from challenge.benchmark.gate_decision import GateDecisionError
from challenge.benchmark.gate_decision_package import (
    GateDecisionPackageError,
    write_gate_decision_package,
)
from challenge.benchmark.policy_manifest import (
    policy_manifest_sha256,
)
from challenge.benchmark.tests.test_gate_decision import (
    _evaluation,
    _policy_manifest,
)

from challenge.benchmark.gate_decision_package import (
    GateDecisionPackageError,
    verify_gate_decision_evidence,
    verify_gate_decision_package,
    write_gate_decision_package,
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


def _canonical_sha256(value: dict) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def test_gate_decision_package_publishes_bound_manifest(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    result = write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    assert destination.is_dir()

    decision_path = destination / "gate_decision.json"
    manifest_path = destination / "manifest.json"

    assert decision_path.is_file()
    assert manifest_path.is_file()

    decision_sha = hashlib.sha256(
        decision_path.read_bytes()
    ).hexdigest()
    manifest_sha = hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()

    assert result["gate_decision_sha256"] == decision_sha
    assert result["manifest_sha256"] == manifest_sha

    manifest = json.loads(manifest_path.read_bytes())

    assert manifest["package_type"] == "b2_gate_decision"
    assert manifest["gate_status"] == "PASS"

    assert manifest["files"] == {
        "gate_decision.json": {
            "sha256": decision_sha,
        },
    }

    assert manifest["evidence"] == {
        "teacher_evaluation_sha256": _canonical_sha256(
            teacher
        ),
        "student_evaluation_sha256": _canonical_sha256(
            student
        ),
        "policy_manifest_sha256": policy_manifest_sha256(
            policy
        ),
    }


def test_gate_decision_package_refuses_existing_destination(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"
    destination.mkdir()

    sentinel = destination / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(
        GateDecisionPackageError,
        match="destination already exists",
    ):
        write_gate_decision_package(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_invalid_evidence_leaves_no_package_or_staging_directory(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()

    destination = tmp_path / "gate_decisions"
    staging = tmp_path / ".gate_decisions.tmp"

    student["case_set_digest"] = "9" * 64

    with pytest.raises(GateDecisionError):
        write_gate_decision_package(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )

    assert not destination.exists()
    assert not staging.exists()


def test_gate_decision_package_refuses_existing_staging_directory(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()

    destination = tmp_path / "gate_decisions"
    staging = tmp_path / ".gate_decisions.tmp"
    staging.mkdir()

    sentinel = staging / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(
        GateDecisionPackageError,
        match="staging directory already exists",
    ):
        write_gate_decision_package(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )

    assert not destination.exists()
    assert sentinel.read_text(encoding="utf-8") == "keep"

def test_gate_decision_package_verifier_accepts_valid_package(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    written = write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    verified = verify_gate_decision_package(destination)

    assert verified["valid"] is True
    assert verified["gate_status"] == "PASS"
    assert (
        verified["gate_decision_sha256"]
        == written["gate_decision_sha256"]
    )
    assert (
        verified["manifest_sha256"]
        == written["manifest_sha256"]
    )
    assert (
        verified["teacher_evaluation_sha256"]
        == written["teacher_evaluation_sha256"]
    )
    assert (
        verified["student_evaluation_sha256"]
        == written["student_evaluation_sha256"]
    )
    assert (
        verified["policy_manifest_sha256"]
        == written["policy_manifest_sha256"]
    )


def test_gate_decision_package_verifier_rejects_tampered_decision(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    decision_path = destination / "gate_decision.json"
    decision = json.loads(
        decision_path.read_text(encoding="utf-8")
    )
    decision["gate_status"] = "FAIL"
    decision_path.write_text(
        json.dumps(
            decision,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        GateDecisionPackageError,
        match="checksum does not match",
    ):
        verify_gate_decision_package(destination)


def test_gate_decision_package_verifier_rejects_extra_file(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    (destination / "unexpected.txt").write_text(
        "unexpected",
        encoding="utf-8",
    )

    with pytest.raises(
        GateDecisionPackageError,
        match="file set does not match contract",
    ):
        verify_gate_decision_package(destination)


def test_gate_decision_package_verifier_rejects_policy_binding_tamper(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    manifest_path = destination / "manifest.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    manifest["evidence"]["policy_manifest_sha256"] = "9" * 64

    manifest_path.write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        GateDecisionPackageError,
        match="policy binding does not match",
    ):
        verify_gate_decision_package(destination)

def test_gate_decision_evidence_verifier_accepts_exact_evidence(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    written = write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    verified = verify_gate_decision_evidence(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    assert verified["valid"] is True
    assert verified["gate_status"] == "PASS"
    assert (
        verified["gate_decision_sha256"]
        == written["gate_decision_sha256"]
    )
    assert (
        verified["manifest_sha256"]
        == written["manifest_sha256"]
    )


def test_gate_decision_evidence_verifier_rejects_wrong_teacher(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    teacher["evaluation_id"] = "wrong-teacher"

    with pytest.raises(
        GateDecisionPackageError,
        match="Teacher evaluation does not match package evidence",
    ):
        verify_gate_decision_evidence(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )


def test_gate_decision_evidence_verifier_rejects_wrong_student(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    student["evaluation_id"] = "wrong-student"

    with pytest.raises(
        GateDecisionPackageError,
        match="Student evaluation does not match package evidence",
    ):
        verify_gate_decision_evidence(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )


def test_gate_decision_evidence_verifier_rejects_wrong_policy(
    tmp_path,
) -> None:
    teacher, student, policy = _evidence()
    destination = tmp_path / "gate_decisions"

    write_gate_decision_package(
        destination,
        teacher_evaluation=teacher,
        student_evaluation=student,
        policy_manifest=policy,
    )

    policy["policy_version"] = "tampered-policy"

    with pytest.raises(
        GateDecisionPackageError,
        match="policy manifest does not match package evidence",
    ):
        verify_gate_decision_evidence(
            destination,
            teacher_evaluation=teacher,
            student_evaluation=student,
            policy_manifest=policy,
        )