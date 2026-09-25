"""Tests for atomic B2 evidence publication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from challenge.benchmark.gate_decision_package import (
    write_gate_decision_package,
)
from challenge.benchmark.publication import (
    PublicationError,
    publish_b2_publication,
    verify_b2_publication,
)
from challenge.benchmark.policy_manifest import (
    policy_manifest_sha256,
)

def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes(
    path: Path,
    payload: bytes,
) -> str:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def _write_json(
    path: Path,
    value: Any,
) -> str:
    return _write_bytes(
        path,
        _canonical_json_bytes(value),
    )


def _make_evidence_bundle(
    root: Path,
    *,
    role: str,
    benchmark_manifest: dict[str, Any],
    policy_manifest: dict[str, Any],
    case_set_digest: str,
) -> tuple[Path, dict[str, Any]]:
    bundle = root / role
    bundle.mkdir(
        parents=True,
        exist_ok=True,
    )

    benchmark_sha = _write_json(
        bundle / "benchmark_manifest.json",
        benchmark_manifest,
    )

    _write_json(
        bundle / "policy_manifest.json",
        policy_manifest,
    )

    policy_sha = policy_manifest_sha256(
        policy_manifest
    )

    predictions_name = f"{role}_predictions.jsonl"

    prediction_record = {
        "sample_id": "sample-001",
        "status": "OK",
        "prediction": {
            "behavior": "STOP",
        },
    }

    predictions_payload = _canonical_json_bytes(
        prediction_record
    )

    predictions_sha = _write_bytes(
        bundle / predictions_name,
        predictions_payload,
    )

    (
        bundle / "predictions.sha256"
    ).write_text(
        f"{predictions_sha}  {predictions_name}\n",
        encoding="ascii",
        newline="\n",
    )

    evaluation = {
    "schema_version": "1.0",
    "evaluation_id": f"b2-test-{role}-evaluation",
    "evaluation_role": role,
    "benchmark_manifest_sha256": benchmark_sha,
    "policy_manifest_sha256": policy_sha,
    "case_set_digest": case_set_digest,
    "evaluator_git_sha": "a" * 40,
    "sample_count": 1,
    "predictions_sha256": predictions_sha,
    "schema_validity": 1.0,
    "metrics": {
        "behavior_accuracy": 1.0,
        "target_pointer_accuracy": 1.0,
        "target_lane_accuracy": 1.0,
        "completion_accuracy": 1.0,
        "plan_sequence_accuracy": 1.0,
        "safety_critical_behavior_recall": 1.0,
    },
}

    _write_json(
        bundle / f"{role}_evaluation.json",
        evaluation,
    )

    return bundle, evaluation


def _make_gate_package(
    root: Path,
    *,
    teacher_evaluation: dict[str, Any],
    student_evaluation: dict[str, Any],
    policy_manifest: dict[str, Any],
) -> Path:
    package = root / "gate"

    write_gate_decision_package(
        package,
        teacher_evaluation=teacher_evaluation,
        student_evaluation=student_evaluation,
        policy_manifest=policy_manifest,
    )

    return package


def _make_complete_sources(
    root: Path,
) -> tuple[Path, Path, Path]:
    benchmark_manifest = {
        "schema_version": "1.0",
        "benchmark_id": "b2-test-benchmark",
        "case_set_digest": "c" * 64,
    }

    policy_manifest = {
    "schema_version": "1.0",
    "policy_id": "b2-test-policy",
    "gate": {
        "schema_validity_required": 1.0,
        "max_core_drop": 0.05,
        "max_safety_drop": 0.05,
    },
}

    teacher, teacher_evaluation = (
        _make_evidence_bundle(
            root,
            role="teacher",
            benchmark_manifest=benchmark_manifest,
            policy_manifest=policy_manifest,
            case_set_digest="c" * 64,
        )
    )

    student, student_evaluation = (
        _make_evidence_bundle(
            root,
            role="student",
            benchmark_manifest=benchmark_manifest,
            policy_manifest=policy_manifest,
            case_set_digest="c" * 64,
        )
    )

    gate = _make_gate_package(
        root,
        teacher_evaluation=teacher_evaluation,
        student_evaluation=student_evaluation,
        policy_manifest=policy_manifest,
    )

    return teacher, student, gate


def test_publish_and_verify_publication(
    tmp_path: Path,
) -> None:
    teacher, student, gate = _make_complete_sources(
        tmp_path / "sources"
    )

    destination = tmp_path / "publication"

    result = publish_b2_publication(
        destination,
        teacher_bundle=teacher,
        student_bundle=student,
        gate_decision_package=gate,
    )

    assert result["valid"] is True
    assert result["directory"] == str(destination)

    assert (
        destination
        / "raw_results"
        / "teacher"
        / "teacher_evaluation.json"
    ).is_file()

    assert (
        destination
        / "raw_results"
        / "student"
        / "student_evaluation.json"
    ).is_file()

    assert (
        destination
        / "gate_decisions"
    ).is_dir()

    verified = verify_b2_publication(destination)

    assert verified["valid"] is True
    assert verified["gate_status"] == "PASS"


def test_publication_rejects_existing_destination(
    tmp_path: Path,
) -> None:
    teacher, student, gate = _make_complete_sources(
        tmp_path / "sources"
    )

    destination = tmp_path / "publication"
    destination.mkdir()

    with pytest.raises(
        PublicationError,
        match="destination already exists",
    ):
        publish_b2_publication(
            destination,
            teacher_bundle=teacher,
            student_bundle=student,
            gate_decision_package=gate,
        )


def test_publication_rejects_extra_teacher_file(
    tmp_path: Path,
) -> None:
    teacher, student, gate = _make_complete_sources(
        tmp_path / "sources"
    )

    (
        teacher / "unexpected.txt"
    ).write_text(
        "must be rejected",
        encoding="utf-8",
    )

    with pytest.raises(
        PublicationError,
        match="contents do not match contract",
    ):
        publish_b2_publication(
            tmp_path / "publication",
            teacher_bundle=teacher,
            student_bundle=student,
            gate_decision_package=gate,
        )


def test_publication_rejects_prediction_tampering(
    tmp_path: Path,
) -> None:
    teacher, student, gate = _make_complete_sources(
        tmp_path / "sources"
    )

    with (
        teacher / "teacher_predictions.jsonl"
    ).open(
        "ab"
    ) as handle:
        handle.write(b'{"tampered":true}\n')

    with pytest.raises(
        PublicationError,
        match="prediction checksum does not match",
    ):
        publish_b2_publication(
            tmp_path / "publication",
            teacher_bundle=teacher,
            student_bundle=student,
            gate_decision_package=gate,
        )


def test_verify_rejects_teacher_student_case_mismatch(
    tmp_path: Path,
) -> None:
    teacher, student, gate = _make_complete_sources(
        tmp_path / "sources"
    )

    destination = tmp_path / "publication"

    publish_b2_publication(
        destination,
        teacher_bundle=teacher,
        student_bundle=student,
        gate_decision_package=gate,
    )

    evaluation_path = (
        destination
        / "raw_results"
        / "student"
        / "student_evaluation.json"
    )

    evaluation = json.loads(
        evaluation_path.read_text(
            encoding="utf-8"
        )
    )

    evaluation["case_set_digest"] = "d" * 64

    _write_json(
        evaluation_path,
        evaluation,
    )

    with pytest.raises(
        PublicationError,
        match="Teacher and Student case_set_digest",
    ):
        verify_b2_publication(destination)


def test_verify_rejects_policy_manifest_tampering(
    tmp_path: Path,
) -> None:
    teacher, student, gate = _make_complete_sources(
        tmp_path / "sources"
    )

    destination = tmp_path / "publication"

    publish_b2_publication(
        destination,
        teacher_bundle=teacher,
        student_bundle=student,
        gate_decision_package=gate,
    )

    policy_path = (
        destination
        / "raw_results"
        / "teacher"
        / "policy_manifest.json"
    )

    policy = json.loads(
        policy_path.read_text(
            encoding="utf-8"
        )
    )

    policy["tampered"] = True

    _write_json(
        policy_path,
        policy,
    )

    with pytest.raises(
        PublicationError,
        match="policy binding does not match",
    ):
        verify_b2_publication(destination)


def test_publication_cleans_staging_on_failure(
    tmp_path: Path,
) -> None:
    teacher, student, gate = _make_complete_sources(
        tmp_path / "sources"
    )

    destination = tmp_path / "publication"
    staging = tmp_path / ".publication.tmp"

    student_evaluation_path = (
        student / "student_evaluation.json"
    )

    student_evaluation = json.loads(
        student_evaluation_path.read_text(
            encoding="utf-8"
        )
    )

    student_evaluation[
        "benchmark_manifest_sha256"
    ] = "0" * 64

    _write_json(
        student_evaluation_path,
        student_evaluation,
    )

    with pytest.raises(PublicationError):
        publish_b2_publication(
            destination,
            teacher_bundle=teacher,
            student_bundle=student,
            gate_decision_package=gate,
        )

    assert not destination.exists()
    assert not staging.exists()