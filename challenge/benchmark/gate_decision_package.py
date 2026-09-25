"""Atomic package writer for B2 gate decisions."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .gate_decision import build_gate_decision
from .gate_decision_artifact import (
    gate_decision_artifact_sha256,
    write_gate_decision_artifact,
)
from .policy_manifest import policy_manifest_sha256


class GateDecisionPackageError(ValueError):
    """Raised when a gate decision package cannot be published safely."""


def write_gate_decision_package(
    destination: str | Path,
    *,
    teacher_evaluation: Mapping[str, Any],
    student_evaluation: Mapping[str, Any],
    policy_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    target = Path(destination)
    staging = target.with_name(f".{target.name}.tmp")

    if target.exists():
        raise GateDecisionPackageError(
            f"destination already exists: {target}"
        )

    if staging.exists():
        raise GateDecisionPackageError(
            f"staging directory already exists: {staging}"
        )

    if not target.parent.exists():
        raise GateDecisionPackageError(
            f"destination parent does not exist: {target.parent}"
        )

    teacher_sha = _canonical_mapping_sha256(
        teacher_evaluation
    )
    student_sha = _canonical_mapping_sha256(
        student_evaluation
    )
    policy_sha = policy_manifest_sha256(
        policy_manifest
    )

    try:
        staging.mkdir()

        decision_result = write_gate_decision_artifact(
            staging / "gate_decision.json",
            teacher_evaluation=teacher_evaluation,
            student_evaluation=student_evaluation,
            policy_manifest=policy_manifest,
        )

        manifest = {
            "schema_version": "1.0",
            "package_type": "b2_gate_decision",
            "gate_status": decision_result["gate_status"],
            "files": {
                "gate_decision.json": {
                    "sha256": decision_result["sha256"],
                },
            },
            "evidence": {
                "teacher_evaluation_sha256": teacher_sha,
                "student_evaluation_sha256": student_sha,
                "policy_manifest_sha256": policy_sha,
            },
        }

        manifest_path = staging / "manifest.json"
        manifest_path.write_bytes(
            _canonical_json_bytes(manifest)
        )

        decision_sha = gate_decision_artifact_sha256(
            staging / "gate_decision.json"
        )
        if decision_sha != decision_result["sha256"]:
            raise GateDecisionPackageError(
                "gate decision checksum changed during packaging"
            )

        manifest_sha = hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest()

        staging.replace(target)

    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "directory": target,
        "gate_status": decision_result["gate_status"],
        "gate_decision_sha256": decision_result["sha256"],
        "manifest_sha256": manifest_sha,
        "teacher_evaluation_sha256": teacher_sha,
        "student_evaluation_sha256": student_sha,
        "policy_manifest_sha256": policy_sha,
    }

def verify_gate_decision_package(
    directory: str | Path,
) -> dict[str, Any]:
    root = Path(directory)

    if not root.is_dir():
        raise GateDecisionPackageError(
            f"gate decision package is not a directory: {root}"
        )

    expected_files = {
        "gate_decision.json",
        "manifest.json",
    }
    actual_files = {
        path.name
        for path in root.iterdir()
        if path.is_file()
    }

    if actual_files != expected_files:
        raise GateDecisionPackageError(
            "gate decision package file set does not match contract"
        )

    if any(path.is_symlink() for path in root.iterdir()):
        raise GateDecisionPackageError(
            "gate decision package must not contain symlinks"
        )

    manifest_path = root / "manifest.json"
    decision_path = root / "gate_decision.json"

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        decision = json.loads(
            decision_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GateDecisionPackageError(
            "gate decision package contains unreadable JSON"
        ) from error

    if not isinstance(manifest, Mapping):
        raise GateDecisionPackageError(
            "gate decision manifest must be an object"
        )

    if not isinstance(decision, Mapping):
        raise GateDecisionPackageError(
            "gate decision must be an object"
        )

    if manifest.get("schema_version") != "1.0":
        raise GateDecisionPackageError(
            "unsupported gate decision package schema"
        )

    if manifest.get("package_type") != "b2_gate_decision":
        raise GateDecisionPackageError(
            "invalid gate decision package type"
        )

    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise GateDecisionPackageError(
            "gate decision manifest files must be an object"
        )

    decision_entry = files.get("gate_decision.json")
    if not isinstance(decision_entry, Mapping):
        raise GateDecisionPackageError(
            "gate decision manifest is missing file evidence"
        )

    expected_decision_sha = decision_entry.get("sha256")
    actual_decision_sha = hashlib.sha256(
        decision_path.read_bytes()
    ).hexdigest()

    if expected_decision_sha != actual_decision_sha:
        raise GateDecisionPackageError(
            "gate decision checksum does not match manifest"
        )

    if manifest.get("gate_status") != decision.get("gate_status"):
        raise GateDecisionPackageError(
            "gate status does not match decision artifact"
        )

    evidence = manifest.get("evidence")
    if not isinstance(evidence, Mapping):
        raise GateDecisionPackageError(
            "gate decision manifest evidence must be an object"
        )

    required_evidence = {
        "teacher_evaluation_sha256",
        "student_evaluation_sha256",
        "policy_manifest_sha256",
    }

    if set(evidence) != required_evidence:
        raise GateDecisionPackageError(
            "gate decision manifest evidence does not match contract"
        )

    for name in required_evidence:
        value = evidence[name]
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(
                character not in "0123456789abcdef"
                for character in value
            )
        ):
            raise GateDecisionPackageError(
                f"invalid evidence checksum: {name}"
            )

    if (
        decision.get("policy_manifest_sha256")
        != evidence["policy_manifest_sha256"]
    ):
        raise GateDecisionPackageError(
            "decision policy binding does not match package evidence"
        )

    return {
        "valid": True,
        "gate_status": decision["gate_status"],
        "gate_decision_sha256": actual_decision_sha,
        "manifest_sha256": hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest(),
        "teacher_evaluation_sha256": evidence[
            "teacher_evaluation_sha256"
        ],
        "student_evaluation_sha256": evidence[
            "student_evaluation_sha256"
        ],
        "policy_manifest_sha256": evidence[
            "policy_manifest_sha256"
        ],
    }

def verify_gate_decision_evidence(
    directory: str | Path,
    *,
    teacher_evaluation: Mapping[str, Any],
    student_evaluation: Mapping[str, Any],
    policy_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    verified = verify_gate_decision_package(directory)

    teacher_sha = _canonical_mapping_sha256(
        teacher_evaluation
    )
    student_sha = _canonical_mapping_sha256(
        student_evaluation
    )
    policy_sha = policy_manifest_sha256(
        policy_manifest
    )

    if (
        teacher_sha
        != verified["teacher_evaluation_sha256"]
    ):
        raise GateDecisionPackageError(
            "Teacher evaluation does not match package evidence"
        )

    if (
        student_sha
        != verified["student_evaluation_sha256"]
    ):
        raise GateDecisionPackageError(
            "Student evaluation does not match package evidence"
        )

    if (
        policy_sha
        != verified["policy_manifest_sha256"]
    ):
        raise GateDecisionPackageError(
            "policy manifest does not match package evidence"
        )

    # Re-run the policy-bound decision from the supplied evidence.
    expected_decision = build_gate_decision(
        teacher_evaluation,
        student_evaluation,
        policy_manifest,
    )

    decision_path = Path(directory) / "gate_decision.json"

    try:
        stored_decision = json.loads(
            decision_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GateDecisionPackageError(
            "gate decision artifact is unreadable"
        ) from error

    if stored_decision != expected_decision:
        raise GateDecisionPackageError(
            "stored gate decision does not match supplied evidence"
        )

    return verified

def _canonical_mapping_sha256(
    value: Mapping[str, Any],
) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(value)
    ).hexdigest()


def _canonical_json_bytes(
    value: Mapping[str, Any],
) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


__all__ = [
    "GateDecisionPackageError",
    "verify_gate_decision_evidence",
    "verify_gate_decision_package",
    "write_gate_decision_package",
]