"""Verified A3 candidate identity adapter for B2 Student evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from challenge.distillation.candidate_handoff import (
    verify_candidate_handoff,
)


class StudentCandidateError(ValueError):
    """Raised when B2 cannot trust an A3 Student candidate handoff."""


def verify_student_candidate(
    package_directory: str | Path,
) -> dict[str, Any]:
    """Return B2 evaluation identity from a verified A3 handoff."""

    try:
        verification = verify_candidate_handoff(
            package_directory
        )
    except (OSError, ValueError) as error:
        raise StudentCandidateError(
            f"cannot verify A3 candidate handoff: {error}"
        ) from error

    if verification.get("valid") is not True:
        raise StudentCandidateError(
            "A3 candidate handoff verification did not succeed"
        )

    identity = verification.get("candidate_identity")

    if not isinstance(identity, dict):
        raise StudentCandidateError(
            "verified A3 candidate has no candidate_identity"
        )

    required = (
        "model_id",
        "config_id",
        "weights_sha256",
        "dataset_version",
    )

    for field in required:
        value = identity.get(field)

        if not isinstance(value, str) or not value.strip():
            raise StudentCandidateError(
                f"verified A3 candidate requires {field}"
            )

    if verification.get("weights_sha256") != identity["weights_sha256"]:
        raise StudentCandidateError(
            "verified candidate weights SHA256 does not match identity"
        )

    return {
        "model_id": identity["model_id"],
        "config_id": identity["config_id"],
        "weights_sha256": identity["weights_sha256"],
        "dataset_version": identity["dataset_version"],
        "candidate_git_sha": identity["git_sha"],
        "handoff_manifest_sha256": verification[
            "manifest_sha256"
        ],
        "release_manifest_sha256": identity[
            "release_manifest_sha256"
        ],
        "a3_view_manifest_sha256": identity[
            "a3_view_manifest_sha256"
        ],
    }